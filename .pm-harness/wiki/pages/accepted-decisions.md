---
title: Accepted product decisions
kind: decision
sources:
  - .pm-harness/ceremonies/2026-07-23-kickoff-KICK-0001.md
  - .pm-harness/harness.json
  - .pm-harness/memory/pm-orchestrator/mem-pm-orchestrator-0001.md
  - .pm-harness/memory/pm-orchestrator/mem-pm-orchestrator-0004.md
  - .pm-harness/memory/pm-orchestrator/mem-pm-orchestrator-0006.md
  - audits/TASK-0006-product-acceptance-audit.md
  - docs/hardware-tiers.md
  - README.md
updated: 2026-07-26
---

# Accepted product decisions

- Initial host: Linux laptop, Ryzen 5/Radeon Vega class, 12 GB RAM; CPU-first
  safe path (source: kickoff §§Proposed plan, Director feedback).
- Product form: downloadable generator-first repository; canonical flow is
  clone → matrix → generate → validate → start (source:
  `mem-pm-orchestrator-0004.md`; audit Approved-scope register).
- Implementation: Python + Jinja2, `ai-server` console command, Chat/localhost/
  medium first, generated outputs ignored by default (source:
  `mem-pm-orchestrator-0006.md`).
- Security direction originally allowed LAN opt-in with bearer token and
  firewall/allowlist controls (source: `mem-pm-orchestrator-0001.md`).
- Capability direction: Chat, Coding, RAG, exploratory Vision where hardware
  permits; balanced medium-fast/medium/good target (source: kickoff §Director
  feedback and incorporation).
- TASK-0010: Hardware tiers use stable machine-readable `tier_id` values and
  renameable display labels. The current provisional mapping is ADJUSTED: its
  host reserve is double-counted, so the corrected fit formula is routed as a
  TASK-0008 amendment while that task remains open (source:
  `docs/hardware-tiers.md`).
- TASK-0010: Apache-2.0 distribution moves the honesty line: recommendations
  remain visibly derived from planning-assumption-only data, and capability
  wording must not imply a runtime guarantee (source:
  `docs/hardware-tiers.md`).

## Contradiction

The historical LAN direction allows an opt-in mode, while the current product
contract refuses LAN, bearer-token, and allowlist generation until an
authenticated TLS gateway can enforce and verify the controls (source:
`README.md` §§Safety defaults, Capability status). The current fail-closed
implementation governs operator instructions; reconciling the older product
decision remains a product-governance concern rather than a manual exposure
exception.

The kickoff ceremony header still says `pending Director approval` (source:
`.pm-harness/ceremonies/2026-07-23-kickoff-KICK-0001.md` line 5), while the
harness registry records KICK-0001 approved by Director at
2026-07-23T23:14:09Z (source: `.pm-harness/harness.json` `kickoffs[0]`).
TASK-0006 preserves both historical records and treats the registry approval as
the governing state; PM Orchestrator owns ceremony reconciliation (source:
audit F-011).

Related: [[generator-workflow]], [[current-capability-status]],
[[security-posture]].
