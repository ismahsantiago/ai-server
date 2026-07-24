# Audit Standards Improvement Protocol

## Purpose

This file is the canonical, append-only register for improvements discovered by independent repository audits. Every audit finding that was not covered by the standards at the audit baseline receives exactly one APR entry and exactly one destination.

## Destination protocol

The allowed destinations are:

- `new rule`: create a normative requirement where no applicable rule existed.
- `harden gate`: strengthen an existing mechanical check that existed but failed to detect the issue.
- `clarify`: remove ambiguity without changing the normative requirement.
- `retire`: remove an obsolete or harmful rule.
- `log only`: retain evidence when no standards change is justified.

An APR must select one destination only. Its justification must explain why that destination is appropriate. A later decision never rewrites an APR row: append a superseding APR and reference the earlier identifier.

## Budget

Triage and destination assignment are limited to 30 minutes per finding. Follow-up work uses a bounded size: `S` is at most one engineering day, `M` is at most two engineering days, and `L` is at most five engineering days. Work exceeding the recorded budget must be split into a new approved task or escalated.

## Health metrics

The register is healthy when all of the following hold:

- 100% of uncovered findings have one unique APR identifier.
- 100% of APRs have one finding identifier, one destination, a justification, a bounded budget, a measurable health metric, and a status.
- 0 APR rows are edited or deleted after registration.
- 100% of resolved `new rule` and `harden gate` APRs cite the enforcing rule or automated check in a later append-only resolution record.
- 0 mechanical-gate failures are represented as passing.

## APR register

The table is append-only. Existing rows must not be edited, reordered, or deleted.

| APR | Date | Finding | Destination | Justification | Budget | Health metric | Status |
|---|---|---|---|---|---|---|---|
| APR-001 | 2026-07-24 | PERF-001 | `new rule` | No baseline rule defined separate validated host and container model paths. | M | Model bind contract tests pass for repository, absolute, missing, non-file, and spaced paths. | open |
| APR-002 | 2026-07-24 | PERF-002 | `new rule` | No baseline rule required versioned model metadata or a resource-fit decision. | L | Every preset has complete metadata and insufficient or unknown capacity produces `NO-GO`. | open |
| APR-003 | 2026-07-24 | PERF-003 | `harden gate` | A mechanical smoke benchmark existed but could report placeholders instead of measured service behavior. | M | The benchmark fails without a service and emits warm-up, p50, p95, tokens/s, and peak-memory evidence. | open |
| APR-004 | 2026-07-24 | PERF-004 | `new rule` | No baseline rule required bounded readiness or finite workstation restart behavior. | M | Startup distinguishes starting, healthy, unhealthy, and timeout states and returns nonzero on failure. | open |
| APR-005 | 2026-07-24 | PERF-005 | `new rule` | No baseline rule governed immutable serving images or compatibility evidence for upgrades. | M | Generated manifests record image version and digest, and every explicit upgrade passes compatibility regression. | open |
| APR-006 | 2026-07-24 | OPS-001 | `new rule` | No baseline rule established one end-to-end model mount contract. | M | Compose resolution proves the selected readable host file is mounted at the declared container path. | open |
| APR-007 | 2026-07-24 | COD-001 | `harden gate` | A destination allowlist existed but its mechanical guard missed parent paths and symlink traversal. | M | Negative generation tests reject protected roots and every destination containing a symlink. | open |
| APR-008 | 2026-07-24 | COD-002 | `new rule` | No baseline rule required parser-backed validation and context-safe serialization. | L | JSON, YAML, and dotenv round-trip tests pass for quotes, line breaks, delimiters, interpolation syntax, and Unicode. | open |
| APR-009 | 2026-07-24 | COD-003 | `new rule` | No baseline rule required staged atomic replacement, recovery, or deterministic input provenance. | L | Interrupted generation preserves the prior workspace and identical inputs produce identical canonical output hashes. | open |
| APR-010 | 2026-07-24 | OPS-002 | `new rule` | No baseline rule prohibited generated secrets or required verified LAN allowlist enforcement. | L | Startup rejects absent, empty, or default secrets and LAN remains `NO-GO` until an automated control check passes. | open |
| APR-011 | 2026-07-24 | OPS-003 | `harden gate` | A smoke script existed but its mechanical result did not enforce secure secret loading, HTTP success, JSON validity, or real latency. | M | Strict smoke returns nonzero for every failed invariant and diagnostic benchmarking cannot convert failure to pass. | open |
| APR-012 | 2026-07-24 | COD-004 | `new rule` | No baseline rule required canonical golden fixtures or generated-workspace drift detection. | M | CI regenerates fixtures and drift-check lists every divergent local workspace before failing. | open |
| APR-013 | 2026-07-24 | OPS-004 | `new rule` | No baseline rule required immutable and hash-locked supply-chain inputs. | L | Installs use reviewed locks, serving images use digests, and updates publish SBOM and scan evidence. | open |
| APR-014 | 2026-07-24 | OPS-005 | `harden gate` | Gate 1 existed but omitted CI execution across supported runtimes and key quality and security checks. | L | CI executes the declared runtime matrix and publishes passing test, lint, type, coverage, shell, Compose, harness, dependency, and image checks. | open |
| APR-015 | 2026-07-24 | ARN-001 | `new rule` | No baseline rule required detected-host provenance in delegation or cross-host routing tests. | M | OpenCode and Claude routing tests verify platform-specific ID, provider, and effort contracts. | open |
| APR-016 | 2026-07-24 | ARN-002 | `new rule` | No baseline rule required native Codex materialization or fail-closed routing for unknown hosts and malformed IDs. | L | Codex discovery and materialization pass, complete provider/model IDs validate, and unknown hosts are rejected. | open |
| APR-017 | 2026-07-24 | OPS-006 | `new rule` | No baseline rule required measurable logging, metrics, retention, and reproducibility evidence. | L | Runs emit numeric latency and memory plus model, digest, config, and hash evidence; absent measurements are never labeled measured. | open |
| APR-018 | 2026-07-24 | OPS-007 | `new rule` | No baseline rule required checksum-backed backup, restore, rollback, or LAN incident drills. | L | A Gate 2 drill restores a checksummed version and records stop, rollback, containment, token rotation, owner, and closure evidence. | open |
| APR-019 | 2026-07-24 | OPS-008 | `new rule` | No baseline rule fixed profile materialization semantics or helper independence from the caller directory. | M | Profile behavior is consistent across docs and artifacts, and scripts pass from the repository, workspace, and an external directory. | open |
| APR-020 | 2026-07-24 | ARN-003 | `harden gate` | A permission review item existed in Gate 1 but did not compare materialized permissions with role boundaries. | M | The permission gate proves read-only and implementation profiles differ correctly and workers cannot delegate or write foreign memory. | open |
| APR-021 | 2026-07-24 | ARN-004 | `new rule` | No baseline rule required version-sealed engine and pack conformance coverage. | L | CI passes the sealed conformance suite for state, plans, checksums, memory, materialization, routing, and migrations. | open |
| APR-022 | 2026-07-24 | UX-20260724-002 | `harden gate` | An output allowlist existed but did not mechanically prevent unsafe parents, symlinks, or unmarked replacement. | L | Generation rejects unsafe targets and replacement requires a valid marker, staging, and recoverable backup. | open |
| APR-023 | 2026-07-24 | UX-20260724-001 | `new rule` | No baseline rule required generated helpers to operate independently of the caller directory. | M | Start, validate, and smoke pass from the repository root, workspace, and a third directory. | open |
| APR-024 | 2026-07-24 | UX-20260724-003 | `new rule` | No baseline rule made the selected host model and container model contract operator-visible and enforceable. | M | The manifest records both paths and preflight rejects missing, unreadable, non-file, or unsupported model inputs. | open |
| APR-025 | 2026-07-24 | UX-20260724-004 | `harden gate` | A validator existed but its single `valid` result concealed host and runtime checks it had not performed. | M | Validation reports structural, host-ready, and runtime-healthy levels and enumerates every skipped check. | open |
| APR-026 | 2026-07-24 | UX-20260724-005 | `harden gate` | A smoke command existed but could fail transport, HTTP, schema, or measurement requirements without a distinct failing result. | M | Smoke returns documented nonzero codes per failure class and report-on-failure never changes the verdict. | open |
| APR-027 | 2026-07-24 | UX-20260724-006 | `new rule` | No baseline rule separated implemented operator behavior from experimental and planned roadmap material. | M | A versioned status table covers every surfaced capability and implemented examples pass automated help validation. | open |
| APR-028 | 2026-07-24 | UX-20260724-007 | `new rule` | No baseline rule defined CLI usage exits, complete option help, destructive warnings, or typo recovery. | S | Missing commands exit 2 and CLI help tests cover defaults, precedence, destinations, examples, warnings, and suggestions. | open |
| APR-029 | 2026-07-24 | SEC-001 | `new rule` | No baseline rule defined minimum secret entropy, secure file mode, or fail-closed placeholder rejection. | M | Secret preflight requires at least 32 random bytes, files are mode 0600, and weak or placeholder values fail. | open |
| APR-030 | 2026-07-24 | SEC-002 | `new rule` | No baseline rule prohibited direct unauthenticated LAN publication or required proof of TLS and CIDR enforcement. | L | LAN exposure remains disabled unless preflight proves authenticated TLS proxying and effective CIDR control. | open |
| APR-031 | 2026-07-24 | SEC-003 | `new rule` | No baseline rule required strict control-character rejection and parser-safe serialization at configuration boundaries. | L | Injection regression cases cannot alter JSON, YAML, dotenv, or Compose structure and invalid inputs fail closed. | open |
| APR-032 | 2026-07-24 | SEC-004 | `harden gate` | A mechanical validator existed but text matching missed cross-file security invariants and Compose resolution. | L | Mutation tests independently break each required control and validator plus `docker compose config` reject every mutation. | open |
| APR-033 | 2026-07-24 | SEC-005 | `new rule` | No baseline rule required digest pinning, hash locks, SBOMs, scanning, or vulnerability-response governance. | L | CI verifies immutable inputs, produces SBOMs, passes scans, and links reviewed update and response records. | open |
| APR-034 | 2026-07-24 | SEC-006 | `new rule` | No baseline rule defined container least privilege and bounded resource invariants. | L | Static and runtime checks prove non-root identity, dropped capabilities, PID and resource limits, minimal log permissions, and network isolation where viable. | open |
| APR-035 | 2026-07-24 | LEG-001 | `new rule` | No baseline rule required project, dependency, image, and model provenance and licensing evidence. | M | Distribution contains license and notices, and every preset and image update has source, version, license, restrictions, and legal-review evidence. | open |
