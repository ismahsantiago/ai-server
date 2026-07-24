#!/usr/bin/env bash
set -euo pipefail

# Generated for setup=chat profile=medium access=localhost
# Preflight validation for the generated workspace (no Docker daemon required).

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(CDPATH='' cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${WORKSPACE}/.env"
fail=0

for f in docker-compose.yml .env manifest.json; do
  if [ ! -f "${WORKSPACE}/${f}" ]; then
    printf "Missing required file: %s\n" "$f" >&2
    fail=1
  fi
done

if grep -q '0.0.0.0:8000:8000' "${WORKSPACE}/docker-compose.yml"; then
  printf "localhost workspace unexpectedly binds to 0.0.0.0.\n" >&2
  fail=1
fi
if grep -qE '^(API_BEARER_TOKEN|LAN_ALLOWLIST)=' "${ENV_FILE}"; then
  printf "Unsupported LAN credential or policy found in localhost workspace.\n" >&2
  fail=1
fi
# GNU stat first (Linux); BSD stat (macOS) rejects -c and falls through to -f.
# The reverse order is wrong: GNU reads -f as --file-system and succeeds with
# verbose output, so the BSD form would never be reached on Linux.
env_mode="$(stat -c '%a' "${ENV_FILE}" 2>/dev/null || stat -f '%Lp' "${ENV_FILE}" 2>/dev/null || true)"
if [ "$env_mode" != "600" ]; then
  printf ".env must have mode 0600 (found %s).\n" "${env_mode:-unknown}" >&2
  fail=1
fi

MODEL_HOST_PATH="{PROJECT_ROOT}/models/ornith-9b.gguf"
if [ ! -f "${MODEL_HOST_PATH}" ] || [ ! -r "${MODEL_HOST_PATH}" ]; then
  printf "Model must exist as a readable regular file: %s\n" "${MODEL_HOST_PATH}" >&2
  fail=1
fi
case "${MODEL_HOST_PATH}" in
  *.gguf|*.GGUF) ;;
  *) printf "Model file extension must be .gguf: %s\n" "${MODEL_HOST_PATH}" >&2; fail=1 ;;
esac
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  printf "Docker Compose is unavailable.\n" >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  printf "Host validation failed.\n" >&2
  exit 1
fi

printf "Host validation passed.\n"
