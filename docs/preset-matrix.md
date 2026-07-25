# Model preset matrix and shorthand workflow

This project ships a preset catalog for concise generation and launch workflows.

## List available model presets

```bash
python3 -m ai_server_generator list models
```

Current stable aliases:

- `ornith-9b` → Ornith 1.0 (9B)
- `devstral-small-v25.07` → Devstral Small (v25.07)
- `qwen3-coder-7b` → Qwen 3 Coder (7B)
- `smollm3-3b` → SmolLM 3 (3B)
- `phi-4-14b` → Phi-4 (14B)

## Preview scenario go/no-go

Use `matrix` before generation to inspect resolved values and guardrails.

```bash
python3 -m ai_server_generator matrix \
  --preset ornith-9b \
  --profile medium \
  --access localhost
```

For LAN previews, include auth + allowlist to get `Decision: GO`:

```bash
python3 -m ai_server_generator matrix \
  --preset ornith-9b \
  --profile medium \
  --access lan \
  --auth bearer-token \
  --lan-allowlist 192.168.1.0/24
```

If LAN requirements are missing, the command returns `Decision: NO-GO`.

`Decision: GO` means only that the requested values pass static generator
guardrails. It does not verify that model weights exist, that Docker starts,
or that the model meets the stated memory, latency, or quality guidance.

## Generate with shorthand preset mode

`--preset` can coexist with explicit options. Explicit flags override preset defaults.

```bash
python3 -m ai_server_generator generate \
  --preset ornith-9b \
  --profile medium \
  --access localhost \
  --out generated/ornith-medium-localhost
```

Generate into a new directory by default. `--force` deletes an existing
generated directory and is not part of the recommended onboarding path.

Generated workspace includes concise helpers:

- `./scripts/validate.sh`
- `./scripts/start.sh`
- `./scripts/smoke.sh`

Expanded resolved config is written to both `manifest.json` and `runbook.md`.
