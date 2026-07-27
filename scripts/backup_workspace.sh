#!/usr/bin/env bash
# Back up a generated workspace to a checksummed archive.
#
# The archive covers the workspace's configuration only. Model weights live
# outside the workspace and are bind-mounted read-only, so they are deliberately
# not copied: they are large, unmodified by this tool, and reproducible from
# their own source.
#
# Usage: scripts/backup_workspace.sh <workspace-dir> [destination-dir]
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_DESTINATION="${PROJECT_ROOT}/backups"

usage() {
  printf "Usage: %s <workspace-dir> [destination-dir]\n" "$0" >&2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

WORKSPACE_INPUT="$1"
DESTINATION="${2:-${DEFAULT_DESTINATION}}"

if [ ! -d "${WORKSPACE_INPUT}" ]; then
  printf "Workspace directory does not exist: %s\n" "${WORKSPACE_INPUT}" >&2
  exit 1
fi

WORKSPACE="$(CDPATH='' cd -- "${WORKSPACE_INPUT}" && pwd)"
WORKSPACE_NAME="$(basename -- "${WORKSPACE}")"

if [ ! -f "${WORKSPACE}/manifest.json" ]; then
  printf "Refusing to back up a directory without manifest.json: %s\n" "${WORKSPACE}" >&2
  printf "This does not look like a generated ai-server workspace.\n" >&2
  exit 1
fi
if [ ! -f "${WORKSPACE}/.env" ] || [ -L "${WORKSPACE}/.env" ]; then
  printf "Refusing to back up a workspace without a regular .env file.\n" >&2
  exit 1
fi
ENV_MODE="$(python3 - "${WORKSPACE}/.env" <<'PY'
import os
import stat
import sys

print(f"{stat.S_IMODE(os.stat(sys.argv[1], follow_symlinks=False).st_mode):o}")
PY
)"
if [ "${ENV_MODE}" != "600" ]; then
  printf "Refusing to back up .env with unsafe mode %s; expected 600.\n" "${ENV_MODE}" >&2
  exit 1
fi

mkdir -p -- "${DESTINATION}"
DESTINATION="$(CDPATH='' cd -- "${DESTINATION}" && pwd)"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${DESTINATION}/${WORKSPACE_NAME}-${TIMESTAMP}.tar.gz"

if [ -e "${ARCHIVE}" ]; then
  printf "Backup archive already exists: %s\n" "${ARCHIVE}" >&2
  exit 1
fi

# Backup and restore share the manifest inventory contract. Mutable runtime
# output (for example logs/benchmarks) is intentionally excluded.
INVENTORY="$(mktemp "${DESTINATION}/.${WORKSPACE_NAME}.inventory.XXXXXX")"
cleanup() {
  rm -f -- "${INVENTORY}"
}
trap cleanup EXIT HUP INT TERM

WORKSPACE="${WORKSPACE}" WORKSPACE_NAME="${WORKSPACE_NAME}" \
  INVENTORY="${INVENTORY}" python3 - <<'PY'
import json
import os
from pathlib import Path, PurePosixPath

workspace = Path(os.environ["WORKSPACE"])
manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
required = manifest.get("required_files")
if not isinstance(required, list) or not required or any(
    not isinstance(item, str) or not item for item in required
):
    raise SystemExit("Manifest required_files must be a non-empty string array.")

entries = set(required)
entries.add(".ai-server-generated.json")
encoded = []
for relative_name in sorted(entries):
    relative = PurePosixPath(relative_name)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise SystemExit(f"Unsafe manifest inventory path: {relative_name}")
    candidate = workspace.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=True).relative_to(workspace)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"Missing or escaping inventory file: {relative_name}") from exc
    if candidate.is_symlink() or not candidate.is_file():
        raise SystemExit(f"Inventory entry is not a regular file: {relative_name}")
    archived_name = f"{os.environ['WORKSPACE_NAME']}/{relative.as_posix()}"
    encoded.append(os.fsencode(archived_name))

Path(os.environ["INVENTORY"]).write_bytes(b"\0".join(encoded) + b"\0")
PY

# Archive only the validated NUL-delimited inventory. COPYFILE_DISABLE avoids
# macOS AppleDouble metadata members, which are outside the manifest contract.
COPYFILE_DISABLE=1 tar -czf "${ARCHIVE}" -C "$(dirname -- "${WORKSPACE}")" \
  --null -T "${INVENTORY}"

if command -v shasum >/dev/null 2>&1; then
  ( cd -- "${DESTINATION}" && shasum -a 256 "$(basename -- "${ARCHIVE}")" >"${ARCHIVE}.sha256" )
elif command -v sha256sum >/dev/null 2>&1; then
  ( cd -- "${DESTINATION}" && sha256sum "$(basename -- "${ARCHIVE}")" >"${ARCHIVE}.sha256" )
else
  printf "Neither shasum nor sha256sum is available; cannot checksum the backup.\n" >&2
  rm -f -- "${ARCHIVE}"
  exit 1
fi

printf "Backed up %s\n" "${WORKSPACE}"
printf "  archive:  %s\n" "${ARCHIVE}"
printf "  checksum: %s\n" "${ARCHIVE}.sha256"
printf "\nModel weights are not included; they are mounted read-only from the host.\n"
printf "Restore with: scripts/restore_workspace.sh %s <target-dir>\n" "${ARCHIVE}"
