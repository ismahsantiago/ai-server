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

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/.." && pwd)"

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

ROOT_ENTRY="${STAGING}/workspace"
ARCHIVE="${ARCHIVE}" ROOT_ENTRY="${ROOT_ENTRY}" python3 - <<'PY'
import json
import os
import shutil
import stat
import tarfile
from pathlib import Path, PurePosixPath

archive = Path(os.environ["ARCHIVE"])
destination = Path(os.environ["ROOT_ENTRY"])

with tarfile.open(archive, "r:gz") as bundle:
    members = bundle.getmembers()
    if not members:
        raise SystemExit("Archive is empty.")

    roots = set()
    normalized = []
    for member in members:
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise SystemExit(f"Unsafe archive member path: {member.name}")
        roots.add(path.parts[0])
        if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
            raise SystemExit(f"Unsupported archive member type: {member.name}")
        normalized.append((member, path))
    if len(roots) != 1:
        raise SystemExit("Archive must contain exactly one workspace root.")

    destination.mkdir(mode=0o700)
    for member, path in normalized:
        relative = PurePosixPath(*path.parts[1:])
        if not relative.parts:
            if not member.isdir():
                raise SystemExit("Archive workspace root must be a directory.")
            continue
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if member.isdir():
            target.mkdir(exist_ok=True)
            continue
        source = bundle.extractfile(member)
        if source is None:
            raise SystemExit(f"Cannot read archive member: {member.name}")
        with source, target.open("xb") as output:
            shutil.copyfileobj(source, output)
        target.chmod(stat.S_IMODE(member.mode) & 0o777)

manifest_path = destination / "manifest.json"
if not manifest_path.is_file():
    raise SystemExit("Archive does not contain a generated workspace manifest.")
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Invalid workspace manifest: {exc}") from exc
required = manifest.get("required_files")
if not isinstance(required, list) or not required or any(
    not isinstance(item, str) or not item for item in required
):
    raise SystemExit("Manifest required_files must be a non-empty string array.")
expected = set(required)
expected.add(".ai-server-generated.json")
actual = {
    path.relative_to(destination).as_posix()
    for path in destination.rglob("*")
    if path.is_file()
}
if actual != expected:
    raise SystemExit(
        "Workspace inventory mismatch: "
        f"missing={sorted(expected - actual)!r}, unexpected={sorted(actual - expected)!r}"
    )

env_path = destination / ".env"
if not env_path.is_file() or env_path.is_symlink():
    raise SystemExit("Archive does not contain a regular .env file.")
env_mode = stat.S_IMODE(env_path.stat().st_mode)
if env_mode != 0o600:
    raise SystemExit(f"Archive contains .env with unsafe mode {env_mode:o}; expected 600.")
PY

PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 -m ai_server_generator validate "${ROOT_ENTRY}" --tier structure

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
