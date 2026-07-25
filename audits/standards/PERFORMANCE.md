# Performance standards

These rules apply to generated model-serving workspaces and to claims that a
workspace is ready or performant on a host.

## STD-PERF-001 — Use an explicit, validated model-file mapping

The model MUST be represented as a validated host file path and the fixed
container path `/models/model.gguf`. Rendering MUST produce the read-only file
bind `${MODEL_HOST_PATH}:/models/model.gguf:ro`. Startup MUST reject missing
paths, non-regular files, unreadable files, and unsupported file types.

**Verify mechanically:** tests cover repository-relative and absolute paths,
paths containing spaces, missing paths, directories, unreadable files, and the
exact parsed Compose bind.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `PERF-001`, `UX-20260724-003`.

## STD-PERF-002 — Version presets and calculate host memory feasibility

Each preset MUST be a versioned contract containing repository, revision, file,
architecture, quantization, byte size, SHA-256, chat template, and minimum and
recommended RAM. Feasibility MUST calculate model memory plus KV cache, runtime
buffers, and a 2–3 GB host reserve. It MUST return `NO-GO` when required
metadata is missing or available memory leaves insufficient margin and MUST
keep “generable” distinct from “verified on this host.”

**Verify mechanically:** schema tests reject every missing field; checksum and
size tests reject mismatches; deterministic resource fixtures cover below,
at, and above the required margin and assert distinct generation and host
verification outcomes.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `PERF-002`.

## STD-PERF-003 — Measure benchmarks instead of reporting placeholders

Benchmarks MUST perform warm-up and repeated measurements of time to first byte,
total latency, tokens per second, and peak memory. They MUST report p50 and p95,
validate the response JSON, and exit non-zero when the service or measurement
fails. They MUST record model, configuration, host, image, and runtime
identifiers and clean temporary files with a shell `trap`.

**Verify mechanically:** benchmark tests use a known response fixture and a
failed service; assert numeric samples and percentiles, reproducibility fields,
non-zero failure status, and removal of temporary files.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `PERF-003`, `UX-20260724-005`.

## STD-PERF-004 — Bound readiness and shutdown

Wait for readiness with a finite timeout and distinguish `starting`, `healthy`,
and `unhealthy`. On timeout or unhealthy state, capture `docker compose ps`
and service logs and exit non-zero. Workstation profiles MUST use no restart or
a finite restart policy. Generate a stop operation with a documented shutdown
timeout.

**Verify mechanically:** lifecycle tests exercise healthy, unhealthy, and
timeout fixtures; assert bounded completion, diagnostics, exit codes, restart
policy, and stop timeout.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `PERF-004`.

## STD-PERF-005 — Pin and regression-test the serving runtime

Pin the serving image to a tested version and immutable digest. Record image,
digest, version, and flag-schema compatibility in the generated manifest.
Every explicit runtime update MUST pass template compatibility checks and a
benchmark regression threshold before approval.

**Verify mechanically:** CI rejects mutable references or incomplete manifest
metadata and compares compatibility plus benchmark results with the approved
baseline for each digest change.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `PERF-005`, `SEC-005`.
