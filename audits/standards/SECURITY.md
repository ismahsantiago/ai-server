# Security standards

These rules apply to the generator, generated workspaces, templates, validation,
CI, and documented LAN-serving paths.

## STD-SEC-001 — Generate and protect serving secrets

Generate every default serving token with a cryptographically secure source and
at least 32 bytes of entropy, or inject it from an approved secret manager.
Write generated `.env` files with mode `0600`. Validation and startup MUST fail
when the token is absent, empty, weak, or equal to a documented placeholder.

**Verify mechanically:** unit tests assert token uniqueness and minimum decoded
length; filesystem tests assert mode `0600`; negative validation/startup tests
cover empty, short, and placeholder values.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `SEC-001`.

## STD-SEC-002 — Fail closed for LAN exposure

Keep the model backend unpublished and place an authenticated TLS proxy in
front of it for LAN access. Enforce the configured CIDR at the proxy or host
firewall. A preflight MUST prove TLS, authentication, CIDR enforcement, and
backend isolation before LAN mode starts; otherwise LAN mode MUST remain
disabled.

**Verify mechanically:** parse the rendered Compose and proxy configuration;
assert no backend host port is published; run negative preflight tests with
each control removed or invalid and require a non-zero exit.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `SEC-002`.

## STD-SEC-003 — Validate inputs and serialize configuration structurally

Path and CIDR inputs MUST be validated against explicit contracts, with NUL,
CR, and LF characters rejected. JSON, YAML, and dotenv MUST be emitted through
format-aware serializers and escaping; untrusted values MUST NOT be
interpolated into configuration text.

**Verify mechanically:** regression tests cover newlines, quotes, traversal,
invalid CIDRs, and attempted Compose-property injection; parse every rendered
JSON/YAML/dotenv artifact and compare its values with the accepted inputs.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `SEC-003`.

## STD-SEC-004 — Validate rendered security controls structurally

Parse rendered JSON, YAML, and dotenv rather than accepting text matches.
Cross-check bind address, allowed CIDR, authentication, non-placeholder secret,
TLS proxy, firewall preflight, privilege restrictions, and mounts. Run
`docker compose config` against generated Compose configuration. Validation
MUST fail closed when a required control is absent, malformed, or inconsistent.

**Verify mechanically:** mutation tests remove or corrupt one control at a time
and require a non-zero result; `docker compose config` MUST exit zero for the
valid fixture and non-zero for invalid Compose.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `SEC-004`.

## STD-SEC-005 — Make the software supply chain reproducible

Pin container images by immutable digest and lock application dependencies with
verified hashes. Generate an SBOM, scan dependencies and images in CI, and
maintain a reviewed update and vulnerability-response procedure. Digest or
catalog changes MUST receive a new security review before distribution.

**Verify mechanically:** CI rejects mutable image references and unlocked or
unhashed dependency declarations; SBOM and scan artifacts MUST exist; an
approved review record MUST identify every changed digest or catalog entry.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `SEC-005`.

## STD-SEC-006 — Enforce runtime least privilege

The serving container MUST run as a verified non-root UID/GID, drop all
capabilities, set a PID limit and explicit resource limits, mount logs with
least privilege, and isolate backend networking where supported. These settings
MUST be treated as structural invariants, not documentation-only guidance.

**Verify mechanically:** parse Compose to assert `user`, `cap_drop: [ALL]`,
PID/resource limits, log mount permissions, and network isolation; CI runtime
checks MUST prove the process UID/GID and effective capabilities.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `SEC-006`.
