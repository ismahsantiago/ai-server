# Operations Standards

These rules are mandatory for generated deployments, CI, and operational
runbooks. Each rule records the current audit finding that established it.

## STD-OPS-001 — Enforce one model-mount contract

The system MUST represent the model location as separate `host_model_path` and
`container_model_path` values and use those values consistently across CLI,
manifest, validation, Compose, and generated documentation. Startup MUST fail
unless the host path exists, is a regular file, and is readable.

**Verify mechanically:** A Compose-resolution test MUST inspect the effective bind
mount and prove that the validated host file maps to the declared container
path. Missing, directory, unreadable, and mismatched paths MUST fail.

**Current finding origin:** `OPS-001` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-002 — Require externally supplied secrets and enforced network policy

The generator MUST NOT generate credentials. Startup MUST load a non-empty,
non-default secret from an approved file or secret store. The system MUST parse
and validate the allowed CIDR and enforce it through a testable proxy or
firewall. The deployment MUST remain `NO-GO` while enforcement is manual or
unverified.

**Verify mechanically:** Startup tests MUST reject missing, empty, and default
secrets. An automated network test MUST prove allowed clients succeed and
disallowed clients fail before the deployment can become `GO`.

**Current finding origin:** `OPS-002` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-003 — Make smoke checks strict and secret-safe

The smoke check MUST read only the required key from `.env` without sourcing
executable content and MUST use a private temporary directory removed by
`trap`. It MUST require HTTP 200, the expected JSON shape, and a numeric
`%{time_total}`, exit non-zero on every violation, and remain separate from
diagnostic benchmarking.

**Verify mechanically:** `bash -n` and ShellCheck MUST pass. Tests MUST demonstrate
non-zero exits for malformed `.env`, unexpected status, invalid JSON, and
missing fields, and MUST confirm temporary data is removed.

**Current finding origin:** `OPS-003` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-004 — Pin and attest every dependency

Runtime images MUST be pinned by immutable digest. Hash-verified locks for
Python and OpenCode MUST be committed beside their manifests, and installation
MUST use only those locks. Automated updates MUST require changelog review and
produce an SBOM plus dependency and image scan results.

**Verify mechanically:** CI MUST reject mutable image tags, unlocked or unhashed
dependencies, manifest-lock drift, and scan failures; it MUST retain the SBOM
and scan reports as build artifacts.

**Current finding origin:** `OPS-004` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-005 — Run the complete supported CI gate

CI MUST run on every supported Python version and execute unit tests,
`pip check`, lint, type checking, coverage enforcement, static Compose
validation, `bash -n`, ShellCheck, fixture generation and validation,
applicable harness gates, dependency scanning, and image scanning. It MUST
publish coverage and gate evidence.

**Verify mechanically:** A required branch check MUST fail when any matrix entry or
listed gate fails. CI configuration tests MUST enumerate the same supported
Python versions declared by project metadata.

**Current finding origin:** `OPS-005` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-006 — Produce verifiable runtime evidence

The runtime or proxy MUST enable access logging with documented format,
rotation, and retention, and service metrics MUST be exposed and collected.
Evidence MUST record numeric latency, memory from `docker stats`, model
identity, image digest, configuration, and configuration hash. An absent
measurement MUST be marked `NOT MEASURED` or fail the evidence-producing
command.

**Verify mechanically:** An integration test MUST produce a parseable evidence bundle
containing every required field and MUST fail, or emit `NOT MEASURED`, when a
measurement source is unavailable.

**Current finding origin:** `OPS-006` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-007 — Make recovery and incident response testable

The project MUST provide idempotent backup and restore commands with
inventories and checksums and retain a documented number of immutable generated
versions. It MUST document and test stop, rollback to the prior image digest
and configuration, and restore, and MUST maintain a LAN incident runbook
covering containment, token rotation, evidence, ownership, and closure
criteria.

**Verify mechanically:** Gate 2 MUST execute a restore drill twice, verify checksums,
prove rollback selects the recorded digest and configuration, and retain the
drill and incident-runbook evidence.

**Current finding origin:** `OPS-007` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-OPS-008 — Keep profile semantics and scripts location-independent

The project MUST define and consistently apply one documented profile
contract: either materialize profile settings or record them only in manifest
and `.env`. Generated scripts MUST resolve paths from `SCRIPT_DIR`, invoke
Compose with an explicit `--project-directory`, and MUST NOT depend on the
caller's working directory.

**Verify mechanically:** Contract tests MUST compare documentation, manifest, `.env`,
and effective Compose settings. Script tests MUST produce the same result when
run from the repository root and an unrelated directory.

**Current finding origin:** `OPS-008` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.
