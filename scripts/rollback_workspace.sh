#!/usr/bin/env bash
# Roll a generated workspace back to the copy the generator set aside.
#
# When `generate --force` replaces a workspace, the renderer moves the previous
# directory to a timestamped sibling instead of deleting it. This script lists
# those copies and swaps one back into place. The workspace being replaced is
# itself preserved, so a rollback can be undone.
#
# Usage:
#   scripts/rollback_workspace.sh --list <workspace-dir>
#   scripts/rollback_workspace.sh <workspace-dir> [backup-dir]
set -euo pipefail

usage() {
  printf "Usage: %s --list <workspace-dir>\n" "$0" >&2
  printf "       %s <workspace-dir> [backup-dir]\n" "$0" >&2
}

LIST_ONLY="no"
if [ "${1:-}" = "--list" ]; then
  LIST_ONLY="yes"
  shift
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

TARGET_INPUT="$1"
TARGET_PARENT="$(CDPATH='' cd -- "$(dirname -- "${TARGET_INPUT}")" && pwd)"
TARGET_NAME="$(basename -- "${TARGET_INPUT}")"
TARGET="${TARGET_PARENT}/${TARGET_NAME}"

# Timestamps are embedded in the directory name, so lexical order is
# chronological order.
BACKUPS=()
for candidate in "${TARGET_PARENT}/.${TARGET_NAME}.backup-"*; do
  [ -d "${candidate}" ] || continue
  BACKUPS+=("${candidate}")
done

if [ "${#BACKUPS[@]}" -eq 0 ]; then
  printf "No generator backups found for %s\n" "${TARGET}" >&2
  exit 1
fi

if [ "${LIST_ONLY}" = "yes" ]; then
  printf "Available backups for %s (oldest first):\n" "${TARGET}"
  for candidate in "${BACKUPS[@]}"; do
    printf "  %s\n" "${candidate}"
  done
  exit 0
fi

if [ "$#" -eq 2 ]; then
  SELECTED_INPUT="$2"
  if [ ! -d "${SELECTED_INPUT}" ]; then
    printf "Backup directory does not exist: %s\n" "${SELECTED_INPUT}" >&2
    exit 1
  fi
  SELECTED="$(CDPATH='' cd -- "${SELECTED_INPUT}" && pwd)"
  case "${SELECTED}" in
    "${TARGET_PARENT}/.${TARGET_NAME}.backup-"*) ;;
    *)
      printf "Not a generator backup of %s: %s\n" "${TARGET}" "${SELECTED}" >&2
      exit 1
      ;;
  esac
else
  SELECTED="${BACKUPS[$(( ${#BACKUPS[@]} - 1 ))]}"
fi

if [ ! -f "${SELECTED}/manifest.json" ]; then
  printf "Backup does not contain a generated workspace (no manifest.json): %s\n" "${SELECTED}" >&2
  exit 1
fi

DISPLACED=""
if [ -e "${TARGET}" ]; then
  if [ ! -d "${TARGET}" ]; then
    printf "Target exists and is not a directory: %s\n" "${TARGET}" >&2
    exit 1
  fi
  DISPLACED="${TARGET_PARENT}/.${TARGET_NAME}.rolledback-$(date -u +%Y%m%dT%H%M%SZ)"
  mv -- "${TARGET}" "${DISPLACED}"
fi

if ! mv -- "${SELECTED}" "${TARGET}"; then
  printf "Rollback failed while installing the backup.\n" >&2
  if [ -n "${DISPLACED}" ] && [ ! -e "${TARGET}" ]; then
    mv -- "${DISPLACED}" "${TARGET}"
    printf "Previous workspace was put back in place.\n" >&2
  fi
  exit 1
fi

printf "Rolled %s back to %s\n" "${TARGET}" "$(basename -- "${SELECTED}")"
if [ -n "${DISPLACED}" ]; then
  printf "  replaced workspace kept at: %s\n" "${DISPLACED}"
fi
printf "\nValidate the restored workspace before starting it:\n"
printf "  python3 -m ai_server_generator validate %s\n" "${TARGET}"
