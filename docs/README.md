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

3. **Generate**

   ```bash
   python3 -m ai_server_generator generate --preset ornith-9b --profile medium --access localhost --out generated/ornith-medium-localhost --force
   ```

4. **Validate**

   ```bash
   python3 -m ai_server_generator validate generated/ornith-medium-localhost
   ```

5. **Start (from generated workspace)**

   ```bash
   ./generated/ornith-medium-localhost/scripts/start.sh
   ```

## Legacy compatibility assets (non-canonical)

The root-level `docker-compose.yml`, `scripts/`, and `config/profiles/` remain
in-repo for compatibility/examples. Prefer the generated equivalents under
`generated/<preset-profile-access>/...` for normal operation.
