# Metadatos de auditoría — TASK-0007

## Identidad

- **Task:** `TASK-0007`, categoría `complex`.
- **Todo integrado:** 6 únicamente.
- **Audit directory:** `audits/audit_opencode_default_gpt-5_25-07-2026_20h23m`.
- **Fecha de integración:** 2026-07-25 20:40:35 CST / 2026-07-26 02:40:35Z.
- **Plataforma:** OpenCode, macOS Darwin arm64, Docker Desktop.
- **Agente/route:** `session-current-model`, `complex --task TASK-0007 --platform opencode`.
- **Commit observado:** `23cd468a4b083a89f20584b28ce695de57f923f7`.
- **Estado:** checkout dirty; cambios preexistentes fueron preservados.
- **Plan:** `.pm-harness/plans/TASK-0007.plan.md`, aprobado; no modificado.
- **Estado Harness:** `.pm-harness/state/TASK-0007.json`; no modificado.

## Dimensiones y fuentes

Se integraron exactamente cuatro dimensiones: security/legal, code/devops/harness,
performance/model-serving y product/UX. Se consultaron `audits/INDEX.md`,
`audits/standards/` aplicables, el plan aprobado y `meta/inventory.md`.
La auditoría anterior fue excluida y no se leyó.

| Fuente | SHA-256 |
|---|---|
| `meta/inventory.md` | `6b895f80a8f91de63811e6ee6a9026e978cc704d71bb9e5c9e630c74eeb294b2` |
| `dimension-security-legal.md` | `90190cc42a264f3f0faf5f7148e66ec9e5ab1f9914dbfc5fd89c4cda306889b7` |
| `dimension-code-devops-harness.md` | `45c2c540ee6a28715fb4da90df598cea945ddb5829dc8123bf0d5b5d3816f450` |
| `dimension-performance-runtime.md` | `c8dc0ecaf131f3ccfd2a8910b47be40e491b6bd78625c1e2e18e1a53e2c8759b` |
| `dimension-product-ux.md` | `1f7a38563fc69f3aa56ff07940c4e8d53049803e8de6f4cb89117510e0cee0e5` |

## Estado del checkout

Se conservó el estado dirty reportado por el inventario: modificaciones en
`CHANGELOG.md`, `pyproject.toml`, `sbom.json`, `scripts/ci.sh`,
`scripts/generate_sbom.py`, `templates/chat/README.md.j2` y el fixture golden;
no rastreados `LICENSE`, `ai_server_generator.egg-info/`, `build/`,
`docs/runtime-decision-phase-r.md` y el log de benchmark. No se modificaron
plan, estado, código fuente, templates existentes ni artefactos generados.

## Severidad y entregables

- Totales: 9 altos actuales, 15 medios actuales, 1 bajo localhost-only y 1
  alto condicional de distribución; 25 hallazgos.
- `informe_completa.md`: informe integrado y plan de cuatro fases.
- `checklist_completa.md`: acciones ejecutables ordenadas por severidad.
- `meta.md`: este registro de identidad, hashes, estado y comandos.
- `mejora-audit.md`: trazabilidad a normas y destinos de mejora.
- `remediation.md`: no requerido en este todo; no se creó porque la tarea
  exige integrar únicamente y no remediar.

## Comandos y evidencia

| Comando | Resultado | Tipo |
|---|---:|---|
| `docker --version` | 0 | Baseline estático de plataforma |
| `python3 --version` | 0 | Baseline estático |
| `python3 -m pip --version` | 0 | Baseline estático |
| `python3 .pm-harness/bin/harness.py validate` | 0 | Contratos Harness |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 | Esperado: 8 todos pendientes; plan intacto |
| `git diff --check` | 0 | Whitespace |

Los pases fuente también registran 42 unittest PASS, Compose, SBOM, `pip check`,
Harness y `wiki check` PASS; ShellCheck terminó 1 por `SC1083`, `ruff` y
`mypy` no estaban disponibles, y no se ejecutó modelo/runtime vivo. El plan
check no puede ser 0 mientras los todos posteriores sigan sin evidencia.

## Operador y duración

- **Operador:** Director; ejecución delegada por PM Harness.
- **Inicio del todo 6:** 2026-07-25 20:40 CST para esta integración.
- **Fin:** registrado al ejecutar los gates finales de este todo.
- **Invocación:** integración audit-only con restricciones de no remediación,
  no lectura de auditoría anterior y no modificación de plan/estado.

## Registro del todo 7

- **Índice:** se añadió una única fila en la primera posición de datos de
  `audits/INDEX.md`, con fecha `2026-07-25 20:22 CST`, plataforma `opencode`,
  agente `default`, modelo `session-current-model`, route
  `complex --task TASK-0007 --platform opencode`, y totales `25/0/9/15/1`.
- **Estándares:** se mantuvo el protocolo append-only de
  `audits/standards/MEJORA.md`; no se añadieron reglas normativas. Los
  hallazgos descubiertos sin cobertura suficiente quedaron en `APR-036`,
  `APR-037` y `APR-038`, cada uno con un único destino `harden gate`.
- **Trazabilidad:** `mejora-audit.md` enlaza cada APR con su finding fresco;
  ningún hallazgo fue marcado como corregido.

### Hashes de registro

Los hashes siguientes se calcularon después de registrar el índice y el
protocolo de mejoras; `meta.md` se excluye de esta lista porque contiene esta
sección de evidencia.

| Artefacto | SHA-256 |
|---|---|
| `audits/INDEX.md` | `9ab68c399acc442c71366863727dd3400667a76c383a466d04e9b58da22918e4` |
| `audits/standards/MEJORA.md` | `4c4baf9bcadceac8ddbf1dac14ed1182682bed86a23a5284d1ee4a7a77dae1f1` |
| `mejora-audit.md` | `abd137a306e709507e399513b145416ae6d28373d323892af80cab36d528a5ae` |

## Registro del todo 8 — congelación pre-remediación

La congelación se realizó antes de cualquier remediación de código, scripts,
plantillas, documentación, plan o estado. Los siguientes hashes son la captura
pre-remediación de los cuatro entregables integrados y de los cuatro informes
dimensionales. El hash de `meta.md` identifica su contenido inmediatamente
antes de añadir este registro; esta sección es la actualización de provenance
exigida por el todo 8.

| Artefacto congelado | SHA-256 pre-remediación |
|---|---|
| `informe_completa.md` | `91e652acba51146d89fcc27133afa1503b4b972f9070cd8c4293a3696397f3f3` |
| `checklist_completa.md` | `976aa51bcf5961de14acf1040da3b245b8095c060d2335cea9e65c81225ce803` |
| `meta.md` (antes de este registro) | `58057a3aff2470d3ecb9313d9361627364f68a34251aaef4bc8786dc1808cfbc` |
| `mejora-audit.md` | `abd137a306e709507e399513b145416ae6d28373d323892af80cab36d528a5ae` |
| `dimension-security-legal.md` | `90190cc42a264f3f0faf5f7148e66ec9e5ab1f9914dbfc5fd89c4cda306889b7` |
| `dimension-code-devops-harness.md` | `45c2c540ee6a28715fb4da90df598cea945ddb5829dc8123bf0d5b5d3816f450` |
| `dimension-performance-runtime.md` | `c8dc0ecaf131f3ccfd2a8910b47be40e491b6bd78625c1e2e18e1a53e2c8759b` |
| `dimension-product-ux.md` | `1f7a38563fc69f3aa56ff07940c4e8d53049803e8de6f4cb89117510e0cee0e5` |

El ledger se creó después de esta captura y quedó registrado como:

| Artefacto | SHA-256 |
|---|---|
| `remediation.md` | `f24f55cce4d374028b29b0623e2de0cdb90ab190c7a508c8e16272af2060ba08` |

El ledger contiene 25 filas para 25 hallazgos confirmados, conserva por
separado `SEC7-001` y `OPS7-001`, rechaza claims especulativos y escala los
casos de decisión de alcance, cambio de red/permisos, runtime externo y
distribución/legal. No se modificaron `.pm-harness/plans/TASK-0007.plan.md`,
`.pm-harness/state/TASK-0007.json` ni fuentes del producto.
