# Runbook — chat / medium / localhost

## Expanded configuration

- Setup: `chat`
- Profile: `medium`
- Access: `localhost`
- Preset alias: `ornith-9b`
- Preset name: `Ornith 1.0 (9B)` — agentic code specialist

- Capability tags: `code, agentic, tool-use`
- Memory guidance: Recommended: 7-9 GB RAM budget for stable local serving.

## Access model

Localhost-only access. The stack binds to `127.0.0.1:8000` and is not
reachable from the LAN. LAN generation is fail-closed because this repository
does not yet provide an authenticated TLS gateway, enforce a client allowlist,
or mechanically prove either control. Do not change the bind to `0.0.0.0` or
publish/forward this port. Treat LAN enablement as pending security engineering
work, not as a manual runbook exception.

The container runs as the explicit non-root UID/GID `65532:65532`, drops all
capabilities, uses `no-new-privileges`, a read-only root filesystem, bounded
PIDs/resources, and only a read-only model bind. Compatibility of that UID/GID
with the selected image still requires runtime validation before serving; the
generator's structural validation does not claim daemon or image verification.

## Operations

- Start: `./scripts/start.sh`
- Benchmark: `./scripts/smoke.sh`
- Host validation: `./scripts/validate.sh`
- Full script references: `./scripts/start_serving.sh`, `./scripts/smoke_benchmark.sh`, `./scripts/validate_host.sh`

## Model

- Host model path: `{PROJECT_ROOT}/models/ornith-9b.gguf`
- Container model path: `/models/model.gguf`

Place a real `.gguf` model before serving; the placeholder path is inert.
