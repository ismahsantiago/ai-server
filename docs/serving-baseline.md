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
     --access localhost
   ```

2. Generate a runnable workspace:

   ```bash
   python3 -m ai_server_generator generate \
     --preset ornith-9b \
     --profile medium \
     --access localhost \
     --out generated/ornith-medium-localhost \
     --force
   ```

3. Validate generated artifacts:

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

4. Start serving:

   ```bash
   ./generated/ornith-medium-localhost/scripts/start.sh
   ```

5. Health check:

   ```bash
   docker compose -f generated/ornith-medium-localhost/docker-compose.yml ps
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
