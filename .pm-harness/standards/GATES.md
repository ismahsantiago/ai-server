# Quality gates

## Gate 0 — Task start

1. Read this file.
2. Classify the task and load only the applicable rule documents
   (table in `README.md`).
3. If the task touches a product invariant, declare it in the plan before
   writing code.
4. Plan gate (HARNESS-SPEC §12): the task's `plans/{TASK-id}.plan.md` exists
   and is approved by the owner's superior before execution starts — the CLI
   refuses `started → in_progress` without it.

## Gate 1 — Before integrating (PR / harness task delivery)

Mechanical block (every command exit 0). The engineering manager fills in the
stack-specific commands during roster generation and keeps them current:

```bash
docker --version  # stack build/runtime baseline (Docker-first lab)
python3 --version  # language runtime baseline
python3 -m pip --version  # package manager baseline
test -f .pm-harness/HARNESS-SPEC.md  # dependency/audit baseline until app deps exist
python3 .pm-harness/bin/harness.py validate    # harness contracts
python3 .pm-harness/bin/harness.py wiki check  # when docs/wiki were touched
python3 .pm-harness/bin/harness.py plan check <task-id>  # plan adherence (§12)
python3 .pm-harness/bin/harness.py changelog check --task <task-id>  # when product behavior changed (§11)
```

Manual checklist:

- [ ] New multi-write sequence? → wrap it in a transaction.
- [ ] New update path? → validates input as strictly as its create path.
- [ ] New UI fetch? → visible error state.
- [ ] New endpoint/parameter? → a UI consumer exists, or a roadmap note.
- [ ] Schema change? → versioned migration, export/backup updated.
- [ ] New data leaving the machine? → recorded consent/notice.
- [ ] Security-relevant change (auth, input parsing, secrets, third-party
      calls)? → security area review recorded on the task.
- [ ] Documented behavior changed? → wiki pages updated (`wiki check` clean).
- [ ] New permission/allowlist entry? → no wildcard that subsumes (and voids)
      granular entries for the same tool (e.g. `Bash(python3 *)` next to
      `Bash(python3 .pm-harness/bin/harness.py *)`).
- [ ] Defect no rule covers? → APR entry in this same change (`IMPROVEMENT.md`).

## Gate 2 — Release

- All of Gate 1 green in CI, not only locally.
- Recent verified backup before migrating a real data store.
- `IMPROVEMENT.md` reviewed: this cycle's APRs resolved (each with a destination).

## Periodic audit

- A full audit at least once per plan phase (or monthly). Every run is
  independent and feeds this system via `IMPROVEMENT.md`.
