# Informe completo de auditoría independiente

## Identificación

- **Proyecto:** ai-server
- **Componentes revisados:** generador CLI Python, catálogo de perfiles y manifiestos, plantillas Jinja, workspaces Docker Compose, scripts operativos, documentación, pruebas y PM Harness/adaptadores de plataforma.
- **Fecha:** 24-07-2026
- **Alcance:** auditoría técnica, de seguridad y aplicabilidad legal, rendimiento/runtime, DevOps/operación, PM Harness, producto y experiencia de operador sobre el checkout actual.
- **Plataforma:** opencode
- **Agente:** default
- **Modelo:** `gpt-5` (procedencia: fallback; Codex no figura en los adaptadores locales, por lo que no se pudo aplicar el ajuste de esfuerzo de la plataforma)
- **Operador:** isma <ismahsantiago@gmail.com>
- **Limitación estática/en vivo:** revisión estática con comprobaciones locales seguras. No se inició el servidor, no se levantaron contenedores, no se descargaron imágenes ni modelos, no se ejecutó inferencia y no se validaron en vivo salud, autenticación, exposición LAN, rendimiento, consumo de memoria o firewall.

## Resumen ejecutivo

Se consolidaron mecánicamente 35 hallazgos independientes de las cuatro dimensiones de esta ejecución. La distribución reconciliada es:

| Severidad | Cantidad |
|---|---:|
| Crítica | 3 |
| Alta | 20 |
| Media | 12 |
| Baja | 0 |
| **Total** | **35** |

La evidencia disponible no sustenta una aprobación operativa para el perfil LAN ni una declaración de runtime listo. El perfil localhost parte de decisiones razonables, pero todavía requiere cerrar fallos críticos de seguridad, integridad destructiva y disponibilidad del modelo, además de mejorar reproducibilidad, validación, observabilidad y operación.

## Fortalezas por dimensión

### Seguridad y aplicabilidad legal

- El modo por defecto es `localhost` (`ai_server_generator/presets.py:13-15`) y la plantilla publica el puerto en `127.0.0.1` para ese modo (`templates/chat/docker-compose.yml.j2:7-11`).
- La generación rechaza LAN sin selección de `bearer-token` y allowlist no vacía (`ai_server_generator/render.py:96-98`), con pruebas negativas (`tests/test_cli.py:302-342`).
- La ruta de salida se resuelve, permanece dentro del repositorio y excluye varios directorios protegidos (`ai_server_generator/render.py:39-53`).
- Las ejecuciones del wizard usan argv sin shell y un `cwd` explícito (`ai_server_generator/cli.py:407-426`); no se encontró `shell=True`, `eval`, `exec` ni `os.system` en el código de producto.
- El contenedor usa `no-new-privileges`, raíz de solo lectura y `tmpfs` limitado (`templates/chat/docker-compose.yml.j2:47-51`).
- `.env` está ignorado por Git (`.gitignore:11-15`) y la CLI no imprime el token. El `.env` local inspeccionado no contenía una variable de token, aunque su modo era `0644`.

### Código, DevOps y PM Harness

1. **Separación de responsabilidades legible.** `ai_server_generator/cli.py:135-165` resuelve la solicitud, `ai_server_generator/render.py:70-128` construye el contexto y `ai_server_generator/validator.py:32-80` valida el workspace. Esto reduce acoplamiento y facilita pruebas focalizadas.
2. **Errores de plantilla fail-closed.** `ai_server_generator/render.py:180-184` activa `StrictUndefined`; una variable ausente no se convierte silenciosamente en texto vacío.
3. **Postura localhost predeterminada.** `templates/chat/docker-compose.yml.j2:6-11` enlaza `127.0.0.1` salvo opt-in LAN; `ai_server_generator/render.py:92-98` rechaza combinaciones LAN sin auth y allowlist no vacío.
4. **Endurecimiento básico del contenedor.** `templates/chat/docker-compose.yml.j2:36-51` monta modelos como solo lectura, aplica límites, healthcheck, `no-new-privileges`, rootfs de solo lectura y `tmpfs`.
5. **Pruebas de CLI útiles.** `tests/test_cli.py:64-216` cubre inventarios, matriz, dry-run, generación y validación; `tests/test_cli.py:218-342` cubre wizard, overwrite y rechazos LAN. `python3 -m unittest` ejecutó 12 pruebas y terminó en código 0.
6. **Materialización nativa presente y consistente.** `.opencode/agents/pm-orchestrator.md:1-16` materializa al root como `primary`; `.opencode/agents/ml-platform-engineer.md:1-16` materializa al worker como `subagent` sin delegación. `harness.py agents check` informó `missing: []` para OpenCode y Claude.
7. **Contratos de estado y conocimiento válidos en esta instantánea.** `harness.py validate` informó cero errores/advertencias y `harness.py wiki check` informó listas vacías.

### Rendimiento y runtime

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

### Producto y experiencia de operador

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

## Hallazgos consolidados

Los bloques siguientes preservan literalmente ubicación/evidencia, impacto y remediación/recomendación de los cuatro insumos. Se reordenan únicamente por dimensión y severidad.

## Dimensión: Seguridad y aplicabilidad legal

**Severidad: Crítica**

### SEC-001 — Crítica — credencial LAN predecible y archivo de secreto legible por otros usuarios

**Evidencia exacta:** `ai_server_generator/render.py:103-111` asigna siempre `change-me-strong-token`; `templates/chat/env.j2:11-14` lo escribe en `.env`; `templates/chat/scripts/start_serving.sh.j2:11-15` y `templates/chat/scripts/validate_host.sh.j2:16-24` solo comprueban que las claves existan. Los archivos no-script se crean con `Path.write_text` sin fijar permisos (`ai_server_generator/render.py:185-191`); con el `umask` observado, `.env` queda `0644`.

**Impacto:** un workspace LAN recién generado puede arrancar con una credencial pública y conocida. Cualquier equipo que alcance el puerto puede autenticarse, consumir recursos, enviar contenido al modelo y acceder a capacidades futuras expuestas por el servidor. En un host multiusuario, otros usuarios locales pueden leer el secreto.

**Remediación específica:** no materializar un token fijo. Generar criptográficamente al menos 32 bytes o exigir inyección desde un gestor/archivo de secretos; escribir `.env` con modo `0600`; rechazar valores vacíos, el placeholder y secretos débiles tanto en validación como antes de `docker compose up`; documentar rotación y evitar incluir el secreto en manifiestos o logs.

**Severidad: Alta**

### SEC-002 — Alta — la allowlist no se aplica y el bearer token viaja por HTTP

**Evidencia exacta:** LAN publica directamente `0.0.0.0` (`templates/chat/docker-compose.yml.j2:7-9`) y solo añade `--api-key` al servidor (`templates/chat/docker-compose.yml.j2:32-35`). `LAN_ALLOWLIST` se escribe en `.env` (`templates/chat/env.j2:11-14`) pero no es consumida por Compose, scripts ni código. El runbook delega el bloqueo a un firewall que el producto no verifica (`templates/chat/runbook.md.j2:21-23`) y los ejemplos usan `http://` con `Authorization: Bearer` (`templates/chat/README.md.j2:41-48`). La guía raíz recomienda proxy, auth y firewall (`docs/lan-safe-runbook.md:8-26`), pero el workspace generado no los incorpora.

**Impacto:** “LAN protegida por allowlist” es actualmente una afirmación declarativa: cualquier origen con ruta al host llega al servicio. Además, un observador de la red puede capturar o reutilizar el bearer token al no haber TLS, agravado por SEC-001.

**Remediación específica:** no publicar directamente el proceso del modelo. Generar un proxy con TLS y autenticación delante de un backend no publicado; aplicar la allowlist en firewall/proxy a partir de un CIDR validado; añadir un preflight que demuestre la regla efectiva o declarar NO-GO. Si no se puede automatizar de forma portable, limitar el generador MVP a localhost y entregar un procedimiento explícito con verificación por plataforma. Definir CORS con una lista de orígenes cerrada si se habilitan clientes web; no se encontró una política CORS actual y su comportamiento efectivo depende de la imagen no ejecutada.

### SEC-003 — Alta — inyección de YAML, dotenv y JSON mediante entradas sin serialización

**Evidencia exacta:** `--model-path` y `--lan-allowlist` aceptan texto libre (`ai_server_generator/cli.py:25-35`); esos valores pasan sin validación de caracteres de control (`ai_server_generator/render.py:96-111`) y se interpolan directamente en YAML (`templates/chat/docker-compose.yml.j2:15-19`), dotenv (`templates/chat/env.j2:11-14`) y JSON entre comillas (`templates/chat/manifest.json.j2:7-20`). La prueba estática en memoria con `model_path="safe.gguf\n    privileged: true"` produjo una propiedad de servicio `privileged: true`; una allowlist con salto de línea produjo una segunda asignación de `API_BEARER_TOKEN`.

**Impacto:** una entrada procedente de automatización, formulario o wrapper puede alterar la configuración del contenedor, sobrescribir variables o invalidar/adulterar el manifiesto. La generación normal termina con éxito antes de cualquier validación, por lo que un operador que ejecute Compose directamente puede activar la configuración inyectada.

**Remediación específica:** rechazar NUL, CR/LF y caracteres fuera de gramáticas estrictas; validar `model_path` como ruta relativa bajo el montaje permitido y `lan_allowlist` con `ipaddress.ip_network`; generar JSON con `json.dumps`, YAML con un serializador seguro y dotenv con escaping formal; validar automáticamente el artefacto antes de declarar éxito y añadir regresiones para saltos de línea, comillas y propiedades Compose inyectadas.

### SEC-004 — Alta — el validador LAN confía en declaraciones y no en controles efectivos

**Evidencia exacta:** para LAN, el validador únicamente comprueba `manifest["auth"] == "bearer-token"` y que `lan_allowlist` sea truthy (`ai_server_generator/validator.py:63-76`). No comprueba el bind real, presencia de `--api-key`, valor/fortaleza del token, sintaxis CIDR, TLS/proxy, firewall, privilegios, montajes ni consistencia entre manifiesto, `.env` y Compose. En localhost usa coincidencias de texto, no parseo estructural (`ai_server_generator/validator.py:64-71`).

**Impacto:** un workspace manipulado o incompleto puede recibir un resultado “valid” pese a carecer de los controles de seguridad anunciados. Esto convierte la validación en una falsa barrera de integración y facilita despliegues inseguros por error.

**Remediación específica:** parsear JSON, YAML y dotenv; comparar valores entre artefactos; validar CIDR, bind, auth, ausencia de `privileged`, límites y secreto no-placeholder; exigir proxy/TLS y artefactos de firewall en LAN; ejecutar `docker compose config` sobre la salida y fallar cerrado ante claves desconocidas o diferencias. Añadir pruebas positivas y negativas que muten cada control.

**Severidad: Media**

### SEC-005 — Media — cadena de suministro reproducible y verificable insuficiente

**Evidencia exacta:** la imagen usa el tag mutable `ghcr.io/ggerganov/llama.cpp:server` (`templates/chat/docker-compose.yml.j2:1-4` y `docker-compose.yml:4-7`); Jinja2 se declara como rango amplio (`requirements.txt:1`, `pyproject.toml:10-12`); el backend de build también es un rango sin lock (`pyproject.toml:1-3`). No hay lock/hashes de Python, SBOM, política de actualización ni workflow de escaneo entre los archivos versionados.

**Impacto:** instalaciones hechas en fechas distintas pueden recibir bytes diferentes, cambios incompatibles o una versión comprometida. No existe una evidencia repetible que relacione un workspace generado con componentes exactos ni una barrera automática ante vulnerabilidades conocidas.

**Remediación específica:** fijar la imagen por digest y conservar un proceso de actualización revisado; generar un lock con hashes para runtime y build; emitir SBOM (por ejemplo SPDX/CycloneDX); añadir escaneo de dependencias e imagen en CI y una política de respuesta/actualización. El escáner `pip-audit` no estaba instalado, por lo que este pase no afirma ausencia de CVE.

### SEC-006 — Media — aislamiento del contenedor incompleto

**Evidencia exacta:** aunque existen `no-new-privileges` y `read_only`, la plantilla no fija `user`, no elimina capabilities, no limita PIDs y monta `./logs` con escritura (`templates/chat/docker-compose.yml.j2:36-51`). El artefacto raíz replica el mismo patrón (`docker-compose.yml:31-46`).

**Impacto:** si el proceso o la imagen se comprometen, conserva más superficie del kernel y del host de la necesaria y puede alterar archivos bajo `logs/`. El usuario efectivo depende de una imagen mutable no inspeccionada en este pase.

**Remediación específica:** fijar UID/GID no-root conocido tras comprobar compatibilidad de la imagen, añadir `cap_drop: [ALL]`, `pids_limit`, límites de recursos y, si es viable, red interna/backend; montar solo rutas indispensables y separar logs con permisos mínimos/rotación. Verificar estos invariantes de forma estructural y mediante una prueba de runtime en CI.

### LEG-001 — Media — distribución sin licencia ni inventario de obligaciones de terceros

**Aplicabilidad:** aplica si el repositorio, paquete, plantillas o workspaces se distribuyen a terceros. También aplica al catálogo porque referencia y facilita el uso de una imagen y modelos de proveedores distintos. No se emite una conclusión jurídica sobre cada licencia: faltan procedencia y versiones exactas.

**Evidencia exacta:** la metadata del paquete no declara `license`, `license-files` ni URLs de proyecto (`pyproject.toml:5-12`); la plantilla distribuye una referencia a `llama.cpp` (`templates/chat/docker-compose.yml.j2:1-4`); el catálogo nombra cinco familias/modelos sin fuente, revisión de licencia ni condiciones de uso (`ai_server_generator/presets.py:22-59`). No hay `LICENSE`, `NOTICE` o inventario legal entre los archivos versionados.

**Impacto:** usuarios y redistribuidores no pueden determinar con claridad los permisos del propio código ni las obligaciones/limitaciones de imagen y modelos. La omisión aumenta el riesgo de redistribución no autorizada, falta de atribución o uso incompatible con términos específicos del modelo.

**Remediación específica:** definir y publicar la licencia del proyecto; completar metadata; mantener `THIRD_PARTY_NOTICES`/SBOM con componente, versión/digest, fuente, licencia y obligaciones; añadir a cada preset fuente oficial, licencia/versión revisada, restricciones y una advertencia de que el usuario debe aportar el modelo legítimamente. Repetir la revisión legal al actualizar digests o presets.

## Legal y privacidad: omisiones justificadas

- No se encontró telemetría, llamada a servicios externos ni envío automático de prompts en el código de producto. Por ello no corresponde afirmar cumplimiento o incumplimiento de GDPR/LFPDPPP/CCPA en el modo local actual.
- En LAN, prompts, respuestas, IP y logs **pueden** contener datos personales o confidenciales. La obligación concreta depende del operador, jurisdicción y uso; antes de un uso organizacional deben definirse retención, acceso, aviso/base jurídica y borrado. El repositorio solo recomienda logs con IP (`templates/chat/runbook.md.j2:24-26`) y no implementa ese ciclo de gobierno.
- No hay evidencia de uso regulado (salud, crédito, empleo, biometría o decisiones automatizadas de alto impacto), así que esos marcos sectoriales quedan fuera de alcance hasta que exista un caso de uso concreto.

## Comandos y evidencia de ejecución

| Comprobación | Resultado | Naturaleza |
|---|---:|---|
| `docker --version` | 0 — Docker 29.6.1 | herramienta local |
| `python3 --version` | 0 — Python 3.14.5 | herramienta local |
| `python3 -m pip --version` | 0 — pip 26.1.1 | herramienta local |
| `python3 -m unittest` | 0 — 12 pruebas | ejecución local; no cubre runtime LAN |
| `python3 -m pip check` | 1 — `wheel 0.47.0 requires packaging` | entorno Python local inconsistente |
| `docker compose config --quiet` | 0 | parseo del Compose raíz, sin iniciar daemon |
| `python3 -m pip_audit --version` | 1 — módulo ausente | no se ejecutó escaneo CVE |
| `docker image inspect ghcr.io/ggerganov/llama.cpp:server` | 1 — daemon no disponible | no se verificó imagen, usuario ni digest en runtime |
| `python3 .pm-harness/bin/harness.py validate` | 0 | contratos del harness |
| `python3 .pm-harness/bin/harness.py agents check` | 0 | materialización de agentes |
| `python3 .pm-harness/bin/harness.py wiki check` | 0 | wiki del harness |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 — 13/13 todos pendientes | esperado durante el pase concurrente; no se modificó el plan |

No se ejecutó `changelog check` porque esta fase no cambió comportamiento de producto. No se modificaron código, tests, configuración, plan, estado, checksum ni memoria del harness.

## Dimensión: Código, DevOps y PM Harness

**Severidad: Crítica**

### OPS-001 — Crítica — El wizard aprueba un modelo que el Compose generado no monta

**Evidencia estática:** `ai_server_generator/cli.py:288-296` comprueba `models/<preset>.gguf` relativo al root del proceso. El output por defecto está bajo `generated/...` (`ai_server_generator/cli.py:298-304`), pero `templates/chat/docker-compose.yml.j2:36-38` monta `./models:/models:ro`, relativo al directorio del Compose generado, y el comando consume `/models/...` (`templates/chat/docker-compose.yml.j2:15-18`). El validator sólo verifica archivos declarados (`ai_server_generator/validator.py:51-53`) y el manifest no declara el modelo como required file (`manifests/chat.json:7-19`).

**Evidencia ejecutada:** no existe `generated/ornith-medium-localhost/models/ornith-9b.gguf` ni `generated/phi4-good-localhost/models/phi-4-14b.gguf`, aunque ambos workspaces pasan `ai-server validate`. En el Compose materializado, `generated/ornith-medium-localhost/docker-compose.yml:13-15` solicita `/models/ornith-9b.gguf` y `:31-33` monta el directorio local inexistente.

**Impacto:** el camino documentado `wizard -> validate -> start` puede terminar en un contenedor que no puede abrir el modelo. Es un falso positivo de readiness y bloquea el caso de uso principal.

**Remediación específica:** escoger un contrato único: montar el `models/` del repositorio mediante una ruta absoluta/resuelta o crear dentro del workspace un symlink controlado/manifest de referencia; validar que el archivo host resuelto existe, es regular y legible antes del start; renderizar explícitamente `host_model_path` y `container_model_path`; añadir una prueba Compose que inspeccione la resolución real del bind mount.

**Severidad: Alta**

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

### ARN-001 — Alta — El manager fija OpenCode aunque el mismo roster se materializa en Claude

**Evidencia estática:** `.pm-harness/teams/engineering-manager/SKILL.md:24-30` obliga a resolver toda delegación con `--platform opencode`. Sin embargo, `.pm-harness/adapters/adapters.json:37-66` instala y materializa también Claude, con niveles de esfuerzo diferentes a OpenCode (`:58-65` frente a `:26-35`).

**Impacto:** una delegación originada en Claude registra/clampa esfuerzo conforme a la plataforma equivocada, debilitando provenance y pudiendo solicitar un nivel no soportado.

**Remediación específica:** sustituir el literal por `<host>` y exigir detección/inyección del host en FACTS; añadir tests de routing para OpenCode y Claude que validen formato de ID, provider y effort permitido.

### ARN-002 — Alta — Falta adaptador Codex y el catálogo activo viola el formato OpenCode

**Evidencia estática:** `.pm-harness/adapters/adapters.json:4-121` declara OpenCode, Claude, Cursor, OpenClaw y Hermes, pero no Codex. El contexto instalado sólo anuncia superficies Claude/OpenCode (`AGENTS.md:9-15`). OpenCode exige IDs `provider/model` (`.pm-harness/adapters/adapters.json:26-35`), mientras `.pm-harness/model-router.json:84-90` registra sólo `gpt-5`, y la resolución de `TASK-0007` queda sin provider (`.pm-harness/model-router.json:220-234`).

**Impacto:** Codex no tiene materialización nativa ni clamping de effort; para OpenCode, el ID activo no permite identificar proveedor ni verificar que corresponda a un modelo realmente configurable. El provenance se degrada a fallback ambiguo.

**Remediación específica:** añadir adaptador Codex con archivos/contexto/agentes/formato/model discovery soportados y tests de materialización; hacer que `models set` valide el `id_format` de la plataforma; registrar IDs OpenCode completos y rechazar routing cuando no se conoce el host.

**Severidad: Media**

### COD-004 — Media — No existe gate de drift entre plantilla canónica y artefactos presentes

**Evidencia estática:** `.gitignore:1` ignora todo `generated/`. El artefacto `generated/chat-medium-localhost/manifest.json:1-22` conserva el esquema anterior y sólo ocho required files, mientras `manifests/chat.json:7-19` exige once. `ai_server_generator/validator.py:10-29` requiere campos que ese manifest viejo no tiene.

**Evidencia ejecutada:** `validate generated/chat-medium-localhost` terminó en código 1 con once errores; los workspaces `ornith-medium-localhost` y `phi4-good-localhost` terminaron en código 0.

**Impacto:** el checkout puede contener ejemplos operativos divergentes aunque la suite principal esté verde; un operador puede escoger un workspace antiguo ignorado y fallar fuera del flujo de revisión.

**Remediación específica:** mantener fixtures dorados mínimos versionados fuera de `generated/`, regenerarlos en CI y comparar con la salida esperada normalizando sólo metadatos volátiles; agregar un comando `validate-all`/`drift-check` que recorra workspaces locales y falle con una lista clara.

## Hallazgos de operación y DevOps

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

## Dimensión: Rendimiento y runtime

**Severidad: Alta**

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

**Severidad: Media**

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

## Dimensión: Producto y experiencia de operador

**Severidad: Crítica**

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

**Severidad: Alta**

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

**Severidad: Media**

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

## Plan de mejora en cuatro fases

### Fase 0 — Bloqueadores

**Estimación aproximada:** 1–2 semanas de trabajo concentrado, más una validación en host controlado.

- Eliminar credenciales predecibles, proteger secretos en disco y hacer que cualquier perfil LAN falle cerrado si no existe una protección efectiva.
- Confinar toda salida reemplazable al árbol generado, exigir identidad verificable del workspace y aplicar staging más reemplazo atómico/recuperable.
- Unificar el contrato de ubicación del modelo entre preflight, manifiesto y Compose; validar existencia, legibilidad, hash y montaje antes de declarar preparación.
- Añadir regresiones negativas para rutas destructivas, saltos de línea/inyección, secretos débiles y workspaces sin modelo.

**Estándares a institucionalizar:** secure-by-default para red y secretos; prohibición de borrado fuera de roots dedicados; escrituras multiarchivo atómicas; validación fail-closed de artefactos antes de cualquier arranque.

### Fase 1 — Fiabilidad

**Estimación aproximada:** 2–4 semanas, incluida una matriz de pruebas offline y de integración Docker en un host identificado.

- Serializar JSON/YAML/dotenv con herramientas contextuales y validar entradas mediante gramáticas estrictas.
- Separar validación estructural, preparación del host y salud de runtime con resultados y códigos de salida inequívocos.
- Hacer que arranque y smoke esperen readiness con timeout, validen la respuesta real, respeten autenticación y terminen en error ante fallos.
- Convertir presets en contratos versionados de artefacto, cuantización, RAM, ruta, origen y checksum.
- Resolver scripts respecto de su propia ubicación y probarlos desde distintos directorios de trabajo.

**Estándares a institucionalizar:** contratos tipados por formato; códigos de salida como API; readiness acotada; smoke tests con aserciones semánticas; fixtures adversariales para CLI y plantillas.

### Fase 2 — Excelencia operativa

**Estimación aproximada:** 2–3 semanas para automatización inicial y documentación verificable.

- Fijar dependencias e imágenes por versión/digest, generar lock con hashes y SBOM, y automatizar escaneos de dependencias e imagen.
- Crear CI que ejecute pruebas, parseo de Compose, sintaxis de scripts, drift plantilla/artefacto y gates del harness.
- Medir latencia real, percentiles, tokens por segundo y pico de memoria, registrando hardware, runtime, configuración y hash del modelo.
- Entregar procedimientos ejecutables y probados de backup, restore, rollback, parada e incidente, con evidencia de simulación.
- Completar licencia del proyecto e inventario trazable de componentes, imágenes y modelos de terceros.

**Estándares a institucionalizar:** builds reproducibles; provenance/SBOM obligatoria; observabilidad basada en métricas numéricas; runbooks ejecutables; prueba periódica de recuperación.

### Fase 3 — Pulido continuo

**Estimación aproximada:** 3–5 días para establecer la línea base y luego 0.5–1 día por ciclo mensual o por release.

- Mantener ejemplos y ayuda del CLI verificados contra la implementación, separando explícitamente capacidades implementadas, experimentales y planificadas.
- Revisar coherencia de idioma, accesibilidad terminal y mensajes accionables sin depender de color.
- Verificar materialización/routing en cada plataforma soportada, eliminar formatos inválidos y reducir permisos nativos de workers al mínimo necesario.
- Ejecutar auditoría independiente por fase o mensualmente y convertir defectos no cubiertos en reglas/gates versionados.

**Estándares a institucionalizar:** documentación ejecutable; matriz de compatibilidad por plataforma; mínimo privilegio; auditoría recurrente con trazabilidad de hallazgo a test, gate y runbook.

## Verificación de integración

| Comando/comprobación | Resultado | Código |
|---|---|---:|
| Verificación mecánica de bloques, encabezados, IDs, severidades y fortalezas contra los cuatro insumos | `integrity_check=PASS`; 35/35 bloques exactos; 4/4 secciones de fortalezas exactas | 0 |
| `docker --version` | Docker 29.6.1, build 8900f1d | 0 |
| `python3 --version` | Python 3.14.5 | 0 |
| `python3 -m pip --version` | pip 26.1.1 para Python 3.14 | 0 |
| `python3 -m unittest` | 12 pruebas; `OK` | 0 |
| `python3 -m pip check` | `wheel 0.47.0 requires packaging, which is not installed.` | 1 |
| `python3 .pm-harness/bin/harness.py validate` | 7 manifiestos y 11 notas; sin errores ni advertencias | 0 |
| `python3 .pm-harness/bin/harness.py agents check` | OpenCode y Claude sin agentes faltantes | 0 |
| `python3 .pm-harness/bin/harness.py wiki check` | Sin errores ni advertencias | 0 |

`python3 .pm-harness/bin/harness.py plan check TASK-0007` no se ejecutó: la excepción de alcance reserva la comprobación y modificación del plan compartido al manager. `python3 .pm-harness/bin/harness.py changelog check --task TASK-0007` no se ejecutó porque esta integración no cambió comportamiento de producto.

## Reconciliación de integridad

- Hallazgos consolidados: 35.
- Encabezados de hallazgo únicos: 35.
- Encabezados repetidos: 0.
- Distribución: 3 críticos, 20 altos, 12 medios y 0 bajos.
- Cada ID de hallazgo aparece exactamente una vez como encabezado de hallazgo; las referencias cruzadas internas se conservaron literalmente cuando formaban parte del contenido original.
