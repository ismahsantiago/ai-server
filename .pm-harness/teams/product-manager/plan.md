## Active
- TASK-0010 — Tier model ownership (KICK-0002, Phase H product half). State `started`. Full §12 plan drafted by product-analyst, reviewed twice by product-manager with the `plan-review` skill (verdict 1: `revise`, 8 findings; verdict 2: `approve`). 20 todos, all ACs mechanical. Awaiting `plan approve TASK-0010 --by pm-orchestrator` — the manifest owner is a manager, so per SPEC §12.2 the approver is pm-orchestrator, not product-manager. The CLI refuses `started → in_progress` until then.
- TASK-0006 — Full product acceptance/documentation audit plan drafted; execution awaits PM Orchestrator review and approval.

## Next
- On TASK-0010 plan approval: transition to `in_progress` and delegate execution to product-analyst, producing `docs/hardware-tiers.md`.
- Carry to pm-orchestrator at TASK-0010 delivery (recorded as `## Delivery conditions` in the plan): the verbatim `tier_label` set for Director visibility before any release prints one; the routing of any `ADJUSTED`/`REPLACED` mapping specification to engineering-manager (TASK-0008 amendment or follow-up task); and the quoted distribution-posture ruling.
- Delegate one evidence pass per closed deliverable to product-analyst, then integrate findings and product-owned documentation remediation under the approved TASK-0006 plan.
- Independently verify TASK-0007 user-visible remediation before final TASK-0006 acceptance.

## Blocked
- TASK-0010 execution — `.pm-harness/plans/TASK-0010.plan.md` is `status: draft`; product-manager cannot self-approve a `complex` plan it owns (§12.2).
- TASK-0006 execution — `.pm-harness/plans/TASK-0006.plan.md` remains draft and TASK-0006 must not transition to `in_progress` before approval.

## Watching (not owned)
- TASK-0008 (engineering-manager) — amendment in flight reporting stock macOS is richer in probeable detail than assumed. TASK-0010's reduced-confidence and macOS rulings are written conditionally on it and must not pre-empt it.
- TASK-0009 — host-side runner evaluation; selects Branch B availability in TASK-0010's macOS ruling.
