# Informe completo de auditoría independiente — TASK-0007

## Alcance y resultado

Esta integración corresponde únicamente al todo 6 y reúne los cuatro pases
frescos de seguridad/legal, código/DevOps/Harness, rendimiento/model-serving y
producto/UX. Es un snapshot **pre-remediación**. No se abrió la auditoría
anterior, no se comparan ejecuciones y ningún hallazgo se clasifica como
persistent, fixed o compared. Los informes de dimensión y el inventario son la
fuente inmutable de evidencia detallada.

Resultado: **INCOMPLETE — findings recorded**. El producto mantiene una
postura localhost-only y fail-closed para LAN; no hay GGUF en `models/`, por lo
que las afirmaciones de runtime, compatibilidad, rendimiento y calidad siguen
sin verificación viva.

## Fortalezas observadas

- La generación confina destinos bajo `generated/` y rechaza symlinks y
  entradas de control; `ai_server_generator/render.py:80-123`.
- La imagen de serving usa digest, el contenedor es no-root, elimina
  capacidades, limita recursos/PIDs, usa filesystem y modelo read-only;
  `ai_server_generator/render.py:44-55` y
  `templates/chat/docker-compose.yml.j2:28-49`.
- LAN, bearer token y allowlist no soportada se rechazan; el bind canónico es
  localhost; `ai_server_generator/render.py:258-273` y
  `templates/chat/docker-compose.yml.j2:6-7`.
- El renderer usa staging y conserva recuperación del workspace anterior;
  `ai_server_generator/render.py:411-524`.
- El flujo CLI diferencia estructura, host y runtime, y declara omisiones;
  `ai_server_generator/cli.py:227-247,354-370`.
- El paso de código ejecutó 42 pruebas con resultado 0 y los checks estáticos
  de Harness, Compose, SBOM y `pip check` fueron satisfactorios. Esto no
  constituye evidencia de runtime saludable ni de cierre de hallazgos.

## Totales de severidad

| Clasificación | Cantidad | Criterio de aplicación |
|---|---:|---|
| Alto aplicable al estado actual | 9 | Riesgos confirmados que bloquean integración segura o claims de runtime. |
| Medio aplicable al estado actual | 15 | Defectos confirmados de control, evidencia u operación. |
| Bajo aplicable en localhost-only | 1 | `SEC7-007`; se vuelve bloqueo antes de LAN. |
| Alto condicional | 1 | `LEG7-001`, obligatorio antes de distribución/publicación. |
| Total | 25 | 24 de estado actual + 1 condición de distribución. |

## Dimensiones aplicables

Las cuatro dimensiones son aplicables: el repositorio tiene CLI, templates y
helpers de terminal; generación y reemplazo de archivos; Compose, CI y
backups; presets y model-serving; y superficies PM Harness/OpenCode. No aplica
una dimensión gráfica separada porque el inventario y el pase UX solo
encontraron producto terminal-only: `ai_server_generator/cli.py:15-77` y
`templates/chat/scripts/start.sh.j2:1-5`.

## Hallazgos integrados

Cada entrada conserva el ID del pase fresco, severidad, evidencia exacta,
impacto y recomendación. Las líneas son evidencia del checkout observado.

### Altos

#### SEC7-001 — CI acoplada a checksum de auditoría histórica

- **Evidencia:** `scripts/ci.sh:138-139` verifica
  `audits/audit_opencode_default_gpt-5_24-07-2026/pre-remediation.sha256`.
- **Impacto:** CI depende de un snapshot ajeno al run actual y pierde una
  frontera de procedencia clara.
- **Recomendación:** usar una entrada explícita del run actual o separar el
  checksum de auditoría de CI; congelar y hashear el snapshot antes de
  remediar. **Norma:** `STD-SEC-005`.

#### OPS7-001 — CI depende de una auditoría histórica concreta

- **Evidencia:** `scripts/ci.sh:138-145` ejecuta checksum y `pip_audit` sobre
  la ruta histórica, fuera del `AUDIT_DIR` fresco.
- **Impacto:** un checkout limpio puede fallar por un artefacto histórico y el
  gate no prueba fuentes reproducibles del run actual.
- **Recomendación:** eliminar rutas históricas o sustituirlas por un manifiesto
  versionado del conjunto canónico; hashear el snapshot solo dentro del run.
  **Normas:** `GATES.md` Gate 1 y `STD-OPS-005`.

#### HARNESS7-001 — `agents check` valida existencia, no contrato

- **Evidencia:** `.pm-harness/bin/harness_core.py:1513-1526` solo usa
  `os.path.isfile`; la materialización escribe directamente en
  `.pm-harness/bin/harness_core.py:1493-1499`.
- **Impacto:** un puntero vacío, stale o con herramientas incorrectas puede
  pasar como agente gobernado.
- **Recomendación:** validar marcador, frontmatter, formato, modo, skill,
  herramientas y plataforma; materializar en temporal y reemplazar
  atómicamente. **Normas:** `STD-ARN-003`, `STD-ARN-004`.

#### HARNESS7-002 — Falta adaptador nativo Codex

- **Evidencia:** `.pm-harness/adapters/adapters.json:4-121` no declara Codex;
  `.pm-harness/bin/harness_core.py:1463-1479` solo selecciona plataformas del
  catálogo.
- **Impacto:** no existe formato, activación, descubrimiento ni materialización
  nativos para un host esperado.
- **Recomendación:** decidir soporte formal; si se soporta, añadir adaptador y
  conformance; si no, declarar Codex fuera de alcance. **Normas:**
  `STD-ARN-001`, `STD-ARN-002`, `STD-ARN-004`.

#### PERF7-001 — Presets sin contratos verificables de modelo

- **Evidencia:** `ai_server_generator/presets.py:6-23,33-115`,
  `ai_server_generator/cli.py:171-201` y `ai_server_generator/validator.py:346-373`;
  faltan los campos exigidos por `audits/standards/PERFORMANCE.md:19-31`.
- **Impacto:** se puede generar un workspace sin archivo, hash, tamaño o
  compatibilidad concreta vinculada al runtime.
- **Recomendación:** versionar contrato GGUF con origen, revisión, archivo,
  arquitectura, cuantización, bytes, SHA-256, chat template y RAM; separar
  “generable” de “verificado en host”. **Norma:** `STD-PERF-002`.

#### PERF7-002 — Memoria nominal, no validada contra el host

- **Evidencia:** límites de `6g`, `8g`, `10g` en `profiles/*.json:5-10`;
  cálculo fijo en `ai_server_generator/cli.py:223-247`; Docker Desktop con
  `8,321,798,144` bytes en `meta/inventory.md:50-64`.
- **Impacto:** un perfil puede parecer apto aunque supere el presupuesto del
  daemon; ningún resultado estático prueba carga.
- **Recomendación:** leer memoria real del daemon, calcular modelo+KV+buffers+
  reserva y devolver `NO-GO` sin margen; separar límite de contenedor,
  presupuesto Docker y RAM del host. **Norma:** `STD-PERF-002`.

#### PERF7-005 — Benchmark sin evidencia de throughput o memoria

- **Evidencia:** `templates/chat/scripts/smoke_benchmark.sh.j2:20-152` deja
  `Tokens per second | NOT_MEASURED` y `Response quality | NOT_MEASURED`;
  `logs/benchmarks/smoke-benchmark-20260725-142634.md:1-21` es placeholder.
- **Impacto:** HTTP 200 y timing cliente no son baseline de rendimiento,
  calidad, memoria o estabilidad.
- **Recomendación:** con GGUF autorizado registrar muestras/p50/p95 de TTFB,
  latencia, tokens/s y memoria, además de modelo, hash, host, digest, flags y
  configuración; fallar si faltan campos. **Normas:** `STD-PERF-003`,
  `STD-OPS-006`.

#### UX7-001 — Workspaces materializados pueden describir otro runtime

- **Evidencia:** renderer actual en `ai_server_generator/render.py:44-55` y
  template en `templates/chat/docker-compose.yml.j2:3-7`; workspace existente
  en `generated/ornith-medium-localhost/docker-compose.yml:2-8` y
  `generated/ornith-medium-localhost/README.md:5-11`.
- **Impacto:** el operador puede ejecutar una imagen, política de reinicio y
  contrato distintos del canónico.
- **Recomendación:** regenerar mediante migración controlada o marcar legacy;
  añadir drift-check y publicar digest/contrato exactos. **Norma:**
  `STD-COD-004`.

#### UX7-002 — Guía LAN contradice el contrato fail-closed

- **Evidencia:** rechazo CLI en `ai_server_generator/cli.py:276-279`; guía
  contradictoria en `docs/human-guide.md:98-110`; runbook correcto en
  `templates/chat/runbook.md.j2:16-21`.
- **Impacto:** operadores pueden seguir un camino muerto o inferir que una
  defensa manual habilita LAN.
- **Recomendación:** reemplazarlo por aviso planned/blocked y limitar ejemplos
  ejecutables a localhost hasta gateway, auth, allowlist y bypass tests.
  **Normas:** `STD-PR-001`, `STD-PR-002`.

### Medios y bajo

#### SEC7-002 — Dependencias sin hashes

- **Evidencia:** `requirements.txt:1-2`, `requirements-dev.txt:3-8`,
  `pyproject.toml:11-22`, instalación sin `--require-hashes` en
  `.github/workflows/ci.yml:37-40`.
- **Impacto:** el mismo pin puede resolver un artefacto distinto al revisado.
- **Recomendación:** lock con hashes, instalar con `--require-hashes` y revisar
  SBOM/scanner junto con actualizaciones. **Norma:** `STD-SEC-005`.

#### SEC7-003 — `.env` generados con permisos 0644

- **Evidencia:** renderer seguro en `ai_server_generator/render.py:417-422` y
  validación en `templates/chat/scripts/start_serving.sh.j2:21-28` y
  `validate_host.sh.j2:27-34`; cuatro artefactos generados actuales están en
  `0644`.
- **Impacto:** otros usuarios locales pueden leer configuración actual y un
  futuro campo secreto quedaría expuesto.
- **Recomendación:** normalizar/regenerar salidas, añadir sweep de permisos y
  preservar modo seguro en backup/restore. **Norma:** `STD-SEC-001`.

#### SEC7-004 — Sin aislamiento explícito de egress

- **Evidencia:** `templates/chat/docker-compose.yml.j2:1-49` no define
  `network_mode: none`, red `internal` ni equivalente; Compose adjunta
  `ai-server_default`.
- **Impacto:** un runtime comprometido conserva alcance de red saliente del
  Docker Desktop.
- **Recomendación:** definir mínima conectividad, preferir no-egress/red
  interna y probar salud/modelo tras la restricción. **Normas:**
  `STD-SEC-002`, `STD-SEC-006`.

#### SEC7-005 — Rutas de modelo fuera de `models/`

- **Evidencia:** `ai_server_generator/render.py:126-130,159-163` permite ruta
  absoluta sin containment ni rechazo del symlink final; bind en
  `templates/chat/docker-compose.yml.j2:28-32`.
- **Impacto:** una entrada local puede montar un archivo arbitrario y cruzar
  una frontera de privacidad.
- **Recomendación:** confinar al root aprobado, rechazar escapes por symlink y
  exigir override explícito y auditado. **Norma:** `STD-SEC-003`.

#### SEC7-006 — Scanner de vulnerabilidades no reproducible localmente

- **Evidencia:** requisito en `scripts/ci.sh:141-146`, `pyproject.toml:21` y
  `requirements-dev.txt:6`; `python3 -m pip_audit ...` terminó con exit 1:
  `No module named pip_audit`.
- **Impacto:** no existe veredicto actual de advisories y el gate local no es
  reproducible.
- **Recomendación:** ejecutar toolchain aislada fijada y retener JSON; reportar
  scanner ausente como gate bloqueado, nunca como PASS. **Norma:**
  `STD-SEC-005`.

#### SEC7-007 — Sin access logging del serving

- **Evidencia:** requisito futuro en `docs/lan-safe-runbook.md:43-45`; benchmark
  solo registra timing en `templates/chat/scripts/smoke_benchmark.sh.j2:127-152`;
  Compose no tiene sink/retención en `templates/chat/docker-compose.yml.j2:1-49`.
- **Impacto:** limitada forensia local y atribución débil antes de cualquier
  LAN.
- **Recomendación:** gateway/backend logs estructurados con origen, resultado,
  redacción, rotación y retención antes de LAN. **Norma:** `STD-SEC-002`.

#### COD7-001 — Template shell no pasa ShellCheck

- **Evidencia:** `templates/chat/scripts/validate_host.sh.j2:36-44`, ShellCheck
  exit 1 con `SC1083`; CI solo cubre `.sh` en `scripts/ci.sh:105-108`.
- **Impacto:** regresiones de la plantilla pueden pasar CI y fallar al
  renderizar.
- **Recomendación:** render fixture controlado y ejecutar `bash -n`/ShellCheck,
  incluyendo espacios, comillas, backslashes y Unicode. **Normas:**
  `STD-COD-002`, `STD-OPS-005`.

#### OPS7-002 — Readiness fallido deja servicio levantado

- **Evidencia:** `templates/chat/scripts/start_serving.sh.j2:40-55` hace
  `compose up -d`, captura diagnóstico y sale 1 sin `compose down`.
- **Impacto:** contenedor unhealthy puede conservar CPU/RAM y puerto.
- **Recomendación:** detener el stack levantado por el comando, conservar logs y
  probar timeout, proceso muerto y reintento idempotente. **Normas:**
  `STD-OPS-006`, `STD-OPS-007`.

#### OPS7-003 — Restore no valida contenido completo

- **Evidencia:** `scripts/restore_workspace.sh:70-89` solo valida raíz y
  `manifest.json`; mueve destino en `:91-103` sin validar miembros, symlinks,
  rutas ni validez semántica.
- **Impacto:** un backup alterado puede instalar contenido inesperado.
- **Recomendación:** inspeccionar miembros antes de extraer, rechazar rutas
  inseguras/symlinks, validar en staging y registrar hashes. **Normas:**
  `STD-COD-003`, `STD-OPS-007`.

#### HARNESS7-003 — OpenCode sin permisos mínimos por ruta/comando

- **Evidencia:** `.opencode/agents/ml-platform-engineer.md:4-11` y
  `security-engineer.md:4-11` exponen el mismo mapa; generación común en
  `.pm-harness/bin/harness_core.py:1451-1457`.
- **Impacto:** el prompt pide prudencia, pero no impone barreras ejecutables.
- **Recomendación:** permisos por plataforma, ruta y comando; confirmación de
  efectos destructivos y tests de materialización. **Norma:** `STD-ARN-003`.

#### PERF7-003 — Compatibilidad de runtime incompletamente fijada

- **Evidencia:** digest en `ai_server_generator/render.py:50-55` y template
  `templates/chat/docker-compose.yml.j2:1-4`; metadata insuficiente validada
  en `ai_server_generator/validator.py:332-344`; flags en `:11-27`.
- **Impacto:** no se puede comparar ni demostrar compatibilidad de flags con
  la imagen identificada.
- **Recomendación:** registrar versión/revisión, digest, esquema de flags y
  prueba de compatibilidad; exigir benchmark al cambiar digest. **Norma:**
  `STD-PERF-005`.

#### PERF7-004 — Readiness no distingue estados

- **Evidencia:** timeout/poll en `templates/chat/scripts/start_serving.sh.j2:9-14,40-55`
  y healthcheck en `templates/chat/docker-compose.yml.j2:37-42`; no lee
  `starting`, `healthy`, `unhealthy`.
- **Impacto:** diagnóstico tardío y ambiguo para el operador.
- **Recomendación:** consultar estado Compose durante espera y diagnosticar
  `unhealthy` inmediatamente, manteniendo timeout finito. **Norma:**
  `STD-PERF-004`.

#### PERF7-006 — Benchmark no califica carga real

- **Evidencia:** payload `model: local`, mensaje corto y `max_tokens: 8` en
  `templates/chat/scripts/smoke_benchmark.sh.j2:20`; perfiles en
  `profiles/*.json:5-10`, pero no se registran configuración efectiva ni
  tokens generados en `:137-139`.
- **Impacto:** resultados futuros no serían auditables ni representativos.
- **Recomendación:** registrar workload, contexto, batch, threads, `n_predict`,
  concurrencia, muestras y tokens; separar smoke de benchmark de regresión.
  **Norma:** `STD-PERF-003`.

#### UX7-003 — Ubicación de modelo inconsistente

- **Evidencia:** README `README.md:57-66`, resolución en
  `ai_server_generator/cli.py:156-170` y `render.py:159-163`, wizard en
  `ai_server_generator/cli.py:387-394`, guía contradictoria en
  `docs/human-guide.md:80-88`, bind en `templates/chat/docker-compose.yml.j2:28-32`.
- **Impacto:** copias innecesarias y fallos por path que no usa Compose.
- **Recomendación:** unificar host path, container path, copia requerida y
  comando de validación en todas las superficies. **Normas:** `STD-UX-002`,
  `STD-OPS-001`.

#### UX7-004 — Documentación nombra `start` inexistente

- **Evidencia:** secuencia en `README.md:82-90`; parser real en
  `ai_server_generator/cli.py:20-57`; helpers en `templates/chat/scripts/start.sh.j2:1-5`,
  `stop.sh.j2:1-14` y `smoke.sh.j2:1-5`.
- **Impacto:** el operador obtiene error argparse en el punto de arranque.
- **Recomendación:** documentar `./scripts/start.sh`, `smoke.sh`, `stop.sh` o
  añadir subcomando real, y generar referencia desde `--help`. **Norma:**
  `STD-PR-001`.

### Alto condicional de distribución

#### LEG7-001 — Provenance legal incompleta antes de distribuir

- **Evidencia:** `audits/standards/LEGAL.md` exige notices/provenance;
  `pyproject.toml:10`, `LICENSE`, `sbom.json` existen, pero
  `test -f THIRD_PARTY_NOTICES` terminó 1; `models/README.md:3-7` y
  `CHANGELOG.md:23` mantienen provenance de runtime/modelos pendiente.
- **Impacto:** publicar runtime, preset o modelo sin licencias, restricciones,
  fuente oficial y lawful-provisioning notice puede incumplir el gate de
  distribución.
- **Recomendación:** crear/revisar `THIRD_PARTY_NOTICES` y registrar fuente,
  revisión, licencia, restricciones y provisión lícita de cada componente antes
  de distribuir. **Norma:** `STD-LEG-001`.

## Plan de trabajo en cuatro fases

1. **Contención y decisión:** mantener localhost-only; congelar evidencia,
   corregir claims contradictorios, declarar soporte Codex y separar hallazgos
   condicionales de distribución.
2. **Integridad y seguridad:** eliminar dependencia histórica de CI, lock con
   hashes, permisos `.env`, validación de paths, egress, restore seguro y
   scanner reproducible; revisión security-engineer.
3. **Contratos operativos:** fortalecer drift-check, agentes/materialización,
   shellcheck renderizado, readiness, rollback y documentación del modelo.
4. **Runtime y release:** con GGUF autorizado validar memoria, flags,
   benchmark, access logging y provenance legal; ejecutar suite completa y
   liberar solo con evidencia viva.

## Límites de esta integración

No se remedia ninguna entrada, no se marca ningún todo, no se actualiza
`audits/INDEX.md`, no se abre la auditoría anterior y no se afirma que Docker,
un modelo, rendimiento, LAN, scanner o recuperación estén verificados en vivo.
