# docs/

Operational runbooks and architecture notes.

- `next-instance-server-handoff.md`: clone/bootstrap, governed resume, authorized-GGUF runtime path, and operational-learning capture contract for the next independent AI instance.
- `human-guide.md`: step-by-step human operator workflow (quick setup, matrix, generate/validate/start, troubleshooting, quality checks).
- `repo-name-suggestions.md`: repository naming criteria, candidates, and recommended choice.
- `serving-baseline.md`: Docker-first local serving setup.
- `lan-safe-runbook.md`: localhost default + LAN opt-in hardening steps.
- `preset-matrix.md`: model preset catalog, shorthand generation, and matrix go/no-go preview.
- `hardware-tiers.md`: product definition of what a given machine can serve.

## Canonical workflow (generator-first)

Use this sequence as the default path for Sprint 1 and onward:

1. **Clone**

   ```bash
   git clone <repo-url>
   cd ai-server
   ```

2. **Matrix**

   ```bash
   MODEL_PATH="$PWD/models/ornith-9b.gguf"
   python3 -m ai_server_generator matrix \
     --preset ornith-9b --profile medium --access localhost \
     --model-path "$MODEL_PATH"
   ```

   `matrix` emits `WARN` for a scenario that fits static planning assumptions or
   `NO-GO` for a refused scenario. It never emits a passing `GO`, and neither
   result proves host or runtime support.

3. **Generate**

   ```bash
   python3 -m ai_server_generator generate \
     --preset ornith-9b --profile medium --access localhost \
     --model-path "$MODEL_PATH" \
     --out generated/ornith-medium-localhost
   ```

4. **Validate**

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

5. **Start (from generated workspace)**

   ```bash
   WORKSPACE=generated/ornith-medium-localhost
   "$WORKSPACE/scripts/start.sh"
   ```

Keep the authorized model under the repository-root `models/` directory and
pass its path with `--model-path` when generating. Generated Compose
bind-mounts that host file read-only; do not copy it into the workspace.
Structural validation does not confirm model visibility or Docker health.
`--tier host` checks those host prerequisites, while `--tier runtime` requires
a running endpoint. Only the runtime tier and smoke request are runtime
evidence.

### Friendlier wrapper: wizard (localhost only)

For a more guided experience you can use:

```bash
python3 -m ai_server_generator wizard --preset ornith-9b --profile medium --run no
```

The wizard wraps the generator commands `matrix → generate → validate` and
leaves lifecycle actions as generated
`generated/<preset>-<profile>-localhost/scripts/` helpers. Start, smoke, and
stop are scripts, not generator subcommands.

## Legacy compatibility assets (non-canonical)

The root-level `docker-compose.yml`, `scripts/`, and `config/profiles/` remain
in-repo for compatibility/examples. Prefer the generated equivalents under
`generated/<preset-profile-access>/...` for normal operation.
