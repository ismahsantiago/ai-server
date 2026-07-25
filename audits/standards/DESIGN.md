# Experience design standards

No graphical interface finding was present in the current audit fragments.
These rules therefore apply conditionally to the audited command-line and
generated-helper experience; they do not invent visual-design requirements.

## STD-UX-001 — Make generated helpers independent of caller location

Each generated helper MUST resolve its script and workspace directories from
`${BASH_SOURCE[0]}` and pass explicit paths for Compose, `.env`, logs, and
other artifacts. It MUST not depend on the caller’s current working directory.

**Verify mechanically:** execute start, validate, and smoke helpers from the
repository root, generated workspace, and an unrelated third directory; assert
identical path resolution and outcomes.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-001`.

## STD-UX-002 — Present one unambiguous model-location contract

The experience MUST ask for or materialize one canonical host model path, with
explicit consent and free-space validation before copying weights. It MUST show
and record both host and container paths. Before startup, it MUST explain and
reject absence, wrong file type, unreadability, or unsupported extension.

**Verify mechanically:** interaction tests cover bind and consented-copy paths,
declined consent, insufficient space, missing file, directory, unreadable file,
unsupported extension, and manifest path consistency.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-003`, `PERF-001`.

## STD-UX-003 — Preserve truthful smoke-test outcomes

Use distinct non-zero exits for missing `curl`, transport failure, non-2xx HTTP,
and invalid minimum JSON. Measure real latency with `time_total` or a monotonic
clock. A separate `--report-even-on-failure` mode MAY preserve diagnostics but
MUST never convert a failure into PASS.

**Verify mechanically:** fixture tests trigger each failure class and assert
its exit code, evidence, measured latency, and final FAIL status in report mode.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-005`, `PERF-003`.

## STD-UX-004 — Make readiness levels and omissions visible

Display `structure valid`, `host ready`, and `runtime healthy` as distinct
states with the failed prerequisite. Reduced validation modes MUST visibly list
what was not verified and MUST not use success language associated with a
higher readiness level.

**Verify mechanically:** snapshot or CLI-output tests cover each state, each
failed prerequisite, and reduced validation with its omission list.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-004`.

## STD-UX-005 — Guard destructive output replacement

The generator MUST default the destination to `PROJECT_ROOT/generated/**`. It
MUST present custom output selection and replacement confirmation as separate
decisions, clearly name the target, reject non-generator-owned content, and
provide a recoverable backup when replacement succeeds.

**Verify mechanically:** interaction tests prove no write occurs without both
required decisions, unsafe and symlink targets are rejected, and the displayed
backup can restore the previous output.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-002`.
