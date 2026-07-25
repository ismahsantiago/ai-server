# Auditoría independiente — código, DevOps y PM Harness

## Alcance y método

- Tarea: `TASK-0007`.
- Dimensiones: límites de módulos, flujo de datos, errores y escrituras; integridad plantilla/artefacto; pruebas, dependencias y gates; Docker/Compose y operación; observabilidad, backup, restauración e incidentes; contratos CLI/API; inventario y materialización PM Harness/OpenCode.
- Restricción respetada: no se leyó ningún informe de auditoría anterior. `audits/INDEX.md` y `audits/standards/` no estaban presentes.
- Naturaleza de la evidencia: inspección estática del checkout y comandos locales sin iniciar el servicio. No se ejecutó `docker compose up`, no se descargó la imagen y no se hizo una inferencia real; por tanto, salud, autenticación, rendimiento y consumo del runtime siguen sin verificarse en vivo.
- Estado inicial observado: `git status --short` sin salida.

## Resumen ejecutivo

La base tiene una separación comprensible entre catálogo (`profiles/`, `manifests/`), renderizado (`ai_server_generator/`), plantillas y workspaces generados. El default localhost, `StrictUndefined`, el confinamiento parcial de la salida al repositorio, el contenedor de solo lectura y la materialización nativa de agentes en OpenCode/Claude son buenas decisiones. Doce pruebas unitarias pasan, todos los Compose presentes superan `docker compose config -q`, los scripts materializados superan `bash -n`, y los validadores principales del harness están verdes.

La operación todavía no puede considerarse reproducible ni segura de extremo a extremo. El defecto de mayor impacto es que el wizard valida el modelo en `models/` del repositorio, pero el Compose generado monta `models/` dentro del workspace generado: los workspaces revisados no contienen el archivo que el contenedor intenta abrir. Además, `--force` puede borrar directorios no protegidos del propio repositorio, el reemplazo no es atómico, el allowlist LAN no se aplica, se genera un token conocido por defecto y el smoke produce un informe exitoso aun sin una respuesta HTTP válida. No hay CI, lock reproducible, backup/restore operativo ni procedimiento de rollback/incidente ejecutable. En el harness, la materialización actual es consistente, pero el routing del manager está fijado a OpenCode y no existe adaptador Codex.

## Fortalezas verificadas

1. **Separación de responsabilidades legible.** `ai_server_generator/cli.py:135-165` resuelve la solicitud, `ai_server_generator/render.py:70-128` construye el contexto y `ai_server_generator/validator.py:32-80` valida el workspace. Esto reduce acoplamiento y facilita pruebas focalizadas.
2. **Errores de plantilla fail-closed.** `ai_server_generator/render.py:180-184` activa `StrictUndefined`; una variable ausente no se convierte silenciosamente en texto vacío.
3. **Postura localhost predeterminada.** `templates/chat/docker-compose.yml.j2:6-11` enlaza `127.0.0.1` salvo opt-in LAN; `ai_server_generator/render.py:92-98` rechaza combinaciones LAN sin auth y allowlist no vacío.
4. **Endurecimiento básico del contenedor.** `templates/chat/docker-compose.yml.j2:36-51` monta modelos como solo lectura, aplica límites, healthcheck, `no-new-privileges`, rootfs de solo lectura y `tmpfs`.
5. **Pruebas de CLI útiles.** `tests/test_cli.py:64-216` cubre inventarios, matriz, dry-run, generación y validación; `tests/test_cli.py:218-342` cubre wizard, overwrite y rechazos LAN. `python3 -m unittest` ejecutó 12 pruebas y terminó en código 0.
6. **Materialización nativa presente y consistente.** `.opencode/agents/pm-orchestrator.md:1-16` materializa al root como `primary`; `.opencode/agents/ml-platform-engineer.md:1-16` materializa al worker como `subagent` sin delegación. `harness.py agents check` informó `missing: []` para OpenCode y Claude.
7. **Contratos de estado y conocimiento válidos en esta instantánea.** `harness.py validate` informó cero errores/advertencias y `harness.py wiki check` informó listas vacías.

## Hallazgos de código

### COD-001 — Alta — `--force` puede borrar contenido del repositorio fuera de `generated/`

**Evidencia estática:** `ai_server_generator/render.py:39-53` sólo prohíbe seis primeros segmentos (`.pm-harness`, `ai_server_generator`, `templates`, `profiles`, `manifests`, `tests`). Rutas como `.git/objects`, `docs`, `scripts`, `models`, `audits` o `.github` permanecen aceptables. Después, `ai_server_generator/render.py:172-178` ejecuta `shutil.rmtree(out_path)` con `force`.

**Impacto:** un error de operador como `--out docs --force`, o una automatización con una ruta mal construida, puede destruir documentación, modelos, scripts, auditorías o incluso metadatos Git. El confinamiento “dentro del proyecto” no equivale a un target seguro.

**Remediación específica:** restringir la salida por contrato a un único root dedicado, por ejemplo `PROJECT_ROOT/generated`, resolver y verificar que el destino sea descendiente estricto de ese root, rechazar symlinks en cualquier componente y añadir pruebas negativas para `.git`, `docs`, `models`, `scripts`, `audits` y rutas con symlink.

### COD-002 — Alta — Entradas CLI se interpolan sin serialización/escape contextual

**Evidencia estática:** `templates/chat/manifest.json.j2:7-20` inserta `model_path`, nombres, texto y allowlist dentro de JSON usando comillas manuales; `templates/chat/env.j2:11-14` inserta token/allowlist como líneas `.env`; `templates/chat/docker-compose.yml.j2:15-35` inserta el path del modelo en YAML. `ai_server_generator/render.py:100-127` transfiere esos valores sin validación de caracteres ni filtros JSON/YAML/env.

**Evidencia ejecutada:** renderizar en memoria un contexto con `model_path='x"broken'` y pasarlo a `json.loads` produjo `JSONDecodeError: Expecting ',' delimiter: line 7 column 20`; no se escribió workspace.

**Impacto:** entradas válidas para `argparse` pueden producir artefactos inválidos o inyectar líneas/estructura en `.env` y YAML. La generación puede dejar archivos parcialmente escritos antes de que el usuario descubra el problema.

**Remediación específica:** generar `manifest.json` con `json.dumps` sobre un objeto, no con interpolación textual; validar paths/CIDR con parsers dedicados; usar quoting explícito seguro para YAML y un escritor `.env`; añadir casos con comillas, saltos de línea, `:`, `#`, `${...}` y Unicode.

### COD-003 — Alta — El overwrite no es transaccional y la salida no es reproducible byte a byte

**Evidencia estática:** `ai_server_generator/render.py:172-178` elimina primero el workspace válido y crea el definitivo; `ai_server_generator/render.py:185-191` escribe después archivo por archivo sin staging ni rollback. Además, `ai_server_generator/render.py:112` incorpora la hora actual en cada render y `templates/chat/manifest.json.j2:6` la materializa.

**Impacto:** cualquier error de Jinja, disco, permiso o proceso deja el destino ausente o incompleto y pierde la última versión buena. Dos ejecuciones con los mismos parámetros nunca son idénticas, lo que impide hashes estables y dificulta verificar drift.

**Remediación específica:** renderizar y validar en un directorio temporal hermano, fsync cuando corresponda y sustituir mediante rename atómico conservando backup recuperable; hacer el timestamp opcional o excluirlo de una sección canónica firmada; incluir un hash de inputs/plantillas y una prueba de regeneración determinista.

### COD-004 — Media — No existe gate de drift entre plantilla canónica y artefactos presentes

**Evidencia estática:** `.gitignore:1` ignora todo `generated/`. El artefacto `generated/chat-medium-localhost/manifest.json:1-22` conserva el esquema anterior y sólo ocho required files, mientras `manifests/chat.json:7-19` exige once. `ai_server_generator/validator.py:10-29` requiere campos que ese manifest viejo no tiene.

**Evidencia ejecutada:** `validate generated/chat-medium-localhost` terminó en código 1 con once errores; los workspaces `ornith-medium-localhost` y `phi4-good-localhost` terminaron en código 0.

**Impacto:** el checkout puede contener ejemplos operativos divergentes aunque la suite principal esté verde; un operador puede escoger un workspace antiguo ignorado y fallar fuera del flujo de revisión.

**Remediación específica:** mantener fixtures dorados mínimos versionados fuera de `generated/`, regenerarlos en CI y comparar con la salida esperada normalizando sólo metadatos volátiles; agregar un comando `validate-all`/`drift-check` que recorra workspaces locales y falle con una lista clara.

## Hallazgos de operación y DevOps

### OPS-001 — Crítica — El wizard aprueba un modelo que el Compose generado no monta

**Evidencia estática:** `ai_server_generator/cli.py:288-296` comprueba `models/<preset>.gguf` relativo al root del proceso. El output por defecto está bajo `generated/...` (`ai_server_generator/cli.py:298-304`), pero `templates/chat/docker-compose.yml.j2:36-38` monta `./models:/models:ro`, relativo al directorio del Compose generado, y el comando consume `/models/...` (`templates/chat/docker-compose.yml.j2:15-18`). El validator sólo verifica archivos declarados (`ai_server_generator/validator.py:51-53`) y el manifest no declara el modelo como required file (`manifests/chat.json:7-19`).

**Evidencia ejecutada:** no existe `generated/ornith-medium-localhost/models/ornith-9b.gguf` ni `generated/phi4-good-localhost/models/phi-4-14b.gguf`, aunque ambos workspaces pasan `ai-server validate`. En el Compose materializado, `generated/ornith-medium-localhost/docker-compose.yml:13-15` solicita `/models/ornith-9b.gguf` y `:31-33` monta el directorio local inexistente.

**Impacto:** el camino documentado `wizard -> validate -> start` puede terminar en un contenedor que no puede abrir el modelo. Es un falso positivo de readiness y bloquea el caso de uso principal.

**Remediación específica:** escoger un contrato único: montar el `models/` del repositorio mediante una ruta absoluta/resuelta o crear dentro del workspace un symlink controlado/manifest de referencia; validar que el archivo host resuelto existe, es regular y legible antes del start; renderizar explícitamente `host_model_path` y `container_model_path`; añadir una prueba Compose que inspeccione la resolución real del bind mount.

### OPS-002 — Alta — El modo LAN declara un allowlist que no aplica y genera un secreto conocido

**Evidencia estática:** `ai_server_generator/render.py:96-111` sólo exige texto no vacío y fija `auth_token` a `change-me-strong-token`. `templates/chat/env.j2:11-14` escribe ese token y el allowlist en `.env`. Sin embargo, `templates/chat/docker-compose.yml.j2:6-35` expone `0.0.0.0`, configura `--api-key` y nunca consume `LAN_ALLOWLIST`. El start sólo comprueba que exista la línea del token (`templates/chat/scripts/start_serving.sh.j2:11-16`), no que sea fuerte, no vacío o distinto del default. El runbook afirma que sólo los rangos indicados pueden alcanzar el puerto (`templates/chat/runbook.md.j2:19-26`), pero delega el firewall al operador.

**Impacto:** un workspace generado con `Decision: GO` queda expuesto a toda interfaz LAN; cualquier host que conozca o adivine el token por defecto puede acceder. El allowlist crea una garantía aparente sin enforcement.

**Remediación específica:** no generar secretos; exigirlos por secret file/store en start y rechazar vacío/default. Materializar el allowlist en un proxy/firewall gestionado y verificable, o renombrarlo como requisito manual y mantener `NO-GO` hasta que una comprobación confirme la regla. Añadir tests de no-default token, CIDR válido y enforcement efectivo.

### OPS-003 — Alta — El smoke da éxito de proceso aunque el servicio falle y rompe auth LAN

**Evidencia estática:** `templates/chat/scripts/smoke_benchmark.sh.j2:10-29` inicializa resultados como placeholders, absorbe errores de `curl` y no sale distinto de cero si falta curl, hay fallo de conexión o HTTP no es 200. `:20` lee `API_BEARER_TOKEN` del entorno del shell, pero el script no carga `.env`; por defecto el header LAN queda vacío. `:21-22` usa un fichero global fijo `/tmp/ai-server-http-code.txt` en vez del `mktemp` ya creado, permitiendo colisiones entre ejecuciones y contenido stale. Finalmente `:30-44` siempre escribe un reporte y termina satisfactoriamente.

**Impacto:** automatización y operadores pueden interpretar un código 0 y un reporte escrito como disponibilidad correcta. En LAN, el smoke falla auth salvo export manual no documentado; ejecuciones concurrentes pueden mezclar estados HTTP.

**Remediación específica:** cargar `.env` de forma segura o leer sólo la clave requerida; usar un directorio temporal privado con `trap`; medir tiempo real con `%{time_total}`; exigir HTTP 200 y JSON esperado; devolver código no cero ante cualquier incumplimiento; separar `smoke` (gate estricto) de `benchmark` (artefacto diagnóstico).

### OPS-004 — Alta — Imagen y dependencias no están cerradas para builds reproducibles

**Evidencia estática:** `templates/chat/docker-compose.yml.j2:1-4` y `docker-compose.yml:4-7` usan `ghcr.io/ggerganov/llama.cpp:server` sin digest. `requirements.txt:1` y `pyproject.toml:10-12` permiten cualquier Jinja 3.1.x; `pyproject.toml:1-3` permite cualquier setuptools >=68. `.opencode/package.json:1-5` sí fija la versión directa, pero `.opencode/.gitignore:1-4` excluye tanto manifest como lock del control de versiones.

**Impacto:** la misma revisión puede instalar código diferente o arrancar otra imagen en fechas distintas; una regresión o compromiso upstream no queda asociado a un cambio auditable del repositorio.

**Remediación específica:** fijar imagen por digest con proceso explícito de actualización; versionar un lock con hashes para Python y ejecutar instalación desde él; conservar/versionar el manifest y lock necesarios de OpenCode si forman parte de la plataforma soportada; automatizar actualización con revisión de changelog, SBOM y escaneo.

### OPS-005 — Alta — No hay CI que ejecute los gates declarados

**Evidencia estática:** `.github/pull_request_template.md:25-39` exige evidencia, pruebas, validate y wiki, y `.pm-harness/standards/GATES.md:12-23` define el bloque mecánico de Gate 1. Sin embargo, `find .github -maxdepth 3 -type f` sólo devolvió `.github/pull_request_template.md`; no existe workflow. `pyproject.toml:5-18` tampoco configura lint, type-check, coverage ni matriz de Python.

**Impacto:** los gates dependen de disciplina local; cambios incompatibles de plataforma, render o shell pueden integrarse sin ejecución independiente. Python soporta `>=3.10`, pero esta auditoría sólo ejecutó 3.14.5.

**Remediación específica:** añadir CI con matriz de versiones soportadas, unit tests, `pip check`, compilación/parseo estático de Compose, `bash -n`/ShellCheck, generación+validación de fixtures, harness validate/agents/wiki/plan/changelog según el task y escaneo de dependencias/imagen; publicar cobertura y artefactos de gate.

### OPS-006 — Media — Observabilidad y benchmark documentados no corresponden a métricas reales

**Evidencia estática:** el runbook promete access logs con timestamp e IP (`templates/chat/runbook.md.j2:19-26`) y monta `./logs:/logs` (`templates/chat/docker-compose.yml.j2:36-38`), pero no configura al runtime/proxy para escribir esos logs. El benchmark etiqueta latencia y memoria como placeholders (`templates/chat/scripts/smoke_benchmark.sh.j2:10-12`) y, aun con HTTP 200, escribe `measured-via-client-timing` sin una medición (`:23-25`); nunca obtiene memoria del contenedor.

**Impacto:** no hay trazabilidad de accesos LAN ni series fiables para capacidad, SLO o regresión. Los reportes existentes pueden parecer evidencia cuantitativa sin contener una medición.

**Remediación específica:** definir formato/rotación/retención de logs, habilitar access logging real o proxy, exponer y recolectar métricas, capturar latencia numérica y `docker stats`, registrar modelo/digest/config/hash, y fallar o marcar explícitamente `NO MEDIDO` sin presentar placeholders como benchmark.

### OPS-007 — Media — Backup, restore, rollback e incidente son sólo marcadores documentales

**Evidencia estática:** `backups/README.md:1-6` únicamente aconseja archivos timestamped y verificar restore; no hay scripts ni formato de snapshot. `templates/chat/runbook.md.j2:34-46` sólo enumera start/benchmark/validate y ubicación del modelo; no contiene stop, rollback, restore, rotación, degradación, diagnóstico ni escalación. `docs/lan-safe-runbook.md:32-42` recomienda “revertir a localhost” sin comando ni procedimiento verificable.

**Impacto:** ante corrupción de configuración, imagen defectuosa, exposición accidental o upgrade fallido, no existe RTO/RPO, backup verificado ni secuencia repetible de recuperación. `--force` agrava el riesgo al eliminar el workspace anterior.

**Remediación específica:** crear backup/restore idempotentes con inventario y checksums; conservar N versiones generadas inmutables; documentar y probar stop/rollback a digest/config previa; añadir runbook de incidente LAN con contención, rotación de token, recolección de evidencia, responsables y criterio de cierre; ejecutar restore drill en Gate 2.

### OPS-008 — Media — La documentación afirma artefactos y comandos con semántica distinta a la implementación

**Evidencia estática:** `docs/serving-baseline.md:64-80` y `config/profiles/README.md:5-14` afirman perfiles emitidos dentro del workspace, pero `ai_server_generator/render.py:15-27` no incluye ningún `config/profiles/*.env`. `docs/human-guide.md:77-82` ejecuta Compose desde el root con `-f`, mientras los scripts generados (`templates/chat/scripts/start.sh.j2:1-4`) dependen del cwd y delegan a rutas relativas; tampoco se documenta claramente que deben ejecutarse desde el workspace.

**Impacto:** operadores buscan archivos inexistentes y pueden ejecutar comandos desde un cwd donde `.env`, bind mounts y scripts resuelven a rutas equivocadas.

**Remediación específica:** decidir si los perfiles se materializan o sólo se registran en manifest/.env y corregir todos los documentos; hacer scripts independientes del cwd mediante `SCRIPT_DIR` y `docker compose --project-directory`; añadir pruebas que los invoquen desde el root y desde otro directorio.

## Hallazgos del PM Harness y OpenCode

### ARN-001 — Alta — El manager fija OpenCode aunque el mismo roster se materializa en Claude

**Evidencia estática:** `.pm-harness/teams/engineering-manager/SKILL.md:24-30` obliga a resolver toda delegación con `--platform opencode`. Sin embargo, `.pm-harness/adapters/adapters.json:37-66` instala y materializa también Claude, con niveles de esfuerzo diferentes a OpenCode (`:58-65` frente a `:26-35`).

**Impacto:** una delegación originada en Claude registra/clampa esfuerzo conforme a la plataforma equivocada, debilitando provenance y pudiendo solicitar un nivel no soportado.

**Remediación específica:** sustituir el literal por `<host>` y exigir detección/inyección del host en FACTS; añadir tests de routing para OpenCode y Claude que validen formato de ID, provider y effort permitido.

### ARN-002 — Alta — Falta adaptador Codex y el catálogo activo viola el formato OpenCode

**Evidencia estática:** `.pm-harness/adapters/adapters.json:4-121` declara OpenCode, Claude, Cursor, OpenClaw y Hermes, pero no Codex. El contexto instalado sólo anuncia superficies Claude/OpenCode (`AGENTS.md:9-15`). OpenCode exige IDs `provider/model` (`.pm-harness/adapters/adapters.json:26-35`), mientras `.pm-harness/model-router.json:84-90` registra sólo `gpt-5`, y la resolución de `TASK-0007` queda sin provider (`.pm-harness/model-router.json:220-234`).

**Impacto:** Codex no tiene materialización nativa ni clamping de effort; para OpenCode, el ID activo no permite identificar proveedor ni verificar que corresponda a un modelo realmente configurable. El provenance se degrada a fallback ambiguo.

**Remediación específica:** añadir adaptador Codex con archivos/contexto/agentes/formato/model discovery soportados y tests de materialización; hacer que `models set` valide el `id_format` de la plataforma; registrar IDs OpenCode completos y rechazar routing cuando no se conoce el host.

### ARN-003 — Media — Permisos nativos de workers son amplios y el límite depende sólo del prompt

**Evidencia estática:** `.opencode/agents/ml-platform-engineer.md:4-11` concede `bash`, lectura, escritura y edición globales; la prohibición de delegar sí es mecánica (`task: false`), pero no hay allowlist de comandos/rutas. El contrato fuente también permite esas herramientas sin restricción (`.pm-harness/teams/engineering-manager/agents/ml-platform-engineer/SKILL.md:1-5`). El propio Gate 1 advierte sobre wildcards que subsumen permisos granulares (`.pm-harness/standards/GATES.md:37-39`).

**Impacto:** un worker comprometido o equivocado puede modificar cualquier archivo accesible o ejecutar comandos fuera de su scope; aislamiento, ownership de memoria y “touch nothing outside task scope” no están reforzados por permisos nativos.

**Remediación específica:** donde OpenCode lo permita, aplicar permisos por ruta/comando y confirmación para efectos destructivos; separar perfiles read-only de audit y write de implementation; añadir un gate que compare permisos materializados con el rol y pruebe que workers no pueden delegar ni escribir stores ajenos.

### ARN-004 — Media — Las verificaciones del harness son de integración local, no una suite versionada del engine instalado

**Evidencia estática:** `.pm-harness/HARNESS-VERSION:1` fija engine 2.1.0 / pack 2.6.0 y `.pm-harness/bin/` contiene el engine instalado, pero el inventario `find .pm-harness -type f | rg 'tests|test_'` no devolvió pruebas. `harness.py validate`, `agents check` y `wiki check` sí ejercitan el estado actual, pero no prueban sistemáticamente transiciones rechazadas, corrupción, concurrencia, permisos ni compatibilidad de upgrades.

**Impacto:** una modificación accidental del CLI instalado o incompatibilidad de Python puede conservar gates felices superficiales y romper caminos de error sólo al operar tareas reales.

**Remediación específica:** distribuir o referenciar una suite de conformance del engine/pack, ejecutarla en CI contra la versión sellada y cubrir state machine, planes/amendments, checksums, memoria/dedupe, materialización/regeneración segura, routing por plataforma y migración entre versiones.

## Gates y evidencia de comandos

| Comando | Código | Resultado observado |
|---|---:|---|
| `docker --version` | 0 | Docker 29.6.1 |
| `python3 --version` | 0 | Python 3.14.5 |
| `python3 -m pip --version` | 0 | pip 26.1.1 |
| `python3 -m unittest` | 0 | 12 pruebas, `OK` |
| `python3 -m pip check` | 1 | `wheel 0.47.0 requires packaging, which is not installed` |
| `python3 .pm-harness/bin/harness.py validate` | 0 | 7 manifests, 11 notas; sin errores ni warnings |
| `python3 .pm-harness/bin/harness.py agents check` | 0 | OpenCode y Claude sin agentes ausentes |
| `python3 .pm-harness/bin/harness.py wiki check` | 0 | sin errores ni warnings |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 | esperado en pasada intermedia: 13 de 13 todos sin marcar |
| `docker compose -f <archivo> config -q` | 0 | root y los tres workspaces presentes |
| `bash -n <script>` | 0 | scripts root y scripts de los tres workspaces presentes |
| `ai-server validate generated/chat-medium-localhost` | 1 | artefacto antiguo incompatible |
| `ai-server validate generated/ornith-medium-localhost` | 0 | validación estática |
| `ai-server validate generated/phi4-good-localhost` | 0 | validación estática |

`python3 .pm-harness/bin/harness.py changelog check --task TASK-0007` no se ejecutó: esta pasada no cambió comportamiento de producto. No se alteraron plan, estado, manifest, checksum ni memoria, conforme a la excepción de handoff.

## Priorización de remediación

1. **Bloquear pérdida/falso readiness:** COD-001, COD-003 y OPS-001.
2. **Cerrar exposición LAN y gates engañosos:** OPS-002 y OPS-003.
3. **Asegurar artefactos y supply chain:** COD-002, COD-004, OPS-004 y OPS-005.
4. **Hacer operable el servicio:** OPS-006, OPS-007 y OPS-008.
5. **Cerrar compatibilidad y gobierno nativo:** ARN-001, ARN-002, ARN-003 y ARN-004.

La condición mínima para declarar “runnable” debería ser: modelo host resoluble y montado, Compose validado con imagen fijada, start desde cualquier cwd, health/smoke estrictos con HTTP/JSON real y rollback documentado. La condición para declarar “LAN-safe” debe añadir secreto no predeterminado, allowlist aplicado y verificado, access logs reales y procedimiento de incidente probado.
