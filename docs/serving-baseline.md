# Docker-first Serving Baseline (Sprint 1)

## Objective

Provide a reproducible local serving baseline with an OpenAI-compatible endpoint,
using generator output as the canonical runtime path.

## Canonical runtime

- Runtime: `ghcr.io/ggerganov/llama.cpp:server`
- Canonical compose path: `generated/<preset-profile-access>/docker-compose.yml`
- Endpoint: `POST /v1/chat/completions`
- Default network binding: `127.0.0.1:${HOST_PORT}` (localhost-only)

## Quick start

1. Preview the resolved scenario:

   ```bash
   python3 -m ai_server_generator matrix \
     --preset ornith-9b \
     --profile medium \
     --access localhost \
     --model-path "$PWD/models/ornith-9b.gguf"
   ```

   `matrix` emits `WARN` when the scenario fits static planning assumptions or
   `NO-GO` when it is refused. It never emits a passing `GO`; this is structural
   planning evidence, not measured host or runtime support.

2. Generate a runnable workspace:

   ```bash
   python3 -m ai_server_generator generate \
     --preset ornith-9b \
     --profile medium \
     --access localhost \
     --model-path "$PWD/models/ornith-9b.gguf" \
     --out generated/ornith-medium-localhost
   ```

3. Validate generated artifacts:

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

4. Start serving:

   ```bash
   WORKSPACE=generated/ornith-medium-localhost
   "$WORKSPACE/scripts/start.sh"
   ```

Keep the authorized GGUF under the repository-root `models/` directory.
Generated Compose bind-mounts that absolute host path read-only at
`/models/model.gguf`; do not copy the weight into the workspace. Structural
validation does not start Docker or prove model visibility,
memory/latency/quality, or inference. Use `--tier host` for host prerequisites
and `--tier runtime` only after startup for live endpoint evidence.

5. Health check:

   ```bash
   docker compose -f "$WORKSPACE/docker-compose.yml" ps
   curl -sS http://127.0.0.1:${HOST_PORT:-8000}/health
   ```

6. OpenAI-compatible smoke request:

   ```bash
   curl -sS -X POST "http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{"model":"local","messages":[{"role":"user","content":"hello"}],"max_tokens":32}'
   ```

## Compatibility-only legacy assets

These root assets are kept as compatibility/examples and are not canonical:

- `docker-compose.yml` → use `generated/<preset-profile-access>/docker-compose.yml`
- `scripts/use_profile.sh` → use generated `config/profiles/*.env` + generated scripts
- `scripts/start_serving.sh` → use `generated/<preset-profile-access>/scripts/start.sh`
- `scripts/smoke_benchmark.sh` → use `generated/<preset-profile-access>/scripts/smoke.sh`
- `config/profiles/*.env` → use generated profile env files in the workspace

## Balanced profile presets (generator outputs)

- `medium-fast`: lower memory and faster response target.
- `medium`: default balance for quality/speed under 12 GB hosts.
- `good`: higher quality target with increased context/memory budget.

Profiles are emitted into the generated workspace and consumed by generated
launch scripts.

`matrix`, `generate`, and `validate` are generator commands. `start.sh`,
`smoke.sh`, and `stop.sh` are generated workspace scripts; similarly named
root scripts remain compatibility examples. This document describes the
runtime checks to perform and does not claim that an authorized GGUF, live
endpoint, or benchmark has already been verified.
