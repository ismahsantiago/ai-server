<!-- PM-HARNESS:START -->
## PM Harness

This project has a local PM Harness installed under `.pm-harness/`.

- **Root agent**: `.pm-harness/teams/pm-orchestrator/SKILL.md` — activate it
  when the user (Director) asks for product work, ceremonies ("standup",
  "retro", "showcase"), or task delegation to the team.
- **Invocation surfaces** (installed with the platform adapter): on Claude
  Code, the local plugin `pm` provides `/pm`, `/pm:kickoff`, `/pm:standup`,
  `/pm:retro`, `/pm:showcase`, `/pm:decision`, `/pm:status` and the roster
  agents as `pm:{member-id}`; on OpenCode, `pm-orchestrator` is a
  Tab-selectable primary agent and `/pm`, `/pm-kickoff`, `/pm-standup`,
  `/pm-retro`, `/pm-showcase`, `/pm-decision`, `/pm-status` are available as
  commands.
- **Kickoff gate**: in the default `guided` autonomy, the orchestrator must
  run a kickoff feedback session with the Director (plan + per-area specs)
  and get approval before any task is created — the CLI enforces it
  (SPEC §5.1). Autonomy exists only when the Director grants it explicitly.
- **Plan gate**: every TASK executes against an approved
  `plans/{TASK-id}.plan.md`, approved by the executor's immediate superior
  and proportional to the task's category — the CLI refuses
  `started → in_progress` without it and `in_review` with unchecked todos
  (SPEC §12). Deviations are append-only amendments, never rewrites.
- **Normative contracts**: `.pm-harness/HARNESS-SPEC.md` (state machine,
  memory, model router, escalation, kickoff, LLM Wiki §9, standards §10).
  Every harness unit of work is governed by that spec. Enforcement CLI:
  `python3 .pm-harness/bin/harness.py`.
- **Knowledge & quality**: project knowledge is compiled into the LLM Wiki
  (`.pm-harness/wiki/`, answer from it first); quality rules and gates live in
  `.pm-harness/standards/` (read `GATES.md` at task start, pass Gate 1 before
  integrating).
- **Isolation**: all harness state lives under `.pm-harness/` and never
  propagates outside this project. All generated artifacts are written in
  English.
- The user of this project acts as the **Director**: only questions the PM
  Orchestrator cannot resolve with its team should reach them.
<!-- PM-HARNESS:END -->
