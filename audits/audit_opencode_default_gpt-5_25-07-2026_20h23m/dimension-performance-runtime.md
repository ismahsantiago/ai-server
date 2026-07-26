# Auditoría independiente de rendimiento y model-serving — TASK-0007

## Alcance y límite de evidencia

Esta pasada cubre únicamente el todo 4 de `TASK-0007`. Se usaron el plan aprobado, el inventario fresco de este directorio, `audits/standards/PERFORMANCE.md` y el checkout actual. No se abrieron informes de auditorías anteriores, no se modificaron fuentes, plan, estado ni workspaces generados, y no se inició un modelo ni un contenedor de serving.

Clasificación usada:

- **Evidencia estática:** código, plantillas, presets, documentación y Compose inspeccionados sin ejecutar inferencia.
- **Placeholder:** salida o artefacto que declara valores no medidos.
- **Medición runtime:** observación contra un servicio y modelo reales. No hay ninguna medición runtime válida disponible.
- **Prerequisito no disponible:** condición que impide calificar la afirmación, principalmente la ausencia de pesos `.gguf`.

## Resumen ejecutivo

Resultado: **INCOMPLETE — findings recorded**.

La ruta canónica genera un workspace estructuralmente coherente para `llama.cpp`, con límites de CPU/memoria, imagen fijada por digest, bind del modelo en modo lectura, healthcheck y espera acotada de readiness. Sin embargo, los contratos de preset siguen siendo supuestos de planificación, no contratos de artefactos de modelo verificables; el manifiesto no identifica versión ni compatibilidad de flags del runtime; y el benchmark visible no demuestra rendimiento porque registra placeholders y no identifica host/imagen/runtime de forma reproducible.

No existe un `.gguf` bajo `models/`, por lo que no es posible concluir carga, compatibilidad efectiva, memoria real, latencia, tokens por segundo, calidad ni readiness de ningún preset.

## Hallazgos

### PERF7-001 — Alto: los presets no son contratos verificables de modelo

**Evidencia:** `ai_server_generator/presets.py:6-23,33-115` declara arquitectura genérica, cuantización asumida, tamaño estimado, KV cache y buffers; `ai_server_generator/cli.py:171-201` materializa esos valores en `model_contract`; `ai_server_generator/validator.py:346-373` solo exige claves y acepta `planning-assumption-only` o `custom-artifact-unverified`; `audits/standards/PERFORMANCE.md:19-31` exige repositorio, revisión, archivo, arquitectura, cuantización, tamaño, SHA-256, chat template y RAM mínima/recomendada.

**Impacto:** un preset puede generar un workspace y producir una decisión de matriz aunque no haya un archivo concreto, hash, tamaño observado ni compatibilidad de formato que vincule el preset con el runtime.

**Clasificación:** evidencia estática; el modelo concreto es un prerequisito no disponible.

**Recomendación:** versionar un contrato por artefacto GGUF con origen, revisión, nombre de archivo, arquitectura, cuantización, bytes, SHA-256, chat template y RAM; rechazar `GO`/validación de host cuando falte metadata. Mantener separados “generable” y “verificado en este host”.

### PERF7-002 — Alto: coherencia de memoria solo nominal y no validada contra el host

**Evidencia:** los perfiles fijan `mem_limit` de `6g`, `8g` y `10g` en `profiles/medium-fast.json:5-10`, `profiles/medium.json:5-10` y `profiles/good.json:5-10`; la decisión estática calcula únicamente modelo + KV + buffer + reserva fija de 2.5 GB en `ai_server_generator/cli.py:223-247`. El inventario reporta Docker Desktop con 8,321,798,144 bytes disponibles en `audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/meta/inventory.md:50-64`. En este host, `good` solicita 10 GB y supera el límite de memoria configurado por Docker Desktop, mientras que el cálculo no lee el presupuesto real del daemon ni el consumo de otras aplicaciones.

**Impacto:** una matriz puede describir un ajuste nominal como apto aunque el host/daemon actual no pueda sostenerlo. El propio flujo solo produce `WARN` para `ornith-9b/medium` y `smollm3-3b/medium-fast`, y `NO-GO` estático para `phi-4-14b/good`; ningún resultado equivale a prueba de carga.

**Clasificación:** evidencia estática; no hay medición runtime.

**Recomendación:** obtener memoria disponible del host/daemon, calcular modelo + KV + buffers + reserva explícita según contexto/batch, y devolver `NO-GO` si no existe margen. Registrar el motivo y diferenciar límite del contenedor, presupuesto Docker Desktop y RAM total del host.

### PERF7-003 — Medio: compatibilidad del runtime no queda completamente fijada

**Evidencia:** la imagen canónica se fija por digest en `ai_server_generator/render.py:50-55` y `templates/chat/docker-compose.yml.j2:1-4`; el manifiesto solo contiene `serving_image`, sin versión semántica ni esquema de flags, y el validador comprueba únicamente igualdad con la imagen y presencia de digest en `ai_server_generator/validator.py:332-344`. `audits/standards/PERFORMANCE.md:63-72` exige registrar imagen, digest, versión y compatibilidad del esquema de flags, además de regresión al cambiar digest. La descripción del setup usa `llama.cpp` en `manifests/chat.json:1-5`, pero no registra una versión del servidor ni la revisión que define `--ctx-size`, `--batch-size`, `--n-predict`, `--metrics` y `--cont-batching` en `templates/chat/docker-compose.yml.j2:11-27`.

**Impacto:** el digest hace inmutable la imagen, pero no prueba que los flags generados sean compatibles con ella ni deja una identificación suficiente para comparar benchmarks.

**Clasificación:** evidencia estática; compatibilidad efectiva no verificada sin arrancar la imagen con un modelo.

**Recomendación:** añadir al manifiesto versión/revisión del runtime, digest, esquema de flags y resultado de una prueba de compatibilidad; exigir regresión de benchmark para cada cambio de digest.

### PERF7-004 — Medio: startup tiene timeout y diagnóstico, pero no distingue estados

**Evidencia:** el template define timeout e intervalo positivos en `templates/chat/scripts/start_serving.sh.j2:9-14`, ejecuta `compose up -d` y espera un endpoint de salud con límite en `:40-50`; en timeout captura `compose ps` y logs en `:52-55`. El healthcheck de Compose está definido en `templates/chat/docker-compose.yml.j2:37-42`. No hay lectura explícita del estado `starting`, `healthy` o `unhealthy`: el script solo repite `curl` hasta éxito o timeout. La norma exige distinguir esos estados en `audits/standards/PERFORMANCE.md:49-59`.

**Impacto:** el operador no puede distinguir un servicio aún iniciando de uno declarado unhealthy; el diagnóstico se retrasa hasta agotar el timeout. No se afirma que el script deje contenedores activos tras timeout: esa condición no fue reproducida en vivo.

**Clasificación:** evidencia estática; estado runtime no disponible por ausencia de modelo y no ejecución del contenedor.

**Recomendación:** consultar `docker compose ps` durante la espera, separar `starting`, `healthy` y `unhealthy`, emitir diagnóstico inmediato para `unhealthy`, y conservar timeout acotado y `restart: "no"` del template en `templates/chat/docker-compose.yml.j2:5`.

### PERF7-005 — Alto: el benchmark no respalda claims de throughput o memoria

**Evidencia:** el benchmark canónico valida warm-up más tres muestras en `templates/chat/scripts/smoke_benchmark.sh.j2:20-71`, calcula p50/p95 de TTFB y latencia total en `:73-98`, y puede tomar snapshot de memoria en `:100-125`. Pero escribe explícitamente `Tokens per second | NOT_MEASURED` y `Response quality | NOT_MEASURED` en `:142-152`; tampoco registra host, imagen, digest, runtime ni configuración completa. El único log actual, `logs/benchmarks/smoke-benchmark-20260725-142634.md:1-21`, declara HTTP 200 y “measured-via-client-timing”, pero deja memoria como `placeholder`, no contiene muestras numéricas, tokens/s, calidad, host o identificadores reproducibles, y dice que faltan modelo/servicio real.

`audits/standards/PERFORMANCE.md:35-47` exige warm-up, mediciones repetidas de TTFB, latencia, tokens/s y memoria pico, p50/p95, JSON válido, identificación de modelo/configuración/host/imagen/runtime, fallo no-cero y limpieza temporal.

**Impacto:** el reporte actual es un smoke/placeholder, no una línea base de rendimiento ni evidencia para comparar runtimes, perfiles o modelos. HTTP 200 por sí solo no prueba calidad, throughput ni estabilidad.

**Clasificación:** el script ofrece evidencia estática de intención; el log visible es placeholder; no existe medición runtime válida.

**Recomendación:** con un GGUF autorizado, ejecutar warm-up y suficientes muestras, registrar muestras y p50/p95 de todas las métricas, tokens generados, memoria pico, host/daemon, imagen+digest, runtime, flags y modelo+hash; fallar si faltan campos o el servicio devuelve respuesta inválida. No reutilizar el log actual como baseline.

### PERF7-006 — Medio: el endpoint/configuración de benchmark no califica carga real

**Evidencia:** la petición fija `model: local`, un mensaje corto y `max_tokens: 8` en `templates/chat/scripts/smoke_benchmark.sh.j2:20`; los perfiles configuran contexto, batch, threads y predict en `profiles/*.json:5-10`, pero el benchmark no registra esos valores en el artefacto, solo el nombre del perfil en `:137-139`.

**Impacto:** los resultados, cuando existan, no serán auditables por payload ni configuración efectiva; una carga de ocho tokens no caracteriza throughput o latencia de una sesión representativa.

**Clasificación:** evidencia estática; no hay resultado medido.

**Recomendación:** registrar resumen de workload, contexto, batch, threads, `n_predict`, concurrencia, número de muestras y tokens realmente generados. Mantener un smoke corto separado de un benchmark de regresión.

## No-hallazgos y controles confirmados

- La plantilla canónica fija `MODEL_HOST_PATH` a un bind de `/models/model.gguf` en modo lectura y el validador verifica esa relación en `templates/chat/docker-compose.yml.j2:28-32` y `ai_server_generator/validator.py:229-269`.
- La imagen de serving se referencia por digest en `ai_server_generator/render.py:50-55`; es un control válido de inmutabilidad, aunque no sustituye metadata de compatibilidad.
- Los límites `mem_limit`, `cpus` y `pids_limit` se emiten en `templates/chat/docker-compose.yml.j2:33-35` y se comprueban en `ai_server_generator/validator.py:217-227`.
- El readiness tiene timeout finito, captura `ps` y logs, y stop tiene timeout documentado en `templates/chat/scripts/start_serving.sh.j2:40-55` y `templates/chat/scripts/stop.sh.j2:6-14`.
- El endpoint documentado es OpenAI-compatible (`POST /v1/chat/completions`) en `docs/serving-baseline.md:8-13`; esto es una afirmación de interfaz, no una prueba de rendimiento o calidad.
- La matriz distingue decisión estática de verificación real en `ai_server_generator/cli.py:227-247` y `docs/human-guide.md:49-54`.

## Prerequisitos no disponibles y claims no calificables

- `models/` contiene solo `README.md`; el inventario fresco lo registra en `meta/inventory.md:64` y la comprobación actual encontró `GGUF_COUNT=0`.
- No se ejecutó `docker compose up`, health real, carga GGUF, benchmark ni prueba de calidad; por tanto no hay medición runtime.
- No se puede validar compatibilidad del archivo con `llama.cpp`, memoria pico, tokens/s, latencia real, estabilidad, calidad ni ajuste de contexto/batch.
- Los mensajes `GO`, `WARN` o `NO-GO` de `matrix` son decisiones de generación estáticas. La ejecución actual produjo `WARN` para `ornith-9b/medium` y `smollm3-3b/medium-fast`, y `NO-GO` para `phi-4-14b/good`; ninguna salida es benchmark.

## Recomendaciones priorizadas

1. Bloquear claims de serving verificado hasta disponer de un GGUF autorizado con contrato, tamaño y SHA-256.
2. Completar `model_contract` y la factibilidad con memoria real del host/daemon.
3. Completar identificación y compatibilidad del runtime por digest/versión/flags.
4. Separar smoke validation de benchmark de regresión y eliminar placeholders de cualquier baseline aprobado.
5. Mejorar la máquina de estados de readiness sin perder timeout, logs y stop acotados.

## Comandos ejecutados y códigos de salida

| Comando | Exit | Evidencia/resultados |
|---|---:|---|
| `docker --version` | 0 | Docker 29.6.1 |
| `python3 --version` | 0 | Python 3.14.5 |
| `python3 -m pip --version` | 0 | pip 26.1.1 |
| `docker compose -f docker-compose.yml config --quiet` | 0 | Compose de compatibilidad parseable |
| `python3 -m ai_server_generator list models` | 0 | Cinco presets listados |
| `python3 -m ai_server_generator list profiles` | 0 | Tres perfiles listados |
| `matrix ornith-9b/medium/localhost` | 0 | `WARN`, solo supuestos estáticos |
| `matrix phi-4-14b/good/localhost` | 0 | `NO-GO` estático por memoria estimada |
| `matrix smollm3-3b/medium-fast/localhost` | 0 | `WARN`, solo supuestos estáticos |
| `bash -n templates/chat/scripts/start_serving.sh.j2` | 0 | Sintaxis shell válida |
| `bash -n templates/chat/scripts/smoke_benchmark.sh.j2` | 0 | Sintaxis shell válida |
| `docker info --format ...` | 0 | Docker Desktop arm64, 8 CPUs, 8,321,798,144 bytes |
| `find models -iname '*.gguf'` | 0 | 0 archivos GGUF |

## Verificación de preservación

Este paso creó únicamente este informe dentro de la nueva `AUDIT_DIR`. No se modificaron `.pm-harness/plans/TASK-0007.plan.md`, `.pm-harness/state/TASK-0007.json`, código, templates, logs existentes ni artefactos generados. El checkbox del todo 4 permanece sin marcar.
