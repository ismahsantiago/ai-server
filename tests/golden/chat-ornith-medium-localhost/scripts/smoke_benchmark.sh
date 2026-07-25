#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(CDPATH='' cd -- "${SCRIPT_DIR}/.." && pwd)"
HOST_PORT="8000"
ENDPOINT="http://127.0.0.1:${HOST_PORT}/v1/chat/completions"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-server-smoke.XXXXXX")"
trap 'rm -rf -- "${TMP_DIR}"' EXIT HUP INT TERM

command -v curl >/dev/null 2>&1 || {
  printf "curl is required for smoke validation.\n" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  printf "python3 is required for JSON validation.\n" >&2
  exit 1
}

REQUEST='{"model":"local","messages":[{"role":"user","content":"Respond with OK."}],"max_tokens":8}'

request_once() {
  index="$1"
  if ! curl --silent --show-error --max-time 30 \
    --output "${TMP_DIR}/response-${index}.json" \
    --write-out '%{http_code} %{time_starttransfer} %{time_total}' \
    --request POST "${ENDPOINT}" \
    --header "Content-Type: application/json" \
    --data "${REQUEST}" >"${TMP_DIR}/meta-${index}.txt"; then
    printf "curl transport failed for sample %s.\n" "${index}" >&2
    return 1
  fi
  meta="$(cat "${TMP_DIR}/meta-${index}.txt")"
  read -r status first total <<<"${meta}"
  if [ "${status}" != "200" ]; then
    printf "Expected HTTP 200, received %s for sample %s.\n" "${status}" "${index}" >&2
    return 1
  fi
  python3 - "${TMP_DIR}/response-${index}.json" <<'PY'
import json
import sys
from pathlib import Path

try:
    value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    choices = value["choices"]
    content = choices[0]["message"]["content"]
except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError):
    raise SystemExit("response is not a valid chat-completion JSON object")
if not isinstance(choices, list) or not isinstance(content, str) or not content.strip():
    raise SystemExit("response chat-completion content is empty or malformed")
PY
  if [ "${index}" = "warmup" ]; then
    return 0
  fi
  python3 - "${first}" "${total}" >>"${TMP_DIR}/samples.txt" <<'PY'
import math
import sys

first, total = map(float, sys.argv[1:])
if not all(math.isfinite(value) and value >= 0 for value in (first, total)):
    raise SystemExit("curl returned a non-numeric timing")
print(f"{first * 1000:.3f} {total * 1000:.3f}")
PY
}

# Warm-up is validated but excluded from measured samples.
request_once warmup
for sample in 1 2 3; do
  request_once "${sample}"
done

read -r TTFB_P50_MS TTFB_P95_MS TOTAL_P50_MS TOTAL_P95_MS < <(
  python3 - "${TMP_DIR}/samples.txt" <<'PY'
import math
import sys
from pathlib import Path

rows = [
    tuple(map(float, line.split()))
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
]
if len(rows) != 3:
    raise SystemExit("expected exactly three measured samples")

def percentile(values, fraction):
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]

first = [row[0] for row in rows]
total = [row[1] for row in rows]
print(
    f"{percentile(first, .50):.3f} {percentile(first, .95):.3f} "
    f"{percentile(total, .50):.3f} {percentile(total, .95):.3f}"
)
PY
)

MEMORY_MB="NOT_MEASURED"
if command -v docker >/dev/null 2>&1; then
  container_id="$(
    docker compose --project-directory "${WORKSPACE}" \
      -f "${WORKSPACE}/docker-compose.yml" ps -q llama-server 2>/dev/null || true
  )"
  if [ -n "${container_id}" ]; then
    raw_memory="$(docker stats "${container_id}" --no-stream --format '{{.MemUsage}}' 2>/dev/null || true)"
    if [ -n "${raw_memory}" ]; then
      MEMORY_MB="$(
        python3 - "${raw_memory%% /*}" <<'PY'
import re
import sys

match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMG]i?B)", sys.argv[1])
if not match:
    raise SystemExit(1)
value = float(match.group(1))
unit = match.group(2)
factor = {"KB": .001, "KiB": 1 / 1024, "MB": 1, "MiB": 1.048576, "GB": 1000, "GiB": 1073.741824}[unit]
print(f"{value * factor:.3f}")
PY
      )" || MEMORY_MB="NOT_MEASURED"
    fi
  fi
fi

TS="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="${WORKSPACE}/logs/benchmarks"
mkdir -p "${OUT_DIR}"
OUT="${OUT_DIR}/smoke-benchmark-${TS}-$$.md"
cat >"${OUT}" <<EOF
# Smoke Benchmark Evidence

- Timestamp (UTC): ${TS}
- Validation: HTTP transport + status + chat-completion JSON content
- Authentication: none (localhost-only endpoint)
- Samples: 1 warm-up + 3 measured
- Profile: medium
- Model host path: {PROJECT_ROOT}/models/ornith-9b.gguf
- Model container path: /models/model.gguf

| Metric | Value |
|---|---:|
| HTTP status | 200 |
| TTFB p50 ms | ${TTFB_P50_MS} |
| TTFB p95 ms | ${TTFB_P95_MS} |
| Total latency p50 ms | ${TOTAL_P50_MS} |
| Total latency p95 ms | ${TOTAL_P95_MS} |
| Container memory MB | ${MEMORY_MB} |
| Tokens per second | NOT_MEASURED |
| Response quality | NOT_MEASURED |
EOF

printf "Smoke passed; evidence: %s\n" "${OUT}"
