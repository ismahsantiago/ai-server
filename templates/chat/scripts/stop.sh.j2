#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(CDPATH='' cd -- "${SCRIPT_DIR}/.." && pwd)"
STOP_TIMEOUT="${AI_SERVER_STOP_TIMEOUT_SECONDS:-30}"

case "${STOP_TIMEOUT}" in
  ''|*[!0-9]*) printf "AI_SERVER_STOP_TIMEOUT_SECONDS must be a positive integer.\n" >&2; exit 2 ;;
  0) printf "AI_SERVER_STOP_TIMEOUT_SECONDS must be greater than zero.\n" >&2; exit 2 ;;
esac

exec docker compose --project-directory "${WORKSPACE}" \
  -f "${WORKSPACE}/docker-compose.yml" down --timeout "${STOP_TIMEOUT}"
