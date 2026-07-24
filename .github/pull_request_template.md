<!-- HARNESS-SPEC §11: every section filled. An unfilled section counts as missing. -->

## Summary

TASK-0006 reconciles TASK-0001 through TASK-0005 against the approved product
scope, corrects product documentation claims, and compiles the accepted state
into the LLM Wiki. Engineering/runtime/security defects remain assigned to
TASK-0007 and are not changed by this product-only work.

## Why / Context

The Director requested a review of pending work and an audit against what was
requested. See TASK-0006, KICK-0001, and
`audits/TASK-0006-product-acceptance-audit.md`.

## Change type

- [ ] Feature (new capability)
- [ ] Fix (corrects existing behavior)
- [ ] Breaking (changes existing behavior/contract in an incompatible way)
- [x] Docs
- [ ] Chore / internal refactor (no observable behavior change)

## Risk & risk type

Security/documentation risk: previous wording could imply static matrix or
validation proved runtime/LAN support. The revised docs disclose the boundary,
require manual firewall enforcement, and avoid normal `--force` guidance.

## How this was tested

The exact TASK-0006 gate commands and literal exit codes are recorded in
`audits/TASK-0006-product-acceptance-audit.md`. Final acceptance remains
pending TASK-0007 evidence.

## Evidence

Evidence: the audit scope register, closed-task reconciliation, F-001 through
F-013, H-001 through H-006, fresh generated acceptance workspace, unit tests,
harness validation, wiki validation, and changelog validation.

## Checklist

- [x] `CHANGELOG.md` has an `[Unreleased]` entry referencing this change
- [x] Tests added/updated for this change (not applicable: product/docs-only; existing unit gates run)
- [x] `harness.py validate` is clean
- [x] Docs/wiki updated if this changes documented behavior (`harness.py wiki check` clean)
