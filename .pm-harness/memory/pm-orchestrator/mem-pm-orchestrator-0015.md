---
id: mem-pm-orchestrator-0015
type: project-fact
scope: project
created: 2026-07-25
ttl_days: null
importance: 3
tags: [hygiene, ci, manifests, debt]
signature: "74a3beb8"
---

Verified 2026-07-25: scripts/ci.sh line 117 pins 'plan check TASK-0007', which exits 1 with '13 unchecked of 13' under set -euo pipefail, so the harness gate block is red on every developer checkout. Fix is in scope of TASK-0008 (derive ids from state/TASK-*.json manifests in in_review/closed plus a HARNESS_PLAN_TASK override, preserving the clean-clone guard), filed as APR-001 with destination 'harden gate'. Root cause is separate and owned by the PM Orchestrator: TASK-0006 and TASK-0007 are both stranded in_progress with fully unchecked plans although TASK-0007's work merged at 2b813e9/23cd468. Those manifests need remediation as separate work; the ci.sh fix must not depend on their state being sane.
