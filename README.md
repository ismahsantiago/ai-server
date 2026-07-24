# ai-server

Generator-first local AI server workspace builder.

This repository is designed for humans who want a safe, reproducible way to run
local AI serving stacks without hand-authoring Docker and runtime files. The
canonical path is:

**clone -> matrix -> generate -> validate -> start**

## Purpose

- Generate runnable local serving workspaces from a small set of choices.
- Keep localhost as the default security posture.
- Require explicit controls for any LAN exposure.
- Preserve compatibility with legacy root files while making generated outputs
  the default operating path.

## Prerequisites

- Python 3.10+
- Docker + Docker Compose
- A local `.gguf` model file path (or placeholder path while scaffolding)

Install Python dependency:

```bash
python3 -m pip install -r requirements.txt
```

## 5-minute quick start

1. Preview a safe scenario:

   ```bash
   python3 -m ai_server_generator matrix --preset ornith-9b --profile medium --access localhost
   ```

2. Generate a workspace:

   ```bash
   python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/ornith-medium-localhost --force
   ```

3. Validate generated output:

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

4. Start from the generated workspace:

   ```bash
   ./generated/ornith-medium-localhost/scripts/start.sh
   ```

5. Send a quick chat completion request:

   ```bash
   curl -sS -X POST "http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{"model":"local","messages":[{"role":"user","content":"hello"}],"max_tokens":32}'
   ```

## Canonical workflow (generator-first)

Use this sequence for normal operation:

1. `matrix` to preview guardrails and GO/NO-GO.
2. `generate` to create a self-contained workspace under `generated/...`.
3. `validate` to verify required files and access posture.
4. `start` from generated scripts.
5. `smoke` and health checks.

## Safety defaults

- Localhost binding (`127.0.0.1`) is the default.
- LAN mode is opt-in and requires `--auth bearer-token` and
  `--lan-allowlist`.
- The generator rejects unsafe LAN combinations.

## Compatibility notes (legacy root files)

Root-level `docker-compose.yml`, `scripts/`, and `config/profiles/` remain for
compatibility/examples. Prefer generated equivalents under
`generated/<preset-profile-access>/...` for day-to-day use.

## Where to go next

- Human operations guide: `docs/human-guide.md`
- Repository naming options: `docs/repo-name-suggestions.md`
- Preset matrix details: `docs/preset-matrix.md`
- LAN hardening runbook: `docs/lan-safe-runbook.md`
- Serving baseline notes: `docs/serving-baseline.md`
- Docs index: `docs/README.md`
