# TASK-0006 Product Acceptance Audit

Date: 2026-07-24  
Owner: product-analyst  
Scope: independent product and documentation reconciliation of closed TASK-0001 through TASK-0005

## Method and classification

This audit distinguishes plan acceptance from current product acceptance. Static
generation, unit tests, and `matrix` output do not prove that a model starts,
fits the target hardware, or meets latency/quality goals.

- `delivered`: explicitly completed by TASK-0001 through TASK-0005.
- `roadmap`: approved direction, but not promised as implementation by a closed task.
- `deferred`: explicitly postponed or awaiting a separate decision/evaluation.
- Acceptance status: `accepted`, `accepted-with-limitation`, `pending`,
  `contradicted`, or `blocked`.

## Approved-scope register

### Incorporated Director preferences

| requirement | source | delivery_task | expected_evidence | scope_class | acceptance |
|---|---|---|---|---|---|
| Linux is the initial host platform. | `.pm-harness/ceremonies/2026-07-23-kickoff-KICK-0001.md` lines 80-94; `mem-pm-orchestrator-0001.md` | TASK-0001, TASK-0002 | Linux prerequisites and generated Linux/Docker workspace | delivered | accepted-with-limitation: static artifacts exist; no target-host run is recorded |
| Support localhost and LAN, with LAN opt-in. | kickoff lines 80-94; `mem-pm-orchestrator-0001.md` | TASK-0001, TASK-0003 | localhost default plus authenticated, allowlisted LAN operation | delivered | accepted-with-limitation: input guard exists; enforcement is pending TASK-0007 |
| Capability direction includes Vision, Coding, Chat, RAG, and other hardware-feasible uses. | kickoff lines 80-94; `mem-pm-orchestrator-0001.md` | TASK-0002 roadmap | distinct setup manifests, runbooks, and hardware evidence | roadmap | pending: only Chat is implemented |
| Docker and simplifying tools are welcome. | kickoff lines 80-94; `mem-pm-orchestrator-0001.md` | TASK-0001, TASK-0003 | Docker-first generated workflow | delivered | accepted |
| Balanced targets are medium-fast response, medium latency, and good quality. | kickoff lines 80-94; `mem-pm-orchestrator-0001.md` | TASK-0001, TASK-0004 | profiles plus measured latency/memory/quality evidence | delivered | accepted-with-limitation: profiles exist; outcomes are not measured |
| Product is a downloadable generator-first repository. | `mem-pm-orchestrator-0004.md` and `mem-pm-orchestrator-0005.md` | TASK-0002, TASK-0003 | clone → matrix → generate → validate → start | delivered | accepted-with-limitation: generation works; launch-path defects are routed to TASK-0007 |
| CLI is Python + Jinja2, command name `ai-server`, Chat/localhost/medium first, generated outputs ignored, bearer-token LAN MVP. | `mem-pm-orchestrator-0006.md` | TASK-0003 | package metadata, CLI, template output, guarded LAN flags | delivered | accepted-with-limitation: LAN allowlist is metadata, not enforced |

### TASK-0001 approved plan todos

| requirement | source | delivery_task | expected_evidence | scope_class | acceptance |
|---|---|---|---|---|---|
| Create the lab directory skeleton. | `.pm-harness/plans/TASK-0001.plan.md` todo 1 | TASK-0001 | models/datasets/experiments/logs/backups/scripts/docs directories | delivered | accepted |
| Define a Docker-first baseline with healthy service. | TASK-0001 todo 2 | TASK-0001 | service start and healthy status | delivered | accepted-with-limitation: Compose exists; live health was not run |
| Expose an API-compatible endpoint with sample response. | TASK-0001 todo 3 | TASK-0001 | valid response payload | delivered | blocked: no live response evidence |
| Implement a balanced resource preset. | TASK-0001 todo 4 | TASK-0001 | CPU/RAM/startup settings | delivered | accepted |
| Store a smoke benchmark with latency and memory. | TASK-0001 todo 5 | TASK-0001 | measured timestamped report | delivered | contradicted: reports contain `placeholder` and `not-tested` |
| Document LAN-safe enablement. | TASK-0001 todo 6 | TASK-0001 | localhost default, opt-in, auth, firewall notes | delivered | accepted-with-limitation: static runbook exists |
| Align legacy artifacts to generator-first flow. | TASK-0001 todo 7 | TASK-0001 | canonical clone → matrix → generate → validate → start docs | delivered | accepted |
| Label legacy files as compatibility examples. | TASK-0001 todo 8 | TASK-0001 | compatibility labels and generated equivalents | delivered | accepted |
| Verify generator-driven replacement path. | TASK-0001 todo 9 | TASK-0001 | preset generation and static validation | delivered | accepted-with-limitation: not a runtime verification |
| Update TASK-0001 changelog closure entry. | TASK-0001 todo 10 | TASK-0001 | `[Unreleased]` TASK-0001 bullet | delivered | accepted |

### TASK-0002 approved plan todos

| requirement | source | delivery_task | expected_evidence | scope_class | acceptance |
|---|---|---|---|---|---|
| Define generator-first product journey. | `.pm-harness/plans/TASK-0002.plan.md` todo 1 | TASK-0002 | clone-to-launch roadmap | delivered | accepted |
| Enumerate Chat, Coding, RAG, optional Vision, access, and profiles. | TASK-0002 todo 2 | TASK-0002 | configuration-family roadmap | roadmap | accepted as planning; implementation pending |
| Define inputs, templates, outputs, validation, and layout. | TASK-0002 todo 3 | TASK-0002 | architecture section | roadmap | accepted |
| Define command UX and generated paths. | TASK-0002 todo 4 | TASK-0002 | concrete command examples | roadmap | accepted-with-limitation: some examples exceed current implementation |
| Break work into sprint-sized phases with acceptance criteria and gates. | TASK-0002 todo 5 | TASK-0002 | phased backlog | roadmap | accepted |
| Define quality/security controls and test strategy. | TASK-0002 todo 6 | TASK-0002 | validation, secrets, rollback, test controls | roadmap | accepted as planning; several controls remain pending |

### TASK-0003 approved plan todos

| requirement | source | delivery_task | expected_evidence | scope_class | acceptance |
|---|---|---|---|---|---|
| Create the implementation-plan artifact. | `.pm-harness/plans/TASK-0003.plan.md` todo 1 | TASK-0003 | `docs/superpowers/plans/2026-07-24-generator-skeleton.md` | delivered | accepted |
| Create package skeleton and console metadata. | TASK-0003 todo 2 | TASK-0003 | module help and `ai-server` entry point | delivered | accepted |
| Declare Jinja2 dependency. | TASK-0003 todo 3 | TASK-0003 | `pyproject.toml` and `requirements.txt` | delivered | accepted |
| Implement profile/setup listing. | TASK-0003 todo 4 | TASK-0003 | list commands | delivered | accepted-with-limitation: only Chat is a real setup |
| Implement no-write dry-run generation. | TASK-0003 todo 5 | TASK-0003 | planned files and absent output | delivered | accepted |
| Migrate Sprint 1 assets into templates/profiles/manifests. | TASK-0003 todo 6 | TASK-0003 | generated Chat workspace | delivered | accepted |
| Validate safe Chat output and reject unsafe LAN inputs. | TASK-0003 todo 7 | TASK-0003 | static validation and negative LAN command | delivered | accepted-with-limitation: enforcement and runtime are not validated |
| Run gates and update changelog. | TASK-0003 todo 8 | TASK-0003 | historical closure plus TASK-0003 changelog entries | delivered | accepted |

### TASK-0004 approved plan todos

| requirement | source | delivery_task | expected_evidence | scope_class | acceptance |
|---|---|---|---|---|---|
| Add five named model presets with tags and memory guidance. | `.pm-harness/plans/TASK-0004.plan.md` todo 1 | TASK-0004 | preset catalog | delivered | accepted-with-limitation: guidance is not runtime evidence |
| Add shorthand preset expansion. | TASK-0004 todo 2 | TASK-0004 | `--preset` resolution into manifest/runbook | delivered | accepted |
| Add concise generated start/validate/smoke helpers. | TASK-0004 todo 3 | TASK-0004 | generated helper scripts and docs | delivered | contradicted: root-invoked helpers do not reliably use generated-workspace cwd |
| Test named presets and core combinations. | TASK-0004 todo 4 | TASK-0004 | automated matrix/generation/LAN tests | delivered | accepted |
| Warn or reject oversize/risky combinations. | TASK-0004 todo 5 | TASK-0004 | warnings/failures | delivered | accepted-with-limitation: warnings are profile/alias rules, not detected hardware fit |
| Document shorthand matrix and go/no-go interpretation. | TASK-0004 todo 6 | TASK-0004 | docs and changelog | delivered | accepted after TASK-0006 clarifies that GO is static only |

### TASK-0005 approved plan todos

| requirement | source | delivery_task | expected_evidence | scope_class | acceptance |
|---|---|---|---|---|---|
| Propose at least five repository names and recommend one. | `.pm-harness/plans/TASK-0005.plan.md` todo 1 | TASK-0005 | `docs/repo-name-suggestions.md` | delivered | accepted |
| Create a human-facing root README. | TASK-0005 todo 2 | TASK-0005 | purpose, prerequisites, quick start, workflow, safety | delivered | accepted after TASK-0006 limitation corrections |
| Create a step-by-step human guide. | TASK-0005 todo 3 | TASK-0005 | matrix/generate/validate/start and troubleshooting | delivered | accepted after TASK-0006 limitation corrections |
| Align docs index and canonical/compatibility distinction. | TASK-0005 todo 4 | TASK-0005 | `docs/README.md` | delivered | accepted after TASK-0006 limitation corrections |
| Add TASK-0005 changelog entry. | TASK-0005 todo 5 | TASK-0005 | `[Unreleased]` TASK-0005 bullet | delivered | accepted |

## Closed-task reconciliation

Checksums are current SHA-256 values compared with the historical manifest
value. A mismatch is reported, not rewritten.

| task | manifest | plan | declared artifact | exists | checksum | changelog | literal evidence |
|---|---|---|---|---|---|---|---|
| TASK-0001 | closed | approved/all todos checked | `docker-compose.yml` | yes | match: `80854009…e535` | Changed entry present | `shasum -a 256 docker-compose.yml` |
| TASK-0002 | closed | approved/all todos checked | `docs/roadmap/generator-first-roadmap.md` | yes | match: `47b2e46c…2b3e` | Added entry present | `shasum -a 256 docs/roadmap/generator-first-roadmap.md` |
| TASK-0003 | closed | approved/all todos checked | `generated/chat-medium-localhost/manifest.json` | yes, ignored/generated | mismatch: state `b7ac6f95…99ca`, current `17512ee0…8c66` (F-009) | Added/Changed entries present | `shasum -a 256 generated/chat-medium-localhost/manifest.json` |
| TASK-0004 | closed | approved/all todos checked | `CHANGELOG.md` | yes | mismatch: state `6af9d87c…7c29`, current `e2dd1599…2209` before TASK-0006 edits (F-010) | Added/Changed entries present | `shasum -a 256 CHANGELOG.md` |
| TASK-0005 | closed | approved/all todos checked | `docs/repo-name-suggestions.md` | yes | match: `51ffcce5…a842` | Added entry present | `shasum -a 256 docs/repo-name-suggestions.md` |

F-009 is expected drift for ignored generated evidence but makes the historical
artifact non-durable. F-010 is expected append-only changelog evolution after
TASK-0004. Neither historical checksum is changed.

## Product and governance findings

Each finding has one disposition and owner. `fix-now` means product-owned and
resolved by TASK-0006; engineering changes are routed to TASK-0007.

### F-001 — Generated helper working directory

- severity: high
- evidence: root docs invoked `./generated/.../scripts/start.sh`, while generated wrappers call `./scripts/...` relative to caller cwd.
- scope_owner: TASK-0007 / engineering-manager
- disposition: TASK-0007
- status: open
- product correction: docs now require `cd generated/<workspace>` before helpers.

### F-002 — Repository model path is not generated-workspace model path

- severity: high
- evidence: wizard checks `./models/<preset>.gguf`; generated Compose mounts workspace-relative `./models:/models:ro`; generation does not materialize that directory.
- scope_owner: TASK-0007 / engineering-manager
- disposition: TASK-0007
- status: open
- product correction: docs disclose the temporary copy requirement.

### F-003 — Validation claims exceeded implementation

- severity: medium
- evidence: `validator.py` verifies manifest/file/bind metadata but not model existence, executable bits, host tools, memory fit, Compose runtime, versions, or live health.
- scope_owner: TASK-0007 / engineering-manager
- disposition: TASK-0007
- status: open
- product correction: docs describe validation as static workspace validation.

### F-004 — LAN allowlist is recorded but not enforced

- severity: high
- evidence: generated LAN Compose binds `0.0.0.0`, passes an API key, and records `LAN_ALLOWLIST`; it emits no firewall/proxy enforcement artifacts.
- scope_owner: TASK-0007 / security-engineer
- disposition: TASK-0007
- status: open
- product correction: LAN is documented as guarded generation plus mandatory manual firewall enforcement.

### F-005 — Destructive overwrite guidance

- severity: medium
- evidence: `render.py` uses `shutil.rmtree(out_path)` for `--force`; quick starts previously promoted `--force`.
- scope_owner: TASK-0007 / engineering-manager
- disposition: TASK-0007
- status: open
- product correction: normal docs no longer recommend `--force`.

### F-006 — Static matrix GO was easy to read as runtime support

- severity: high
- evidence: matrix checks requested configuration only; it does not inspect model weights, Docker, host RAM, quantization, latency, or quality.
- scope_owner: product-analyst
- disposition: fix-now
- status: resolved
- resolution: README and product guides define GO as static pre-render compatibility.

### F-007 — Capability breadth remains roadmap work

- severity: medium
- evidence: roadmap lists Coding, RAG, and optional Vision, while implementation has only `manifests/chat.json` and `templates/chat/`.
- scope_owner: product-manager
- disposition: follow-up
- status: open
- scope note: Coding/RAG are approved roadmap work; Vision and acceleration remain feasibility/deferred work.

### F-008 — LLM Wiki was structurally valid but empty

- severity: medium
- evidence: prior `.pm-harness/wiki/INDEX.md` had no Pages or Sources despite documentation-changing closed tasks.
- scope_owner: product-analyst
- disposition: fix-now
- status: resolved
- resolution: TASK-0006 compiled workflow, capability, security, and accepted-decision pages.

### F-009 — Generated TASK-0003 artifact drift

- severity: low
- evidence: current ignored generated manifest checksum differs from historical state checksum and lacks current manifest fields.
- scope_owner: product-manager
- disposition: accepted
- status: resolved

### F-010 — TASK-0004 changelog artifact drift

- severity: low
- evidence: append-only later entries necessarily change `CHANGELOG.md` after TASK-0004 closure.
- scope_owner: product-manager
- disposition: accepted
- status: resolved

### F-011 — Kickoff ceremony status contradicts harness state

- severity: low
- evidence: kickoff Markdown says `pending Director approval`; `.pm-harness/harness.json` records KICK-0001 approved by Director at `2026-07-23T23:14:09Z`.
- scope_owner: pm-orchestrator
- disposition: follow-up
- status: open
- handling: both claims are retained in the wiki; historical ceremony was not rewritten.

### F-012 — Live serving and benchmark acceptance is absent

- severity: high
- evidence: `logs/benchmarks/*.md` records `placeholder`/`not-tested`; static tests do not provide a model response, latency, memory, or quality result.
- scope_owner: TASK-0007 / ml-systems-engineer
- disposition: TASK-0007
- status: open

### F-013 — Post-closure wizard work is not mapped to TASK-0001..0005

- severity: medium
- evidence: commits `b75a3aa` and `47027c7` add wizard spec/code after the five audited tasks, but CHANGELOG has no wizard entry and no closed task claims it.
- scope_owner: pm-orchestrator
- disposition: follow-up
- status: open

## TASK-0007 engineering handoff

### H-001 — Workspace-independent generated helpers

- reproduction: generate a workspace, remain at repository root, invoke `./generated/<name>/scripts/{validate,start,smoke}.sh`.
- expected: each helper operates on its own generated workspace regardless of caller cwd.
- actual: wrappers resolve `./scripts/...` and Compose files from caller cwd.
- user-visible acceptance: all helpers pass a fake-Docker cwd/Compose regression from repository root and workspace root.

### H-002 — Container-visible model source

- reproduction: place a preset file at repository `models/<alias>.gguf`, run wizard/generate, inspect generated Compose mount and model path.
- expected: a model that passes preflight is visible at the generated container path.
- actual: preflight checks repository root; Compose mounts generated-workspace `./models`.
- user-visible acceptance: one documented placement succeeds through Compose model resolution without undocumented copying.

### H-003 — Validation contract

- reproduction: generate a workspace with missing model, non-executable helper, invalid memory field, or absent Docker and run generator `validate`.
- expected: documented controls are checked or explicitly separated into host/runtime tiers.
- actual: metadata validation can return success.
- user-visible acceptance: docs and commands expose static, host, and live tiers with negative tests for every promised invariant.

### H-004 — Enforced LAN boundary

- reproduction: generate authenticated LAN output with an allowlist and inspect network enforcement artifacts.
- expected: only allowlisted sources can reach the service; output includes enforceable firewall/proxy configuration.
- actual: allowlist is metadata; host port binds all interfaces.
- user-visible acceptance: unsafe LAN output cannot start without effective auth and allowlist enforcement, with a testable deny path.

### H-005 — Recoverable overwrite

- reproduction: put an operator marker in existing output and generate into it with `--force`.
- expected: refusal, backup, or explicit recoverable lifecycle.
- actual: directory is recursively removed.
- user-visible acceptance: onboarding never requires destructive overwrite; any overwrite path states impact and governs recovery.

### H-006 — Real runtime evidence

- reproduction: inspect TASK-0001 benchmark reports or run static unit/matrix gates.
- expected: one real target-like model start with HTTP response, latency, and memory.
- actual: placeholder/not-tested reports only.
- user-visible acceptance: sanitized report records model/quantization/runtime, target hardware, HTTP success, time-to-first-response, throughput, and peak memory.

## Independent command evidence

Live Docker/model-serving remains `not-run` pending TASK-0007 prerequisites and
is not inferred from the static commands.

| command | exit code | result |
|---|---:|---|
| `python3 -m unittest` | 0 | 12 tests passed |
| `python3 -m ai_server_generator --help` | 0 | help lists list/generate/matrix/validate/wizard |
| `python3 -m ai_server_generator list profiles` | 0 | medium-fast, medium, good |
| `python3 -m ai_server_generator list setups` | 0 | chat-localhost-medium shortcut and Chat only |
| `python3 -m ai_server_generator list models` | 0 | five requested preset aliases listed |
| `python3 -m ai_server_generator matrix --preset ornith-9b --profile medium --access localhost` | 0 | static `Decision: GO`; resolved Chat/medium/localhost |
| `python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/task-0006-acceptance --force` | 0 | fresh dedicated workspace; 11 files |
| `python3 -m ai_server_generator validate generated/task-0006-acceptance` | 0 | static workspace valid |
| guarded LAN negative generation | 1 | expected rejection: bearer token and allowlist required; no output written |
| `python3 .pm-harness/bin/harness.py validate` | 0 | no errors or warnings |
| `python3 .pm-harness/bin/harness.py wiki check` | 0 | no errors or warnings |
| `python3 .pm-harness/bin/harness.py changelog check --task TASK-0006` | 0 | no errors or warnings |
| `python3 .pm-harness/bin/harness.py plan check TASK-0006` | 1 | expected partial-pass result; todo 7 remains unchecked pending TASK-0007 |
| live Docker/model serving | not-run | target model/runtime prerequisites and TASK-0007 remediation evidence unavailable |

## Partial recommendation

- Accepted: generator-first architecture and roadmap; Python/Jinja2 CLI; Chat
  workspace generation; profile/preset discovery; static LAN input guard;
  naming proposal and human documentation structure.
- Accepted with limitations: target-host Linux/Docker operation, balanced
  performance, all model presets, generated helpers, and LAN operation.
- Resolved product defects: matrix-GO overclaim, unsafe default overwrite
  guidance in onboarding, missing limitation disclosure, and empty wiki.
- Pending approved roadmap: Coding and minimal RAG setup implementation.
- Deferred/evaluation: Vision, iGPU acceleration, fine-tuning, multi-model,
  and broader operations milestones.
- No new scope was approved by this audit. Final acceptance waits for TASK-0007
  evidence and TASK-0006 todo 7.
