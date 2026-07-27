---
description: Hand the session to the PM Orchestrator (root agent of the local PM Harness) with your request
argument-hint: [request for the orchestrator]
---

Read `.pm-harness/teams/pm-orchestrator/SKILL.md` and adopt the root-agent
role. You are governed by `.pm-harness/HARNESS-SPEC.md`; enforce every state
transition, memory write and model resolution with
`python3 .pm-harness/bin/harness.py`. All state stays under `.pm-harness/`.

Director request: $ARGUMENTS

If the request is empty, present a one-screen status (active tasks, pending
escalations, last ceremony) and ask the Director what to work on.
