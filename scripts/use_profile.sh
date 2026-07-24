#!/usr/bin/env bash
# COMPATIBILITY EXAMPLE (legacy root helper)
# Canonical equivalent: generated/<preset-profile-access>/config/profiles/*.env
set -euo pipefail

if [ "${1:-}" = "" ]; then
  printf "Usage: %s <medium-fast|medium|good>\n" "$0"
  exit 1
fi

PROFILE_FILE="config/profiles/${1}.env"

if [ ! -f "$PROFILE_FILE" ]; then
  printf "Profile not found: %s\n" "$PROFILE_FILE"
  exit 1
fi

cp "$PROFILE_FILE" .env
printf "Applied profile '%s' to .env\n" "$1"
