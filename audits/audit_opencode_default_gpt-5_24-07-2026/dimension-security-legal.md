# Auditoría independiente — seguridad y aplicabilidad legal

**Tarea:** TASK-0007  
**Fecha:** 24-07-2026  
**Rol:** security-engineer  
**Modelo:** `gpt-5` (procedencia: fallback; Codex no figura en los adaptadores locales, por lo que no se pudo aplicar el ajuste de esfuerzo de la plataforma)  
**Veredicto:** **NO-GO para el perfil LAN** hasta corregir SEC-001, SEC-002 y SEC-003. El perfil localhost conserva una base razonable, con deuda de defensa en profundidad y cadena de suministro.

## Alcance y método

Se realizó un pase nuevo sobre el código, plantillas, configuración, dependencias, scripts, pruebas y documentación actuales. No se consultaron informes de auditoría anteriores. La revisión fue estática salvo las comprobaciones locales enumeradas al final; no se inició el servidor, no se descargaron imágenes, no se envió ninguna petición de inferencia y no se comprobó un firewall real.

Se revisaron:

- secretos, valores por defecto y salidas de consola;
- autenticación/autorización, exposición localhost/LAN, TLS, CORS, firewall y allowlist;
- límites de entrada, rutas, plantillas, comandos y contenedores;
- declaraciones Python y referencia de imagen;
- privilegios, montajes, red y artefactos generados;
- aplicabilidad legal derivada de la distribución del generador y de referencias de terceros.

## Fortalezas verificadas

- El modo por defecto es `localhost` (`ai_server_generator/presets.py:13-15`) y la plantilla publica el puerto en `127.0.0.1` para ese modo (`templates/chat/docker-compose.yml.j2:7-11`).
- La generación rechaza LAN sin selección de `bearer-token` y allowlist no vacía (`ai_server_generator/render.py:96-98`), con pruebas negativas (`tests/test_cli.py:302-342`).
- La ruta de salida se resuelve, permanece dentro del repositorio y excluye varios directorios protegidos (`ai_server_generator/render.py:39-53`).
- Las ejecuciones del wizard usan argv sin shell y un `cwd` explícito (`ai_server_generator/cli.py:407-426`); no se encontró `shell=True`, `eval`, `exec` ni `os.system` en el código de producto.
- El contenedor usa `no-new-privileges`, raíz de solo lectura y `tmpfs` limitado (`templates/chat/docker-compose.yml.j2:47-51`).
- `.env` está ignorado por Git (`.gitignore:11-15`) y la CLI no imprime el token. El `.env` local inspeccionado no contenía una variable de token, aunque su modo era `0644`.

## Hallazgos

### SEC-001 — Crítica — credencial LAN predecible y archivo de secreto legible por otros usuarios

**Evidencia exacta:** `ai_server_generator/render.py:103-111` asigna siempre `change-me-strong-token`; `templates/chat/env.j2:11-14` lo escribe en `.env`; `templates/chat/scripts/start_serving.sh.j2:11-15` y `templates/chat/scripts/validate_host.sh.j2:16-24` solo comprueban que las claves existan. Los archivos no-script se crean con `Path.write_text` sin fijar permisos (`ai_server_generator/render.py:185-191`); con el `umask` observado, `.env` queda `0644`.

**Impacto:** un workspace LAN recién generado puede arrancar con una credencial pública y conocida. Cualquier equipo que alcance el puerto puede autenticarse, consumir recursos, enviar contenido al modelo y acceder a capacidades futuras expuestas por el servidor. En un host multiusuario, otros usuarios locales pueden leer el secreto.

**Remediación específica:** no materializar un token fijo. Generar criptográficamente al menos 32 bytes o exigir inyección desde un gestor/archivo de secretos; escribir `.env` con modo `0600`; rechazar valores vacíos, el placeholder y secretos débiles tanto en validación como antes de `docker compose up`; documentar rotación y evitar incluir el secreto en manifiestos o logs.

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
