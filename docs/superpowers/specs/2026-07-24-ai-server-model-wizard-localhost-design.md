# Localhost Model Wizard (ai-server generator-first)

**Date:** 2026-07-24  
**Audience:** human operators of `ai-server` (local dev/lab)  
**Goal:** provide a friendlier, interactive way to select a model preset + runtime profile, generate a validated workspace, and optionally run the local server.

## 1) Context

The repo already supports a generator-first workflow via:

1. `python3 -m ai_server_generator matrix ...` (preview)
2. `python3 -m ai_server_generator generate ...` (render workspace)
3. `python3 -m ai_server_generator validate <generated_dir>` (contract checks)
4. `./generated/<...>/scripts/start.sh` (run)
5. `./generated/<...>/scripts/smoke.sh` (quick smoke)

This spec adds an **interactive wizard** that wraps those steps with guided prompts (localhost-only for now).

## 2) User requirements (what the wizard must do)

The wizard is intended to be used from the repo root.

### Wizard UX (agreed behavior)

1. **Model preset selection** (menu): operator chooses one of the stable preset aliases (e.g. `ornith-9b`, `qwen3-coder-7b`, `phi-4-14b`, etc.).
2. **Profile selection** (menu): operator chooses one of the available runtime profiles (`medium`, `medium-fast`, `good`).
3. **Access mode is fixed to localhost** (wizard does not offer LAN at this time).
4. **Output directory**:
   - Default: `generated/<preset>-<profile>-localhost`
   - Wizard asks if the operator wants to override the output path.
5. **If output directory already exists**:
   - Wizard asks whether to overwrite.
   - If yes, it uses the generator’s `--force`.
6. **Preflight model file check (hard fail)**:
   - For the selected preset alias `X`, the wizard expects `./models/X.gguf`.
   - If the file does not exist, the wizard fails with a clear message and asks the operator to add the file manually.
7. Run **matrix preview → generate → validate** for the resolved localhost scenario.
8. **After validate**, ask: “¿deseas correr el servidor? (SI/NO)”
   - If **NO**: do not start anything. The generated workspace scripts remain available.
   - If **SI**: run `./scripts/start.sh` and then run `./scripts/smoke.sh`.

## 3) Non-goals (explicitly out of scope)

- LAN support (bearer-token, allowlist) is not offered in this wizard version.
- No automatic downloading of model weights.
- No automatic tuning/quantization selection beyond preset+profile.

## 4) Inputs and outputs

### Inputs

- Model preset alias (wizard menu)
- Runtime profile (wizard menu)
- Output path (optional override)
- Overwrite confirmation (only if output path exists)
- Run server confirmation (SI/NO)

### Outputs

- A fully generated workspace under the chosen output directory:
  - `docker-compose.yml`, `.env`, `manifest.json`, `README.md`, `runbook.md`
  - `scripts/start.sh`, `scripts/validate.sh`, `scripts/smoke.sh`, etc.
- Validation result printed to stdout.

## 5) Operational details

### Default output path naming

`generated/<preset>-<profile>-localhost`

### Preflight rule (hard fail)

Expected model file: `./models/<preset_alias>.gguf`

If missing:

- wizard exits non-zero
- message explains what exact file is expected
- wizard does not attempt alternative model paths

### Matrix preview

The wizard should show the matrix preview output for the selected preset/profile/access.

If the preview would fail (e.g., invalid profile/setup), the wizard must exit with the error.

## 6) Acceptance criteria

1. **Local generation happy path**: selecting any supported preset + any supported profile generates and validates a workspace successfully.
2. **Hard fail on missing model**: if `./models/<preset_alias>.gguf` is missing, wizard fails before generation.
3. **Overwrite behavior**: if output dir exists, wizard can overwrite only when user confirms.
4. **Run path**:
   - SI: runs `start.sh` then `smoke.sh`.
   - NO: performs no runtime actions.
5. **Reproducibility**: the generated artifacts match what the underlying generator would produce for equivalent `matrix/generate/validate` flags.

## 7) Implementation notes (high level)

- Add a new `ai_server_generator` subcommand: `wizard`.
- Reuse existing generator primitives already implemented in the repo:
  - `matrix` logic (or `build_context`)
  - `render_workspace` (generate)
  - `validate_workspace` (validate)
- Use subprocess execution only for:
  - `./scripts/start.sh`
  - `./scripts/smoke.sh`

## 8) Testing plan (practical)

- Unit tests for non-interactive helper logic (e.g. default output path computation, expected model path calculation).
- Integration tests using `subprocess.run(..., input=...)` to simulate wizard answers via stdin.
