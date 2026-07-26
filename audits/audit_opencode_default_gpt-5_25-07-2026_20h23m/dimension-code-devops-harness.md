# Auditoría independiente de código, arquitectura, DevOps y Harness

## Alcance y método

- **TASK:** `TASK-0007`, únicamente todo 3.
- **AUDIT_DIR:** `audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/`.
- **Rol:** `ml-platform-engineer`.
- **Modo:** solo lectura; no se modificaron código, plan, estado ni artefactos de auditorías anteriores.
- **Fuentes:** plan aprobado, inventario fresco, checkout actual, `audits/INDEX.md`, normas actuales de `audits/standards/` y contratos locales de `.pm-harness/`.
- **Evidencia:** inspección estática y gates ejecutables; Docker daemon disponible, pero no se arrancó un modelo ni se afirmó salud runtime.

## Resumen ejecutivo

La arquitectura del generador tiene límites de salida, renderizado en staging, validación previa y reemplazo recuperable. El stack localhost está estructuralmente bien definido y las pruebas actuales pasan (`42` tests). Sin embargo, la integración de CI y Harness no es reproducible ni suficientemente verificable para cerrar la dimensión: CI conserva una dependencia a una suma de una auditoría histórica; la comprobación de agentes no valida contenido ni materialización; la plantilla shell no pasa ShellCheck sin renderizar; y la matriz de adaptadores no contiene un adaptador nativo Codex ni permisos por ruta/comando.

## Hallazgos

### COD7-001 — Medio — La plantilla shell no pasa la validación estática declarada

**Evidencia:** `templates/chat/scripts/validate_host.sh.j2:36-44` inserta `{{ host_model_path_yaml }}` directamente en shell. `shellcheck scripts/*.sh templates/chat/scripts/*.j2` terminó con **exit 1**, reportando `SC1083` en esa línea. `scripts/ci.sh:105-108` solo ejecuta `shellcheck` sobre scripts `.sh` de `scripts/` y del workspace generado, no sobre las plantillas `.j2`; por tanto CI no detecta el fallo antes de renderizar.

**Impacto:** una regresión en la plantilla canónica puede pasar CI aunque el artefacto generado sea el que se ejecuta. La evidencia de sintaxis es incompleta y el resultado depende de la expansión concreta del valor.

**Recomendación:** renderizar las plantillas en un fixture controlado y ejecutar `bash -n`/ShellCheck sobre el resultado; alternativamente mantener una comprobación específica que excluya sintaxis Jinja solo con una justificación verificable. Añadir casos con espacios, comillas, backslashes y Unicode en la ruta.

**Normas:** `audits/standards/CODE.md` — `STD-COD-002`; `audits/standards/OPS.md` — `STD-OPS-005`.

### OPS7-001 — Alto — CI depende de una auditoría histórica concreta

**Evidencia:** `scripts/ci.sh:138-145` ejecuta `shasum -a 256 -c audits/audit_opencode_default_gpt-5_24-07-2026/pre-remediation.sha256` y además ejecuta `pip_audit` sobre ese flujo. El plan y el inventario de esta ejecución prohíben usar esa auditoría anterior como entrada. La ruta no pertenece al `AUDIT_DIR` fresco.

**Impacto:** un checkout limpio puede fallar por ausencia o cambio de un artefacto histórico no derivado del estado actual; además, CI queda acoplado a la evidencia de una ejecución concreta y no a un contrato reproducible de fuentes. Esto impide usar el gate como prueba de la revisión actual.

**Recomendación:** eliminar la dependencia de rutas históricas o sustituirla por una verificación generada desde un manifiesto versionado y el conjunto canónico de archivos; hacer que la auditoría fresca congele sus propios hashes dentro de su `AUDIT_DIR`, sin convertirlos en dependencia global de CI.

**Normas:** `audits/standards/GATES.md` — Gate 1 y periodic independent audit; `audits/standards/OPS.md` — `STD-OPS-005`.

### OPS7-002 — Medio — El fallo de readiness deja el servicio levantado

**Evidencia:** `templates/chat/scripts/start_serving.sh.j2:40-55` ejecuta `compose up -d`, espera el endpoint y, al agotar el tiempo, solo imprime `ps` y logs y termina con `exit 1`; no ejecuta `compose down` ni deja un identificador de ejecución para recuperación automática.

**Impacto:** un arranque fallido puede dejar un contenedor no saludable, consumiendo CPU/RAM y ocupando el puerto. El operador recibe un error, pero el estado residual no queda contenido.

**Recomendación:** definir el comportamiento de fallo explícitamente: detener el stack que este comando levantó, conservar logs/evidencia y documentar la ruta de recuperación. Probar timeout, proceso muerto y reintento idempotente.

**Normas:** `audits/standards/OPS.md` — `STD-OPS-006`, `STD-OPS-007`; `audits/standards/GATES.md` — Gate 2, punto 4.

### OPS7-003 — Medio — Backup/restore no verifica el contenido completo antes de instalarlo

**Evidencia:** `scripts/restore_workspace.sh:70-89` extrae el tar y solo comprueba que exista una única entrada raíz, que sea directorio y que contenga `manifest.json`; no valida que las rutas sean descendientes seguras, que no haya symlinks, que coincidan los archivos planificados ni que el manifiesto sea válido antes de mover el destino en `scripts/restore_workspace.sh:91-103`.

**Impacto:** un archivo de backup alterado que conserve el checksum externo puede instalar contenido inesperado o enlaces dentro del workspace. La recuperación es atómica respecto al movimiento de directorios, pero no es una restauración semánticamente validada.

**Recomendación:** inspeccionar y validar la lista de miembros del tar antes de extraer/instalar, rechazar rutas absolutas, `..`, symlinks y archivos inesperados; ejecutar el validador del workspace en staging antes del reemplazo y registrar inventario/hash del contenido.

**Normas:** `audits/standards/CODE.md` — `STD-COD-003`; `audits/standards/OPS.md` — `STD-OPS-007`.

### HARNESS7-001 — Alto — `agents check` comprueba existencia, no contrato ni materialización íntegra

**Evidencia:** `.pm-harness/bin/harness_core.py:1513-1526` marca un agente como presente únicamente con `os.path.isfile(...)`. No comprueba el marcador `PM-HARNESS:AGENT`, frontmatter, formato nativo, `mode`, mapa de herramientas, ruta de skill ni que el archivo sea el generado para el miembro actual. La materialización escribe directamente con `open(dst, "w")` en `.pm-harness/bin/harness_core.py:1493-1499`.

**Impacto:** un archivo truncado, stale o con permisos/herramientas incorrectos produce `agents check` exitoso. Esto permite que una superficie invocable no corresponda al contrato gobernado del equipo.

**Recomendación:** validar contenido y frontmatter contra el roster, plataforma y formato del adaptador; comprobar marcador, referencia a la skill local, `mode` y herramientas permitidas; escribir de forma temporal y reemplazar atómicamente; añadir negativos para archivo vacío, plataforma equivocada y worker con `task: true`.

**Normas:** `audits/standards/HARNESS.md` — `STD-ARN-003`, `STD-ARN-004`; `.pm-harness/HARNESS-SPEC.md:440-475`.

### HARNESS7-002 — Alto — No existe adaptador nativo Codex en el checkout auditado

**Evidencia:** `.pm-harness/adapters/adapters.json:4-121` declara `opencode`, `claude`, `cursor`, `openclaw` y `hermes`, pero no `codex`. El inventario fresco registra que `.codex/` no aparece en el checkout; `.pm-harness/bin/harness_core.py:1463-1479` solo selecciona plataformas presentes en ese archivo y con `agents_dir`. `agents check` actual solo reporta OpenCode y Claude.

**Impacto:** el contrato de soporte multiplataforma no es completo: Codex no tiene formato, directorio, activación, descubrimiento ni materialización nativos. La ausencia queda fuera del gate aunque el Harness declare un modelo de adaptadores extensible.

**Recomendación:** decidir formalmente si Codex es host soportado para este proyecto. Si lo es, añadir adaptador nativo completo y pruebas de conformance; si no lo es, declararlo explícitamente fuera de soporte y retirar la expectativa normativa correspondiente del alcance local.

**Normas:** `audits/standards/HARNESS.md` — `STD-ARN-001`, `STD-ARN-002`, `STD-ARN-004`; `.pm-harness/HARNESS-SPEC.md:440-475`.

### HARNESS7-003 — Medio — Los punteros OpenCode no expresan permisos mínimos por ruta y comando

**Evidencia:** `.opencode/agents/ml-platform-engineer.md:4-11` habilita `bash`, `write`, `edit` y `read`; `.opencode/agents/security-engineer.md:4-11` expone el mismo conjunto. `.pm-harness/bin/harness_core.py:1451-1457` genera para cada worker el mismo mapa booleano desde `TOOL_NAMES`, diferenciando únicamente `task: false`; no hay restricciones por ruta, comando destructivo ni memoria de otro rol en el formato materializado.

**Impacto:** la superficie nativa describe capacidad general, no least privilege verificable. El prompt de rol puede pedir prudencia, pero no constituye una barrera ejecutable contra escrituras fuera de alcance o comandos destructivos.

**Recomendación:** definir permisos nativos por plataforma con alcance de paths/comandos, confirmar efectos destructivos y separar auditoría read-only de implementación. Añadir una prueba de materialización que compare el resultado con el contrato del rol y rechace capacidades no autorizadas.

**Normas:** `audits/standards/HARNESS.md` — `STD-ARN-003`; `.pm-harness/HARNESS-SPEC.md:453-470`.

## No-hallazgos y límites

- `ai_server_generator/render.py:93-112` mantiene la salida bajo `generated/`, rechaza el propio root y comprueba componentes symlink.
- `ai_server_generator/render.py:411-434` renderiza en staging, fija modos (`.env` 0600, scripts ejecutables) y escribe archivos con `O_EXCL`.
- `ai_server_generator/render.py:481-524` valida staging y conserva el workspace anterior antes del reemplazo; el reemplazo recupera el anterior si falla.
- `templates/chat/docker-compose.yml.j2:3-49` usa imagen por digest, usuario no-root, `cap_drop: ALL`, filesystem read-only, límites de CPU/memoria/PIDs y modelo read-only.
- `templates/chat/scripts/start_serving.sh.j2:16-34` comprueba modo de `.env`, bloquea credenciales/política LAN no soportadas y ejecuta validación de host antes de iniciar.
- `templates/chat/scripts/smoke_benchmark.sh.j2:8-9,22-64,100-152` usa directorio temporal con `trap`, exige HTTP 200, JSON de chat válido y timings numéricos; no se tomó como evidencia de runtime saludable.
- `python3 -m unittest` sí pasó 42 pruebas en este checkout; esto no cubre por sí solo la ausencia de los contratos señalados.
- No se verificó carga de un `.gguf`, salud de un modelo, rendimiento, compatibilidad real de imagen/UID ni eficacia de controles de red.

## Comandos y exit codes

| Comando | Exit | Tipo/evidencia |
|---|---:|---|
| `python3 -m unittest` | 0 | ejecutable; 42 tests, 42 OK |
| `python3 -m pip check` | 0 | ejecutable |
| `docker compose config --quiet` | 0 | estática contra Compose local |
| `python3 .pm-harness/bin/harness.py validate` | 0 | estática; 13 manifests, 29 notas |
| `python3 .pm-harness/bin/harness.py agents check` | 0 | existencia de punteros; no prueba integridad (hallazgo HARNESS7-001) |
| `python3 .pm-harness/bin/harness.py wiki check` | 0 | estática |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 | esperado: 11 todos siguen sin marcar |
| `python3 scripts/generate_sbom.py --check` | 0 | estática |
| `bash -n scripts/*.sh` | 0 | estática |
| `bash -n templates/chat/scripts/*.j2` | 0 | no detecta la expansión problemática |
| `shellcheck scripts/*.sh templates/chat/scripts/*.j2` | 1 | `SC1083` en `templates/chat/scripts/validate_host.sh.j2:36` |
| `ruff check .` | 127 | herramienta `ruff` no disponible como ejecutable |
| `mypy ai_server_generator` | 127 | herramienta `mypy` no disponible como ejecutable |

Los dos `127` no se interpretan como aprobación ni como defectos confirmados del código: son evidencia de que esos gates no fueron ejecutables en este entorno. No se ejecutó `scripts/ci.sh` porque crea/modifica `generated/.ci-fixture.*`, `artifacts/` y otros productos de CI, lo que violaría el límite de auditoría read-only.

## Resultado del todo 3

**Resultado:** `INCOMPLETE — findings recorded`.

El informe satisface la entrega de la dimensión con hallazgos nuevos y evidencia exacta, pero la dimensión no queda aprobada para remediación/cierre hasta resolver o escalar los siete hallazgos, especialmente la dependencia histórica de CI y la integridad/materialización de Harness.
