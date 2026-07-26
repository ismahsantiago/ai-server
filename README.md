# ai-server

Generator-first local AI server workspace builder.

This repository is designed for humans who want a safe, reproducible way to run
local AI serving stacks without hand-authoring Docker and runtime files. The
canonical path is:

**clone -> matrix -> generate -> validate -> start**

## Purpose

- Generate runnable local serving workspaces from a small set of choices.
- Keep localhost as the only supported security posture.
- Refuse to generate LAN exposure until real controls exist.
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

   `matrix` reports `WARN` or `NO-GO`; it never reports a passing `GO`, because
   every input to the decision is a static planning assumption. `WARN` means the
   scenario fits nominal limits on paper. It does not prove that model weights
   are present, Docker can start, or the model fits the host memory/latency
   target. `NO-GO` means the scenario is refused outright.

2. Generate a workspace:

   ```bash
   python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/ornith-medium-localhost
   ```

3. Validate generated output:

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

4. Start from the generated workspace:

   ```bash
   generated/ornith-medium-localhost/scripts/start.sh
   ```

   The generated Compose bind-mounts the model read-only from its absolute host
   path, so no copy into the workspace is needed. The scripts resolve their own
   workspace, so they can be run from any working directory. Stop the stack with
   `scripts/stop.sh`.

   Default `validate` checks structure only. Use `--tier host` to also check the
   model file and Docker/Compose, and `--tier runtime` to additionally check a
   live health endpoint. Use a new output directory for regeneration; `--force`
   replaces an existing workspace and only works on a directory this generator
   owns.

5. Send a quick chat completion request:

   ```bash
   curl -sS -X POST "http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{"model":"local","messages":[{"role":"user","content":"hello"}],"max_tokens":32}'
   ```

## Canonical workflow (generator-first)

Use this sequence for normal operation:

1. `matrix` to preview guardrails and the WARN/NO-GO decision.
2. `generate` to create a self-contained workspace under `generated/...`.
3. `validate` to verify required files and access posture.
4. `start` from generated scripts.
5. `smoke` and health checks, then `stop`.

### Guided alternative

`wizard` runs that whole sequence interactively — it prompts for a preset and
profile, checks that `./models/<preset>.gguf` exists, then generates, validates,
and optionally starts and smokes the workspace:

```bash
python3 -m ai_server_generator wizard
```

Pass `--preset`, `--profile`, and `--run yes|no` to run it unattended. Without a
terminal the wizard never blocks on a prompt: it requires those flags and will
not start a server on its own.

Relative `--out` paths are resolved against the repository root, not your
current directory, and must stay inside `generated/`.

## Safety defaults

- Localhost binding (`127.0.0.1`) is the only supported exposure.
- `--access lan` is refused. LAN serving stays fail-closed until this repository
  ships an authenticated TLS gateway that mechanically enforces a client
  allowlist. Do not port-forward or publish a generated workspace to reach it
  from another machine.
- `--auth bearer-token` is refused, and no credential is generated or written.
  A localhost-only service has no transport to protect a bearer token on.
- `--lan-allowlist` is refused rather than recorded, so no generated file can
  claim a network policy that nothing enforces.
- The container runs non-root with all capabilities dropped, a read-only root
  filesystem, `no-new-privileges`, and bounded CPU/memory/PID limits. The model
  is mounted read-only.

## Capability status

What this repository actually does today, so nothing has to be inferred from
the help text. `Refused` means the generator rejects the input by design rather
than silently producing something that does not work.

| Capability | Status | Notes |
|---|---|---|
| `list profiles \| setups \| models` | Implemented | `chat` is the only real setup; profiles are `medium-fast`, `medium`, `good`. |
| `matrix` scenario preview | Implemented | Static planning only; reports `WARN` or `NO-GO`, never `GO`. |
| `generate --access localhost` | Implemented | Output confined to a strict descendant of `generated/`. |
| `wizard` | Implemented | Interactive and unattended (`--preset/--profile/--run`). |
| `validate --tier structure` | Implemented | Files, manifest, posture, Compose invariants. No host or runtime check. |
| `validate --tier host` | Implemented | Adds model file and Docker/Compose checks. |
| `validate --tier runtime` | Implemented | Adds a live `/health` probe. Requires a running stack. |
| Generated `start`/`stop`/`smoke`/`validate` scripts | Implemented | Run from any working directory. |
| Backup / restore / rollback | Implemented | `scripts/backup_workspace.sh`, `restore_workspace.sh`, `rollback_workspace.sh`. |
| Image pinned by digest + SBOM | Implemented | `sbom.json`; refresh with `scripts/resolve_image_digest.sh` and `scripts/generate_sbom.py`. |
| `generate --access lan` | **Refused** | No authenticated TLS gateway or enforced allowlist exists. |
| `--auth bearer-token` | **Refused** | No credential is generated or stored. |
| `--lan-allowlist` | **Refused** | Rejected rather than recorded as an unenforced claim. |
| Latency/throughput as a release gate | Planned | `smoke` measures and reports, but nothing gates on the numbers. |
| Setups beyond `chat` | Planned | The template tree supports more; only `chat` is defined. |
| GPU / accelerated profiles | Planned | Current profiles are CPU-oriented. |

## Backup, restore, and rollback

Generated workspaces are cheap to recreate, but a workspace you have tuned by
hand is not. Model weights are never included: they live outside the workspace
and are mounted read-only.

```bash
# Archive a workspace with a checksum (defaults to backups/)
scripts/backup_workspace.sh generated/ornith-medium-localhost

# Restore it; the checksum is verified before anything is written
scripts/restore_workspace.sh backups/<archive>.tar.gz generated/ornith-medium-localhost

# Undo a --force regeneration using the copy the generator set aside
scripts/rollback_workspace.sh --list generated/ornith-medium-localhost
scripts/rollback_workspace.sh generated/ornith-medium-localhost
```

Restore and rollback both preserve whatever they replace, so either can be
undone. Validate a recovered workspace before starting it.

## Supply chain

The serving image is pinned by digest in `ai_server_generator/render.py`, and
the validator rejects any workspace whose image is not that exact reference.
`sbom.json` inventories the pinned Python dependencies and the image.

```bash
scripts/resolve_image_digest.sh          # read the registry's current digest
python3 scripts/generate_sbom.py         # refresh sbom.json after a pin change
python3 scripts/update_golden_fixture.py # refresh the generated-output fixture
```

CI fails if `sbom.json` or the golden fixture is stale, so a pin or template
change cannot land without the evidence being regenerated alongside it.

## Compatibility notes (legacy root files)

Root-level `docker-compose.yml`, `scripts/`, and `config/profiles/` remain for
compatibility/examples. Prefer generated equivalents under
`generated/<preset-profile-access>/...` for day-to-day use.

## Where to go next

- Human operations guide: `docs/human-guide.md`
- Repository naming options: `docs/repo-name-suggestions.md`
- Preset matrix details: `docs/preset-matrix.md`
- Hardware tier product definition: `docs/hardware-tiers.md`
- LAN hardening runbook: `docs/lan-safe-runbook.md`
- Serving baseline notes: `docs/serving-baseline.md`
- Docs index: `docs/README.md`
