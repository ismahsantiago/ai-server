# Standards improvement protocol

## Core rule

Every defect found (in an audit, review, or development) that **no existing
rule covers** generates an **APR-nnn** entry in the log below, in the same
change that fixes it. Each APR has **exactly one destination**:

- `new rule` — a STD-XXX-nn is added to the matching rule document.
- `harden gate` — the rule existed but the gate missed it: the mechanical
  verification is strengthened.
- `clarify` — the rule existed but was ambiguous: it is rewritten.
- `retire` — the rule no longer earns its slot: it is removed (frees budget).
- `log only` — a one-off not worth generalizing: documented, no rule.

If a defect of the same type reappears in a later run, that is evidence the
rule/gate does not work → a `harden gate` APR is mandatory.

## Budget and health

- Max ~20 rules per document. Full document ⇒ retire before adding.
- Per-audit metrics: total findings, how many were already covered by a rule
  (gate failure) vs. not covered (new rule), rules retired.
- Healthy trend: over time, "finding covered by a rule that happened anyway"
  tends to zero.

## APR log

| APR | Date | Origin | Destination | Result |
|---|---|---|---|---|
| APR-001 | 2026-07-26 | TASK-0008 found `scripts/ci.sh` pinned `plan check TASK-0007`, so Gate 1 asserted a neighboring in-progress task instead of the task under integration and kept developer CI red. | harden gate | `scripts/ci.sh` now keeps the `.pm-harness/` clean-clone guard, honors `HARNESS_PLAN_TASK` for the current integration task, and automatically checks only TASK manifests in `in_review`, `approved`, or `closed`. |
