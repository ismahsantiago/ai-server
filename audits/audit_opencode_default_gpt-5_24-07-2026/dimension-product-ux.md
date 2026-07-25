# Auditoría de producto y experiencia de operador

## Alcance y criterio

Pasada independiente sobre el estado actual del repositorio. Se trazó el
recorrido `clone -> prerrequisitos -> matrix -> generate -> validate -> start`
en la documentación, el CLI, las plantillas y las pruebas. No se consultaron
informes de auditoría anteriores. No se iniciaron contenedores, no se cargaron
modelos y no se generaron workspaces; por tanto, las afirmaciones sobre runtime
que no tienen una prueba segura se distinguen expresamente de la evidencia
estática.

La interfaz actual es exclusivamente CLI y archivos Markdown/shell. No existe
una UI visual o dashboard implementado al que aplicar WCAG, navegación por
teclado, contraste o el sistema de diseño Astryx. Sí se evaluaron legibilidad
terminal, consistencia de idioma, códigos de salida, prevención de acciones
destructivas y recuperación ante errores.

## Recorrido observado

1. La portada declara el recorrido canónico y prerrequisitos en
   `README.md:5-29`.
2. `matrix` resuelve preset/perfil/acceso y presenta una decisión GO/NO-GO
   (`ai_server_generator/cli.py:177-218`).
3. `generate` renderiza once archivos y `--force` reemplaza el destino
   (`ai_server_generator/cli.py:235-267`,
   `ai_server_generator/render.py:168-191`).
4. `validate` comprueba estructura de manifiesto, archivos declarados y una
   parte de la postura de red (`ai_server_generator/validator.py:32-80`).
5. La documentación invoca el script generado desde la raíz
   (`README.md:51-55`), mientras que los scripts generados presuponen que el
   directorio actual ya es el workspace.

## Fortalezas confirmadas

- El orden conceptual `matrix -> generate -> validate -> start` es consistente
  en la portada y la guía humana (`README.md:65-73`,
  `docs/human-guide.md:65-75`).
- El CLI ofrece ayuda superior concisa y subcomandos bien agrupados
  (`ai_server_generator/cli.py:15-51`). La ejecución de
  `python3 -m ai_server_generator --help` terminó con código `0`.
- La vista previa localhost fue clara y determinista: mostró preset, setup,
  perfil, acceso, ruta de modelo y `Decision: GO`, con código `0`.
- El control LAN básico falla de forma explícita: `matrix --access lan` sin
  autenticación ni allowlist devolvió `Decision: NO-GO`, explicó los dos
  controles faltantes y terminó con código `1`
  (`ai_server_generator/render.py:96-98`,
  `ai_server_generator/cli.py:201-204`).
- `--dry-run` enumera los once artefactos sin escribir el destino
  (`ai_server_generator/render.py:168-170`). La validación de un directorio
  inexistente también produjo un error accionable y código `1`
  (`ai_server_generator/validator.py:35-36`).
- Los mensajes no dependen de color ni secuencias ANSI, lo cual conserva
  legibilidad básica en terminales monocromas y lectores de pantalla.

## Hallazgos

### UX-20260724-001 — Alta — El inicio canónico ejecuta scripts según el CWD y puede usar los artefactos legacy equivocados

**Evidencia exacta:** `README.md:51-55` indica ejecutar
`./generated/ornith-medium-localhost/scripts/start.sh` desde la raíz. Sin
embargo, el wrapper generado llama a `./scripts/start_serving.sh` sin resolver
su propia ubicación (`templates/chat/scripts/start.sh.j2:1-4`), y ese script
busca `.env` y ejecuta `docker compose` también respecto del CWD
(`templates/chat/scripts/start_serving.sh.j2:6-18`). Los wrappers de validación
y smoke repiten el mismo patrón
(`templates/chat/scripts/validate.sh.j2:1-4`,
`templates/chat/scripts/smoke.sh.j2:1-4`).

**Impacto concreto:** siguiendo literalmente el quickstart desde la raíz,
`start.sh` puede invocar `scripts/start_serving.sh` del repositorio legacy y
usar el compose/.env raíz, en vez del workspace generado. `validate.sh` falla
porque no hay equivalente raíz `scripts/validate_host.sh`. El recorrido más
visible no es reproducible y puede arrancar una configuración distinta de la
que el operador acaba de validar.

**Remediación específica:** en cada wrapper y script largo, calcular
`SCRIPT_DIR` y `WORKSPACE_DIR` a partir de `${BASH_SOURCE[0]}`, hacer
`docker compose --project-directory "$WORKSPACE_DIR" -f
"$WORKSPACE_DIR/docker-compose.yml" ...`, y referenciar `.env`/logs mediante
rutas absolutas derivadas. Añadir pruebas que ejecuten cada helper desde la
raíz, desde el workspace y desde un tercer CWD.

**Tipo de evidencia:** estática; no se arrancó Docker.

### UX-20260724-002 — Crítica — `--force` puede borrar directorios de producto ajenos a `generated/`

**Evidencia exacta:** la lista protegida solo contiene seis nombres y omite,
entre otros, `docs`, `scripts`, `models`, `config`, `backups` y `audits`
(`ai_server_generator/render.py:39-53`). Si el destino existe y es directorio,
`--force` ejecuta `shutil.rmtree(out_path)` antes de recrearlo
(`ai_server_generator/render.py:172-178`). La portada incorpora `--force` al
comando de inicio recomendado (`README.md:39-43`).

La prueba segura
`generate ... --out docs --force --dry-run` terminó con código `0` y anunció
que generaría once archivos en `docs`; no escribió ni eliminó nada.

**Impacto concreto:** un error de selección o una variable vacía puede
convertir una opción presentada como “sobrescribir output” en borrado
recursivo de documentación, modelos, backups u otros datos del repositorio.
No hay confirmación, backup ni restricción al árbol `generated/`.

**Remediación específica:** restringir por defecto los destinos mutables a
`PROJECT_ROOT/generated/**`; para destinos personalizados exigir una opción
separada y confirmación interactiva explícita. Rechazar cualquier destino
existente que no contenga un marcador/manifiesto generado válido y, antes de
reemplazar, usar escritura a staging + rename o un backup recuperable. Añadir
pruebas negativas para todos los directorios de primer nivel y symlinks.

**Tipo de evidencia:** análisis estático y `--dry-run`; no se ejecutó el
borrado.

### UX-20260724-003 — Alta — El modelo comprobado en la raíz no queda disponible en el workspace generado

**Evidencia exacta:** el preset resuelve a `./models/<alias>.gguf`
(`ai_server_generator/presets.py:17-19`) y el wizard solo comprueba esa ruta
relativa al CWD (`ai_server_generator/cli.py:288-296`). El compose generado
monta `./models:/models:ro`, relativo al workspace de Compose
(`templates/chat/docker-compose.yml.j2:36-38`). El generador no crea ni copia
un directorio/modelo: su mapa de once salidas no contiene `models/`
(`ai_server_generator/render.py:15-27`). La guía dice colocar el peso en
`./models/<preset>.gguf` (`docs/human-guide.md:8-21`) y luego arranca desde
`generated/...`, sin un paso de materialización.

**Impacto concreto:** el preflight del wizard puede aprobar un peso en
`<repo>/models`, pero el contenedor busca el mismo nombre bajo
`<workspace>/models`, donde no fue copiado ni enlazado. El operador supera
matrix, generate y validate para descubrir el fallo recién en el arranque del
modelo.

**Remediación específica:** elegir un contrato único y visible: montar en el
compose la ruta host absoluta/canónica seleccionada, o materializar el modelo
en el workspace mediante copia/enlace explícito con confirmación de tamaño y
espacio. Registrar ambas rutas en el manifiesto y hacer que `validate`
compruebe existencia, archivo regular, legibilidad y extensión antes de
declarar el workspace listo.

**Tipo de evidencia:** estática; no se cargó un modelo.

### UX-20260724-004 — Alta — “valid” significa solo estructura, pero se presenta como preparación para arrancar

**Evidencia exacta:** el validador revisa claves, archivos declarados,
quick-commands y parte del bind/auth
(`ai_server_generator/validator.py:32-80`), pero no comprueba Docker/Compose,
existencia del modelo, permisos ejecutables, memoria/CPU ni salud del daemon.
Aun así imprime `valid: <dir>` sin calificador
(`ai_server_generator/cli.py:268-275`) y la portada coloca inmediatamente
`start` después de esa validación (`README.md:45-55`). El roadmap incluso
describe validación de ruta de modelo, presupuesto de memoria y herramientas
host (`docs/roadmap/generator-first-roadmap.md:42-47`), capacidades que el
validador actual no implementa.

**Impacto concreto:** se crea una señal de éxito demasiado fuerte. Un
workspace con placeholder, sin Docker disponible o con scripts no ejecutables
puede ser “valid” y fallar en el paso costoso siguiente, degradando confianza
y dificultando el diagnóstico.

**Remediación específica:** separar resultados en niveles
`estructura válida`, `host listo` y `runtime saludable`; hacer que el comando
por defecto muestre claramente qué no se verificó. Incorporar comprobaciones
seguras de modelo, permisos, Docker Compose y presupuesto, con `--offline` o
`--structural-only` explícito para el modo reducido.

**Tipo de evidencia:** estática y validación segura de una ruta inexistente;
no se verificó un daemon vivo.

### UX-20260724-005 — Alta — El smoke puede devolver éxito aunque no haya respuesta útil

**Evidencia exacta:** si no hay `curl`, si `curl` falla o si el HTTP no es 200,
el script conserva `HTTP_STATUS=not-tested` o un estado no exitoso, pero no
marca error (`templates/chat/scripts/smoke_benchmark.sh.j2:10-29`). Después
siempre escribe el informe y termina por el `printf` exitoso
(`templates/chat/scripts/smoke_benchmark.sh.j2:32-46`). Además,
`LATENCY_MS` pasa a la cadena `measured-via-client-timing` sin medir ninguna
duración (`templates/chat/scripts/smoke_benchmark.sh.j2:16-27`). El wizard
propaga ese código como su resultado final
(`ai_server_generator/cli.py:421-431`).

**Impacto concreto:** `wizard --run yes`, CI o un operador pueden recibir
código `0` aunque el endpoint no exista, rechace autenticación o responda con
error. El informe rotula una métrica de latencia sin valor medido, por lo que
no sirve para decidir si el servidor funciona o rinde aceptablemente.

**Remediación específica:** fallar con códigos diferenciados si falta `curl`,
hay error de transporte, HTTP no-2xx o respuesta incompatible; medir tiempo
real (`time_total` o reloj monotónico), validar JSON mínimo y reservar un modo
`--report-even-on-failure` que escriba evidencia sin convertir el resultado
en PASS.

**Tipo de evidencia:** estática; no se llamó a un endpoint vivo.

### UX-20260724-006 — Media — El roadmap mezcla capacidades planificadas con comandos que parecen disponibles

**Evidencia exacta:** el roadmap afirma que `list setups` reporta chat,
coding, RAG y visión (`docs/roadmap/generator-first-roadmap.md:23-26`) y
ofrece ejemplos ejecutables de `coding` y RAG
(`docs/roadmap/generator-first-roadmap.md:410-430`), además de un comando
`explain` (`docs/roadmap/generator-first-roadmap.md:482-500`). El parser
actual solo expone `list`, `generate`, `matrix`, `validate` y `wizard`
(`ai_server_generator/cli.py:20-51`); el catálogo actual solo contiene
`chat` (`manifests/chat.json:1-19`).

**Impacto concreto:** aunque el archivo se titule “roadmap”, sus bloques
copiables y frases en presente pueden llevar a evaluar como defectuoso un
CLI que todavía no implementa esas fases, o a prometer soporte de producto
inexistente.

**Remediación específica:** añadir una tabla por capacidad con estados
`implementado`, `experimental` y `planificado`, versión objetivo y comando
actual verificable. Mover ejemplos no ejecutables a pseudocódigo claramente
rotulado y generar/validar los ejemplos de la documentación contra
`--help`.

**Tipo de evidencia:** estática y ayuda real del CLI.

### UX-20260724-007 — Media — Una invocación incompleta termina con éxito y la ayuda de opciones no explica semántica ni riesgo

**Evidencia exacta:** los subparsers no son obligatorios
(`ai_server_generator/cli.py:20`) y la ruta sin comando imprime ayuda y
devuelve `0` (`ai_server_generator/cli.py:433-434`). Las opciones de
`generate` carecen de texto `help`, incluida la destructiva `--force`
(`ai_server_generator/cli.py:25-35`). En ejecución,
`python3 -m ai_server_generator` terminó con código `0`; `generate --help`
mostró nombres de opciones sin descripciones.

**Impacto concreto:** un script mal configurado puede omitir el subcomando y
ser contabilizado como éxito sin generar ni validar nada. Un operador nuevo
no puede descubrir desde `--help` precedencias preset/flags, destino
permitido, efecto destructivo de `--force` o garantías limitadas de
`--dry-run`.

**Remediación específica:** hacer obligatorio el subcomando y devolver el
código de uso de argparse (`2`) cuando falte; documentar cada opción, defaults,
precedencias, ejemplos y advertencias. Para errores de alias, mostrar
alternativas válidas y sugerencia por similitud.

**Tipo de evidencia:** ejecución segura y análisis estático.

## Accesibilidad e internacionalización

No hay dimensión visual implementada, por lo que contraste, foco y layout no
aplican todavía. En terminal, el uso de texto plano es una fortaleza. Queda
una inconsistencia menor: el wizard acepta `si/s/yes/y`, pide
`Please answer SI/NO` y combina la pregunta española de arranque con errores
ingleses (`ai_server_generator/cli.py:74-81`,
`ai_server_generator/cli.py:391-400`). Antes de considerar localización como
capacidad de producto, conviene elegir un idioma de sesión o incorporar un
selector/locale coherente; los prompts deben conservar códigos y vocabulario
estable para automatización y lectores de pantalla.

## Evidencia de comandos seguros

| Comando/escenario | Resultado observado | Código |
|---|---|---:|
| `python3 -m ai_server_generator --help` | Subcomandos visibles | 0 |
| `python3 -m ai_server_generator` | Imprime ayuda, no realiza trabajo | 0 |
| `matrix --preset ornith-9b --profile medium --access localhost` | `Decision: GO` | 0 |
| `matrix --preset ornith-9b --profile medium --access lan` | `NO-GO`; exige auth + allowlist | 1 |
| `validate generated/does-not-exist-ux-audit` | Error de directorio inexistente | 1 |
| `generate ... --out generated/ux-audit-dry-run --dry-run` | Enumera once archivos; no escribe | 0 |
| `generate ... --out docs --force --dry-run` | Acepta `docs` como destino | 0 |
| `bash -n` sobre scripts raíz y plantillas shell | Sintaxis aceptada en todos | 0 |

Los comandos de inicio, smoke y salud de Docker quedaron **no ejecutados**:
habrían iniciado o contactado runtime vivo, fuera del alcance seguro de esta
fase. En consecuencia, no se afirma que un contenedor o modelo real arranque;
los hallazgos de esa capa se sustentan en contratos de ruta, control de flujo y
códigos de salida del código actual.

## Prioridad recomendada

1. Bloquear el borrado fuera de `generated/` (UX-20260724-002).
2. Hacer los scripts independientes del CWD y alinear el montaje del modelo
   (UX-20260724-001 y UX-20260724-003).
3. Convertir validate/smoke en señales honestas y escalonadas
   (UX-20260724-004 y UX-20260724-005).
4. Endurecer contrato de CLI y separar claramente presente de roadmap
   (UX-20260724-006 y UX-20260724-007).
