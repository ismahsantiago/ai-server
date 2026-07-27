<!-- HARNESS-SPEC §11: every section filled. An unfilled section counts as missing. -->

## Summary

TASK-0012 prepares a minimal portable packet for cloning this repository onto
the intended server and continuing it with an independent equivalent AI
instance. It shares the same-project PM Harness, root activation bridges,
minimal Claude/OpenCode Markdown routers, sanitized compatibility template, and
an English operator handoff while excluding host-local and runtime state.

## Why / Context

The Director approved KICK-0003 to exercise continuity between instances from
the same AI provider/model family and capture the resulting operational
learning. The next event is a clean server clone. The packet must preserve
governed project history without carrying credentials, permissions, sessions,
dependencies, model weights, caches, logs, or unsupported runtime claims.

## Change type

- [ ] Feature (new capability)
- [ ] Fix (corrects existing behavior)
- [ ] Breaking (changes an existing behavior/contract incompatibly)
- [x] Docs (portable operator and AI-instance continuity contract)
- [ ] Chore / internal refactor (no observable behavior change)

## Risk & risk type

Medium security and integrity risk. Sharing governance and platform routing
surfaces could expose host-local authorization/session data or allow stale
summaries to override executable contracts. Repository-local deny rules,
source-only platform trees, same-project isolation, redacted evidence, exact
index review, independent security review, and clean-clone validation bound the
risk. LAN remains unauthorized and fail-closed.

## How this was tested

- `python3 -m unittest` — exit 0, 97 tests.
- `python3 .pm-harness/bin/harness.py validate` — exit 0.
- `python3 .pm-harness/bin/harness.py agents check` — exit 0 for Claude and
  OpenCode.
- `python3 .pm-harness/bin/harness.py wiki check` — exit 0 before the final
  integration-record update and repeated as an integration gate.
- `git diff --check` — exit 0 for the documentation slice.
- Generator `doctor --models-path/--out` and `validate --tier host/runtime`
  syntax was checked against current CLI help.
- Full isolated CI, exact-index security review, and clean-checkout walkthrough
  remain pending integration gates; no GGUF/runtime/benchmark pass is claimed.

## Evidence

- `docs/next-instance-server-handoff.md` records the authority map, portable
  inventory/denylist, hash-locked bootstrap, governed resume rules,
  authorized-GGUF flow, evidence tiers, capture contract, safety recovery, and
  end-session checklist.
- `.pm-harness/wiki/pages/current-capability-status.md` compiles the portable
  continuity and evidence boundaries while preserving the existing roadmap
  contradiction.
- `CHANGELOG.md` records the user-visible TASK-0012 addition.
- Final filename/secret/symlink/large-file review, index-only checkout, no-local
  clone, and full CI evidence will be supplied by the integration owner.

## Checklist

- [x] `CHANGELOG.md` has an `[Unreleased]` entry referencing TASK-0012.
- [x] Operator documentation and LLM Wiki describe the same evidence boundary.
- [x] `.codex/` absence and same-project `.pm-harness/` isolation are explicit.
- [x] LAN remains unauthorized/fail-closed; no live runtime result is inferred.
- [x] Focused unit, harness, agent, wiki, and diff checks pass.
- [ ] Independent whole-packet security review approves the exact candidate.
- [ ] Index-only and committed `git clone --no-local` walkthroughs pass.
- [ ] Full isolated CI and final plan/changelog gates pass.
- [ ] Final staged allowlist/denylist inspection passes before commit.
- [ ] No push, tag, or release occurs without Director-confirmed publication.
