# Security and conditional legal audit — TASK-0007

## Scope and independence

- **Task:** `TASK-0007`, todo 2 only.
- **Audit directory:** `audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/`.
- **Dimension:** security and conditional legal applicability.
- **Boundary:** current checkout, the fresh inventory, `audits/INDEX.md`, and the
  current `audits/standards/SECURITY.md` and `audits/standards/LEGAL.md`.
- **Excluded:** prior audit deliverables, comparison with any previous run,
  remediation, plan changes, state changes, and source changes.
- **Observed platform:** macOS arm64 with Docker Desktop; Python 3.14.5.

This is a pre-remediation dimension report. Finding identifiers are scoped to
this dimension and do not assert persistence, regression, or comparison with
another audit.

## Executive result

The current generated posture is deliberately localhost-only and fail-closed
for LAN, with useful container hardening and digest-pinned image references.
No bearer token is generated or embedded, and the focused Compose, SBOM,
dependency-consistency, Harness validation, and whitespace checks passed.

The actionable risks are concentrated in supply-chain reproducibility, current
generated artifact permissions, backend network isolation, and unrestricted
operator-selected model paths. The current checkout also cannot produce a live
dependency-vulnerability verdict because `pip_audit` is not installed in the
audit environment. Legal obligations are conditional: they apply before this
project, a generated preset, a model, or a third-party runtime component is
distributed or published; internal undistributed development is not enough to
establish that trigger from the available evidence.

## Findings

### SEC7-001 — CI integrity depends on an historical audit checksum

- **Severity:** High
- **Evidence:** `scripts/ci.sh:138-139` verifies
  `audits/audit_opencode_default_gpt-5_24-07-2026/pre-remediation.sha256`.
- **Impact:** The normal CI path is coupled to a historical audit snapshot
  rather than to the current run's frozen evidence. A missing, stale, or
  unrelated historical file can block CI; if the file is updated outside the
  current change, the security gate no longer has a clear provenance boundary.
- **Applicability:** Confirmed as a CI/supply-chain control defect in the
  current source. No historical report was opened or used as evidence.
- **Recommendation:** Replace the historical path with an explicit current-run
  evidence input, or remove the pre-remediation checksum from normal CI and
  make audit snapshot verification a separately parameterized audit gate. The
  selected snapshot must be frozen and hashed before remediation.
- **Standard mapping:** `STD-SEC-005`; also affects audit evidence integrity.

### SEC7-002 — Dependency declarations are version-pinned but not hash-pinned

- **Severity:** Medium
- **Evidence:** `requirements.txt:1-2`, `requirements-dev.txt:3-8`, and
  `pyproject.toml:11-22` use `==` versions without package hashes.
  `.github/workflows/ci.yml:37-40` installs them without `--require-hashes`.
- **Impact:** A version pin narrows drift but does not prove that the artifact
  downloaded from an index is the reviewed artifact. A compromised or replaced
  distribution at the same version can enter development or CI environments.
- **Applicability:** Confirmed against the current supply-chain standard.
- **Recommendation:** Maintain a hash-locked installation input for the
  supported Python versions, install it with `--require-hashes`, and review
  updates together with the SBOM and vulnerability scan. Keep the editable or
  source-install path separate from release verification.
- **Standard mapping:** `STD-SEC-005`.

### SEC7-003 — Existing generated `.env` artifacts do not uniformly meet mode 0600

- **Severity:** Medium
- **Evidence:** The generator writes `.env` with mode `0600` at
  `ai_server_generator/render.py:417-422`, and startup/validation enforce that
  mode at `templates/chat/scripts/start_serving.sh.j2:21-28` and
  `templates/chat/scripts/validate_host.sh.j2:27-34`. The current checkout scan
  found `generated/task-0006-acceptance/.env`,
  `generated/ornith-medium-localhost/.env`,
  `generated/phi4-good-localhost/.env`, and
  `generated/chat-medium-localhost/.env` at mode `0644`.
- **Impact:** Current generated artifacts can be read by other local users.
  The observed files contain configuration values rather than bearer tokens,
  but future generated secret-bearing fields would inherit the unsafe exposure
  unless the artifact is repaired or rejected before use.
- **Applicability:** Confirmed for the current checkout artifacts; the canonical
  renderer has the intended secure default.
- **Recommendation:** Normalize or regenerate every current generated
  workspace, add a repository-local permission sweep for existing outputs, and
  ensure backup/restore preserves secure modes. Keep startup fail-closed.
- **Standard mapping:** `STD-SEC-001`.

### SEC7-004 — The backend has no explicit network-egress isolation

- **Severity:** Medium
- **Evidence:** `templates/chat/docker-compose.yml.j2:1-49` defines the
  serving service and localhost port binding but no `network_mode: none`,
  `internal` network, or equivalent egress restriction. The resolved root
  Compose configuration showed a default `ai-server_default` network attached
  to `llama-server`.
- **Impact:** The service is protected from unsolicited LAN ingress by the
  `127.0.0.1` publish at `templates/chat/docker-compose.yml.j2:6-7`, but a
  compromised runtime image or model-serving process can still reach whatever
  Docker Desktop permits on the default network. This increases supply-chain
  and runtime-compromise blast radius.
- **Applicability:** Confirmed as a defense-in-depth gap. It does not convert
  the current localhost bind into LAN exposure.
- **Recommendation:** Define the minimum required network behavior explicitly;
  prefer a no-egress or internal backend network where the runtime supports it,
  and test health/model operation after the restriction. Do not claim LAN
  readiness from this control alone.
- **Standard mapping:** `STD-SEC-002` and `STD-SEC-006`.

### SEC7-005 — Operator-selected model paths can resolve outside the model tree

- **Severity:** Medium
- **Evidence:** `ai_server_generator/render.py:126-130` rejects parent traversal,
  but `ai_server_generator/render.py:159-163` accepts an absolute path and
  resolves it without requiring containment under `models/` or rejecting a
  final symlink target. The generated Compose bind mounts that resolved path
  read-only at `templates/chat/docker-compose.yml.j2:28-32`.
- **Impact:** A local operator or automation process that supplies a readable
  `.gguf`-looking path can cause the serving container to receive an arbitrary
  host file. The mount is read-only and the input is local CLI data, so this is
  not a remote path traversal; it is nevertheless a privacy boundary and
  accidental-disclosure risk if the API or runtime exposes content derived
  from the mounted file.
- **Applicability:** Confirmed design risk for custom model paths; not observed
  as an exploit during this read-only audit.
- **Recommendation:** Constrain paths to an approved model root by default,
  resolve and reject symlink escapes, and require an explicit audited override
  for external model stores. Preserve the `.gguf` regular-file and readability
  checks at host validation.
- **Standard mapping:** `STD-SEC-003`.

### SEC7-006 — Vulnerability scanning is not reproducible in this audit environment

- **Severity:** Medium (evidence gap, not a confirmed vulnerable dependency)
- **Evidence:** `scripts/ci.sh:141-146` requires `python3 -m pip_audit`, and
  `pyproject.toml:21` / `requirements-dev.txt:6` declare `pip-audit==2.9.0`.
  The focused command `python3 -m pip_audit --strict --progress-spinner off
  --format json --requirement requirements.txt` exited `1` with `No module named
  pip_audit`.
- **Impact:** This checkout has no current vulnerability verdict for the
  declared dependencies. `pip check` only established dependency consistency;
  it does not scan advisories. The missing tool also means local reproduction
  of the CI security gate is incomplete.
- **Applicability:** Confirmed as an audit-evidence limitation. No CVE is
  inferred from the failed command.
- **Recommendation:** Run the pinned development toolchain in an isolated
  environment or CI and retain the JSON result with the task evidence. Add a
  clear preflight that reports the missing scanner as a blocked security gate,
  not as a passing scan.
- **Standard mapping:** `STD-SEC-005`.

### SEC7-007 — Access logging is not implemented for the serving path

- **Severity:** Low while localhost-only; Medium before LAN enablement
- **Evidence:** `docs/lan-safe-runbook.md:43-45` lists timestamp/source-IP access
  logs as a future LAN auditability requirement. The generated benchmark writes
  only request timing and validation evidence at
  `templates/chat/scripts/smoke_benchmark.sh.j2:127-152`; the Compose service
  has no access-log sink or retention policy at
  `templates/chat/docker-compose.yml.j2:1-49`.
- **Impact:** Local operators have limited forensic evidence for requests and
  source identity. If LAN were enabled without a gateway, incident review and
  abuse attribution would be weak.
- **Applicability:** The current localhost-only posture keeps this below a LAN
  exposure finding. It is a release blocker for any future LAN profile.
- **Recommendation:** Implement structured gateway/backend access logs with
  timestamps, source identity, request outcome, redaction, retention, and
  rotation before LAN support; do not treat smoke benchmark files as access
  logs.
- **Standard mapping:** `STD-SEC-002`.

## Verified controls and non-findings

- **LAN fail-closed:** `ai_server_generator/render.py:258-273` rejects LAN,
  bearer-token, and unenforced allowlist inputs. The generated Compose bind is
  explicitly localhost at `templates/chat/docker-compose.yml.j2:6-7`.
- **Authentication boundary:** Current localhost workspaces use no bearer
  token by design; the validator rejects token-bearing or inert LAN claims at
  `ai_server_generator/validator.py:504-525`.
- **Container hardening:** The template declares a non-root UID, bounded
  resources/PIDs, no-new-privileges, all capabilities dropped, read-only root
  filesystem, and read-only model mount at
  `templates/chat/docker-compose.yml.j2:28-49`.
- **Output path safety:** Generated output is confined to a strict descendant
  of `generated/` and rejects symlink traversal at
  `ai_server_generator/render.py:80-112`.
- **Serialization and input controls:** Text controls reject NUL/CR/LF and
  other control characters at `ai_server_generator/render.py:115-123`; Compose
  and dotenv values are serialized through dedicated helpers at
  `ai_server_generator/render.py:143-156`.
- **Image pin and SBOM:** The image digest is defined at
  `ai_server_generator/render.py:44-55`; `scripts/generate_sbom.py:35-62`
  rejects unpinned requirement lines and `scripts/generate_sbom.py:146-158`
  verifies the committed SBOM.
- **Secret search:** The current source/templates and non-generated checkout
  were inspected for common private-key and credential patterns; no confirmed
  secret value was recorded in this report. The root and generated `.env` files
  were inspected by key name only and their values were not copied into the
  evidence.

## Conditional legal applicability ruling

### Ruling

**Conditional applicability: not triggered for internal, undistributed
development on the evidence available; mandatory before publication,
distribution, or supply to another party.** The repository contains packaging
metadata and a project license at `pyproject.toml:5-14`, `LICENSE`, and a
committed SBOM at `sbom.json`, so a future distribution path is plausible. The
current checkout does not establish that a release or external supply has
occurred. Therefore this audit does not label the project legally compliant or
non-compliant in the abstract; it records the pre-distribution gate below.

### LEG7-001 — Distribution provenance package is incomplete

- **Severity:** High before distribution; not applicable to internal-only use
- **Evidence:** `audits/standards/LEGAL.md` requires project license metadata,
  `LICENSE`, third-party notices/SBOM, and provenance for every distributed
  model preset/component. Current evidence confirms `pyproject.toml:10`,
  `LICENSE`, and `sbom.json`, but `test -f THIRD_PARTY_NOTICES` exited `1`.
  `models/README.md:3-7` says model weights are local-only and must not be
  committed, while `CHANGELOG.md:23` expressly carries upstream runtime/model
  license review forward rather than discharging it.
- **Impact:** Publishing the generator with a bundled runtime image, preset
  catalog, or model could omit required upstream license, restriction, and
  lawful-provisioning information. Model provenance is not available for a
  distributable weight because the current checkout contains no `.gguf` file.
- **Ruling:** The legal standard applies immediately to any generated artifact
  or package supplied to another party; it is a release blocker until provenance
  and notices are complete. It is not evidence of a legal violation during
  internal undistributed development.
- **Recommendation:** Before any distribution, create and review
  `THIRD_PARTY_NOTICES`, record official source/revision/license/restrictions for
  the llama.cpp image and each preset/model, verify lawful model provisioning,
  and tie digest/catalog changes to a fresh legal review. Keep model weights
  excluded unless their separate rights are documented.
- **Standard mapping:** `STD-LEG-001`.

## Focused command evidence

| Command | Exit | Result |
|---|---:|---|
| `docker --version` | 0 | Docker 29.6.1 available |
| `python3 --version` | 0 | Python 3.14.5 |
| `python3 -m pip --version` | 0 | pip 26.1.1 |
| `docker compose --project-directory . --env-file /dev/null -f docker-compose.yml config --quiet` | 0 | Root Compose parses |
| `python3 scripts/generate_sbom.py --check` | 0 | `sbom.json` current |
| `python3 -m pip check` | 0 | No broken requirements |
| `python3 -m pip_audit --strict --progress-spinner off --format json --requirement requirements.txt` | 1 | `pip_audit` module unavailable; no vulnerability verdict |
| `python3 .pm-harness/bin/harness.py validate` | 0 | Harness valid; 13 manifests, 29 memory notes |
| `python3 .pm-harness/bin/harness.py agents check` | 0 | OpenCode and Claude rosters complete |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 | 12 of 13 plan todos remain unchecked; expected for todo 2-only execution |
| `git diff --check` | 0 | No whitespace errors |
| `test -f LICENSE` | 0 | Project license present |
| `test -f THIRD_PARTY_NOTICES` | 1 | Required pre-distribution notice artifact absent |
| `find models -type f -iname "*.gguf" -print -quit \| grep -q .` | 1 | No model weights present |

## Summary by severity

| Severity | Count | IDs |
|---|---:|---|
| High | 1 confirmed security/control + 1 conditional legal blocker | SEC7-001; LEG7-001 before distribution |
| Medium | 5 | SEC7-002, SEC7-003, SEC7-004, SEC7-005, SEC7-006 |
| Low / conditional Medium | 1 | SEC7-007 |
| Confirmed secrets | 0 | No secret value recorded |

## Handoff boundary

This report completes only the security/legal dimension review. It does not
remediate findings, modify `.pm-harness/plans/TASK-0007.plan.md`, modify
`.pm-harness/state/TASK-0007.json`, contact another role, or close any later
todo.
