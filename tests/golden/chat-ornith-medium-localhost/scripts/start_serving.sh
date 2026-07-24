#!/usr/bin/env bash
set -euo pipefail

# Generated for setup=chat profile=medium access=localhost

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(CDPATH='' cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${WORKSPACE}/.env"
READINESS_TIMEOUT="${AI_SERVER_READINESS_TIMEOUT_SECONDS:-120}"
READINESS_INTERVAL="${AI_SERVER_READINESS_INTERVAL_SECONDS:-2}"

case "${READINESS_TIMEOUT}:${READINESS_INTERVAL}" in
  *[!0-9:]*|:*|*:|0:*|*:0) printf "Readiness timeout and interval must be positive integers.\n" >&2; exit 2 ;;
esac

if [ ! -f "${ENV_FILE}" ]; then
  printf "No .env found in generated workspace.\n" >&2
  exit 1
fi

env_mode="$(stat -f '%Lp' "${ENV_FILE}" 2>/dev/null || stat -c '%a' "${ENV_FILE}" 2>/dev/null || true)"
if [ "$env_mode" != "600" ]; then
  printf ".env must have mode 0600 before startup (found %s).\n" "${env_mode:-unknown}" >&2
  exit 1
fi
if grep -qE '^(API_BEARER_TOKEN|LAN_ALLOWLIST)=' "${ENV_FILE}"; then
  printf "LAN credentials/policy are unsupported; regenerate a localhost workspace.\n" >&2
  exit 1
fi

"${SCRIPT_DIR}/validate_host.sh"

compose() {
  docker compose --project-directory "${WORKSPACE}" -f "${WORKSPACE}/docker-compose.yml" "$@"
}

compose up -d
deadline=$((SECONDS + READINESS_TIMEOUT))
while [ "${SECONDS}" -lt "${deadline}" ]; do
  if curl --fail --silent --show-error --max-time 2 \
    "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    printf "Runtime healthy: http://127.0.0.1:8000/health\n"
    compose ps
    exit 0
  fi
  sleep "${READINESS_INTERVAL}"
done

printf "Runtime readiness timed out after %s seconds.\n" "${READINESS_TIMEOUT}" >&2
compose ps >&2 || true
compose logs --tail 80 llama-server >&2 || true
exit 1
