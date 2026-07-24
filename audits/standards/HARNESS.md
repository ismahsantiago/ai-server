# Harness Standards

These rules are mandatory for model routing, native agent materialization, and
harness conformance. Each rule records the current audit finding that
established it.

## STD-ARN-001 — Route against the detected host

The harness MUST detect the active host and inject it verbatim into every
delegated FACTS block. Routing MUST receive `--platform <host>` and MUST NOT
hard-code a platform. The resolved model identifier, provider, and effort MUST
be validated against the selected host adapter.

**Verify mechanically:** Routing tests for OpenCode and Claude MUST assert the
platform-specific identifier format, provider, and allowed effort. A FACTS
block without the detected host or with a mismatched host MUST be rejected.

**Current finding origin:** `ARN-001` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-ARN-002 — Require complete native host adapters

The harness MUST provide a native adapter for every supported host, including
Codex, with activation surfaces, discovery, model identifier format, and
materialization behavior. It MUST validate `models set` entries against the
adapter's `id_format`, store OpenCode models as complete `provider/model`
identifiers, and refuse routing when the host is missing or unknown.

**Verify mechanically:** Adapter conformance tests MUST discover and materialize
agents on every supported host, reject malformed model identifiers, preserve
full OpenCode identifiers, and reject unidentified-host routing.

**Current finding origin:** `ARN-002` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-ARN-003 — Materialize least-privilege role permissions

Native permissions MUST be encoded by path and command. They MUST require
confirmation for destructive effects, separate read-only audit roles from
write-capable implementation roles, deny delegation to workers, and deny
writes to another role's memory store.

**Verify mechanically:** A materialization gate MUST compare emitted permissions with
the source role contract. Negative tests MUST prove that workers cannot
delegate, audit roles cannot write, destructive commands require confirmation,
and no role can write another role's memory.

**Current finding origin:** `ARN-003` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.

## STD-ARN-004 — Gate sealed harness versions with conformance

The project MUST distribute or immutably reference a versioned conformance
suite for the sealed engine and pack versions. CI MUST run it against the
declared seal and cover the state machine, plans and amendments, checksums,
memory deduplication, materialization and safe regeneration, platform routing,
and migrations between supported versions.

**Verify mechanically:** CI MUST reject a missing or mismatched conformance-suite
version and any failed conformance case. For the current seal, the evidence
MUST identify engine `2.1.0` and pack `2.6.0`.

**Current finding origin:** `ARN-004` in
`audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md`.
