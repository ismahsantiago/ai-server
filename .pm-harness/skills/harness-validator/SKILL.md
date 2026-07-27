---
name: harness-validator
description: "Walks all .pm-harness state manifests and memory stores and reports inconsistencies: orphans, dependency cycles, invalid transitions, stuck in_progress beyond timeout, resumable stale units, duplicate memory signatures. Read-only. Triggers: 'validate the harness', 'harness health check'."
allowed-tools:
  - "bash"
  - "read"
  - "glob"
  - "grep"
---

# harness-validator — consistency validator (read-only)

You walk `.pm-harness/state/*.json` and `.pm-harness/memory/**` and report
inconsistencies against `.pm-harness/HARNESS-SPEC.md`. **You never modify
anything**: you report; fixing belongs to the owner or the corresponding manager.

**Run it via the CLI** — the checks are implemented in code:

```
python3 .pm-harness/bin/harness.py validate
```

## Normative checks (in this order)

Over `state/*.json`:
1. **Parseable JSON** with required fields (`id, kind, owner, status, history`).
2. **status vs history**: `status` == `to` of the last non-rejected entry.
3. **Valid transitions**: every consecutive (`from → to`) pair in the history
   exists in the SPEC §1.1 table; `history` strictly append-only
   (non-decreasing timestamps).
4. **Orphans**: `owner` references a role existing in `harness.json → roster`
   (or `pm-orchestrator`); `depends_on` references existing ids.
5. **Cycles**: the `depends_on` graph is acyclic (detect and list the cycle).
6. **Stuck**: `in_progress` with no transition for >48h → `stale` candidate.
7. **Resumable**: list units in `stale` (informative, not an error).

Over `memory/`:
8. **Complete frontmatter** per note (`id, type, scope, importance, signature`).
9. **Duplicate signatures**: two live notes with the same `signature` in the same store.
10. **Supersedes chains**: the referenced id exists; no supersedes cycles.

## Report format (deterministic)

```yaml
checked: { manifests: N, memory_notes: M }
errors:      # hard violations (checks 1-5, 8-10)
  - { check: "invalid-transition", unit: "TASK-0002", detail: "closed → in_progress without reopened" }
warnings:    # check 6
  - { check: "stuck-in-progress", unit: "TASK-0005", detail: "no transition since <ts>" }
info:        # check 7
  - { check: "stale-resumable", unit: "TASK-0001" }
```

Exit semantics: a report with `errors: []` = healthy (exit 0). Any error =
inconsistent harness (exit 1); the PM Orchestrator must not close a session
without resolving it or registering it as a task.

## QA Scenarios

### Happy path
**Input**: "validate the harness" on a `.pm-harness/` with correct manifests.
**Expected**: report with real counts and `errors: []`, exit 0.
**Verify**: the report lists `checked` > 0 and zero entries under `errors`.
**Evidence**: report block in the reply.

### Error path
**Input**: "validate the harness" with a manifest whose history contains
`closed → in_progress` (without going through `reopened`).
**Expected**: `errors` contains `check: invalid-transition` with the unit and
the offending pair cited; all other checks still run and report. Exit 1.
**Verify**: the report contains the exact entry plus the other counts.
**Evidence**: report block with the error.
