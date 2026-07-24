# Ledger de remediación

## Alcance y restricciones

Este ledger deriva exclusivamente de los cuatro artefactos inmutables y de los seis fragmentos de checklist de la ejecución actual. No aplica remediaciones, no publica ni hace `push`, no inicia un modelo y no convierte evidencia estática en una afirmación de runtime. Las comprobaciones que requieren daemon, imagen, modelo, firewall, host identificado o revisión jurídica permanecen calificadas hasta obtener evidencia independiente.

Fallos y límites de línea base que deben conservarse al ejecutar la remediación:

- `python3 -m pip check` falla porque `wheel 0.47.0` requiere `packaging`, que no está instalado.
- Docker CLI está presente, pero no hubo daemon disponible ni ejecución de imagen, contenedor o modelo.
- Codex no figura en los adaptadores locales; el modelo `gpt-5` procede de fallback y no pudo recibir clamping de esfuerzo de plataforma.

## Clusters de causa raíz

| Cluster | Causa raíz deduplicada |
|---|---|
| C1 | Generación segura, confinamiento de paths, serialización contextual y reemplazo transaccional. |
| C2 | Autenticación LAN, secretos, TLS, allowlist, validación de controles y aislamiento de red/contenedor. |
| C3 | Contrato de modelo, validación por niveles, readiness, smoke/benchmark y ajuste verificable al host. |
| C4 | Dependencias, imagen, fixtures, build y CI reproducibles. |
| C5 | Scripts operativos, documentación ejecutable, observabilidad, backup, restore e incidentes. |
| C6 | Routing, adaptadores, permisos y conformance del PM Harness. |
| C7 | Condiciones de distribución, metadata legal y pulido de producto sujeto a decisión. |

## Ledger por hallazgo

| Finding | Severity | Cluster | Declared owner role | Planned files/surface | Test/evidence | Initial status |
|---|---|---|---|---|---|---|
| SEC-001 | Crítica | C2 | security-engineer | `render.py`, plantilla `.env`, start y preflight | secreto no-placeholder; modo `0600`; negativos vacío/débil | planned |
| UX-20260724-002 | Crítica | C1 | ux-dev | política de output en `render.py`, CLI y README | negativos de roots superiores, marcador y symlinks; backup recuperable | planned |
| OPS-001 | Crítica | C3 | ml-platform-engineer | CLI, render, Compose, manifest y validator | bind host/contenedor estructural; runtime queda sujeto a daemon/modelo | planned |
| SEC-002 | Alta | C2 | security-engineer | Compose LAN, proxy/TLS, firewall/preflight y runbooks | CIDR aplicado y fail-closed; prueba viva calificada hasta host LAN | qualified |
| SEC-003 | Alta | C1 | security-engineer | validación CLI; emisores JSON/YAML/dotenv | regresiones NUL/CR/LF, comillas e inyección Compose | planned |
| SEC-004 | Alta | C2 | security-engineer | validator estructural y `docker compose config` | mutación individual de bind, auth, TLS, CIDR, secreto y privilegios | planned |
| PERF-001 | Alta | C3 | ml-systems-engineer | presets, CLI, render y bind mount del modelo | rutas relativas, absolutas, con espacios y archivo ausente | planned |
| PERF-002 | Alta | C3 | ml-systems-engineer | catálogo versionado de modelos y cálculo de memoria | metadata/hash obligatorios; GO/NO-GO; ajuste real calificado hasta host/modelo | qualified |
| PERF-003 | Alta | C3 | ml-systems-engineer | smoke/benchmark generado y legacy | HTTP/JSON estricto; métricas numéricas; benchmark real calificado hasta runtime | planned |
| PERF-004 | Alta | C3 | ml-platform-engineer | start, wizard, Compose y nuevo stop | estados de salud, timeout, logs y exit no cero; runtime sujeto a daemon | planned |
| UX-20260724-001 | Alta | C5 | ux-dev | wrappers start/validate/smoke y README | ejecución desde root, workspace y tercer CWD | planned |
| UX-20260724-003 | Alta | C3 | ux-dev | CLI, presets, manifest, Compose y guía humana | existencia, tipo, legibilidad, extensión y paths host/contenedor | planned |
| UX-20260724-004 | Alta | C3 | ux-dev | validator, CLI, README y roadmap | niveles estructura/host/runtime y lista explícita de no verificado | planned |
| UX-20260724-005 | Alta | C3 | ux-dev | smoke/benchmark y propagación de códigos del wizard | fallos curl/transporte/HTTP/JSON; latencia real; reporte sin falso PASS | planned |
| COD-001 | Alta | C1 | ml-platform-engineer | `render.py` y tests de `--force` | confinamiento bajo `generated`, roots protegidos y symlinks | planned |
| COD-002 | Alta | C1 | ml-platform-engineer | render y plantillas JSON/YAML/dotenv | comillas, CR/LF, `:`, `#`, `${...}` y Unicode | planned |
| COD-003 | Alta | C1 | ml-platform-engineer | staging/rename/backup en render y manifest canónico | fallo durante render conserva versión previa; hash determinista | planned |
| OPS-002 | Alta | C2 | security-engineer | secretos, Compose LAN, start y runbook | secret file/store; CIDR válido; NO-GO sin enforcement verificable | planned |
| OPS-003 | Alta | C3 | ml-platform-engineer | smoke estricto y benchmark diagnóstico | `.env` con lectura mínima, `mktemp`/`trap`, HTTP 200 y JSON | planned |
| OPS-004 | Alta | C4 | ml-platform-engineer | digest Compose, locks Python/OpenCode, SBOM y actualización | instalación desde locks; resolución de digest; escaneo CI | planned |
| OPS-005 | Alta | C4 | ml-platform-engineer | workflows CI, configuración lint/type/coverage y gates | matriz Python, unit, pip check, Compose, shell, fixtures, harness y scanners | planned |
| ARN-001 | Alta | C6 | engineering-manager | contrato de manager, adapters y tests de routing | host inyectado; ID/provider/effort correctos en OpenCode y Claude | escalated |
| ARN-002 | Alta | C6 | engineering-manager | pack/engine: adaptador Codex, router y materialización | discovery, formato de ID y rechazo de host desconocido | escalated |
| SEC-005 | Media | C4 | security-engineer | digest, locks con hashes, SBOM, CI y política de actualización | reproducibilidad y escaneo; no afirmar ausencia de CVE sin scanner | planned |
| SEC-006 | Media | C2 | security-engineer | hardening Compose raíz y plantilla | invariantes UID/GID, caps, PIDs, recursos; runtime calificado hasta daemon | planned |
| LEG-001 | Media | C7 | product-manager | `pyproject.toml`, licencia, notices/SBOM y metadata de presets | revisión jurídica por digest/catálogo y sólo si se distribuye | qualified |
| PERF-005 | Media | C4 | ml-systems-engineer | digest/version/flags en Compose y manifest | compatibilidad CI; benchmark de regresión calificado hasta runtime | planned |
| UX-20260724-006 | Media | C5 | product-manager | roadmap, help y manifest de capacidades | tabla implementado/experimental/planificado; ejemplos contra `--help` | planned |
| UX-20260724-007 | Media | C5 | ux-dev | argparse y ayuda de CLI | sin subcomando retorna 2; defaults, riesgos y sugerencias visibles | planned |
| COD-004 | Media | C4 | ml-platform-engineer | fixtures dorados y `validate-all`/`drift-check` | regeneración CI y enumeración completa de drift | planned |
| OPS-006 | Media | C5 | ml-platform-engineer | runtime/proxy, métricas, logs, benchmark y runbook | valores numéricos o `NO MEDIDO`; runtime sujeto a daemon/modelo | qualified |
| OPS-007 | Media | C5 | ml-platform-engineer | scripts de backup/restore/rollback y runbook LAN | checksums, idempotencia y restore drill; ejercicio vivo calificado | planned |
| OPS-008 | Media | C5 | ux-dev | docs de perfiles, scripts y Compose project directory | coherencia documental y ejecución desde múltiples CWD | planned |
| ARN-003 | Media | C6 | engineering-manager | pack/adapters: permisos de rol y gate de materialización | worker sin delegación ni escritura en stores ajenos | escalated |
| ARN-004 | Media | C6 | engineering-manager | suite versionada de conformance engine/pack | state machine, planes, checksums, memoria, routing y migraciones | escalated |

## Orden de ejecución por cluster

1. **C1**, para impedir pérdida de datos e inyección antes de regenerar cualquier artefacto.
2. **C2**, para mantener LAN en `NO-GO` hasta que secreto, TLS y allowlist sean controles efectivos.
3. **C3**, para alinear el modelo, hacer honestos validate/start/smoke y separar evidencia estructural de runtime.
4. **C4**, para fijar los insumos y ejecutar automáticamente los gates de las fases anteriores.
5. **C5**, para cerrar operación, documentación, observabilidad y recuperación sobre contratos ya estables.
6. **C6**, mediante escalación al owner del pack/engine y sin parche local oportunista.
7. **C7**, sólo tras confirmar distribución y obtener la revisión jurídica o decisión de producto aplicable.

## Racional de deduplicación

Los hallazgos conservan identidad y fila propias, pero una causa compartida debe implementarse una sola vez y producir evidencia reutilizable. El contrato único `host_model_path`/`container_model_path` cubre OPS-001, PERF-001 y UX-20260724-003; el confinamiento y reemplazo transaccional cubren UX-20260724-002, COD-001 y COD-003; los emisores seguros cubren SEC-003 y COD-002; el smoke estricto cubre PERF-003, UX-20260724-005 y OPS-003; digest, locks, SBOM y CI cubren SEC-005, PERF-005, OPS-004 y OPS-005. La evidencia compartida se enlazará desde cada finding sin fusionar ni cerrar IDs por asociación.

## Criterios de cierre

- Un estado `planned` autoriza sólo trabajo bounded dentro del repositorio y exige test asociado; no equivale a PASS.
- Un estado `qualified` exige evidencia externa o una condición previa y no permite declarar runtime, LAN safety, rendimiento o conformidad legal.
- Un estado `escalated` requiere cambio gobernado de pack/engine o decisión del superior; no se remedia alterando artefactos instalados de forma aislada.
- No se publicará, hará `push`, descargará un modelo ni afirmará éxito en vivo como parte de este ledger.

---

# Amendment 1 — Verificación de remediación (2026-07-24)

Enmienda append-only. No reescribe el ledger anterior: la columna
`Initial status` conserva su valor original y esta sección registra el estado
**verificado** contra el árbol de trabajo, con la evidencia que lo sostiene.

## Contexto

El ledger original quedó con todos los hallazgos en `planned`/`qualified`/
`escalated`, pero la remediación de los clusters C1, C2 y C3 sí se ejecutó y
permanece sin commitear. Esta enmienda cierra esa brecha de trazabilidad.

## Límites de evidencia de esta verificación

Sin cambios respecto de la corrida original: **no hubo daemon de Docker, imagen,
contenedor ni modelo en vivo**. Todo lo marcado `implemented` aquí es evidencia
estructural, de configuración o de prueba unitaria. Nada en esta enmienda
convierte evidencia estática en una afirmación de runtime, rendimiento o LAN
safety.

Línea base de la verificación: `python3 -m unittest` → 32 tests, OK.
Los cuatro artefactos inmutables siguen verificando contra
`pre-remediation.sha256`.

## Estado verificado por hallazgo

| Finding | Initial | Verificado | Evidencia |
|---|---|---|---|
| SEC-001 | planned | implemented | No se genera credencial alguna: `--auth bearer-token` es rechazado en `build_context`. `.env` se escribe en modo `0600` y el validador lo exige. |
| UX-20260724-002 | planned | implemented | `resolve_output_path` exige descendiente estricto de `generated/` y rechaza travesía por symlink. Comprobado: `--out ../evil` y `--out generated/../../evil` rechazados. |
| OPS-001 | planned | implemented | Contrato `host_model_path`/`container_model_path` presente en manifest, bind de Compose y `.env`; el validador cruza los tres. |
| SEC-002 | qualified | superseded | LAN ya no se genera: `--access lan` es rechazado. La condición externa deja de aplicar mientras LAN siga fail-closed. |
| SEC-003 | planned | implemented | Escapado contextual verificado con payload de inyección: YAML entrecomillado vía `json.dumps`, dotenv en comilla simple escapada, JSON válido. |
| SEC-004 | planned | implemented | El validador comprueba controles efectivos del Compose (bind, usuario no-root, caps, `read_only`, pids, límites), no declaraciones. |
| PERF-001 | planned | implemented | Ruta de modelo resuelta a absoluta; probada con rutas relativas y con espacios. |
| PERF-002 | qualified | qualified | Contrato de modelo versionado y presente, pero `metadata_status` sigue siendo `planning-assumption-only`; el ajuste real exige host y modelo. |
| PERF-003 | planned | implemented | `smoke_benchmark.sh` exige HTTP 200, valida la forma del JSON de chat-completion y rechaza timings no numéricos. Ejecución real sigue sujeta a runtime. |
| PERF-004 | planned | implemented | `scripts/stop.sh` generado, con timeout acotado y validado. |
| UX-20260724-001 | planned | implemented | Los scripts resuelven su propio workspace vía `SCRIPT_DIR`, por lo que corren desde cualquier CWD. |
| UX-20260724-003 | planned | implemented | Igual que OPS-001; el wizard además exige `./models/<preset>.gguf` antes de generar. |
| UX-20260724-004 | planned | implemented | `validate --tier structure|host|runtime` con listado explícito de lo NO VERIFICADO en cada nivel. |
| UX-20260724-005 | planned | implemented | Cubierto por el smoke estricto; los códigos de salida se propagan. |
| COD-001 | planned | implemented | Igual que UX-20260724-002; `--force` además exige marcador de propiedad del generador. |
| COD-002 | planned | implemented | Igual que SEC-003. |
| COD-003 | planned | implemented | Render a staging, validación previa al swap, `os.replace` atómico, backup con timestamp y rollback ante fallo. Fingerprint determinista. |
| OPS-002 | planned | superseded | Igual que SEC-002: no hay modo LAN que endurecer. |
| OPS-003 | planned | implemented | Smoke con `mktemp`/`trap`, lectura mínima y aserciones estrictas. |
| OPS-004 | planned | **partial** | Dependencias Python fijadas (`requirements.txt`, `requirements-dev.txt`) y `pip-audit` en CI. **La imagen del contenedor sigue en tag flotante `ghcr.io/ggerganov/llama.cpp:server`, sin digest.** Sin SBOM. |
| OPS-005 | planned | implemented | `.github/workflows/ci.yml` (matriz 3.10–3.14) ejecutando `scripts/ci.sh` con los gates declarados. |
| ARN-001 | escalated | escalated | Sin cambio; corresponde al owner del pack/engine. |
| ARN-002 | escalated | escalated | Sin cambio. |
| SEC-005 | planned | **partial** | Igual que OPS-004: falta digest de imagen y SBOM. |
| SEC-006 | planned | implemented | Compose con usuario no-root, `cap_drop: ALL`, `no-new-privileges`, root FS read-only, tmpfs acotado, `pids_limit` y límites de CPU/memoria. Runtime sigue calificado. |
| LEG-001 | qualified | **open** | No existe archivo `LICENSE` ni metadata de licencia en `pyproject.toml`. Sigue sujeto a decisión de distribución del Director. |
| PERF-005 | planned | **partial** | Flags y versión en Compose/manifest, pero sin digest (ver OPS-004). |
| UX-20260724-006 | planned | **open** | No existe tabla implementado/experimental/planificado. |
| UX-20260724-007 | planned | implemented (en esta enmienda) | La invocación sin subcomando ahora imprime ayuda en stderr y retorna 2. Test: `test_bare_invocation_is_a_usage_error`. |
| COD-004 | planned | **partial** | `scripts/ci.sh` compara el árbol generado contra `planned_files()`, pero no existe fixture dorado commiteado, por lo que no se asegura drift byte a byte. |
| OPS-006 | qualified | qualified | Sin cambio; exige daemon y modelo. |
| OPS-007 | planned | **open** | No existen scripts de backup/restore/rollback. |
| OPS-008 | planned | implemented (en esta enmienda) | `README.md` y `docs/lan-safe-runbook.md` corregidos (ver «Deriva documental» abajo). |
| ARN-003 | escalated | escalated | Sin cambio. |
| ARN-004 | escalated | escalated | Sin cambio. |

## Deriva documental corregida en esta enmienda (OPS-008)

La documentación afirmaba capacidades que el código rechaza. Esto es
relevante para seguridad porque instruía a operadores hacia una exposición LAN
inexistente:

1. `README.md` declaraba que «LAN generation is opt-in and requires
   `--auth bearer-token` and `--lan-allowlist`». Los tres argumentos son
   **rechazados**. Corregido a fail-closed explícito.
2. `README.md` documentaba `Decision: GO`, que `matrix` nunca emite: sólo
   produce `WARN` o `NO-GO`. Corregido.
3. `README.md` instruía copiar el `.gguf` dentro del workspace; el Compose lo
   monta read-only desde su ruta absoluta de host desde la remediación de
   OPS-001. Corregido.
4. `docs/lan-safe-runbook.md` se titulaba «LAN opt-in» y presentaba un checklist
   accionable. Reencabezado como estado fail-closed y requisitos de diseño no
   implementados.
5. `README.md` no documentaba `wizard`, `stop.sh` ni `validate --tier`.
   Añadidos.

## Hallazgos nuevos de esta verificación

No estaban en la corrida original. Ambos corregidos con test de regresión.

| ID | Severidad | Descripción | Estado |
|---|---|---|---|
| COD-005 | Alta | El wizard resolvía `--out` relativo contra el CWD del invocante mientras el renderer lo resuelve contra la raíz del proyecto. Ejecutado desde cualquier otro directorio, la comprobación de sobrescritura apuntaba a una ruta distinta de la que se escribía: el wizard no detectaba el workspace existente y el fallo emergía dentro del renderer con una guía equivocada (`--force` en vez de `--overwrite`). | fixed |
| UX-20260724-008 | Media | Sin terminal, el wizard llamaba `input()` y abortaba con traceback `EOFError` **después** de haber generado el workspace. Afectaba a la selección de preset/perfil y al prompt de arranque. Ahora exige los flags correspondientes con error limpio, y en modo `--run ask` sin TTY declina arrancar el servidor en vez de fallar. | fixed |

## Trabajo pendiente tras esta enmienda

Ordenado por prioridad, sin autorización implícita para ejecutarlo:

1. **OPS-004 / SEC-005 / PERF-005** — fijar la imagen del contenedor por digest y
   emitir SBOM. Requiere red o daemon para resolver el digest; **no debe
   inventarse un digest**. Verificar además si el repositorio canónico de la
   imagen migró de `ggerganov` a `ggml-org`.
2. **OPS-007** — scripts de backup/restore/rollback con checksums e idempotencia.
3. **COD-004** — fixture dorado commiteado para drift byte a byte.
4. **UX-20260724-006** — tabla de capacidades implementado/experimental/planificado.
5. **LEG-001** — decisión de distribución del Director y, si aplica, `LICENSE` y
   metadata en `pyproject.toml`.
6. **ARN-001..004** — escalados al owner del pack/engine; sin parche local.

---

# Amendment 2 — Cierre de pendientes (2026-07-24)

Enmienda append-only. Ejecutada tras aprobación explícita del Director para
resolver todo lo pendiente y añadir lo faltante, con una decisión de producto
registrada: **el proyecto es privado, de uso personal, y no se distribuirá.**

## Evidencia externa obtenida en esta corrida

A diferencia de las corridas anteriores, **hubo acceso de red al registro de
contenedores** (sólo lectura de metadata; no se descargó ninguna imagen). Sigue
sin haber daemon de Docker ni modelo en vivo, así que las afirmaciones de
runtime, rendimiento y calidad continúan sin verificar.

Línea base: `python3 -m unittest` → 37 tests, OK. `shellcheck` 0.11.0 ejecutado
sobre todos los scripts del repositorio y del workspace generado: sin hallazgos.

## Hallazgos cerrados en esta enmienda

| Finding | Estado anterior | Estado | Evidencia |
|---|---|---|---|
| OPS-004 | partial | **closed** | Imagen fijada por digest en `render.py` como fuente única; el validador rechaza cualquier referencia distinta, tanto en el texto del Compose como en la salida de `docker compose config`. `scripts/resolve_image_digest.sh` permite mover el pin deliberadamente. |
| SEC-005 | partial | **closed** | `sbom.json` (CycloneDX 1.5) inventaria dependencias Python fijadas y la imagen con su digest. `scripts/generate_sbom.py --check` es gate de CI y falla si el pin cambia sin regenerar el inventario. |
| PERF-005 | partial | **closed** | Digest y flags presentes en Compose y manifest; el benchmark de regresión sigue calificado hasta runtime. |
| OPS-007 | open | **closed** | `backup_workspace.sh`, `restore_workspace.sh` y `rollback_workspace.sh`, con checksum SHA-256 verificado antes de escribir, reemplazo atómico y preservación de lo sustituido. Cubierto por `test_backup_restore_and_rollback_round_trip`, que incluye el negativo de archivo manipulado. |
| COD-004 | partial | **closed** | Fixture dorado commiteado en `tests/golden/`, comparado byte a byte. Se normalizan sólo dos valores dependientes de máquina (raíz absoluta del proyecto y el fingerprint, que es un hash sobre un contexto que la contiene); todo lo demás se compara literalmente. |
| UX-20260724-006 | open | **closed** | Tabla de capacidades en `README.md` con estados Implemented / Refused / Planned, contrastada contra `--help` y contra `list setups|profiles`. |
| LEG-001 | qualified | **closed por decisión del Director** | No habrá licencia: proyecto particular de uso personal, sin distribución. Registrado en `pyproject.toml` con el clasificador `Private :: Do Not Upload`, que hace fallar una publicación accidental en PyPI. Si alguna vez se distribuye, licencia y revisión de terceros vuelven a ser prerrequisito. |
| ARN-001..004 | escalated | **escalado formalmente** | `ESC-0001` en `.pm-harness/escalations/pending/`, con manifiesto de estado y recomendación: upstream para ARN-001/002, aceptación documentada del riesgo para ARN-003/004 en un proyecto privado de operador único. |

## Hallazgos nuevos de esta enmienda

| ID | Severidad | Descripción | Estado |
|---|---|---|---|
| OPS-009 | **Alta** | La imagen de servicio referenciaba `ghcr.io/ggerganov/llama.cpp:server`, un repositorio que **ya no existe y devuelve 404**. Ningún workspace generado podía arrancar. El repositorio canónico es `ghcr.io/ggml-org/llama.cpp`. Corregido y fijado por digest (índice multi-arch: linux/amd64, arm64, s390x). La corrida original no lo detectó porque no había red ni daemon para resolver la referencia. | fixed |
| OPS-010 | **Alta** | El gate de `shellcheck` de CI **nunca pudo pasar**: el idioma `CDPATH= cd` dispara SC1007 en todos los scripts generados y de repositorio preexistentes. CI se había declarado implementado (OPS-005) sin haberse ejecutado nunca de forma completa. Sustituido por `CDPATH='' cd`, semánticamente idéntico; los 11 scripts pasan shellcheck 0.11.0 sin hallazgos. | fixed |
| COD-006 | Media | El `.env` del fixture dorado quedaba capturado por la regla `.env` de `.gitignore`, por lo que no se habría commiteado y el gate de drift habría fallado en un checkout limpio. Añadida negación acotada `!tests/golden/**/.env`. | fixed |

OPS-009 y OPS-010 tienen la misma causa raíz que el resto de esta auditoría: se
declaró implementado aquello cuya evidencia nunca llegó a ejecutarse.

## Estado final

Los 35 hallazgos originales están cerrados, calificados por límite de evidencia,
o escalados con dueño explícito. No queda ningún hallazgo en `planned`.

Lo que sigue sin verificarse, y no debe afirmarse sin daemon y modelo en vivo:

- Arranque real del contenedor, salud del endpoint y calidad de respuesta.
- Rendimiento (latencia, throughput) y ajuste real del modelo al host.
- El digest fijado corresponde a una imagen que **no se ha ejecutado**; sólo se
  verificó que la referencia existe y qué plataformas cubre.

---

# Amendment 3 — Decisiones del Director y refuerzo de CI (2026-07-24)

Enmienda append-only tras aprobación del Director de los cuatro pasos de cierre.

- **ARN-001..004** — resueltos vía `ESC-0001`, ahora en
  `.pm-harness/escalations/resolved/` con el manifiesto de estado en `closed`.
  Decisión: ARN-001/002 al owner del pack/engine (upstream, sin parche local);
  ARN-003/004 riesgo aceptado y documentado por ser proyecto privado de operador
  único. Revisable si se suman operadores.
- **CI** — a petición del Director se añadió cobertura funcional: `scripts/ci.sh`
  ahora genera, valida y corre `docker compose config` sobre **todos** los
  presets del catálogo (la lista sale del propio CLI, sin duplicación), más un
  `python3 -m compileall`. Antes sólo se ejercitaba `ornith-9b/medium`.
- **Runtime** — el Director ejecutará la verificación en vivo (daemon + `.gguf`
  real) en la máquina destino tras el push. Los hallazgos calificados por falta
  de daemon/modelo permanecen calificados hasta esa corrida; esta enmienda no
  los cierra.
