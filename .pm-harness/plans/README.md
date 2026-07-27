# plans/ — per-TASK execution plans

One `{TASK-id}.plan.md` per TASK unit (HARNESS-SPEC §12): frontmatter
(`task_ref`, `category`, `status`, approver fields) + Objective / Todos (with
acceptance criteria) / Gates / Risks / Open questions / Amendments
(append-only). Create with `python3 ../bin/harness.py plan new`, approve with
`plan approve` (owner's superior), verify adherence with `plan check`. The
CLI refuses `started → in_progress` without an approved plan and
`in_progress → in_review` with unchecked todos. Deviations are recorded with
`plan amend` — an approved plan is never rewritten.
