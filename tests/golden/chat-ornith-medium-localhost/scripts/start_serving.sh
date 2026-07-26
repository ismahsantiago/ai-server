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

# GNU stat first (Linux); BSD stat (macOS) rejects -c and falls through to -f.
# The reverse order is wrong: GNU reads -f as --file-system and succeeds with
# verbose output, so the BSD form would never be reached on Linux.
env_mode="$(stat -c '%a' "${ENV_FILE}" 2>/dev/null || stat -f '%Lp' "${ENV_FILE}" 2>/dev/null || true)"
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

was_running=0
if compose ps --status running --services 2>/dev/null | grep -qx 'llama-server'; then
  was_running=1
fi

compose up -d
deadline=$((SECONDS + READINESS_TIMEOUT))
while [ "${SECONDS}" -lt "${deadline}" ]; do
  if curl --fail --silent --show-error --max-time 2 \
    "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    printf "Runtime healthy: http://127.0.0.1:8000/health\n"
    compose ps
    exit 0
  fi
  container_id="$(compose ps -q llama-server 2>/dev/null || true)"
  if [ -n "${container_id}" ]; then
    health_status="$(
      docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
        "${container_id}" 2>/dev/null || true
    )"
    case "${health_status}" in
      unhealthy|exited|dead)
        printf "Runtime entered terminal state: %s.\n" "${health_status}" >&2
        compose ps >&2 || true
        compose logs --tail 80 llama-server >&2 || true
        if [ "${was_running}" -eq 0 ]; then
          compose down --timeout 30 >&2 || true
        fi
        exit 1
        ;;
      starting|created|running|"")
        printf "Runtime state: %s; waiting for health endpoint.\n" "${health_status:-starting}" >&2
        ;;
    esac
  else
    printf "Runtime state: starting; container id not available yet.\n" >&2
  fi
  sleep "${READINESS_INTERVAL}"
done

printf "Runtime readiness timed out after %s seconds.\n" "${READINESS_TIMEOUT}" >&2
compose ps >&2 || true
compose logs --tail 80 llama-server >&2 || true
if [ "${was_running}" -eq 0 ]; then
  printf "Stopping the unhealthy stack started by this command.\n" >&2
  compose down --timeout 30 >&2 || true
else
  printf "The stack was already running; leaving it unchanged for diagnosis.\n" >&2
fi
exit 1
