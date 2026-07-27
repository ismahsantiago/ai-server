# state/ — unit-of-work manifests

One `{id}.json` file per unit (TASK-, CER-, ESC-, ART-). Format and valid
transitions: `../HARNESS-SPEC.md` §1. History is append-only; `status` must
match the last non-rejected transition. Create/transition with
`python3 ../bin/harness.py state ...`; validate with `harness.py validate`.
