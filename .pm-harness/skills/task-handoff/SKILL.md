---
name: task-handoff
description: "Delivery protocol for any delegated task in this harness: append the state transition to the task manifest, compute memory-note signatures, report gates. Referenced in the Skill(s) block of every delegation. Triggers: any task() delegation."
allowed-tools: ["bash", "read", "write", "edit"]
---

# task-handoff — delivery protocol for delegated tasks

When you finish your delegated task (task-id given in the prompt):

0. **Plan adherence (SPEC §12)**: check off the todos of
   `plans/{task-id}.plan.md` that your work actually completed
   (`- [ ]` → `- [x]`); if you deviated from the plan, record it first with
   `harness.py plan amend <task-id> --reason ... --by <you> --approved-by
   <the plan's approver>` — never rewrite an approved plan. The CLI refuses
   `in_review` while todos remain unchecked (`harness.py plan check`).
1. **Manifest**: append (never rewrite existing entries) the corresponding
   transition (`{ts, agent, from, to, reason}`) to
   `.pm-harness/state/{task-id}.json → history` and update the `status` field
   to your entry's `to`. Prefer `python3 .pm-harness/bin/harness.py state
   transition <task-id> <to> --agent <you> --reason "..."` — it enforces the
   transition table and stamps the real timestamp. Validate the JSON before
   finishing.
2. **Memory (only if a relevant decision was made)**: write the note in YOUR
   store `.pm-harness/memory/{your-agent}/` with the SPEC §2.1 frontmatter;
   `signature` = first 8 hex of sha256 of the lowercased, trimmed body,
   computed for real. Prefer `harness.py memory add <you> ...` — it computes
   the signature, deduplicates, and updates your `MEMORY.md`.
3. **Gates**: run the verification gates from your SKILL.md and report their
   literal exit codes.
4. **Report**: changes, exit codes, signature (if a note was written). Never
   touch files outside your task, nor another agent's memory store.

## QA Scenarios

### Happy path
**Input**: a delegated task with an existing task-id; the agent finishes its work.
**Expected**: manifest gains exactly one new valid transition, JSON parses,
gates reported with exit 0.
**Verify**: `python3 -c "import json;json.load(open('.pm-harness/state/<task-id>.json'))"` and the report contains the exit codes.

### Error path
**Input**: a task-id that does not exist under `.pm-harness/state/`.
**Expected**: the agent does NOT create the manifest on its own (creating it is
the delegator's job); it reports the missing id and returns the task without
transitioning anything.
**Verify**: no new file appears under `state/` and the report cites the missing task-id.
