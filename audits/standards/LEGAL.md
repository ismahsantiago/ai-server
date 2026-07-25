# Legal standards

This standard applies when the project or a generated preset is distributed,
published, or supplied to another party. Internal, undistributed development
does not remove the requirement to collect the metadata before distribution.

## STD-LEG-001 — Establish distribution provenance and license review

Declare project license metadata and ship `LICENSE`. For every distributed
model preset or third-party component, record its official source, pinned
version or revision, license, applicable restrictions, and lawful-provisioning
notice. Ship both `THIRD_PARTY_NOTICES` and an SBOM. Changing an image digest,
model revision, or preset catalog entry MUST trigger a new legal review before
distribution.

**Verify mechanically:** packaging CI rejects missing project license metadata,
`LICENSE`, third-party notices/SBOM, or preset provenance fields; the release
gate compares distributed digests and catalog entries with the latest approved
legal-review record.

**Current finding origin:** `audits/audit_opencode_default_gpt-5_24-07-2026/informe_completa.md` — `LEG-001`.
