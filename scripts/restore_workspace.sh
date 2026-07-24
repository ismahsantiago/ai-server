#!/usr/bin/env bash
# Restore a generated workspace from a checksummed backup archive.
#
# The checksum is verified before anything is written, and the replacement is
# atomic: the archive is expanded into a staging directory first, and the
# previous target is moved aside rather than deleted, so a failed restore leaves
# a recoverable directory behind.
#
# Usage: scripts/restore_workspace.sh <archive.tar.gz> <target-dir>
set -euo pipefail

usage() {
  printf "Usage: %s <archive.tar.gz> <target-dir>\n" "$0" >&2
}

if [ "$#" -ne 2 ]; then
  usage
  exit 2
fi

ARCHIVE_INPUT="$1"
TARGET_INPUT="$2"

if [ ! -f "${ARCHIVE_INPUT}" ]; then
  printf "Archive does not exist: %s\n" "${ARCHIVE_INPUT}" >&2
  exit 1
fi

ARCHIVE_DIR="$(CDPATH='' cd -- "$(dirname -- "${ARCHIVE_INPUT}")" && pwd)"
ARCHIVE_NAME="$(basename -- "${ARCHIVE_INPUT}")"
ARCHIVE="${ARCHIVE_DIR}/${ARCHIVE_NAME}"
CHECKSUM_FILE="${ARCHIVE}.sha256"

if [ ! -f "${CHECKSUM_FILE}" ]; then
  printf "Missing checksum file: %s\n" "${CHECKSUM_FILE}" >&2
  printf "Refusing to restore an unverified archive.\n" >&2
  exit 1
fi

if command -v shasum >/dev/null 2>&1; then
  CHECKSUM_COMMAND=(shasum -a 256 -c)
elif command -v sha256sum >/dev/null 2>&1; then
  CHECKSUM_COMMAND=(sha256sum -c)
else
  printf "Neither shasum nor sha256sum is available; cannot verify the backup.\n" >&2
  exit 1
fi

if ! ( cd -- "${ARCHIVE_DIR}" && "${CHECKSUM_COMMAND[@]}" "$(basename -- "${CHECKSUM_FILE}")" ); then
  printf "Checksum verification failed for %s\n" "${ARCHIVE}" >&2
  exit 1
fi

TARGET_PARENT="$(CDPATH='' cd -- "$(dirname -- "${TARGET_INPUT}")" && pwd)"
TARGET_NAME="$(basename -- "${TARGET_INPUT}")"
TARGET="${TARGET_PARENT}/${TARGET_NAME}"

if [ -e "${TARGET}" ] && [ ! -d "${TARGET}" ]; then
  printf "Target exists and is not a directory: %s\n" "${TARGET}" >&2
  exit 1
fi

STAGING="$(mktemp -d "${TARGET_PARENT}/.${TARGET_NAME}.restore-XXXXXX")"
DISPLACED=""
cleanup() {
  rm -rf -- "${STAGING}"
}
trap cleanup EXIT HUP INT TERM

tar -xzf "${ARCHIVE}" -C "${STAGING}"

# The archive holds exactly one root directory; find it without parsing ls.
ROOT_COUNT=0
ROOT_ENTRY=""
for entry in "${STAGING}"/*; do
  [ -e "${entry}" ] || continue
  ROOT_COUNT=$((ROOT_COUNT + 1))
  ROOT_ENTRY="${entry}"
done

if [ "${ROOT_COUNT}" -ne 1 ] || [ ! -d "${ROOT_ENTRY}" ]; then
  printf "Archive does not contain exactly one workspace directory.\n" >&2
  exit 1
fi

if [ ! -f "${ROOT_ENTRY}/manifest.json" ]; then
  printf "Archive does not contain a generated workspace (no manifest.json).\n" >&2
  exit 1
fi

if [ -d "${TARGET}" ]; then
  DISPLACED="${TARGET_PARENT}/.${TARGET_NAME}.replaced-$(date -u +%Y%m%dT%H%M%SZ)"
  mv -- "${TARGET}" "${DISPLACED}"
fi

if ! mv -- "${ROOT_ENTRY}" "${TARGET}"; then
  printf "Restore failed while installing the workspace.\n" >&2
  if [ -n "${DISPLACED}" ] && [ ! -e "${TARGET}" ]; then
    mv -- "${DISPLACED}" "${TARGET}"
    printf "Previous workspace was put back in place.\n" >&2
  fi
  exit 1
fi

printf "Restored %s\n" "${TARGET}"
printf "  from archive: %s\n" "${ARCHIVE}"
if [ -n "${DISPLACED}" ]; then
  printf "  previous workspace kept at: %s\n" "${DISPLACED}"
  printf "  remove it once the restore is confirmed good.\n"
fi
printf "\nValidate the restored workspace before starting it:\n"
printf "  python3 -m ai_server_generator validate %s\n" "${TARGET}"
