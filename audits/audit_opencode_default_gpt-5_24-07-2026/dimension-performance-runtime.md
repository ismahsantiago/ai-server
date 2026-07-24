# Auditoría de rendimiento y serving local

## Alcance y método

Revisión independiente y pre-remediación de los perfiles de CPU/RAM, catálogo
de modelos, plantillas de `llama.cpp`, ciclo de vida del servicio, resolución
de rutas y scripts de benchmark. La revisión fue estática: no se arrancó
Docker, no se descargó ni cargó ningún modelo y no se interpretó un `GO` del
generador como evidencia de ejecución real.

La compatibilidad efectiva depende, como mínimo, del archivo GGUF concreto, su
cuantización y tamaño, la versión de `llama.cpp`, la arquitectura del host y la
memoria disponible. Esos datos no están fijados en el contrato actual, por lo
que las conclusiones de capacidad se limitan a lo demostrable por código y
configuración.

## Fortalezas verificadas

- Los tres perfiles imponen límites explícitos de memoria y CPU
  (`profiles/medium-fast.json:5-10`, `profiles/medium.json:5-10`,
  `profiles/good.json:5-10`), lo que acota el consumo del contenedor mejor que
  un servicio sin límites.
- La plantilla activa un endpoint de salud, `--metrics`, batching continuo,
  filesystem de solo lectura, `no-new-privileges` y un `tmpfs` acotado
  (`templates/chat/docker-compose.yml.j2:22-31`,
  `templates/chat/docker-compose.yml.j2:41-51`).
- Hay perfiles diferenciados de contexto, batch, hilos y límite de predicción,
  y el perfil `good` emite una advertencia de presión de memoria
  (`ai_server_generator/cli.py:168-174`).
- El preflight generado comprueba la presencia de los artefactos mínimos y
  conserva `localhost` como postura predeterminada
  (`templates/chat/scripts/validate_host.sh.j2:7-14`,
  `templates/chat/scripts/validate_host.sh.j2:25-35`).
- Los scripts shell revisados pasan análisis sintáctico con `bash -n`.

## Hallazgos

### PERF-001 — Alta — La ruta del modelo del host no coincide con el volumen del workspace generado

**Evidencia:** el preset resuelve por defecto a
`./models/<alias>.gguf` (`ai_server_generator/presets.py:17-20`) y el wizard
comprueba ese archivo relativo al directorio desde el que se ejecuta
(`ai_server_generator/cli.py:288-295`). Sin embargo, el Compose generado monta
`./models` relativo al propio workspace generado
(`templates/chat/docker-compose.yml.j2:36-38`). El generador no copia ni enlaza
el GGUF. Además, una ruta absoluta se conserva como ruta de contenedor
(`ai_server_generator/render.py:56-60`), aunque Compose nunca monta ese
directorio absoluto.

**Impacto concreto:** el flujo documentado
`models/<preset>.gguf -> generated/... -> start` puede superar el preflight del
wizard y después fallar al iniciar porque `/models/<preset>.gguf` no existe
dentro del contenedor. Las rutas absolutas personalizadas también quedan
inaccesibles. Con `restart: unless-stopped`, el fallo puede convertirse en un
bucle de reinicios y consumo innecesario de CPU/I/O.

**Remediación específica:** separar `host_model_path` de
`container_model_path`; resolver y validar el archivo real antes de generar;
emitir un bind mount de archivo explícito, por ejemplo
`${MODEL_HOST_PATH}:/models/model.gguf:ro`, y pasar
`--model /models/model.gguf`. Rechazar archivos ausentes/no regulares y añadir
pruebas para ruta del repositorio, ruta absoluta y ruta con espacios.

### PERF-002 — Alta — La matriz declara `GO` sin un contrato de cuantización ni ajuste real a RAM

**Evidencia:** los presets sólo almacenan alias, etiquetas y texto libre de
memoria (`ai_server_generator/presets.py:6-15`,
`ai_server_generator/presets.py:22-59`). La matriz imprime `Decision: GO` una
vez que la combinación nominal es válida, sin inspeccionar el GGUF, tamaño,
cuantización, RAM libre ni CPU (`ai_server_generator/cli.py:177-218`). Los
tests convierten incluso `medium-fast` y `medium` en `GO` obligatorio para
todos los presets (`tests/test_cli.py:129-150`). La comprobación estática
reprodujo `GO` para las 15 combinaciones preset/perfil, incluidas
Devstral/6 GB y Phi-4/6 GB.

El catálogo oficial identifica Devstral Small 2507 como un modelo de 24B, no
como una carga que pueda presumirse compatible con 6–8 GB:
<https://huggingface.co/mistralai/Devstral-Small-2507>. El GGUF oficial de
Phi-4 muestra que sólo el peso Q4 ocupa aproximadamente 8.0–9.3 GB, antes del
KV cache y buffers:
<https://huggingface.co/microsoft/phi-4-gguf>. El alias
`qwen3-coder-7b` tampoco queda ligado a un repositorio/revisión oficial
concreto; la colección oficial debe ser la fuente de identidad:
<https://huggingface.co/collections/Qwen/qwen3-coder>.

**Impacto concreto:** un usuario puede tratar `GO` y la guía “6–8 GB” como
validación de ejecución, seleccionar un GGUF demasiado grande y sufrir OOM,
swap intenso, latencia extrema o reinicios. El resultado varía silenciosamente
según qué archivo haya sido renombrado al alias esperado.

**Remediación específica:** convertir cada preset en un contrato versionado
con repositorio, revisión, nombre de archivo, arquitectura, cuantización,
bytes, SHA-256, chat template requerido, RAM mínima y RAM recomendada por
contexto. Calcular `modelo + KV cache + buffers + reserva del host`; devolver
`NO-GO` cuando falte metadata o no exista margen (recomendado: al menos
2–3 GB fuera del contenedor en un host de 12 GB). Separar “generable” de
“verificado en este host” y corregir tests para no equipararlos.

### PERF-003 — Alta — El benchmark generado no mide latencia ni memoria

**Evidencia:** el script generado inicializa latencia y memoria como
`placeholder` (`templates/chat/scripts/smoke_benchmark.sh.j2:10-12`). `curl`
sólo recoge el código HTTP; ante 200 sustituye la latencia por el literal
`measured-via-client-timing`, sin medir tiempo alguno
(`templates/chat/scripts/smoke_benchmark.sh.j2:14-27`). `MEMORY_MB` nunca se
actualiza y se escribe directamente en el informe
(`templates/chat/scripts/smoke_benchmark.sh.j2:32-43`). El helper legacy sí
toma una instantánea de `docker stats`, pero también usa un literal para la
latencia (`scripts/smoke_benchmark.sh:12-35`).

**Impacto concreto:** los artefactos denominados “benchmark” no permiten
comparar perfiles/modelos, detectar regresiones, sostener afirmaciones de
latencia o confirmar ajuste en memoria. Un HTTP 200 con payload inválido puede
aparentar éxito, y el script termina en cero incluso sin servicio.

**Remediación específica:** hacer que la ausencia/fallo del servicio produzca
exit distinto de cero; medir `time_starttransfer` y `time_total` de `curl`,
validar JSON/contenido, capturar bytes reales de `docker stats`, y registrar
timings/tokens de `llama.cpp`. Ejecutar warm-up más varias repeticiones y
reportar p50/p95, tokens/s y pico de memoria. Grabar hash del modelo,
cuantización, configuración completa, CPU/RAM del host, digest de imagen y
versión del runtime. Usar temporales por proceso con `trap`, no rutas globales
en `/tmp`.

### PERF-004 — Alta — El arranque no espera readiness y el fallo puede reiniciarse indefinidamente

**Evidencia:** el arranque sólo ejecuta `docker compose up -d` seguido de
`docker compose ps` (`templates/chat/scripts/start_serving.sh.j2:18-19`).
El wizard ejecuta el smoke inmediatamente después de que ese script termina
(`ai_server_generator/cli.py:406-431`). Aunque existe healthcheck, su ventana
puede superar dos minutos
(`templates/chat/docker-compose.yml.j2:41-46`), y el servicio usa
`restart: unless-stopped` (`templates/chat/docker-compose.yml.j2:3-5`). No se
genera un helper de parada ni una ruta que recopile logs y desactive el
servicio al agotar la espera.

**Impacto concreto:** el happy path es sensible al tiempo de carga del modelo:
el smoke puede fallar de forma intermitente antes de readiness. Un modelo
ausente, incompatible u OOM puede entrar en reinicio permanente y degradar el
host sin entregar un diagnóstico final útil.

**Remediación específica:** arrancar con espera acotada de salud
(`docker compose up -d --wait --wait-timeout <s>` cuando la versión mínima lo
permita, o polling explícito), distinguir `starting`, `healthy` y
`unhealthy`, y ante timeout capturar `compose ps`/logs y devolver error.
Cambiar el reinicio predeterminado a `no` o a una política finita para
workstations; generar `stop.sh` con `docker compose down --timeout ...` y
documentar señales, timeout y recuperación.

### PERF-005 — Media — Runtime e imagen no están fijados, por lo que los resultados no son reproducibles

**Evidencia:** tanto el Compose generado como el legacy usan la etiqueta móvil
`ghcr.io/ggerganov/llama.cpp:server`
(`templates/chat/docker-compose.yml.j2:1-4`, `docker-compose.yml:4-7`). Los
flags de serving se fijan en la plantilla, pero no hay versión/digest ni
validación de compatibilidad de CLI. El manifest tampoco registra imagen,
digest o versión del runtime (`templates/chat/manifest.json.j2:1-28`).

**Impacto concreto:** dos generaciones idénticas pueden descargar builds
distintos, modificar rendimiento, compatibilidad de GGUF, defaults o
disponibilidad de utilidades usadas por el healthcheck. Los benchmarks no se
pueden atribuir ni repetir con precisión.

**Remediación específica:** fijar una versión probada y, para evidencia,
resolver/registrar el digest inmutable. Añadir versión de runtime y esquema de
flags al manifest; comprobar en CI que la plantilla es aceptada por esa imagen
y mantener una actualización explícita con benchmark de regresión.

## Evidencia de comandos

| Comando/comprobación | Resultado |
|---|---|
| Render estático en memoria de los 5 presets × 3 perfiles | Las 15 combinaciones resultaron nominalmente `GO`; no se escribió workspace |
| Inspección de `models/` | Sólo existe `models/README.md`; no hay GGUF para una prueba real |
| `bash -n scripts/*.sh` | exit 0 para los tres helpers legacy |
| `bash -n templates/chat/scripts/*.j2` | exit 0 para los seis scripts plantilla |
| Búsqueda de métricas en ambos benchmark scripts | No existe medición numérica de latencia en ninguno; la plantilla no invoca `docker stats` |

## Qué queda por verificar en ejecución

No se afirma éxito de serving, salud ni rendimiento real. Para cerrar la
dimensión tras remediación se necesita, en un host identificado de hasta
12 GB, ejecutar al menos dos GGUF con hash y cuantización fijados, validar
arranque/parada/fallo por modelo ausente/OOM, medir warm/cold start,
time-to-first-token, tokens/s, p50/p95 y pico de RSS/container, y repetir con
la imagen fijada. También debe confirmarse que la utilidad usada por el
healthcheck existe en esa imagen exacta.
