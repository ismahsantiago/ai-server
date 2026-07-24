#!/usr/bin/env bash
# COMPATIBILITY EXAMPLE (legacy root helper)
# Canonical equivalent: generated/<preset-profile-access>/scripts/smoke.sh
set -euo pipefail

TS="$(date -u +%Y%m%d-%H%M%S)"
OUT="logs/benchmarks/smoke-benchmark-${TS}.md"
PROFILE="${PROFILE_NAME:-unknown}"

mkdir -p logs/benchmarks

LATENCY_MS="placeholder"
MEMORY_MB="placeholder"
HTTP_STATUS="not-tested"

if command -v curl >/dev/null 2>&1; then
  TMP_JSON="$(mktemp)"
  if curl -sS -o "$TMP_JSON" -w "%{http_code}" \
    -X POST "http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"model":"local","messages":[{"role":"user","content":"Respond with OK."}],"max_tokens":8}' \
    > /tmp/ai-server-http-code.txt 2>/tmp/ai-server-curl.err; then
    HTTP_STATUS="$(cat /tmp/ai-server-http-code.txt)"
    if [ "$HTTP_STATUS" = "200" ]; then
      LATENCY_MS="measured-via-client-timing"
    fi
  fi
  rm -f "$TMP_JSON"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -q '^ai-lab-llama-server$'; then
    MEMORY_MB="$(docker stats ai-lab-llama-server --no-stream --format '{{.MemUsage}}')"
  fi
fi

cat > "$OUT" <<EOF
# Smoke Benchmark Report

- Timestamp (UTC): ${TS}
- Runtime: llama.cpp server (Docker)
- Endpoint target: http://127.0.0.1:${HOST_PORT:-8000}/v1/chat/completions
- Profile: ${PROFILE}
- Model path: ${MODEL_PATH:-/models/placeholder.gguf}

## Results

| Metric | Value |
|---|---|
| HTTP status | ${HTTP_STATUS} |
| First-response latency | ${LATENCY_MS} |
| Container memory snapshot | ${MEMORY_MB} |

## Notes

- Placeholder values are expected when no model is mounted or service is not running.
- Re-run after generated/<preset-profile-access>/scripts/start.sh (or legacy
  scripts/start_serving.sh) and with a real model in models/.
EOF

printf "Wrote %s\n" "$OUT"
