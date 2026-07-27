# Next-instance server handoff

## Purpose and next event

The next event is to clone this repository onto the intended server and resume
the same project with an independent instance from the same AI provider and
model family. The exercise is intended to test continuity between equivalent AI
instances and to capture operational learning reproducibly.

The live checkout and its executable contracts outrank summaries, chat history,
and remembered intent. Do not claim that a GGUF, container runtime, endpoint, or
benchmark works until that result has been produced on the server and recorded
at the corresponding evidence tier.

## Current evidence boundary

The repository contains generator, validation, unit-test, and prior structural
evidence. It does **not** currently contain an authorized GGUF or verified
server-host inference/benchmark result for this next event. Treat every
GGUF/runtime/benchmark check below as `not-run` until the new server produces
and records it. LAN serving is not an available capability.

## Authority map

- `AGENTS.md` activates the project instructions for Codex-compatible agents.
- `CLAUDE.md`, `.claude/`, and `.opencode/` provide native activation and routing
  pointers; their authority remains the matching skill under
  `.pm-harness/teams/`.
- `.pm-harness/HARNESS-SPEC.md` is the normative lifecycle contract.
- `.pm-harness/state/` and `.pm-harness/plans/` are append-only task history and
  approved execution plans.
- `.pm-harness/wiki/` is the first knowledge source; code and current command
  behavior win if documentation has drifted.
- `.pm-harness/standards/GATES.md` defines quality gates.

`.pm-harness/` belongs to this repository and this project only. Do not copy or
reuse its state, memory, or authority in another project. A missing `.codex/`
directory is intentional unless a real project-local Codex surface is
materialized; do not fabricate one.

## Portable inventory and forbidden state

The portability packet is deliberately source-only:

- `.pm-harness/` is the coherent same-project governance corpus: contracts,
  CLI, adapters, schemas, standards, skills, teams, plans, append-only state,
  ceremonies, memory, and wiki.
- `AGENTS.md` and `CLAUDE.md` are root activation bridges.
- `.claude/skills/pm/` contains 17 portable files: the plugin manifest, root
  skill, eight roster-agent pointers, and seven command routers.
- `.opencode/` contains 16 portable Markdown routers: one activation skill,
  eight roster-agent pointers, and seven commands, plus its repository-local
  ignore contract. Package metadata and installed dependencies are unnecessary
  for these Markdown surfaces.
- `.env.example` is an intentional sanitized compatibility template containing
  only non-secret profile, localhost port, container placeholder-model path,
  and resource defaults.
- This handoff and the operator documentation are portable source material.
- `.codex/` is intentionally absent in this checkout; absence is not an
  installation failure.

Forbidden host/runtime state includes `.claude/settings.local.json` and nested
permissions, credentials, tokens, authentication data, sessions/history, logs,
caches, `.opencode/node_modules/` and package/lock metadata, harness bytecode or
runtime residue, real `.env` files, secrets, private keys/certificates, model
weights, generated workspaces, build/install outputs, runtime evidence, and
raw sensitive host/network data. Never recreate an excluded path merely to make
the two hosts look alike.

## First session: clone, inspect, and bootstrap

Replace `<repository-url>` with the authorized remote:

```bash
git clone <repository-url> ai-server
cd ai-server

git status --short
git log -1 --format='%H %cI %s'
test -f AGENTS.md
test -f .pm-harness/HARNESS-SPEC.md
test ! -e .codex
test ! -e .claude/settings.local.json
test ! -e .opencode/node_modules

python3 --version
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --require-hashes --requirement requirements.lock
python -m pip install --no-build-isolation --no-deps .
python -m pip check

docker --version
docker compose version
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py agents check
python3 .pm-harness/bin/harness.py wiki check
python3 -m unittest
```

A missing prerequisite is a blocker to record, not permission to silently
install host services, regenerate governed files, or weaken a gate.

## Governed resume protocol

1. Read `AGENTS.md`, this handoff, `.pm-harness/HARNESS-SPEC.md`, and
   `.pm-harness/standards/GATES.md`.
2. Inspect `git status`, the current commit, `.pm-harness/state/`, and the
   approved plan for any active task. Do not infer status from a prior chat.
3. Ask the PM Orchestrator first for product work, ceremonies, or delegation.
   In guided autonomy, obtain Director kickoff approval before creating tasks.
4. Execute each task only against its approved
   `.pm-harness/plans/<TASK-id>.plan.md`. Record deviations with `plan amend`;
   never rewrite approved plan history.
5. Write durable learning only through the owning agent's memory store. Do not
   write another agent's memory or transition a task owned by another agent.

Use CLI help before mutating state:

```bash
python3 .pm-harness/bin/harness.py plan amend --help
python3 .pm-harness/bin/harness.py state transition --help
python3 .pm-harness/bin/harness.py memory add --help
```

## Authorized-GGUF server path

Model weights are not part of Git. Obtain a specifically authorized GGUF
through its official distribution channel, keep it under the repository-root
`models/` directory, and record its basename and SHA-256 without committing the
weight:

```bash
mkdir -p models
MODEL="$PWD/models/<authorized-model>.gguf"
test -f "$MODEL"
MODEL_SHA256="$(sha256sum "$MODEL" | awk '{print $1}')"
printf 'model=%s\nsha256=%s\n' "$(basename "$MODEL")" "$MODEL_SHA256"

PRESET=smollm3-3b
PROFILE=medium-fast
WORKSPACE="generated/${PRESET}-${PROFILE}-server-test"

python -m ai_server_generator doctor \
  --models-path "$PWD/models" \
  --out artifacts/host-profile.json
python -m ai_server_generator matrix \
  --preset "$PRESET" --profile "$PROFILE" --access localhost \
  --model-path "$MODEL"
python -m ai_server_generator generate \
  --preset "$PRESET" --profile "$PROFILE" --access localhost \
  --model-path "$MODEL" --out "$WORKSPACE"
python -m ai_server_generator validate "$WORKSPACE" --tier host
```

The generator resolves the repository-root model to an absolute host path and
the generated Compose file bind-mounts it read-only at
`/models/model.gguf`. Do not copy it into the generated workspace.

`matrix` emits static planning evidence (`WARN` or `NO-GO`), never runtime
proof. Structural validation checks generated contracts. Host validation adds
local prerequisites and model visibility. Neither proves inference success.
Only after the host tier passes, collect runtime evidence:

```bash
"$WORKSPACE/scripts/start.sh"
python -m ai_server_generator validate "$WORKSPACE" --tier runtime
"$WORKSPACE/scripts/smoke.sh"
"$WORKSPACE/scripts/stop.sh"
```

These lifecycle actions are generated workspace scripts, not
`ai_server_generator` subcommands. Root Compose and root `scripts/` are
compatibility examples, not the canonical server path.

## Operational-learning capture contract

For every attempt, record the following in a task-owned, sanitized Markdown or
JSON evidence artifact:

- UTC timestamp and exact commit SHA;
- sanitized provider/model-family label, never account or session identifiers;
- host OS, CPU/RAM observation scope, Python, Docker, and Compose versions;
- authorized GGUF basename and SHA-256, never the weight itself;
- preset, profile, workspace path, image digest, and relevant configuration;
- exact commands, literal exit codes, and sanitized evidence/output paths;
- each statement classified as `fact`, `decision`, or `hypothesis`;
- each result classified as `structural`, `host`, or `runtime` evidence;
- failures, recovery actions, and the result of each recovery attempt;
- benchmark method: warm-up, prompt/workload, repetitions, context and output
  limits, elapsed-time method, latency/throughput units, and host load.

Record facts even when they contradict expectations. Preserve approved plans
and task histories append-only. A deviation requires an approved plan
amendment. A durable project fact or decision belongs in the owning agent's
memory through `harness.py memory add`, with the supporting artifact path in
the body; raw logs do not belong in memory.

Never record or commit provider tokens, credentials, sessions/history,
machine-local permissions, model weights, private keys/certificates, raw
sensitive host/network identifiers, `.env` files, runtime caches, or
`node_modules`. Sanitize evidence before sharing it.

## Safety and failure recovery

- LAN remains unauthorized and fail-closed. Do not use `--access lan`, bind to
  `0.0.0.0`, forward/publish the port, or tunnel the service.
- Do not treat `WARN`, a host `FIT`, successful generation, or a healthy Docker
  daemon as proof that inference or performance targets pass.
- If bootstrap or validation fails, preserve the command, exit code, sanitized
  error, evidence tier, and attempted recovery. Escalate after the governing
  role's bounded attempts; do not bypass the contract.
- If a secret or credential is found, stop. Do not print or commit it; route
  revocation/rotation and security review before continuing.
- Before regeneration, preserve operator changes. Prefer a new workspace;
  `--force` is limited to generator-owned outputs but still replaces content.

## End-of-session checklist

- Record UTC time, commit SHA, task/status, commands, exit codes, and sanitized
  evidence paths.
- Separate facts, decisions, and hypotheses; label every result by evidence
  tier and mark unrun checks `not-run`.
- Record failures and recovery outcomes; do not convert absence of evidence
  into a pass.
- Add only durable learning to the owning agent's memory and keep task/plan
  history append-only.
- Stop the generated workspace and confirm no unauthorized listener remains.
- Run the task's required gates plus `git diff --check`.
- Inspect `git status` and staged filenames for credentials, weights, logs,
  caches, local permissions, and unrelated changes.
- Leave the next instance a concise continuation note naming the next action
  and any blocker without relying on chat history.
