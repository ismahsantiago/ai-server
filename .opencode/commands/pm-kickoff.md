---
description: Run the kickoff feedback session with the Director (plan + per-area specs; required before task work in guided autonomy)
agent: pm-orchestrator
---
Run the `kickoff` ceremony exactly per `.pm-harness/HARNESS-SPEC.md` §5.1:
present the proposed plan and draft specs per applicable area (Product,
Engineering, Design, Security, others), collect the Director's feedback,
record the session via `python3 .pm-harness/bin/harness.py kickoff new`, and
request Director approval (`kickoff approve <id> --by director`). Task
creation stays blocked by the CLI until then.

Director input: $ARGUMENTS
