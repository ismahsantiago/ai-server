---
name: pm
description: "Entry point for this project's local PM Harness. Use when the user (Director) asks for product work, task delegation, or ceremonies (standup, retro, showcase, decision). Loads the PM Orchestrator runtime from .pm-harness/."
---

# pm-harness — activation skill (Claude Code plugin `pm`)

This project has a local PM Harness, installed as the local plugin `pm`
(`.claude/skills/pm/`, auto-loaded after workspace trust). This skill only
redirects:

1. Read `.pm-harness/teams/pm-orchestrator/SKILL.md` and adopt that role (root
   agent). Where it says `task()`, use your subagent/Task tool; pass the model
   resolved by `harness.py route` when your platform allows per-subagent models.
2. Govern everything by the contracts in `.pm-harness/HARNESS-SPEC.md`;
   enforce them with `python3 .pm-harness/bin/harness.py`.
3. All state (tasks, memory, ceremonies, escalations) lives under
   `.pm-harness/` of THIS project and never leaves it.

Natural invocation surfaces shipped by the plugin:

- Commands: `/pm` (hand the session to the orchestrator), `/pm:kickoff`
  (Director feedback session, SPEC §5.1 — required before task work in guided
  autonomy), `/pm:standup`, `/pm:retro`, `/pm:showcase`, `/pm:decision`
  (ceremonies, SPEC §5) and `/pm:status` (read-only snapshot).
- Agents: `pm-orchestrator` ships with the plugin (`agents/`), invocable from
  the @-mention picker as `pm:pm-orchestrator` even before the roster exists.
  Once the roster is generated (Phase B), every roster member is materialized
  into `.claude/skills/pm/agents/{member-id}.md` (HARNESS-SPEC §7.1) and
  surfaces as `pm:{member-id}`. If `teams/` has a roster but `agents/` lacks
  the pointer files, run `python3 .pm-harness/bin/harness.py agents
  materialize` before delegating (agent changes need `/reload-plugins` or a
  restart to appear).

If `.pm-harness/` is missing or incomplete, tell the user to run the global
installer: "install the pm harness".

If the project uses the private-outer layout (`.pm-harness/harness.json` has
`layout: "private-outer-v1"`, or the only trace you find is a
`PM-HARNESS-BRIDGE` stub in `AGENTS.md`), the harness and all AI/dev
artifacts live in the OUTER directory: tell the user to open Claude Code from
the outer root (one level up from the public inner repo). Never scaffold or
write harness state inside the inner repository.
