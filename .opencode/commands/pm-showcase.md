---
description: Run the showcase ceremony (executive summary of artifacts closed since the last showcase)
agent: pm-orchestrator
---
Run the `showcase` ceremony exactly per `.pm-harness/HARNESS-SPEC.md` §5:
compile the executive summary of artifacts `closed` since the last showcase,
regenerate `executive-summary.md`, and write
`ceremonies/{YYYY-MM-DD}-showcase.md` plus a `state/CER-*.json` manifest via
`python3 .pm-harness/bin/harness.py`.

Director input: $ARGUMENTS
