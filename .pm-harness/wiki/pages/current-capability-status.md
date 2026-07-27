---
title: Current capability status
kind: area
sources:
  - ai_server_generator/doctor.py
  - README.md
  - docs/README.md
  - docs/human-guide.md
  - docs/serving-baseline.md
  - docs/next-instance-server-handoff.md
  - docs/roadmap/generator-first-roadmap.md
  - docs/preset-matrix.md
  - docs/hardware-tiers.md
  - audits/TASK-0006-product-acceptance-audit.md
updated: 2026-07-27
---

# Current capability status

Chat workspace generation is the only implemented setup family. It supports
three static profiles, localhost generation, five model preset aliases,
generated Compose/runbooks/helpers, and structure/host/runtime validation
tiers. LAN, bearer-token authentication, and allowlist inputs are refused
until an authenticated TLS gateway and enforceable policy exist (source:
`README.md` §§Safety defaults, Capability status; `docs/human-guide.md`
§§3-6).

The preset matrix is a configuration preview that emits `WARN` or `NO-GO`,
never a passing `GO`. Preset tags and memory guidance are not measured
target-host support, and all presets currently resolve to the Chat setup
(source: `README.md` §5-minute quick start; `docs/preset-matrix.md`).

Host inspection is delivered through `python3 -m ai_server_generator doctor`.
It reports infrastructure observations, a separate software-readiness gap
report, and writes the versioned machine-local profile
`artifacts/host-profile.json` by default; it does not install, configure, or
start anything (source: `ai_server_generator/doctor.py`).

Measured facts in that profile are observations of the current host. The tier
and preset partition are derived from the committed, product-defined footprint
inputs and remain explicitly labelled
`provisional-pending-product-signoff`; a `FIT` result is planning guidance,
not a runtime guarantee (source: `ai_server_generator/doctor.py`;
`docs/hardware-tiers.md` §§Mapping, Honesty posture).

## Cross-instance continuity

The next planned event is a clone onto the intended server followed by
continuation with an independent instance from the same AI provider/model
family. The portable project context consists of the same-repository PM
Harness, root activation bridges, minimal Claude/OpenCode Markdown routers, a
sanitized `.env.example`, and operator documentation. Host-local permissions,
credentials, sessions, dependencies, caches, weights, logs, generated outputs,
and runtime evidence are excluded; `.codex/` is intentionally absent until a
real native project surface exists (source:
`docs/next-instance-server-handoff.md` §§Purpose and next event, Authority map,
Portable inventory and forbidden state).

On the server, an authorized GGUF remains under repository-root `models/` and
is bind-mounted read-only into a generated workspace. `matrix` is static
planning evidence, structure validation checks generated contracts, host
validation checks prerequisites/model visibility, and only a live runtime
validation plus smoke request constitutes runtime evidence. The handoff does
not claim that an authorized GGUF, endpoint, or benchmark has already run
(source: `docs/next-instance-server-handoff.md` §§Current evidence boundary,
Authorized-GGUF server path; `docs/serving-baseline.md` §Quick start;
`docs/human-guide.md` §§2-4).

Operational learning must record the UTC timestamp, commit, sanitized
provider/model label, tool versions, GGUF basename/checksum, configuration,
exact commands and exit codes, evidence paths and tiers, fact/decision/
hypothesis class, failures/recovery, and benchmark method. Tokens, sessions,
weights, permissions, and sensitive host/network data are prohibited, and
durable memory remains owned-agent and same-project only (source:
`docs/next-instance-server-handoff.md` §Operational-learning capture contract).

## Contradiction

The roadmap describes Coding and minimal RAG as MVP-supported families and
optional Vision as later/experimental (source:
`docs/roadmap/generator-first-roadmap.md` §2). Current repository evidence has
only the Chat manifest/template family (source:
`audits/TASK-0006-product-acceptance-audit.md` F-007). Therefore:

- Chat generation and host inspection: delivered, runtime unverified.
- Coding and minimal RAG: pending approved roadmap work.
- Vision and iGPU acceleration: deferred feasibility/evaluation.
- Fine-tuning, multi-model routing, and broader operations milestones: pending
  later phases, not closed-task deliverables.

Related: [[generator-workflow]], [[security-posture]],
[[accepted-decisions]].
