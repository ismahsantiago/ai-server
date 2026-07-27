---
description: Run the decision ceremony (structured debate among the relevant managers/agents)
agent: pm-orchestrator
---
Run the `decision` ceremony exactly per `.pm-harness/HARNESS-SPEC.md` §5:
convene only the relevant managers/agents, run the structured debate
(position → evidence → rebuttal → close), and record the memory note
(`type: decision, scope: team`) plus minutes in
`ceremonies/{YYYY-MM-DD}-decision.md` and a `state/CER-*.json` manifest via
`python3 .pm-harness/bin/harness.py`.

Topic: $ARGUMENTS
