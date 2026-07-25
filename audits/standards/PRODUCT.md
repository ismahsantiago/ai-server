# Product standards

These rules govern product truth, readiness claims, CLI behavior, and generated
workspace safety.

## STD-PR-001 — Keep capability claims versioned and executable

Publish a versioned capability table using only `implemented`,
`experimental`, and `planned`. Operational documentation and manifests MUST
not present planned or pseudocode examples as executable. Every implemented
CLI example MUST remain compatible with the current `--help` contract.

**Verify mechanically:** documentation checks reject unknown status values and
unlabelled pseudocode; an example test extracts implemented commands and runs
their help or dry validation successfully.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-006`.

## STD-PR-002 — State validation maturity precisely

Report validation as `structure valid`, `host ready`, or `runtime healthy`;
never collapse these levels into a generic `valid`. Host readiness MUST check
the model file, helper executability, Docker Compose availability, and resource
budget. `--offline` or `--structural-only` MUST list every skipped check.

**Verify mechanically:** tests assert each level independently, prohibit a
higher-level result when a prerequisite fails, and compare reduced-mode output
with the complete list of skipped checks.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-004`.

## STD-PR-003 — Make CLI intent and destructive risk explicit

Require a subcommand and return usage exit code `2` when it is absent. Document
each option’s default, precedence, allowed destination, example, and side
effects. Mark `--force` as destructive. Invalid aliases MUST show valid values
or a similarity-based suggestion without executing an action.

**Verify mechanically:** CLI tests assert exit code `2`, complete help fields,
the destructive warning, typo suggestions, and no generated or replaced output
after invalid invocation.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-007`.

## STD-PR-004 — Protect generated-output ownership

Limit ordinary generation to `PROJECT_ROOT/generated/**`. A custom destination
MUST require a separate option and confirmation. Replacement MUST require a
valid generator-owned marker or manifest and use staging plus a recoverable
backup. Never follow a symlink or parent path outside the approved destination.

**Verify mechanically:** negative tests cover parent directories, unrelated
existing directories, malformed ownership markers, symlinks, and interrupted
replacement; successful replacement tests prove backup recovery.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `UX-20260724-002`.
