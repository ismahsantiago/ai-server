# Inventario inicial independiente — TASK-0007

## Límite y trazabilidad

- **TASK:** `TASK-0007`, únicamente todo 1: establecimiento de límite e inventario.
- **AUDIT_DIR seleccionado:** `audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/`.
- **Fecha de captura:** 2026-07-25 20:22–20:23 CST (America/Mexico_City); UTC 2026-07-26 02:22–02:23.
- **Commit observado:** `23cd468a4b083a89f20584b28ce695de57f923f7`.
- **Plataforma observada:** macOS Darwin arm64, Docker Desktop.
- **Agente/ejecutor:** `ml-platform-engineer` delegado; modelo de la sesión actual según FACTS.
- **Entrada excluida explícitamente:** `audits/audit_opencode_default_gpt-5_24-07-2026/` y todos sus entregables. No se abrió ni se usó como fuente.
- **Fuentes de auditoría permitidas consultadas:** `audits/INDEX.md` y el estado actual de `audits/standards/` (`README.md`, `MANIFESTO.md`, `GATES.md`, `SECURITY.md`, `CODE.md`, `PERFORMANCE.md`, `DESIGN.md`, `PRODUCT.md`, `OPS.md`, `LEGAL.md`, `HARNESS.md`).
- **Fuentes de gobierno consultadas:** `.pm-harness/plans/TASK-0007.plan.md` y `.pm-harness/standards/GATES.md`, para respetar el plan aprobado y sus gates.
- **No realizado:** revisión de dimensiones posteriores, hallazgos, comparación con auditorías anteriores, remediación, regeneración, modificación del plan o modificación del estado.

## Estado Git y límites de cambios

`git status --short --branch` reportó `master...origin/master` y estos cambios preexistentes, conservados sin modificación por este paso:

- Modificados: `CHANGELOG.md`, `pyproject.toml`, `sbom.json`, `scripts/ci.sh`, `scripts/generate_sbom.py`, `templates/chat/README.md.j2`, `tests/golden/chat-ornith-medium-localhost/README.md`.
- No rastreados: `LICENSE`, `ai_server_generator.egg-info/`, `build/`, `docs/runtime-decision-phase-r.md`, `logs/benchmarks/smoke-benchmark-20260725-142634.md`.
- El commit HEAD y la rama no cambiaron durante la captura.
- No se modificaron `.pm-harness/plans/TASK-0007.plan.md` ni `.pm-harness/state/TASK-0007.json`.

## Mapa del checkout

| Área | Evidencia observada |
|---|---|
| Componentes de producto | `ai_server_generator/` (21 archivos); módulos visibles: `cli.py`, `data.py`, `presets.py`, `render.py`, `validator.py`, `__main__.py`, `__init__.py`. |
| Plantillas | `templates/chat/` (12 archivos): README, Compose, dotenv, manifiesto, runbook y helpers de start/stop/validate/smoke/benchmark. |
| Tests y fixtures | `tests/` (19 archivos contados): `test_cli.py` y fixture golden `tests/golden/chat-ornith-medium-localhost/`; también hay `__pycache__` generado. |
| Documentación | `README.md`, `docs/README.md`, guía humana, runbook LAN, matriz de presets, baseline de serving, roadmap, diseño/spec y decisión Phase R. |
| Configuración y catálogos | `pyproject.toml`, `requirements*.txt`, `profiles/`, `manifests/chat.json`, `models/README.md`, `datasets/`, `experiments/`, `backups/`, `logs/`. |
| CI y operaciones | `.github/workflows/ci.yml`, `scripts/ci.sh`, SBOM, digest resolver, backup/restore/rollback, start, smoke benchmark, perfil y fixture golden. |
| Docker | `docker-compose.yml`, `templates/chat/docker-compose.yml.j2`, Compose generado y fixture golden. Docker Compose está disponible. |
| Salidas generadas | `generated/` contiene 132 archivos, incluidos workspaces activos y copias de backup/reemplazo/rollback; se inventarió, no se regeneró ni alteró. |
| PM Harness | `.pm-harness/` contiene contrato, versión, configuración, router, SpecPack, agentes, planes, estado, wiki, estándares y CLI local. |
| OpenCode | `.opencode/agents/` contiene `engineering-manager`, `ml-platform-engineer`, `ml-systems-engineer`, `pm-orchestrator`, `product-analyst`, `product-manager`, `security-engineer`, `ux-dev`; `.opencode/commands/` contiene superficies PM. Hay `node_modules/` instalado. |
| Otros hosts | `.claude/` y `CLAUDE.md` están presentes; `.codex/` no apareció en el inventario de archivos local del checkout. |

## Disponibilidad de plataforma y runtime

Comandos ejecutados y resultado observado:

```text
date -u +%Y-%m-%dT%H:%M:%SZ
  2026-07-26T02:22:56Z
TZ=America/Mexico_City date '+%Y-%m-%d %H:%M:%S %Z'
  2026-07-25 20:22:56 CST
docker --version
  Docker version 29.6.1, build 8900f1d
docker info --format 'Server={{.ServerVersion}} OS={{.OperatingSystem}} Arch={{.Architecture}} CPUs={{.NCPU}} Mem={{.MemTotal}}'
  Server=29.6.1 OS=Docker Desktop Arch=aarch64 CPUs=8 Mem=8321798144
docker compose version
  Docker Compose version v5.3.0
python3 --version
  Python 3.14.5
python3 -c 'import jinja2, sys; print(sys.version.split()[0], jinja2.__version__)'
  3.14.5 3.1.6
python3 .pm-harness/bin/harness.py --version
  exit 2: el CLI requiere el subcomando version; no se interpretó como fallo del runtime.
```

El directorio `models/` no contiene pesos: solo `models/README.md` (272 bytes). Por tanto, este inventario no afirma disponibilidad de un modelo, salud de runtime, rendimiento, compatibilidad de carga ni readiness.

## Controles y hashes de referencia

Los hashes se capturaron para detectar contaminación de artefactos de gobierno, no para modificar esos archivos:

```text
.pm-harness/plans/TASK-0007.plan.md  d3823a39e0ec92fb51010f076fc7530fd5399d23a
.pm-harness/state/TASK-0007.json     c603ffc0dd65ca4b5f8022e713a4f2e6b03652aa
audits/INDEX.md                      37bc5e2b51f1b93078585a7269f8b2bae90f310a
```

El plan aprobado conserva 13 todos pendientes al iniciar este paso; este artefacto cubre únicamente el primero y no cambia su checkbox.

## Verificación del paso

- `git diff --check`: exit 0.
- `python3 .pm-harness/bin/harness.py validate`: exit 0 (`manifests: 13`, `memory_notes: 29`, sin errores ni warnings).
- `python3 .pm-harness/bin/harness.py plan check TASK-0007`: exit 1 por `13 unchecked of 13`; es esperado para este todo porque no se modificó el plan ni se marcaron fases posteriores como hechas.
- No se ejecutó `python3 -m unittest`, `pip check`, Docker Compose startup ni modelo en vivo, porque no son necesarios para establecer el inventario y podrían producir evidencia de fases posteriores.
