---
name: plan-review
description: "Approver-side review of a §12 task plan before approving it: gap/ambiguity hunting, todo atomicity, acceptance-criteria testability, scope-creep detection, risk and open-question triage. Run by the owner's superior for every complex/strategic/creative/research plan. Triggers: 'review this plan', 'plan approve' for a full-weight plan."
allowed-tools:
  - "bash"
  - "read"
  - "grep"
  - "glob"
---

# plan-review — approve plans on evidence, not optimism (SPEC §12.5)

You are the approver (the plan owner's immediate superior, or the PM
Orchestrator acting on a Director decision) reviewing
`plans/{TASK-id}.plan.md` before `harness.py plan approve`. You are a skill,
not a roster role: you never rewrite the plan, never execute the task, and
never approve your own plan. Your verdict is `approve` or `revise` with
concrete findings — a `revise` returns the plan to its author.

## Preconditions

1. The TASK manifest exists and the plan's frontmatter `task_ref` and
   `category` match the manifest and the §3.1 delegation block.
2. Lightweight plans (`trivial`/`routine`) do NOT come through here: they are
   auto-approved by the delegator (`plan new --approve`, §12.3). If one was
   sent to you anyway, check only that its category is honest — a "routine"
   plan hiding multi-file design work is your first finding.

## Review checklist (all seven, in order)

1. **Objective verifiability** — is the objective an observable outcome
   (command output, artifact, state) rather than an intention? "Improve X"
   fails; "X does Y, proven by Z" passes.
2. **Todo completeness** — walk the objective backwards: does executing every
   todo actually produce it? Name any missing step (migrations, wiring,
   docs/wiki update per §9, CHANGELOG entry per §11).
3. **Todo atomicity** — each todo is one verifiable step. A todo hiding three
   ("implement, test and document the endpoint") gets split.
4. **Acceptance-criteria testability** — every todo carries an AC that a
   third party could check mechanically (a command, a file, a diff). "Works
   correctly" is not an AC.
5. **Scope creep** — everything in the todos serves the objective; flag
   opportunistic extras ("while we're at it...") for their own TASK.
6. **Risks and rollback** — irreversible steps (data migration, deletions,
   published artifacts) are flagged in `## Risks` with a rollback line. An
   empty Risks section on a plan touching state is a finding.
7. **Open questions triage** — each open question gets one destination:
   answer it now (you know the answer), accept it (explicitly, as a risk), or
   escalate it (§4 — it exceeds your authority). None may stay unowned.

## Verdict and actions

- **approve** → run `python3 .pm-harness/bin/harness.py plan approve
  <TASK-id> --by <you>` and report the checklist results.
- **revise** → do NOT approve; return the plan to its author with findings
  numbered against the checklist. The author edits the draft (drafts may be
  edited freely; only APPROVED plans are amendment-only, §12.4).

## Report format (deterministic)

```yaml
plan_review:
  task_id: "TASK-0007"
  category: complex
  verdict: revise          # approve | revise
  findings:
    - { check: 4, todo: 2, detail: "AC 'works correctly' is not testable" }
  open_questions: { answered: 1, accepted: 0, escalated: 1 }
```

## QA Scenarios

### Happy path
**Input**: "review the plan for TASK-0007" — a complete complex plan: testable
objective, 5 atomic todos with mechanical ACs, gates filled, risks with
rollback, no open questions.
**Expected**: verdict `approve`, `plan approve` executed, report emitted.
**Verify**: `python3 .pm-harness/bin/harness.py plan check TASK-0007` no
longer reports `plan-not-approved` (only unchecked todos remain).
**Evidence**: the report block and the plan's `approved_by` frontmatter.

### Error path
**Input**: a plan whose todos include "make the API robust" with no AC, plus
an unrelated "also refactor the logger" todo.
**Expected**: verdict `revise` with findings on checks 4 (untestable AC) and
5 (scope creep); `plan approve` is NOT run; the plan file is not edited by
the reviewer.
**Verify**: the plan's frontmatter still says `status: draft` and its content
hash is unchanged from before the review.
**Evidence**: the report block naming both findings.
