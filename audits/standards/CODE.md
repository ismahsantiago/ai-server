# Code Standards

These rules are mandatory for generator output and validation changes. Each
rule records the current audit finding that established it.

## STD-COD-001 — Confine generated output

Every generated workspace MUST remain a strict descendant of
`PROJECT_ROOT/generated`. The generator MUST resolve the complete destination
before writing, reject every destination containing a symlink component, and
MUST NOT let `--force` weaken either restriction.

**Verify mechanically:** Negative tests MUST prove that normal and `--force`
generation reject `.git`, `docs`, `models`, `scripts`, `audits`, paths outside
`generated`, and destinations containing symlink components. Tests MUST assert
that none of those targets changed.

**Current finding origin:** `COD-001` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-COD-002 — Serialize structured output safely

The renderer MUST build manifests as objects and serialize them with
`json.dumps`, serialize YAML with a YAML emitter, and encode `.env` values with
context-correct quoting. It MUST validate filesystem paths and CIDRs with
dedicated parsers before rendering and MUST NOT interpolate untrusted values
directly into JSON, YAML, or `.env` structure.

**Verify mechanically:** Parser round-trip tests MUST cover quotes, newlines, colons,
hashes, `${...}`, and Unicode in every applicable output. Invalid paths and
CIDRs MUST fail before any workspace is committed.

**Current finding origin:** `COD-002` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-COD-003 — Commit generation atomically and deterministically

The generator MUST render and validate in a sibling temporary directory, then
replace the target with an atomic rename while retaining a recoverable backup.
It MUST exclude timestamps from canonical output unless explicitly requested
and MUST record a digest of all effective inputs and templates.

**Verify mechanically:** Failure-injection tests MUST leave the previous workspace
usable and the recovery backup intact. Two runs with identical inputs and
templates MUST produce byte-equivalent canonical output and the same recorded
digest.

**Current finding origin:** `COD-003` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-COD-004 — Detect generated-workspace drift

The project MUST keep minimal golden fixtures under version control outside
`generated/`, regenerate them in CI, and compare them after normalizing only
explicitly declared volatile metadata. It MUST provide `validate-all` or
`drift-check` behavior that checks every local generated workspace and reports
all divergences in one run.

**Verify mechanically:** CI MUST fail when a golden fixture or any local workspace
differs from regenerated output, list every divergent path, and pass when the
only differences are declared volatile fields.

**Current finding origin:** `COD-004` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.
