---
description: Hand the request to the PM Orchestrator (root agent of the local PM Harness)
agent: pm-orchestrator
---
Director request: $ARGUMENTS

Adopt your role per `.pm-harness/teams/pm-orchestrator/SKILL.md`, governed by
`.pm-harness/HARNESS-SPEC.md` (enforce with `python3 .pm-harness/bin/harness.py`).
If the request is empty, present a one-screen status (active tasks, pending
escalations, last ceremony) and ask the Director what to work on.
