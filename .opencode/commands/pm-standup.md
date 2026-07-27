---
description: Run the standup ceremony (per-manager report of done / in progress / blocked / next)
agent: pm-orchestrator
---
Run the `standup` ceremony exactly per `.pm-harness/HARNESS-SPEC.md` §5:
inputs are `teams/*/plan.md` plus active state manifests (read-only); output is
`ceremonies/{YYYY-MM-DD}-standup.md` and a `state/CER-*.json` manifest, both
via `python3 .pm-harness/bin/harness.py`.

Director input: $ARGUMENTS
