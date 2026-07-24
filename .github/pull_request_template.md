<!-- HARNESS-SPEC §11: every section filled. An unfilled section counts as missing. -->

## Summary

<!-- What changed, in one or two sentences. -->

## Why / Context

<!-- The problem or need this addresses. What prompted it. Link the TASK id
     and any relevant escalation/decision/ceremony record. -->

## Change type

- [ ] Feature (new capability)
- [ ] Fix (corrects existing behavior)
- [ ] Breaking (changes existing behavior/contract in an incompatible way)
- [ ] Docs
- [ ] Chore / internal refactor (no observable behavior change)

## Risk & risk type

<!-- None | Data loss | Security | Availability | Cost | Other — one line
     on why, and the mitigation if any. -->

## How this was tested

<!-- Exact commands run, or the manual steps followed. -->

## Evidence

<!-- Command output, logs, screenshots — whatever demonstrates the change
     works and doesn't regress adjacent behavior. -->

## Checklist

- [ ] `CHANGELOG.md` has an `[Unreleased]` entry referencing this change
- [ ] Tests added/updated for this change (or explicitly not applicable, and why)
- [ ] `harness.py validate` is clean
- [ ] Docs/wiki updated if this changes documented behavior (`harness.py wiki check` clean)
