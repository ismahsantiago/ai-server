# Remediation ledger — TASK-0007

## Scope and provenance

This ledger is the todo 8 handoff for the fresh audit run
`audits/audit_opencode_default_gpt-5_25-07-2026_20h23m/`. It was created after
the pre-remediation deliverables and four dimension reports were hashed and
before any TASK-0007 source remediation. The ledger does not authorize a
change; it assigns the finding, names the proposed change surface, and records
the focused evidence required for a later todo.

`open` means confirmed and awaiting implementation or evidence. `ready` means
the proposed action is repository-local and can be planned by the named owner.
`escalated` means implementation must wait for a Director/PM decision, a
security review, or external/live-runtime evidence. No finding is marked fixed
or resolved here.

## Confirmed finding ledger

| Finding | Severity | Owner / role | Proposed change files | Focused test or mechanical check | Status / escalation |
|---|---|---|---|---|---|
| SEC7-001 | High | security-engineer | `scripts/ci.sh`; versioned audit evidence-manifest input | CI rejects historical audit paths and accepts only the declared current-run/canonical manifest; hash verification has provenance | implemented — security review required before integration |
| OPS7-001 | High | ml-platform-engineer, security-engineer review | `scripts/ci.sh`; CI workflow and evidence-manifest fixture | CI configuration test proves checksum/scanner inputs are current-run or canonical-source inputs, never prior audit output | implemented — security review required before integration |
| HARNESS7-001 | High | ml-platform-engineer | `.pm-harness/bin/harness_core.py`; harness agent fixtures/tests | `agents check` rejects empty, stale, wrong-platform, wrong-role, missing-marker and malformed-frontmatter agents; materialization is atomic | ready |
| HARNESS7-002 | High | engineering-manager / pm-orchestrator | `.pm-harness/adapters/adapters.json`; adapter/materialization tests; support documentation if decision changes | Native Codex discovery/materialization conformance, or a recorded out-of-support decision with matching contract checks | escalated — scope-changing host-support decision required before implementation |
| PERF7-001 | High | ml-systems-engineer | `ai_server_generator/presets.py`; `ai_server_generator/validator.py`; `manifests/`; model-contract tests | Incomplete GGUF metadata is rejected; contract covers source, revision, filename, architecture, quantization, bytes, SHA-256, template and RAM | open — requires authorized model artifact/metadata; no runtime claim may be made |
| PERF7-002 | High | ml-systems-engineer | `ai_server_generator/cli.py`; host/daemon inspection and profile tests | Fixtures under, at and above Docker/host budget produce correct `GO`, `WARN` or `NO-GO`; output separates host, daemon and container limits | escalated — depends on host/runtime measurement and profile-policy confirmation |
| PERF7-005 | High | ml-systems-engineer | `templates/chat/scripts/smoke_benchmark.sh.j2`; benchmark schema/tests; `logs/benchmarks/` only for authorized run output | Authorized GGUF run emits samples, p50/p95, tokens/s, peak memory, host, runtime, image digest, flags and model hash; missing measurements fail nonzero | escalated — external runtime/model execution required; current placeholder remains non-baseline |
| UX7-001 | High | ux-dev, ml-platform-engineer | generator templates; controlled generated fixture/migration path; drift-check | Regeneration/drift test proves canonical image digest, restart policy, mounts and README contract; legacy outputs are explicitly marked if not migrated | open — existing generated outputs require controlled ownership decision |
| UX7-002 | High | ux-dev, security-engineer review | `docs/human-guide.md`; LAN runbook and documentation tests | Docs state LAN is planned/blocked and executable examples remain localhost-only; CLI refusal test remains fail-closed | ready |
| SEC7-002 | Medium | security-engineer | `requirements*.txt`; `pyproject.toml`; `.github/workflows/ci.yml`; lock-generation metadata | Hash-locked install with `--require-hashes`, `pip check`, SBOM and CI install test pass for supported Python versions | ready — dependency update requires security review |
| SEC7-003 | Medium | security-engineer | `ai_server_generator/render.py`; generated-output permission sweep; backup/restore scripts/tests | All generated `.env` files are mode `0600`; sweep and restore preserve/reject unsafe modes without exposing values | open — existing generated artifacts are pre-existing checkout state |
| SEC7-004 | Medium | security-engineer | `templates/chat/docker-compose.yml.j2`; Compose/network tests; runbook | Resolved Compose has the approved minimum egress policy and serving health still works under restriction | escalated — network-policy change is security-sensitive and runtime-dependent |
| SEC7-005 | Medium | security-engineer | `ai_server_generator/render.py`; `ai_server_generator/validator.py`; path/symlink tests | Absolute, traversal and symlink-escape cases are rejected; only approved model-root paths pass unless an audited override exists | ready — security review required before merge |
| SEC7-006 | Medium (evidence gap) | security-engineer | `pyproject.toml`; `requirements-dev.txt`; CI/toolchain preflight; audit evidence output | Isolated pinned `pip-audit` run emits retained JSON, or the security gate explicitly fails as blocked; no CVE is inferred from absence of the tool | escalated — external package-index/toolchain execution required |
| SEC7-007 | Low localhost / Medium before LAN | security-engineer | future gateway/backend logging templates; LAN runbook and logging tests | Structured timestamp/source/outcome logs redact secrets and enforce rotation/retention in a gateway/backend rehearsal | escalated — future LAN scope and external gateway runtime required |
| COD7-001 | Medium | ml-platform-engineer | `scripts/ci.sh`; rendered shell fixture; shell template tests | Rendered fixture passes `bash -n` and ShellCheck with spaces, quotes, backslashes and Unicode in paths | ready |
| OPS7-002 | Medium | ml-platform-engineer | `templates/chat/scripts/start_serving.sh.j2`; lifecycle tests | Timeout, dead process and retry leave no newly-started unhealthy stack; logs are retained and exit is nonzero | ready — Docker lifecycle verification required |
| OPS7-003 | Medium | ml-platform-engineer, security-engineer review | `scripts/restore_workspace.sh`; backup/restore tests | Tar inspection rejects absolute/parent/symlink/unexpected members; staging validates manifest and full inventory before replacement | ready |
| HARNESS7-003 | Medium | ml-platform-engineer, security-engineer review | adapter schemas/materializers; `.opencode/agents/`; permission conformance tests | Materialized permissions match role path/command boundaries; destructive actions require confirmation and foreign-memory writes/delegation are rejected | escalated — native host permission capability and contract change require approval |
| PERF7-003 | Medium | ml-systems-engineer | `ai_server_generator/render.py`; manifest schema/validator; runtime compatibility fixtures | Manifest records runtime version/revision, digest and flag schema; digest changes require compatibility regression evidence | open — runtime compatibility remains unverified without the image/model |
| PERF7-004 | Medium | ml-systems-engineer | `templates/chat/scripts/start_serving.sh.j2`; Compose lifecycle tests | Startup distinguishes `starting`, `healthy` and `unhealthy`, diagnoses unhealthy early and returns nonzero on timeout | ready — requires Docker lifecycle test |
| PERF7-006 | Medium | ml-systems-engineer | `templates/chat/scripts/smoke_benchmark.sh.j2`; benchmark schema/tests | Artifact records workload, context, batch, threads, `n_predict`, concurrency, samples and generated tokens; smoke and regression benchmark remain separate | open |
| UX7-003 | Medium | ux-dev | `README.md`; `docs/human-guide.md`; templates/runbook; manifest/Compose documentation tests | Every surface states the same host path, container path, copy policy and validation command | ready |
| UX7-004 | Medium | ux-dev, ml-platform-engineer | `README.md`; CLI help/docs tests; generated helper documentation | Every documented command exists in `--help` or is explicitly identified as a generated helper; extracted examples execute with documented exit behavior | ready |
| LEG7-001 | High conditional distribution | engineering-manager / security-engineer; legal review if distribution begins | `THIRD_PARTY_NOTICES`; runtime/preset/model provenance; SBOM and distribution docs | Distribution rehearsal contains licenses, notices, source/version/restrictions and legal sign-off; no publication occurs before review | escalated — distribution scope and legal review are outside this todo |

## Rejected or unconfirmed claims

- No CVE, vulnerable dependency, runtime throughput, memory result, model
  compatibility result, or LAN readiness claim is inferred from the reports.
- The reports' positive controls and non-findings are not remediation rows.
- The terminal-only product does not create a separate graphical-UI finding.
- `PERF7-004` is retained as a state-reporting defect; no claim that timeout
  leaves containers running is made because that behavior was not reproduced.
- Existing generated artifacts are recorded as evidence only; this todo does
  not normalize, regenerate, delete, or overwrite them.

## Coverage and handoff

The ledger contains one row for each of the 25 confirmed findings integrated in
`checklist_completa.md`: 8 high, 14 medium, 1 low/conditional-medium and 1
high conditional distribution item, with the audit's duplicate-root findings
`SEC7-001` and `OPS7-001` preserved as separate finding IDs. Proposed changes
are assigned to the role declared by the corresponding dimension; escalated
rows are not silently implementable. Completion requires later ledger updates
with changed files and passing evidence, plus the plan's remaining gates.

## Remediation evidence

`SEC7-001` and `OPS7-001` implementation evidence, recorded after verification:

- Changed files: `scripts/ci.sh`, `tests/test_ci_contract.py`.
- Normal CI no longer references `audits/audit_opencode_default_gpt-5_24-07-2026/`
  or `pre-remediation.sha256` and does not require any audit deliverable.
- Audit checksum verification is available only when both `AUDIT_DIR` and
  `AUDIT_EVIDENCE_MANIFEST` are supplied; the manifest must be named
  `evidence-manifest.sha256` and resolve inside the declared `AUDIT_DIR`.
- The existing clean-clone PM Harness guard and `HARNESS_PLAN_TASK` behavior
  remain in `scripts/ci.sh`.
- Focused checks passed: `bash -n scripts/ci.sh`, `shellcheck scripts/ci.sh`,
  `python3 -m unittest tests.test_ci_contract`,
  `python3 .pm-harness/bin/harness.py validate`, and `git diff --check`.
- Security-engineer review remains required before integration because the
  change alters a security and supply-chain CI gate; no final integration or
  task-state transition is claimed here.

## Independent security review — 2026-07-25

**Verdict: CHANGES_REQUESTED**

Reviewed only the current `scripts/ci.sh` / `tests/test_ci_contract.py` patch
and this fresh ledger. Normal CI no longer reads the historical audit
deliverable, and the existing PM Harness validation, agent/wiki checks, clean
clone guard, and task-plan dispatch remain present. No command-injection issue
was found in the quoted shell arguments or Python subprocess invocation.

The patch is not yet fail-closed or fully path-confined:

- If `AUDIT_DIR` is set without `AUDIT_EVIDENCE_MANIFEST`, audit verification
  is silently skipped; partial opt-in must fail.
- The manifest file itself is confined, but its checksum entries are passed to
  `shasum -c` without validating that each referenced path resolves beneath
  `AUDIT_DIR`; a `../` entry or symlink can therefore verify a file outside the
  declared audit directory.
- The focused tests are static string checks and do not exercise missing-pair,
  traversal, symlink, or out-of-tree checksum-entry cases.

Required follow-up: enforce both-variable pairing, parse and resolve every
manifest entry under `AUDIT_DIR` before checksum verification (reject traversal
and symlink escape), and add executable tests for those fail-closed cases.
TASK-0007 was not transitioned and its plan/state were not modified.

### Review gates

| Gate | Exit code |
|---|---:|
| `bash -n scripts/ci.sh` | 0 |
| `shellcheck scripts/ci.sh` | 0 |
| `python3 -m unittest tests/test_ci_contract.py` | 0 |
| `python3 .pm-harness/bin/harness.py validate` | 0 |
| `git diff --check` | 0 |

## Corrective patch — 2026-07-25

The prior `CHANGES_REQUESTED` review is superseded by this bounded corrective
patch. The audit opt-in now fails closed when only one variable is supplied,
and `scripts/validate_audit_manifest.py` parses every checksum entry before
`shasum` runs. Absolute paths, traversal, and symlink-resolved paths outside
the declared `AUDIT_DIR` are rejected. `tests/test_ci_contract.py` exercises
the missing-pair, traversal, and symlink cases with temporary directories.

This records implementation evidence only. It does not claim final security
approval; a fresh `security-engineer` review remains required. `TASK-0007`
plan/state and task transition were intentionally left unchanged.

### Corrective gates

| Gate | Exit code |
|---|---:|
| `python3 -m unittest tests/test_ci_contract.py` | 0 |
| `bash -n scripts/ci.sh` | 0 |
| `shellcheck scripts/ci.sh` | 0 |
| `python3 .pm-harness/bin/harness.py validate` | 0 |
| `git diff --check` | 0 |

## Fresh security review — 2026-07-25

**Verdict: APPROVED**

The corrected SEC7-001/OPS7-001 implementation was reviewed against the
required fail-closed, path-confinement, and command-safety criteria. No prior
audit deliverable was read for this review.

1. Normal CI contains no reference to the historical audit path. Audit mode
   reads only the explicitly declared `AUDIT_DIR` and
   `AUDIT_EVIDENCE_MANIFEST`; there is no implicit historical-audit input.
2. With neither variable set, the validator returns successfully and ordinary
   CI remains valid. Supplying only one variable fails closed before `shasum`.
3. The manifest must be named `evidence-manifest.sha256` and must resolve
   inside the declared `AUDIT_DIR`.
4. Every non-comment manifest entry is parsed before checksum verification.
   Absolute paths, traversal, and symlink-resolved paths outside
   `AUDIT_DIR` are rejected before `shasum` executes. A symlink resolving
   within `AUDIT_DIR` is accepted as an in-scope path.
5. `tests/test_ci_contract.py` executes the missing-pair, traversal, and
   symlink-escape cases. Additional review checks covered a valid manifest,
   an in-tree symlink, and an out-of-tree manifest.
6. Shell arguments are quoted; the manifest filename is reduced with
   `basename` after validation; no `eval`, command substitution from manifest
   contents, or unsafe subprocess shell invocation was introduced. A
   shell-metacharacter filename was verified not to execute a command.

### Fresh review evidence

| Gate / check | Exit code / result |
|---|---:|
| `python3 -m unittest tests/test_ci_contract.py` | 0 |
| `bash -n scripts/ci.sh` | 0 |
| `shellcheck scripts/ci.sh` | 0 |
| `python3 .pm-harness/bin/harness.py validate` | 0 |
| `git diff --check` | 0 |
| Additional confinement and command-execution checks | PASS |

No follow-up is required for SEC7-001/OPS7-001 from this review. This is a
security approval of the corrected implementation only; TASK-0007 was not
transitioned, and no code, plan, or state file was modified.

## SEC7-005 bounded remediation — 2026-07-25

Implemented only the repository-local model-source confinement. The renderer
now resolves relative and absolute model paths and requires the resolved path
to remain below the repository `models/` root. Parent traversal, absolute
paths outside that root, and symlink escapes are rejected; existing regular
files with spaces and special characters remain supported. The validator
applies the same root and regular-file contract to `manifest.json`, so a
generated workspace cannot claim an out-of-root bind source. The Compose model
bind remains read-only.

Changed files:

- `ai_server_generator/render.py`
- `ai_server_generator/validator.py`
- `tests/test_cli.py`

Executable coverage includes outside absolute paths, parent traversal, a
symlink escaping `models/`, a valid in-root absolute path, the existing
special-character fixture, and a manipulated manifest claiming an outside
source. No external override was created. An audited external model-root
override is future scope and requires a separately approved design, explicit
authorization, and security review; it is not part of this remediation.

### SEC7-005 gates

| Gate / check | Exit code / result |
|---|---:|
| `python3 -m unittest tests/test_cli.py` | 0 — 43 tests |
| `python3 .pm-harness/bin/harness.py validate` | 0 |
| `git diff --check` | 0 |

This entry records bounded implementation evidence only. `TASK-0007` plan,
state, and transition were intentionally left unchanged.

## Fresh security review of SEC7-005 — 2026-07-25

**Verdict: CHANGES_REQUESTED**

The review was limited to the current SEC7-005 implementation and this fresh
remediation ledger. No prior audit report was used. The implementation is
fail-closed for external model sources, but it does not yet satisfy the full
compatibility requirement that relative and absolute paths resolving inside
`models/` be accepted.

1. A relative path directly below `models/` and an absolute in-root path are
   accepted. A symlink resolving inside `models/` is also accepted.
2. Absolute paths outside `models/`, symlink escapes, directories, and
   manipulated manifest sources outside the root are rejected before a valid
   generation/validation result can be claimed.
3. Symlink resolution is consistent: an in-root symlink resolves to an in-root
   regular file, while an escaping symlink is rejected. No second escape was
   observed.
4. Manifest validation applies the same resolved-root check and rejects an
   external model source, including an external symlink target.
5. The existing read-only Compose model bind and special-character handling
   remain intact; the complete CLI suite passed.
6. The tests are executable and cover outside absolute paths, parent
   traversal, symlink escape, an in-root absolute path, special characters,
   and a manipulated manifest. Additional executable review checks covered an
   in-root symlink, an external symlink, a directory, and a normalized path.

Blocking compatibility defect: both renderer and validator reject any path
containing a `..` component before resolving it. Therefore
`./models/review-subdir/../review-root.gguf` is rejected even though it
resolves to a regular file below `models/`. The implementation should reject
only after canonical resolution (while retaining root confinement, symlink
escape rejection, and regular-file checks), and tests should explicitly cover
this accepted normalized in-root case.

### SEC7-005 fresh review gates

| Gate / check | Exit code / result |
|---|---:|
| `python3 -m unittest tests/test_cli.py` | 0 — 43 tests |
| `python3 .pm-harness/bin/harness.py validate` | 0 |
| `git diff --check` | 0 |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 — 5 unchecked todos; plan was not modified |
| Additional executable confinement checks | FAIL — normalized in-root `..` path rejected |

No code, plan, or state file was modified. Only this fresh remediation ledger
was updated. `TASK-0007` was not transitioned. Residual future scope remains
the separately authorized external model-root override; this review does not
approve such an override.

## SEC7-005 corrective evidence — 2026-07-25

The requested bounded correction supersedes the implementation evidence above:

- `render.py` no longer rejects `..` components before resolution. It resolves
  the candidate first and then confines the resolved path to the repository
  `models/` root, preserving rejection of external paths, escaping symlinks,
  directories, and non-regular files.
- `validator.py` applies the same resolved-path contract to the absolute
  `manifest.host_model_path`, so an in-root normalized path remains valid while
  an external resolved path remains invalid.
- `tests/test_cli.py` adds an executable regression covering
  `models/subdir/../model.gguf`, including generation and structure validation.

This is corrective evidence only. It does not claim security approval,
integration, task transition, or authorization for an external model-root
override.

## Final security review of SEC7-005 corrective patch — 2026-07-25

**Verdict: APPROVED**

The review was limited to the corrected SEC7-005 implementation, its
regression coverage, and this fresh remediation ledger. No prior audit report
was used. The renderer resolves the supplied model path before applying
confinement to the repository `models/` root, so an in-root normalized path
such as `models/subdir/../model.gguf` is accepted. Absolute external paths,
parent traversal that resolves outside the root, external symlinks, directory
paths, and non-regular model artifacts remain rejected. The validator applies
the same resolved-root contract to `manifest.host_model_path`, including
manipulated manifests.

The renderer and validator agree on the confinement rule. The generated
Compose model bind remains read-only, and the 44-test regression suite covers
the corrected normalized in-root case, external traversal, absolute external
paths, symlink escape, invalid model artifacts, and manipulated manifest
sources. No external model-root override is approved by this review.

### Final SEC7-005 review gates

| Gate / check | Exit code / result |
|---|---:|
| `python3 -m unittest tests/test_cli.py` | 0 — 44 tests, `OK` |
| `python3 .pm-harness/bin/harness.py validate` | 0 |
| `git diff --check` | 0 |

This approval applies only to the corrected SEC7-005 implementation. No
code, plan, or state file was modified by the review, and `TASK-0007` was not
transitioned.

## Final remediation reconciliation — 2026-07-26

This matrix is the append-only final disposition of all 25 findings. “Locally
resolved” means the repository contract and automated evidence are complete;
it does not imply a live model, Linux host, registry, network, or distribution
claim. External and scope decisions remain fail-closed and have an explicit
owner.

| Finding | Final disposition | Evidence or blocking owner |
|---|---|---|
| SEC7-001 | Locally resolved; implementation security-approved | `scripts/ci.sh`, `scripts/validate_audit_manifest.py`, `tests/test_ci_contract.py`; the fresh review above is `APPROVED`. |
| OPS7-001 | Locally resolved; implementation security-approved | Same current-run-only, fail-closed audit-manifest implementation and executable traversal/symlink tests as SEC7-001. |
| HARNESS7-001 | Locally resolved | `tests/test_harness_agents.py` proves malformed, stale and wrong-role OpenCode agents are rejected and materialization leaves no temporary file; `agents check` exits 0 for installed OpenCode and Claude surfaces. |
| HARNESS7-002 | Formally scope-blocked | Codex is not declared in `.pm-harness/adapters/adapters.json`; adding native support changes the installed harness/platform contract. Owner: `pm-orchestrator` and Harness Engine governance. Exact reason: TASK-0007 cannot silently add a new supported host. |
| PERF7-001 | Locally resolved as a fail-closed metadata contract; artifact verification external | `ai_server_generator/presets.py`, `render.py`, `validator.py`, `tests/test_cli.py` define contract v2 and reject incomplete `verified-artifact` metadata. Owner of the remaining evidence: Director/operator supplying an authorized GGUF and provenance. No model compatibility is claimed. |
| PERF7-002 | Locally resolved for deterministic host/profile classification; live measurement external | Current `doctor` tests exercise below/at/above resource envelopes, host/container observation and provisional FIT/NO-FIT decisions. Owner of target-Linux measurement and product ratification: TASK-0008/product governance. |
| PERF7-005 | Locally resolved as a strict evidence schema; authorized run external | `smoke_benchmark.sh.j2` and `test_smoke_is_strict_and_emits_only_numeric_or_not_measured_evidence` record workload, samples, percentiles, tokens/s, memory, host, runtime, image and model fields; regression mode fails when required measurements are absent. Owner: Director/operator on an authorized Linux/model runtime. |
| UX7-001 | Locally resolved | Canonical templates and `tests/golden/chat-ornith-medium-localhost/` were regenerated through `scripts/update_golden_fixture.py`; `test_generated_output_matches_golden_fixture` is the byte-for-byte drift gate. |
| UX7-002 | Locally resolved | `README.md`, `docs/human-guide.md`, generated README and documentation-contract tests keep LAN planned/blocked and executable serving examples localhost-only. |
| SEC7-002 | Locally resolved | `requirements.lock`, `uv.lock`, `.github/workflows/ci.yml`, `scripts/generate_sbom.py`, `sbom.json`, CI contract tests and `pip check` provide hash-locked installation and current SBOM inputs. |
| SEC7-003 | Locally resolved for generated and governed backup/restore outputs | Renderer enforces `.env` mode `0600`; backup rejects unsafe mode; restore stages, checks inventory and rejects unsafe restored mode. Covered by `tests/test_cli.py`. Pre-existing unowned outputs are not silently rewritten. |
| SEC7-004 | Formally security/runtime-blocked | Localhost-only Compose remains the approved posture. Owner: security-engineer plus Phase N network design. Exact reason: an egress policy cannot be selected or claimed healthy without an approved gateway/network contract and runtime test. |
| SEC7-005 | Locally resolved; implementation security-approved | Root confinement, normalized in-root paths, traversal and symlink escape coverage in renderer/validator and the 44-test CLI review recorded above; final verdict `APPROVED`. |
| SEC7-006 | Locally resolved as a reproducible gate | `pip-audit==2.9.0` is hash-locked; `scripts/ci.sh` emits `artifacts/ci/pip-audit.json` and fails on scanner failure. The result is dependency evidence only, never an inferred CVE claim. |
| SEC7-007 | Formally future-scope blocked | Owner: Phase N gateway/security implementation. Exact reason: no LAN gateway/backend is authorized, so structured access logging, rotation and retention cannot be implemented or represented as verified in this localhost-only product. |
| COD7-001 | Locally resolved | `test_rendered_shell_scripts_pass_static_checks_with_complex_model_path` renders complex paths and runs `bash -n` and ShellCheck; the full CI also checks repository and generated shell files. |
| OPS7-002 | Locally resolved for lifecycle behavior; real Docker run external | `start_serving.sh.j2` distinguishes starting/healthy/terminal states, retains diagnostics and tears down only a newly started unhealthy stack. `test_generated_lifecycle_scripts_are_cwd_independent_bounded_and_stop` exercises timeout and unhealthy paths. Owner of live Docker confirmation: target-host operator. |
| OPS7-003 | Locally resolved | `backup_workspace.sh`, `restore_workspace.sh` and CLI tests enforce a manifest inventory, reject absolute/parent/symlink/unexpected members, validate in staging and preserve displaced targets. |
| HARNESS7-003 | Formally platform-capability blocked | Owner: `pm-orchestrator` and Harness Engine governance. Exact reason: current native host permission schemas do not authorize a TASK-local rewrite of cross-host delegation, confirmation and foreign-memory semantics. Existing installed agent conformance remains green. |
| PERF7-003 | Locally resolved as a static compatibility contract; runtime compatibility external | Manifest `runtime_contract` binds implementation, image digest and flag schema; validator rejects image mismatch and incomplete `runtime-verified` claims. Owner of version/revision and model compatibility evidence: authorized runtime operator. |
| PERF7-004 | Locally resolved for state handling; live Docker evidence external | Startup template and lifecycle regression distinguish `starting`, `healthy`, `unhealthy`, `exited`, `dead` and timeout with nonzero failure and bounded cleanup. |
| PERF7-006 | Locally resolved as benchmark-contract enforcement | Smoke/regression modes record workload, context, batch, threads, prediction limit, concurrency, samples and token counts; regression mode fails when token or memory measurement is absent. Live values remain external evidence. |
| UX7-003 | Locally resolved | Root, human-guide and generated README surfaces consistently document repository `models/`, absolute host path, `/models/model.gguf`, read-only bind, no-copy policy and validation tiers; documentation contract tests pass. |
| UX7-004 | Locally resolved | Root and human documentation distinguish generator CLI subcommands from generated helper scripts; `tests/test_documentation_contract.py` enforces the distinction and current command examples. |
| LEG7-001 | Formally conditional-distribution blocked | Owner: engineering-manager/security-engineer and qualified legal reviewer if distribution begins. Exact reason: no publication is authorized and model/image license terms depend on the selected artifacts; no distribution-readiness claim is made. |

### Aggregate evidence

- `python3 -m unittest`: exit 0, 97 tests.
- Focused TASK-0007 suites
  (`tests.test_cli`, `tests.test_ci_contract`,
  `tests.test_documentation_contract`, `tests.test_harness_agents`): exit 0,
  60 tests.
- `python3 .pm-harness/bin/harness.py agents check`: exit 0 for OpenCode and
  Claude installed surfaces.
- `python3 .pm-harness/bin/harness.py wiki check`: exit 0.
- Frozen pre-remediation hashes remain unchanged:
  `informe_completa.md`
  `91e652acba51146d89fcc27133afa1503b4b972f9070cd8c4293a3696397f3f3`,
  `checklist_completa.md`
  `976aa51bcf5961de14acf1040da3b245b8095c060d2335cea9e65c81225ce803`,
  and `mejora-audit.md`
  `abd137a306e709507e399513b145416ae6d28373d323892af80cab36d528a5ae`.
  `meta.md` is intentionally self-referential: its recorded pre-append hash
  remains the frozen value and its current file hash is not substituted for it.
- Audit APR lineage remains in `audits/standards/MEJORA.md` APR-036–038.
  No new PM Harness APR is required: every remediation category is already
  covered by the rules mapped in the frozen `mejora-audit.md`; this
  reconciliation did not discover a new uncovered defect.
- The independent whole-change security/plan-adherence review is still
  pending. The earlier `APPROVED` verdicts apply only to SEC7-001/OPS7-001 and
  SEC7-005, not to the aggregate TASK-0007 patch.

## Independent whole-change security review — 2026-07-26

**Verdict: APPROVED**

The security-engineer rereview of the integrated TASK-0007 patch approved the
whole change after `SR7-FINAL-001` was corrected. The final focused
backup/restore checks, ShellCheck, `bash -n`, and `git diff --check` all exited
0. The preceding integrated evidence also recorded 97 passing unit tests,
`pip check`, `pip-audit`, current SBOM verification, and PM Harness
validate/agents/wiki checks with exit 0.

This verdict closes the risk-area review for repository-local remediation. It
does not convert any formally external row in the matrix into a live runtime,
LAN, model, Codex-adapter, distribution, or legal-readiness claim.
