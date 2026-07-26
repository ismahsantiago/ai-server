#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! docker info >/dev/null 2>&1; then
  printf '%s\n' "SKIPPED: no reachable Docker daemon" | python3 -m ai_server_generator.containercheck
  exit 0
fi
result="$(docker run --rm -v "${ROOT}:/w" -w /w --memory=2g python:3-slim python3 -m ai_server_generator doctor --no-write --format json)"
printf '%s' "${result}" | python3 -m ai_server_generator.containercheck
