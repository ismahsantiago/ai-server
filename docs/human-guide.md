# Human guide: run ai-server with the generator-first workflow

This guide is the operator path from a repository clone to a local chat
endpoint. The supported exposure is localhost only.

## 1) Prepare the model

Install the Python dependency and place the selected GGUF file under the
repository-root `models/` directory:

```bash
python3 -m pip install -r requirements.txt
mkdir -p models
# Obtain an approved model through its official distribution channel.
# Example destination:
MODEL_PATH="$PWD/models/ornith-9b.gguf"
test -f "$MODEL_PATH"
sha256sum "$MODEL_PATH"
```

The generator resolves that repository-root path to an absolute host path.
Generated Compose mounts the same file read-only as `/models/model.gguf`.
Do not copy the model into the generated workspace.

## 2) Preview the scenario

List the available values if needed:

```bash
python3 -m ai_server_generator list models
python3 -m ai_server_generator list profiles
```

Preview a localhost scenario:

```bash
python3 -m ai_server_generator matrix \
  --preset ornith-9b \
  --profile medium \
  --access localhost \
  --model-path "$MODEL_PATH"
```

`matrix` reports `WARN` when a scenario fits its static planning assumptions
or `NO-GO` when it is refused. It never reports `GO`: it does not prove that
the model exists, Docker works, the model fits memory, or runtime targets are
met.

## 3) Generate and validate

From the repository root:

```bash
WORKSPACE=generated/ornith-medium-localhost

python3 -m ai_server_generator generate \
  --preset ornith-9b \
  --profile medium \
  --access localhost \
  --model-path "$MODEL_PATH" \
  --out "$WORKSPACE"

python3 -m ai_server_generator validate "$WORKSPACE" --tier host
```

The host tier adds model-file and Docker/Compose checks to structural
validation. Inspect `$WORKSPACE/manifest.json` to see the resolved host model
path, `/models/model.gguf` container path, exact image digest, generation
fingerprint, and helper commands.

Use a new output directory for regeneration. `--force` is limited to a
generator-owned workspace under `generated/`, but it still replaces that
workspace; back up operator changes first.

## 4) Start, smoke, and stop

The lifecycle actions are generated scripts, not generator subcommands. The
scripts resolve their own workspace and may be called from any directory:

```bash
"$WORKSPACE/scripts/start.sh"
"$WORKSPACE/scripts/smoke.sh"
python3 -m ai_server_generator validate "$WORKSPACE" --tier runtime
```

Send a direct request if desired:

```bash
curl -sS -X POST "http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"local","messages":[{"role":"user","content":"Say hello from local server"}],"max_tokens":64}'
```

When finished:

```bash
"$WORKSPACE/scripts/stop.sh"
```

## 5) Guided alternative

The wizard follows the same localhost contract:

```bash
python3 -m ai_server_generator wizard \
  --preset ornith-9b \
  --profile medium \
  --run no
```

It expects `models/<preset>.gguf`, generates
`generated/<preset>-<profile>-localhost/`, and leaves the lifecycle scripts
inside that workspace. Without a terminal, supply `--preset`, `--profile`, and
`--run`; the wizard does not start a server implicitly.

## 6) LAN status: planned and blocked

LAN serving is not an opt-in mode in the current product. Both `matrix` and
`generate` refuse `--access lan`, even if bearer-token and allowlist flags are
provided. This fail-closed state remains until an authenticated TLS gateway,
mechanically enforced client allowlist, and bypass tests exist.

Do not change the generated bind to `0.0.0.0`, forward or publish its port, or
treat the LAN runbook as an authorization exception. See
`docs/lan-safe-runbook.md` for the future acceptance criteria.

## 7) Troubleshooting

Run these checks in order:

```bash
python3 -m ai_server_generator list setups
python3 -m ai_server_generator list profiles
python3 -m ai_server_generator list models
python3 -m ai_server_generator validate "$WORKSPACE" --tier host
docker compose -f "$WORKSPACE/docker-compose.yml" ps
docker compose -f "$WORKSPACE/docker-compose.yml" logs --tail=100
```

Common failures:

- `unknown profile/setup`: use the exact value printed by `list`.
- `Decision: NO-GO` for LAN: this is the intended refusal, not a request for
  more flags.
- Missing model during host validation: verify the manifest's
  `host_model_path`; do not copy the file into the workspace.
- Missing generated files: generate into a new workspace or restore a known
  backup before using `--force`.
- No health response: inspect Compose status and service logs, then stop the
  stack if startup did not complete.

## Compatibility note

Legacy root files (`docker-compose.yml`, `scripts/`, `config/profiles/`) remain
compatibility examples. Canonical operation uses generated workspaces under
`generated/<preset-profile-access>/...`.
