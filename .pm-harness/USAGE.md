# USAGE — PM Harness operator manual

Guide for whoever holds the reins of the harness (the **Director**). No
ambiguity: what to type, where, and what to expect, per platform. The full
contract is `HARNESS-SPEC.md`; this manual is the "how to drive it".

## 0. Who is who

| Role | Who | How you interact |
|---|---|---|
| **Director** | You (human) | Gives direction, approves kickoffs/plans, resolves escalations |
| **pm-orchestrator** | Root agent | Single entry point; delegates to managers, never executes domain work itself |
| Managers (e.g. `eng-manager`) | Area agents | Receive work ONLY via the orchestrator (or your direct @-mention) |
| Agents (e.g. `backend-dev`) | Workers | Execute concrete tasks; never delegate |

Golden rule: **talk to the pm-orchestrator**. Only invoke a manager or
worker directly when you want exactly that role and know why.

## 1. Session start (any platform)

1. Open your platform **at the project root** (where `.pm-harness/` lives).
   On the private-outer layout: open at the OUTER directory — the inner is
   just a code subdirectory.
2. First message: ask for product work in natural language ("plan the next
   milestone", "standup"). The context file (`CLAUDE.md`/`AGENTS.md`)
   activates the root agent automatically.
3. The root agent syncs the model catalog at session start
   (`harness.py models set ...`); if it didn't, ask it to.

## 2. Claude Code — how to invoke

Claude Code has **no Tab agent selector**. The three ways, in order of
preference:

1. **Slash commands** (they route to the pm-orchestrator, no logic of their
   own):

   ```
   /pm             → activate the harness / general product work
   /pm:kickoff     → kickoff feedback session (required before any TASK)
   /pm:standup     → per-manager status report
   /pm:retro       → improvement proposals → self-improvement cycle
   /pm:showcase    → executive summary of closed work + release decision
   /pm:decision    → structured debate with the relevant members
   /pm:status      → short status read
   ```

   Example: `/pm:decision should we persist slugs in SQLite or Postgres?`

2. **@-mention a specific agent** (they appear in the @ picker namespaced by
   the local plugin `pm`): `@pm:pm-orchestrator`, `@pm:eng-manager`,
   `@pm:backend-dev`. The agent file orders it to read
   `.pm-harness/teams/<role>/SKILL.md` and adopt that role verbatim — **no
   guessing involved**; the role is written down.

   Example: `@pm:eng-manager review the shorten-endpoint design for risks`.

3. **Plain natural language**: works because `CLAUDE.md` instructs Claude to
   activate the harness for product work. If you notice it did NOT adopt the
   role, use `/pm` or the @-mention — that is the explicit form.

⚠️ Roster agents (managers/workers) **only exist in the picker after
materialization**: after generating or changing the roster, run
`python3 .pm-harness/bin/harness.py agents materialize`. Before that, only
`pm-orchestrator` exists (statically installed). Verify with
`harness.py agents check`.

## 3. OpenCode — how to invoke

OpenCode has first-class agents; it is the most direct surface:

1. **Tab** cycles primary agents → select **pm-orchestrator** and type your
   instruction. This is "talking to the harness".
2. **@-mention** managers/workers (they are `mode: subagent`):
   `@eng-manager`, `@backend-dev` (no prefix — plain names under
   `.opencode/agents/`).
3. **Commands** (prefix `pm-`):

   ```
   /pm  /pm-kickoff  /pm-standup  /pm-retro  /pm-showcase
   /pm-decision  /pm-status
   ```

Same caveat: managers/workers appear after `agents materialize`.

## 4. Cursor / OpenClaw / Hermes

No named-subagent concept (`agents_dir: null`): the adapter installs only
the activation context/rule. Everything is operated via **natural language +
CLI**; the model acts as pm-orchestrator following the SPEC.

## 5. Canonical workflow (exact commands)

```bash
CLI=".pm-harness/bin/harness.py"

# 1) Mandatory kickoff (§5.1 gate) — no TASK is created without it
python3 $CLI kickoff new --initiative "URL shortener MVP"
#    … feedback session with you; when you approve:
python3 $CLI kickoff approve KICK-0001 --by director

# 2) Task + plan (§12 gate): no approved plan, no execution
python3 $CLI state new TASK-0001 --title "Shorten endpoint" --owner eng-manager/backend-dev
python3 $CLI plan new TASK-0001 --category complex --by backend-dev
python3 $CLI plan approve TASK-0001 --by eng-manager    # the superior approves
#    … execution: todos get checked [x]; deviation = plan amend, never a rewrite

# 3) Behavior changed? changelog entry before the unit closes (§11)
python3 $CLI changelog check --task TASK-0001

# 4) Public repo? keep the harness out of it (§8.2)
python3 $CLI private-split status
python3 $CLI private-split init --dry-run     # always inspect the plan first

# 5) Session close: ALWAYS
python3 $CLI validate                          # errors: [] required to close
```

## 6. CLI cheat sheet

| I need to… | Command |
|---|---|
| See/adjust the roster | `harness.py roster show` · `roster toggle <mgr> <agent> --active false --reason "…"` |
| Refresh platform agents | `harness.py agents materialize` · `agents check` |
| Pick a model per task | `harness.py route <category> --task TASK-x` |
| Recall an agent's memory | `harness.py memory recall <agent> --keywords a,b` |
| Release | `harness.py version current` · `version bump minor --by director` |
| Layout health (split) | `harness.py private-split validate` |
| Global health | `harness.py validate` |

## 7. Troubleshooting

- **"The agent didn't adopt the role" (Claude Code)** → use the explicit
  @-mention `@pm:<agent>`; if it's not in the picker, run
  `agents materialize` and reopen the session.
- **"/pm:… command not found"** → the claude adapter isn't installed in this
  project; re-run the installer (it detects `.claude/`).
- **A gate rejected my transition** → the CLI error is JSON with the exact
  cause and the remedy command; the attempt stays in history as
  `rejected: true` (by design — don't edit it).
- **`validate` fails on split-postcondition** → the layout declares
  private-outer-v1 but the inner has no `.git`; `git init` the inner.
- **I want to skip the kickoff** → only you can:
  `harness.py autonomy set autonomous --by director` (recorded in the
  changelog).
