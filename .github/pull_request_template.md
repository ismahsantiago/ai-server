<!-- HARNESS-SPEC §11: every section filled. An unfilled section counts as missing. -->

## Summary

TASK-0007 records a fresh independent audit and remediates every confirmed
repository-local finding that can be closed without inventing live runtime,
network, model, distribution, or legal evidence. The patch hardens dependency
installation, audit evidence inputs, model-source validation, generated
workspace lifecycle and recovery, benchmark evidence, documentation, golden
fixture drift checks, and installed harness-agent conformance.

## Why / Context

The Director requested completion of the outstanding technical, security and
operational audit work. The immutable Spanish pre-remediation deliverables and
the append-only finding disposition are under
`audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/`. External Linux/model
runs, future LAN gateway policy, Codex harness support, and conditional legal
review are explicitly owned and blocked rather than represented as verified.

## Change type

- [ ] Feature (new capability)
- [x] Fix (corrects existing behavior)
- [ ] Breaking (changes existing behavior/contract in an incompatible way)
- [ ] Docs
- [ ] Chore / internal refactor (no observable behavior change)

## Risk & risk type

Medium security and availability risk. The patch changes path confinement,
dependency and audit supply-chain checks, generated secret-file handling,
archive restoration, container lifecycle cleanup, and evidence contracts.
Defaults remain localhost-only and fail-closed. Restore preserves displaced
targets; startup tears down only a stack started by that invocation.

## How this was tested

- `python3 -m unittest` — exit 0, 97 tests.
- `python3 -m unittest tests.test_cli tests.test_ci_contract tests.test_documentation_contract tests.test_harness_agents` — exit 0, 60 tests.
- `python3 .pm-harness/bin/harness.py agents check` — exit 0 for OpenCode and Claude.
- `python3 .pm-harness/bin/harness.py wiki check` — exit 0.
- Frozen audit hashes were recomputed for the three immutable files whose
  current hashes can be compared directly and matched `meta.md`.
- The final full CI and independent whole-change security review remain
  integration gates; no live Docker/model result is claimed here.

## Evidence

Finding-level ownership, changed surfaces, focused tests and formal blockers
for all 25 findings are in the final reconciliation section of
`audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/remediation.md`.
Security approval is already recorded there for SEC7-001/OPS7-001 and
SEC7-005; aggregate approval is intentionally pending.

## Checklist

- [x] `CHANGELOG.md` has an `[Unreleased]` entry referencing TASK-0007
- [x] Tests added/updated for behavior-changing fixes
- [x] `harness.py validate` has prior passing implementation evidence and is a final integration gate
- [x] Docs updated; `harness.py wiki check` exits 0
- [x] External/runtime/legal blockers have explicit owners and no unsupported claims
- [x] Independent whole-change security review approved
- [x] Full final CI and plan-adherence gates pass
