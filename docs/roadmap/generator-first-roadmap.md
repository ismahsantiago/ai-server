# Generator-First Roadmap for ai-server

## 1. Vision & product model (clone -> generate -> launch user journey)

`ai-server` should be a downloadable local AI server repository whose primary product is a **configuration and document generator**, not a hand-maintained set of final runtime files. The user clones the repository onto a Linux laptop, answers or passes a small set of setup choices, receives generated configuration files plus exact launch commands, and then starts a local AI server that matches their hardware, access mode, and intended workload.

Target hardware for the default product path:

- Host: Linux laptop.
- CPU/GPU class: Ryzen 5 with Radeon Vega iGPU.
- Memory: 12 GB RAM.
- Storage: 1 TB local storage.
- Default assumption: CPU-first or low-VRAM local inference using quantized models, with iGPU/ROCm only as an advanced opt-in if validated later.
- Default network posture: localhost-only. LAN exposure is always explicit opt-in and requires authentication plus firewall guidance before generation succeeds.

The intended user journey is:

1. **Clone**
   - User downloads or clones the repository.
   - Repository includes the generator, templates, model/setup manifests, validation rules, and documentation.
   - Repository does not require the user to hand-author Docker Compose, env profiles, launch scripts, or LAN hardening notes.

2. **Inspect supported setups**
   - User runs a discovery command such as `python3 -m ai_server_generator list setups`.
   - The generator reports supported families: chat, coding, RAG, optional vision, performance profiles, and localhost/LAN access modes.
   - Each setup declares approximate memory budget, model class, required files, exposed ports, security posture, and known limitations for 12 GB RAM hosts.

3. **Generate**
   - User runs one command with explicit choices, for example:
     ```bash
     python3 -m ai_server_generator generate \
       --setup chat \
       --profile medium \
       --access localhost \
       --model local-gguf \
       --out generated/chat-medium-localhost
     ```
   - The generator emits all files required to launch and operate that setup.
   - It also emits a generated runbook with the exact commands to run next.

4. **Validate**
   - User runs:
     ```bash
     python3 -m ai_server_generator validate generated/chat-medium-localhost
     ```
   - Validation checks generated file presence, model path placeholders, memory budget, port binding, security defaults, and required host tools.
   - Invalid LAN exposure without auth/firewall configuration fails validation.

5. **Launch**
   - User runs either the generated command directly or a generated launch script:
     ```bash
     cd generated/chat-medium-localhost
     docker compose up -d
     ./scripts/smoke_benchmark.sh
     ```
   - The server exposes an OpenAI-compatible endpoint by default at `http://127.0.0.1:8000/v1/chat/completions` for supported chat/coding setups.

6. **Iterate safely**
   - User can regenerate into a new output directory without destroying the previous working setup.
   - The generator records what choices produced a setup in `generated/<setup>/manifest.json`.
   - Rollback is directory-based: stop the new generated setup and return to a previous generated directory.

Product principles:

- **Generator-first**: hand-maintained root examples are treated as development references or generated-output templates, not the final product surface.
- **Local-first**: the default server binds to localhost and does not send data off the machine.
- **Hardware-realistic**: MVP profiles fit within a 12 GB RAM laptop by default; heavier setups are labeled experimental or deferred.
- **Explicit security posture**: LAN mode requires an explicit access decision, auth method, firewall allowlist guidance, and generated runbook warnings.
- **Reproducible outputs**: given the same inputs and template version, the generated files should be deterministic.

## 2. Configuration families / supported setups for MVP and later

### MVP configuration families

MVP should support a small, coherent set of generated setups that can run on the target 12 GB RAM Linux laptop.

| Family | MVP support | Primary output | 12 GB RAM posture | Notes |
|---|---:|---|---|---|
| Chat | Yes | Single llama.cpp OpenAI-compatible server | Default supported path | Uses quantized GGUF model path supplied by the user. |
| Coding | Yes | Same serving baseline with coding-oriented model manifest and profile hints | Supported with conservative context | Focuses on local code assistant backend, not IDE integration in MVP. |
| RAG | Yes, minimal | Chat server plus generated local data/runbook scaffolding | Constrained; retrieval service may be stubbed or single-process initially | MVP should generate directories and docs even if full vector service is a later task. |
| Vision | Later / optional experimental | Multimodal model profile and runbook | High risk on 12 GB RAM | Defer full support until memory and model compatibility are validated. |
| Localhost access | Yes | Compose bound to `127.0.0.1` | Default | Always generated unless explicitly overridden. |
| LAN access | Yes, guarded | Compose/reverse-proxy outputs plus LAN runbook | Opt-in only | Requires auth and firewall inputs before validation passes. |
| Performance profiles | Yes | `medium-fast`, `medium`, `good` generated env values | Default profile is `medium` | Existing Sprint 1 values become template defaults. |

### MVP setup matrix

MVP should generate these named setup presets:

1. `chat-localhost-medium`
   - Intended first successful path.
   - Generates Docker Compose for `llama.cpp:server`, `.env`, profile metadata, launch script, smoke benchmark script, and runbook.
   - Binds host port to `127.0.0.1:${HOST_PORT:-8000}`.

2. `chat-localhost-medium-fast`
   - Lower memory and lower latency target.
   - Smaller context and batch values.
   - Based on current `config/profiles/medium-fast.env` values.

3. `chat-localhost-good`
   - Higher quality/context target within a 10 GB container memory limit.
   - Requires validation warning that the host may become memory constrained if other apps are running.
   - Based on current `config/profiles/good.env` values.

4. `coding-localhost-medium`
   - Same runtime pattern as chat, but generated manifest and runbook recommend a coding-oriented GGUF model family.
   - Acceptance focuses on generated clarity: model expectations, endpoint compatibility, and memory-safe defaults.

5. `rag-localhost-minimal`
   - Generates a chat server plus `datasets/`, `indexes/`, and RAG runbook scaffolding.
   - MVP may avoid a separate vector database service until there is a validated memory budget.
   - The generated manifest must declare whether RAG is documentation-only, script-assisted, or service-backed for that version.

6. `chat-lan-medium-authenticated`
   - Opt-in LAN setup.
   - Requires explicit `--access lan`, `--auth bearer-token` or equivalent, and `--lan-allowlist` input.
   - Generates auth/firewall instructions and refuses insecure unauthenticated LAN output.

### Later configuration families

Later releases can add:

- **Vision / multimodal local server**
  - Only after validating a model/runtime combination that fits the 12 GB host or clearly documenting higher hardware requirements.
  - Generated outputs may include alternative runtime templates if llama.cpp server is insufficient.

- **Service-backed RAG**
  - Add a local embedding service, vector store, index/update scripts, and retrieval API.
  - Must include memory budgets and start/stop ordering.

- **GPU/iGPU acceleration profiles**
  - Detect or ask for ROCm/Vulkan/OpenCL readiness.
  - Generate hardware-specific runtime flags only when the user opts in and validation confirms prerequisites.

- **Multi-model router**
  - Generate a small local gateway or profile set that switches between chat, coding, and embedding models.
  - Defer until single-server generation is stable.

- **Web UI bundle**
  - Optional local UI connected to the OpenAI-compatible endpoint.
  - Must keep local-only defaults and explicit LAN rules.

## 3. Generator architecture (inputs, templates engine, outputs, validation, directory layout: templates/, generated/, profiles/, manifests/)

### Architectural model

The generator should be a deterministic CLI application that transforms a typed setup request into a complete generated output directory.

```text
User intent + hardware/access/profile choices
        |
        v
Generator CLI
        |
        +--> load setup manifests
        +--> load profile definitions
        +--> validate requested combination
        +--> render templates
        +--> write generated output directory
        +--> write manifest + runbook + exact commands
        +--> run optional validation checks
```

### Inputs

The generator should accept inputs from three layers, in this precedence order:

1. **CLI flags** for explicit one-off generation.
   - Examples: `--setup chat`, `--profile medium`, `--access localhost`, `--model-path ./models/model.gguf`, `--out generated/chat-medium-localhost`.

2. **Setup manifest file** for repeatable generation.
   - Example: `manifests/examples/chat-medium-localhost.yaml`.
   - The manifest records the same options as CLI flags, making generation reproducible.

3. **Built-in defaults** for the target hardware.
   - Default profile: `medium`.
   - Default access: `localhost`.
   - Default runtime: Docker Compose with llama.cpp server.
   - Default memory cap: no more than the current `medium` profile budget unless the user opts into `good` or experimental profiles.

### Template engine

Recommendation: use a small Python CLI with a real templating engine, preferably **Jinja2**, and keep shell scripts as generated artifacts rather than the orchestration brain.

Rationale:

- Python is better than shell for structured validation, manifest parsing, path handling, testing, and deterministic rendering.
- Jinja2 is widely understood and appropriate for Docker Compose, env files, shell scripts, Markdown runbooks, and JSON manifests.
- Shell remains useful inside generated `scripts/*.sh` files for launching and smoke checks, but shell should not own the generator's product logic.

If avoiding third-party dependencies is a hard requirement, the fallback is Python stdlib `string.Template` plus strict schema conventions. However, the roadmap recommendation is **Python CLI + Jinja2 templates + generated shell scripts**.

### Outputs

Each generation run writes a self-contained output directory:

```text
generated/<setup-name>/
  docker-compose.yml
  .env
  manifest.json
  README.md
  runbook.md
  profiles/
    selected.env
    profile.json
  scripts/
    start_serving.sh
    stop_serving.sh
    smoke_benchmark.sh
    validate_host.sh
  logs/
    .gitkeep
```

For RAG-capable outputs, add:

```text
generated/<setup-name>/
  datasets/
    README.md
  indexes/
    README.md
  rag/
    ingest.md
    query.md
```

For LAN-capable outputs, add:

```text
generated/<setup-name>/
  security/
    lan-safe-runbook.md
    firewall.md
    auth.md
  proxy/
    Caddyfile.example  # or nginx/traefik equivalent after Director choice
```

### Validation

Validation should happen in two places:

1. **Pre-render validation** checks whether the requested combination is allowed.
   - `--access lan` without auth choice fails.
   - LAN allowlist omitted for LAN setup fails or prompts in interactive mode.
   - `good` profile on 12 GB RAM emits a warning but may pass.
   - Vision setup on MVP should fail unless `--experimental` is explicitly supplied.

2. **Post-render validation** checks the generated directory.
   - Required files exist.
   - Docker Compose port binding matches access mode.
   - `.env` contains no generated secrets committed to template paths.
   - Generated scripts are executable.
   - Generated `manifest.json` records setup inputs and template versions.
   - Memory limits are within declared profile bounds.
   - LAN outputs include auth and firewall documents.

### Proposed repository layout

The repository should evolve toward this layout:

```text
ai-server/
  ai_server_generator/                 # Python package for the generator
    __init__.py
    cli.py
    models.py                          # typed setup/profile/access models
    render.py                          # template rendering
    validate.py                        # pre/post validation
    paths.py
  templates/                           # generated-output templates
    compose/
      llama-server.docker-compose.yml.j2
    env/
      profile.env.j2
    scripts/
      start_serving.sh.j2
      stop_serving.sh.j2
      smoke_benchmark.sh.j2
      validate_host.sh.j2
    docs/
      README.md.j2
      runbook.md.j2
      lan-safe-runbook.md.j2
    rag/
      datasets.README.md.j2
      indexes.README.md.j2
  profiles/                            # canonical profile definitions, not final .env files
    medium-fast.yaml
    medium.yaml
    good.yaml
  manifests/                           # supported setup definitions and examples
    setups/
      chat.yaml
      coding.yaml
      rag-minimal.yaml
      lan-authenticated.yaml
    examples/
      chat-medium-localhost.yaml
      coding-medium-localhost.yaml
      rag-minimal-localhost.yaml
  generated/                           # ignored/generated workspace; outputs go here by default
    .gitkeep
  config/profiles/                     # Sprint 1 compatibility path, later generated or deprecated
  scripts/                             # Sprint 1 compatibility path, later generated or thin wrappers
  docs/                                # product docs and roadmap; generated runbooks live under generated/
  docs/roadmap/
    generator-first-roadmap.md
```

Key directory decisions:

- `templates/` contains versioned templates for generated files.
- `profiles/` contains canonical structured profile definitions; these replace hand-maintained final `.env` profiles over time.
- `manifests/` contains setup families and reproducible example inputs.
- `generated/` is the default output workspace and should be ignored except for `.gitkeep` and maybe example snapshots if the Director chooses to commit examples later.
- Existing `config/profiles/*`, `docker-compose.yml`, `scripts/*`, and `docs/lan-safe-runbook.md` should be refactored into templates rather than treated as source-of-truth final runtime files.

## 4. Command UX (proposed CLI commands with concrete examples and generated artifact paths; recommend implementation approach: Python CLI vs shell vs hybrid, with a recommendation)

### Recommendation

Implement the generator as a **Python CLI with generated shell scripts**.

- Python owns product logic, setup selection, validation, rendering, manifests, and tests.
- Jinja2 or a similar template engine owns file rendering.
- Shell scripts remain generated runtime helpers for users who prefer simple `./scripts/start_serving.sh` commands inside the generated output directory.
- Avoid a shell-only generator because shell will become fragile for schema validation, security conditions, manifest merging, and testability.
- Avoid a heavy web UI or daemon for MVP because the product need is deterministic local file generation.

### Proposed command namespace

Use one of these entry points:

```bash
python3 -m ai_server_generator <command>
```

Later, package it as:

```bash
ai-server <command>
```

### Command examples

#### Show supported setup families

```bash
python3 -m ai_server_generator list setups
```

Expected output includes:

```text
chat                 OpenAI-compatible local chat server
coding               OpenAI-compatible local coding backend
rag-minimal          Local chat server plus RAG directories/runbook
chat-lan-auth        LAN opt-in chat server with auth/firewall outputs
```

#### Show performance profiles

```bash
python3 -m ai_server_generator list profiles
```

Expected output includes:

```text
medium-fast  ctx=2048 batch=128 threads=4 mem=6g  lower latency
medium       ctx=4096 batch=256 threads=6 mem=8g  default balance
good         ctx=6144 batch=384 threads=8 mem=10g higher quality/context
```

#### Generate default localhost chat setup

```bash
python3 -m ai_server_generator generate \
  --setup chat \
  --profile medium \
  --access localhost \
  --model-path ./models/placeholder.gguf \
  --out generated/chat-medium-localhost
```

Generated paths:

```text
generated/chat-medium-localhost/docker-compose.yml
generated/chat-medium-localhost/.env
generated/chat-medium-localhost/manifest.json
generated/chat-medium-localhost/runbook.md
generated/chat-medium-localhost/scripts/start_serving.sh
generated/chat-medium-localhost/scripts/smoke_benchmark.sh
```

Generated next commands in `runbook.md`:

```bash
cd generated/chat-medium-localhost
./scripts/validate_host.sh
docker compose up -d
./scripts/smoke_benchmark.sh
```

#### Generate coding setup

```bash
python3 -m ai_server_generator generate \
  --setup coding \
  --profile medium \
  --access localhost \
  --model-family coding-gguf \
  --out generated/coding-medium-localhost
```

Generated paths:

```text
generated/coding-medium-localhost/docker-compose.yml
generated/coding-medium-localhost/.env
generated/coding-medium-localhost/manifest.json
generated/coding-medium-localhost/README.md
```

#### Generate minimal RAG setup

```bash
python3 -m ai_server_generator generate \
  --setup rag-minimal \
  --profile medium-fast \
  --access localhost \
  --out generated/rag-minimal-medium-fast-localhost
```

Generated paths:

```text
generated/rag-minimal-medium-fast-localhost/docker-compose.yml
generated/rag-minimal-medium-fast-localhost/datasets/README.md
generated/rag-minimal-medium-fast-localhost/indexes/README.md
generated/rag-minimal-medium-fast-localhost/rag/ingest.md
generated/rag-minimal-medium-fast-localhost/rag/query.md
```

#### Generate authenticated LAN setup

```bash
python3 -m ai_server_generator generate \
  --setup chat \
  --profile medium \
  --access lan \
  --auth bearer-token \
  --lan-allowlist 192.168.1.0/24 \
  --host-port 8000 \
  --out generated/chat-medium-lan-auth
```

Required behavior:

- If `--access lan` is supplied without `--auth`, generation fails.
- If `--access lan` is supplied without `--lan-allowlist`, generation fails or prompts in interactive mode.
- Generated Compose may bind to a LAN interface only when auth/firewall docs and proxy config are present.
- Generated `security/lan-safe-runbook.md` must preserve the current localhost-default doctrine.

Generated paths:

```text
generated/chat-medium-lan-auth/docker-compose.yml
generated/chat-medium-lan-auth/security/lan-safe-runbook.md
generated/chat-medium-lan-auth/security/firewall.md
generated/chat-medium-lan-auth/security/auth.md
generated/chat-medium-lan-auth/proxy/Caddyfile.example
generated/chat-medium-lan-auth/manifest.json
```

#### Validate generated output

```bash
python3 -m ai_server_generator validate generated/chat-medium-localhost
```

Validation checks:

- `manifest.json` exists and matches generated files.
- Docker Compose has localhost binding for localhost setups.
- LAN setups include auth and firewall artifacts.
- `.env` contains expected profile values.
- Scripts are executable.
- Memory budget is declared and within profile limits.

#### Explain a generated setup

```bash
python3 -m ai_server_generator explain generated/chat-medium-localhost
```

Expected output:

- Chosen setup/profile/access mode.
- Generated files and their purpose.
- Exact launch/stop/smoke-test commands.
- Security posture and limitations.
- Hardware assumptions.

#### Dry-run generation

```bash
python3 -m ai_server_generator generate \
  --setup chat \
  --profile medium \
  --access localhost \
  --out generated/chat-medium-localhost \
  --dry-run
```

Expected output:

- Planned files to be written.
- Whether the output directory exists.
- Warnings before write.
- No filesystem changes except optional logs if explicitly enabled.

## 5. Phased implementation backlog broken into sprint-sized tasks (each with acceptance criteria and Gate 1 commands), mapping how TASK-0001 output gets refactored into templates

This roadmap is plan/design only. The following backlog intentionally does not implement the generator in this task.

### Sprint 2 — Establish generator skeleton and template migration

#### Task 2.1 — Create Python CLI skeleton

Scope:

- Add `ai_server_generator/` package with CLI entry point.
- Add commands: `list setups`, `list profiles`, `generate --dry-run`, and `validate` stub.
- Do not yet replace root runtime files.

Acceptance criteria:

- `python3 -m ai_server_generator list profiles` prints `medium-fast`, `medium`, and `good`.
- `python3 -m ai_server_generator list setups` prints MVP setup names.
- `python3 -m ai_server_generator generate --dry-run ...` reports intended paths without writing final outputs.
- CLI returns non-zero for unknown setup/profile names.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator list profiles
python3 -m ai_server_generator list setups
```

#### Task 2.2 — Convert Sprint 1 profiles into canonical profile definitions

Mapping from TASK-0001 output:

- `config/profiles/medium-fast.env` becomes `profiles/medium-fast.yaml` plus `templates/env/profile.env.j2` expected values.
- `config/profiles/medium.env` becomes `profiles/medium.yaml` and remains the default.
- `config/profiles/good.env` becomes `profiles/good.yaml` with warning metadata for 12 GB hosts.
- `config/profiles/README.md` becomes a generated docs template or static product note explaining profile generation.

Acceptance criteria:

- Structured profiles include `ctx_size`, `batch_size`, `threads`, `n_predict`, `mem_limit`, `cpu_limit`, and user-facing description.
- Generated `.env` for each profile matches the current Sprint 1 values.
- Profile validation rejects missing required fields.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup chat --profile medium --access localhost --out generated/test-medium --dry-run
```

#### Task 2.3 — Convert Docker Compose baseline into template

Mapping from TASK-0001 output:

- Root `docker-compose.yml` becomes `templates/compose/llama-server.docker-compose.yml.j2`.
- Current localhost binding `127.0.0.1:${HOST_PORT:-8000}:8000` becomes a template branch controlled by access mode.
- Current container hardening options (`no-new-privileges`, `read_only`, `tmpfs`) remain default template content.
- Current memory and CPU limits become profile-driven template variables.

Acceptance criteria:

- Generated localhost Compose preserves localhost-only binding.
- Generated Compose includes model path, context, threads, batch, predict, metrics, continuous batching, volumes, memory limit, CPU limit, healthcheck, and container hardening.
- LAN Compose cannot be generated without auth/firewall inputs.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup chat --profile medium --access localhost --out generated/test-chat
python3 -m ai_server_generator validate generated/test-chat
```

#### Task 2.4 — Convert Sprint 1 scripts into generated script templates

Mapping from TASK-0001 output:

- `scripts/start_serving.sh` becomes `templates/scripts/start_serving.sh.j2`.
- `scripts/use_profile.sh` is replaced by generator selection; if kept, it becomes a compatibility wrapper that calls the generator or explains migration.
- `scripts/smoke_benchmark.sh` becomes `templates/scripts/smoke_benchmark.sh.j2`.
- Add generated `stop_serving.sh` and `validate_host.sh` templates.

Acceptance criteria:

- Generated scripts are executable.
- Generated start script no longer copies root `.env.example`; it assumes the generated directory already contains `.env`.
- Generated smoke benchmark targets the generated host/port and writes under generated `logs/benchmarks/`.
- Generated validate script checks Docker, Docker Compose, model file path placeholder, and memory-profile warning.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup chat --profile medium-fast --access localhost --out generated/test-scripts
python3 -m ai_server_generator validate generated/test-scripts
test -x generated/test-scripts/scripts/start_serving.sh
test -x generated/test-scripts/scripts/smoke_benchmark.sh
```

### Sprint 3 — Complete MVP generation and validation

#### Task 3.1 — Generate full chat localhost outputs

Acceptance criteria:

- `chat-localhost-medium`, `chat-localhost-medium-fast`, and `chat-localhost-good` can be generated.
- Each output includes Compose, `.env`, scripts, `manifest.json`, `README.md`, and `runbook.md`.
- `manifest.json` records generator version, template versions, setup, profile, access mode, model path, and timestamp.
- `good` profile includes explicit 12 GB memory warning.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup chat --profile medium --access localhost --out generated/chat-medium-localhost
python3 -m ai_server_generator validate generated/chat-medium-localhost
```

#### Task 3.2 — Add coding setup manifest and generated runbook

Acceptance criteria:

- `coding-localhost-medium` can be generated.
- Generated manifest distinguishes coding from chat while reusing the same safe serving baseline.
- Generated runbook explains model-family expectations and OpenAI-compatible endpoint usage for coding tools.
- No IDE-specific integration is promised unless generated as a documented later step.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup coding --profile medium --access localhost --out generated/coding-medium-localhost
python3 -m ai_server_generator validate generated/coding-medium-localhost
```

#### Task 3.3 — Add minimal RAG generation

Acceptance criteria:

- `rag-minimal-localhost` can be generated.
- Generated output includes `datasets/`, `indexes/`, and RAG runbook scaffolding.
- The generated manifest explicitly labels RAG as minimal and states whether retrieval is documentation-only or service-backed for that release.
- Memory budget remains within 12 GB target.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup rag-minimal --profile medium-fast --access localhost --out generated/rag-minimal-medium-fast
python3 -m ai_server_generator validate generated/rag-minimal-medium-fast
```

#### Task 3.4 — Add strict LAN opt-in generation

Mapping from TASK-0001 output:

- `docs/lan-safe-runbook.md` becomes `templates/docs/lan-safe-runbook.md.j2`.
- Current rule "localhost default, LAN opt-in" becomes a validator invariant.
- Current checklist expands into generated `security/lan-safe-runbook.md`, `security/firewall.md`, and `security/auth.md`.

Acceptance criteria:

- `--access lan` without `--auth` fails.
- `--access lan` without `--lan-allowlist` fails or prompts only in interactive mode.
- Generated LAN output includes auth and firewall documents.
- Localhost generation never emits LAN bind by default.
- Generated runbook states that unauthenticated LAN exposure is unsupported.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
! python3 -m ai_server_generator generate --setup chat --profile medium --access lan --out generated/invalid-lan-no-auth
python3 -m ai_server_generator generate --setup chat --profile medium --access lan --auth bearer-token --lan-allowlist 192.168.1.0/24 --out generated/chat-medium-lan-auth
python3 -m ai_server_generator validate generated/chat-medium-lan-auth
```

### Sprint 4 — Product hardening and examples

#### Task 4.1 — Add deterministic generation tests

Acceptance criteria:

- Same inputs generate identical file contents except approved timestamp fields.
- Dry-run reports match actual generated file list.
- Unknown setup/profile/access values return non-zero exit codes.
- Tests cover localhost and LAN security branches.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m pytest
```

#### Task 4.2 — Add example generated snapshots or documented examples

Acceptance criteria:

- Director decision recorded on whether examples are committed snapshots or generated-on-demand only.
- If committed, examples are clearly marked as generated and do not include secrets.
- If not committed, docs show commands to regenerate examples locally.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator generate --setup chat --profile medium --access localhost --out generated/example-chat-medium
python3 -m ai_server_generator validate generated/example-chat-medium
```

#### Task 4.3 — Update user documentation around generator-first workflow

Acceptance criteria:

- Root README or docs index describes clone -> generate -> launch.
- Sprint 1 root files are no longer presented as the canonical manual setup if generator outputs replace them.
- Documentation states localhost default and LAN opt-in requirements.
- Documentation states 12 GB RAM assumptions and limitations.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
python3 -m ai_server_generator list setups
python3 -m ai_server_generator list profiles
```

### Sprint 5 — Optional advanced families

#### Task 5.1 — Evaluate vision setup feasibility

Acceptance criteria:

- A research artifact identifies candidate model/runtime combinations, memory budget, and whether they fit the 12 GB target.
- If not feasible, vision remains explicitly deferred.
- If feasible, add only an experimental manifest gated behind `--experimental`.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
```

#### Task 5.2 — Evaluate GPU/iGPU acceleration profiles

Acceptance criteria:

- Research documents Linux driver prerequisites and runtime flags.
- Generator does not emit iGPU-specific flags unless prerequisites are selected and validated.
- CPU-safe path remains default.

Gate 1 commands:

```bash
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py plan check <task-id>
test -f .pm-harness/HARNESS-SPEC.md
```

## 6. Quality & security controls (config validation, secrets handling, localhost default/LAN opt-in, rollback, test strategy)

### Config validation controls

- Every setup/profile/access combination must be validated before files are written.
- Every generated output directory must include `manifest.json` recording:
  - generator version,
  - template version or checksum,
  - setup family,
  - profile,
  - access mode,
  - model path or model-family placeholder,
  - generation timestamp,
  - validation status.
- Validation must reject unknown setup names, unknown profiles, missing required profile fields, missing template variables, unsafe LAN combinations, and generated paths outside the repository output directory.
- Validation should warn, not necessarily fail, when `good` profile may pressure a 12 GB host.
- Generated Compose should be parsed or structurally checked enough to verify binding and service fields.

### Secrets handling

- Templates must never contain real secrets.
- Generated `.env` may contain placeholders, but should not generate committed credentials.
- LAN bearer tokens should be supplied by the user or generated locally only inside ignored generated outputs.
- If a token is generated, the runbook must tell the user where it was written and how to rotate it.
- `generated/` should be ignored by default to reduce accidental credential commits.
- Example outputs, if committed, must use obvious placeholders and pass a no-secret check.

### Localhost default and LAN opt-in

- Localhost is the default access mode.
- Localhost Compose must bind to `127.0.0.1:${HOST_PORT}:8000` or equivalent.
- LAN access must require explicit `--access lan`.
- LAN generation must require authentication selection.
- LAN generation must require firewall or allowlist information.
- LAN runbook must state that unauthenticated LAN exposure is unsupported.
- Validation must fail if a generated LAN setup lacks auth/firewall artifacts.
- Validation must fail if a generated localhost setup binds to `0.0.0.0` on the host.

### Rollback strategy

- Generate into new directories by default rather than overwriting current working outputs.
- If `--force` is later added, it should create a backup or require a clean generated directory.
- Each generated directory is self-contained and can be stopped independently with its generated stop script.
- Rollback is:
  ```bash
  cd generated/new-setup
  docker compose down
  cd ../previous-known-good-setup
  docker compose up -d
  ```
- Generated manifests support comparison between versions.

### Test strategy

- Unit tests:
  - Profile parsing and defaults.
  - Setup manifest parsing.
  - Access-mode validation.
  - Template variable completeness.
  - Output path safety.

- Golden/snapshot tests:
  - `chat-medium-localhost` output.
  - `coding-medium-localhost` output.
  - `rag-minimal-medium-fast-localhost` output.
  - Authenticated LAN output.

- Negative tests:
  - LAN without auth fails.
  - LAN without allowlist fails.
  - Unknown profile fails.
  - Vision without `--experimental` fails while vision is not MVP-supported.
  - Output path outside project fails.

- Smoke tests:
  - Generated localhost output validates.
  - Generated scripts are executable.
  - Docker Compose config can be checked where Docker Compose is available.
  - Runtime smoke benchmark remains optional because model file availability may vary.

- Harness gates for every implementation task:
  ```bash
  python3 .pm-harness/bin/harness.py validate
  python3 .pm-harness/bin/harness.py plan check <task-id>
  test -f .pm-harness/HARNESS-SPEC.md
  ```

### Product quality controls

- The generator must always print the next command the user should run.
- Generated runbooks must be written for a user operating on a Linux laptop, not for a cloud/server team.
- Hardware assumptions must be visible in every generated setup.
- Advanced or unvalidated setups must be labeled experimental.
- Existing Sprint 1 files should remain usable during migration, but product docs should increasingly point users to generator commands as soon as they exist.

## 7. Open decisions for the Director (list the choices needed to proceed)

1. **CLI packaging name**
   - Should the command remain `python3 -m ai_server_generator` for MVP, or should Sprint 2 package a console command such as `ai-server`?

2. **Template dependency policy**
   - Approve Python + Jinja2 as the generator implementation path, or require stdlib-only templating for zero Python dependencies?

3. **Generated output commit policy**
   - Should generated outputs be ignored by default under `generated/`, or should the repository commit curated generated examples for users to inspect?

4. **First MVP setup priority**
   - Should Sprint 2 prioritize `chat-localhost-medium` as the first end-to-end setup, or prioritize `coding-localhost-medium` because the project may serve coding workflows first?

5. **LAN auth mechanism for MVP**
   - Is a static bearer token acceptable for MVP LAN mode, with reverse proxy/OIDC/mTLS deferred, or should reverse-proxy auth be mandatory from the first LAN generator release?

6. **RAG MVP depth**
   - Should `rag-minimal` be documentation/scaffold-only in MVP, or should it include a real local embedding/vector-store service despite the 12 GB RAM target?

7. **Root Sprint 1 file migration policy**
   - During migration, should root `docker-compose.yml`, `config/profiles/*`, and `scripts/*` remain compatibility examples, or should they be removed/deprecated once generated equivalents exist?

8. **Vision support posture**
   - Should optional vision be explicitly out of MVP until hardware feasibility is proven, or should an experimental manifest be allowed early behind `--experimental`?

9. **GPU/iGPU acceleration posture**
   - Should the product stay CPU-first until after MVP, or should Sprint 3 include detection/research for Radeon Vega iGPU acceleration?

10. **Manifest format**
    - Prefer YAML for human-authored setup manifests and JSON for generated manifests, or use one format for both?
