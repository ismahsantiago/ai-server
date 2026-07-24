#!/usr/bin/env bash
# COMPATIBILITY EXAMPLE (legacy root helper)
# Canonical equivalent: generated/<preset-profile-access>/scripts/start.sh
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
  printf "No .env found. Seeded from .env.example (medium profile).\n"
fi

docker compose up -d
docker compose ps
