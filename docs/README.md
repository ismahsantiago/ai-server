# docs/

Operational runbooks and architecture notes.

- `human-guide.md`: step-by-step human operator workflow (quick setup, matrix, generate/validate/start, troubleshooting, quality checks).
- `repo-name-suggestions.md`: repository naming criteria, candidates, and recommended choice.
- `serving-baseline.md`: Docker-first local serving setup.
- `lan-safe-runbook.md`: localhost default + LAN opt-in hardening steps.
- `preset-matrix.md`: model preset catalog, shorthand generation, and matrix go/no-go preview.

## Canonical workflow (generator-first)

Use this sequence as the default path for Sprint 1 and onward:

1. **Clone**

   ```bash
   git clone <repo-url>
   cd ai-server
   ```

2. **Matrix**

   ```bash
   python3 -m ai_server_generator matrix --preset ornith-9b --profile medium --access localhost
   ```

   `GO` confirms static generator compatibility only, not runtime/model support.

3. **Generate**

   ```bash
   python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/ornith-medium-localhost
   ```

4. **Validate**

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

5. **Start (from generated workspace)**

   ```bash
   mkdir -p generated/ornith-medium-localhost/models
   cp models/ornith-9b.gguf generated/ornith-medium-localhost/models/
   cd generated/ornith-medium-localhost
   ./scripts/start.sh
   ```

Static validation does not confirm model visibility or Docker health. The
workspace-local model copy is required by the current generated Compose layout.

### Friendlier wrapper: wizard (localhost only)

For a more guided experience you can use:

```bash
python3 -m ai_server_generator wizard --preset ornith-9b --profile medium --run no
```

The wizard wraps the canonical `matrix → generate → validate` flow and leaves you with `generated/<preset>-<profile>-localhost/scripts/` helpers.

## Legacy compatibility assets (non-canonical)

The root-level `docker-compose.yml`, `scripts/`, and `config/profiles/` remain
in-repo for compatibility/examples. Prefer the generated equivalents under
`generated/<preset-profile-access>/...` for normal operation.
