---
title: Generator workflow
kind: concept
sources:
  - ai_server_generator/doctor.py
  - README.md
  - docs/human-guide.md
  - docs/roadmap/generator-first-roadmap.md
  - audits/TASK-0006-product-acceptance-audit.md
updated: 2026-07-26
---

# Generator workflow

The canonical product path is clone → doctor → matrix → generate → validate →
start. `doctor` is the non-invasive front step: it records host observations
and software-readiness gaps, and by default writes
`artifacts/host-profile.json`; its tiers and preset results are derived
planning guidance rather than runtime verification (source:
`ai_server_generator/doctor.py`; `docs/hardware-tiers.md` Honesty posture).
Python/Jinja2 owns selection, static validation, and rendering; generated shell
helpers own local operations (source: `docs/roadmap/generator-first-roadmap.md`
§§1,3-4).

`matrix` reports `WARN` or `NO-GO`, never `GO`. Generator validation is tiered:
the default structure tier is static, the host tier checks the model file and
Docker/Compose, and the runtime tier probes a running health endpoint. None of
these results alone proves target-hardware fit, latency, or quality
(source: `README.md` §§5-minute quick start, Safety defaults;
`docs/human-guide.md` §§2-4).

The generator resolves a model below repository-root `models/` to an absolute
host path and Compose mounts that same file read-only at
`/models/model.gguf`; operators do not copy model weights into the generated
workspace. Lifecycle actions are generated `scripts/start.sh`,
`scripts/smoke.sh`, and `scripts/stop.sh` helpers rather than generator
subcommands, and they resolve their workspace independently of the caller's
current directory (source: `README.md` §§5-minute quick start, Canonical
workflow; `docs/human-guide.md` §§1,3-4).

Use a new output directory by default. `--force` is confined to a
generator-owned workspace under `generated/`, but it replaces that workspace,
so operator changes require a backup first (source: `README.md` §5-minute
quick start; `docs/human-guide.md` §3).

Related: [[security-posture]], [[accepted-decisions]].
