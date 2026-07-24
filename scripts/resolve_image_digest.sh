#!/usr/bin/env bash
# Resolve the current digest of the serving image tag from the registry.
#
# This script only reads public registry metadata; it pulls nothing and changes
# nothing. Paste its output into SERVING_IMAGE_DIGEST in
# ai_server_generator/render.py to move the pin deliberately.
set -euo pipefail

REPOSITORY="${1:-ggml-org/llama.cpp}"
TAG="${2:-server}"
REGISTRY="ghcr.io"

command -v curl >/dev/null 2>&1 || {
  printf "curl is required to resolve an image digest.\n" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  printf "python3 is required to parse the registry response.\n" >&2
  exit 1
}

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-server-digest.XXXXXX")"
trap 'rm -rf -- "${TMP_DIR}"' EXIT HUP INT TERM

if ! curl --silent --show-error --fail --max-time 20 \
  --output "${TMP_DIR}/token.json" \
  "https://${REGISTRY}/token?scope=repository:${REPOSITORY}:pull&service=${REGISTRY}"; then
  printf "Could not obtain a pull token for %s/%s.\n" "${REGISTRY}" "${REPOSITORY}" >&2
  exit 1
fi

TOKEN="$(python3 -c '
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
token = value.get("token")
if not isinstance(token, str) or not token:
    raise SystemExit("registry did not return a pull token")
print(token)
' "${TMP_DIR}/token.json")"

ACCEPT='application/vnd.oci.image.index.v1+json'
ACCEPT="${ACCEPT},application/vnd.docker.distribution.manifest.list.v2+json"
ACCEPT="${ACCEPT},application/vnd.oci.image.manifest.v1+json"
ACCEPT="${ACCEPT},application/vnd.docker.distribution.manifest.v2+json"

if ! curl --silent --show-error --fail --max-time 20 \
  --dump-header "${TMP_DIR}/headers.txt" \
  --output "${TMP_DIR}/manifest.json" \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Accept: ${ACCEPT}" \
  "https://${REGISTRY}/v2/${REPOSITORY}/manifests/${TAG}"; then
  printf "Could not resolve %s/%s:%s. The repository or tag may not exist.\n" \
    "${REGISTRY}" "${REPOSITORY}" "${TAG}" >&2
  exit 1
fi

DIGEST="$(
  tr -d '\r' <"${TMP_DIR}/headers.txt" \
    | awk 'tolower($1) == "docker-content-digest:" { print $2 }' \
    | tail -n 1
)"

if [ -z "${DIGEST}" ]; then
  printf "Registry response did not include a content digest.\n" >&2
  exit 1
fi

printf "image:  %s/%s:%s\n" "${REGISTRY}" "${REPOSITORY}" "${TAG}"
printf "digest: %s\n" "${DIGEST}"
printf "pinned: %s/%s:%s@%s\n" "${REGISTRY}" "${REPOSITORY}" "${TAG}" "${DIGEST}"
printf "\nPlatforms covered by this reference:\n"
python3 - "${TMP_DIR}/manifest.json" <<'PY'
import json
import sys
from pathlib import Path

value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifests = value.get("manifests")
if not isinstance(manifests, list):
    print("  (single-platform manifest)")
else:
    for entry in manifests:
        platform = entry.get("platform", {})
        if platform.get("architecture") == "unknown":
            continue
        print(f"  {platform.get('os')}/{platform.get('architecture')}")
PY
