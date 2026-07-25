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

mkdir -p -- "${DESTINATION}"
DESTINATION="$(CDPATH='' cd -- "${DESTINATION}" && pwd)"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${DESTINATION}/${WORKSPACE_NAME}-${TIMESTAMP}.tar.gz"

if [ -e "${ARCHIVE}" ]; then
  printf "Backup archive already exists: %s\n" "${ARCHIVE}" >&2
  exit 1
fi

# Archive from the parent so the workspace name is the single root entry, which
# keeps restore unambiguous.
tar -czf "${ARCHIVE}" -C "$(dirname -- "${WORKSPACE}")" "${WORKSPACE_NAME}"

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
