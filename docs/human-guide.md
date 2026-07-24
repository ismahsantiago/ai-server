# Human guide: run ai-server with the generator-first workflow

This guide is for human operators who want a practical command path from clone
to a local chat endpoint.

## 1) Quick local chat setup

### Optional: use the interactive wizard (localhost only)

If you have the preset model weight file present at `./models/<preset>.gguf`,
you can run:

```bash
python3 -m ai_server_generator wizard \
  --preset ornith-9b \
  --profile medium \
  --run no
```

It will generate + validate into `generated/<preset>-<profile>-localhost/`
and leave you with `scripts/start.sh` and `scripts/smoke.sh`.

From repository root:

```bash
python3 -m pip install -r requirements.txt
python3 -m ai_server_generator matrix --preset ornith-9b --profile medium --access localhost
python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/ornith-medium-localhost --force
python3 -m ai_server_generator validate generated/ornith-medium-localhost
./generated/ornith-medium-localhost/scripts/start.sh
```

Test the endpoint:

```bash
curl -sS -X POST "http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"local","messages":[{"role":"user","content":"Say hello from local server"}],"max_tokens":64}'
```

## 2) Preset matrix preview

Use matrix before generation to confirm GO/NO-GO and resolved inputs.

List available model presets:

```bash
python3 -m ai_server_generator list models
```

Preview a localhost scenario:

```bash
python3 -m ai_server_generator matrix --preset qwen3-coder-7b --profile medium --access localhost
```

Preview a guarded LAN scenario:

```bash
python3 -m ai_server_generator matrix --preset ornith-9b --profile medium --access lan --auth bearer-token --lan-allowlist 192.168.1.0/24
```

If required LAN controls are missing, matrix returns `Decision: NO-GO`.

## 3) Generate -> validate -> start flow (canonical)

Use this as your standard operating path:

```bash
python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/ornith-medium-localhost --force
python3 -m ai_server_generator validate generated/ornith-medium-localhost
./generated/ornith-medium-localhost/scripts/validate.sh
./generated/ornith-medium-localhost/scripts/start.sh
./generated/ornith-medium-localhost/scripts/smoke.sh
```

Health check:

```bash
docker compose -f generated/ornith-medium-localhost/docker-compose.yml ps
curl -sS http://127.0.0.1:${HOST_PORT:-8000}/health
```

## 4) LAN guarded usage (opt-in only)

LAN mode requires both auth and allowlist controls.

```bash
python3 -m ai_server_generator matrix --preset ornith-9b --profile medium --access lan --auth bearer-token --lan-allowlist 192.168.1.0/24
python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access lan --auth bearer-token --lan-allowlist 192.168.1.0/24 --out generated/ornith-medium-lan --force
python3 -m ai_server_generator validate generated/ornith-medium-lan
```

Then review and enforce security steps in `docs/lan-safe-runbook.md` before
starting LAN-exposed services.

## 5) Troubleshooting quick checks

If something fails, run these quick checks in order:

```bash
python3 -m ai_server_generator list setups
python3 -m ai_server_generator list profiles
python3 -m ai_server_generator list models
python3 -m ai_server_generator validate generated/ornith-medium-localhost
docker compose -f generated/ornith-medium-localhost/docker-compose.yml ps
```

Common failure patterns:

- `ERROR: unknown profile/setup`: check `list profiles` / `list setups` names.
- `Decision: NO-GO` for LAN: provide both `--auth bearer-token` and
  `--lan-allowlist`.
- Validation errors for missing files: regenerate with `--force` into the same
  output directory.
- No health response: check Docker status and generated compose service logs.

## 6) How to know if we are going well

Use this command set as a quality signal pack:

```bash
python3 -m unittest
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py wiki check
python3 .pm-harness/bin/harness.py changelog check --task TASK-0005
```

For this task's plan adherence:

```bash
python3 .pm-harness/bin/harness.py plan check TASK-0005
```

Green exits across these checks indicate docs, harness state, and verification
gates are aligned.

## Compatibility note

Legacy root files (`docker-compose.yml`, `scripts/`, `config/profiles/`) remain
for compatibility/examples. Canonical operation is always generated workspaces
under `generated/<preset-profile-access>/...`.
