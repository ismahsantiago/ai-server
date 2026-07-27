---
title: Security posture
kind: area
sources:
  - README.md
  - docs/human-guide.md
  - docs/lan-safe-runbook.md
  - docs/roadmap/generator-first-roadmap.md
  - audits/TASK-0006-product-acceptance-audit.md
updated: 2026-07-26
---

# Security posture

Localhost is the only supported generated exposure. The generator refuses LAN,
bearer-token authentication, and allowlist inputs because no authenticated TLS
gateway mechanically enforces those controls. Generated instructions must not
present executable LAN examples or a manual bypass (source: `README.md`
§§Safety defaults, Capability status; `docs/human-guide.md` §6).

## Contradiction

The roadmap and TASK-0006 audit describe a guarded LAN input path and manual
firewall/token handling (source: `docs/roadmap/generator-first-roadmap.md`
§§2,4,6; `audits/TASK-0006-product-acceptance-audit.md` F-004/H-004). Current
behavior deliberately refuses that path because recording an allowlist without
enforcing it is not a security control (source: `README.md` §Safety defaults;
`docs/human-guide.md` §6). The LAN runbook therefore supplies future acceptance
criteria, not current authorization.

Generated outputs can be replaced only when they are generator-owned and below
`generated/`. Normal onboarding still uses a new output directory; operators
back up changes before `--force` (source: `README.md` §5-minute quick start;
`docs/human-guide.md` §3).

Related: [[generator-workflow]], [[current-capability-status]],
[[accepted-decisions]].
