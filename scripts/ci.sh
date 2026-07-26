#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
GENERATED_ROOT="${PROJECT_ROOT}/generated"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts"

mkdir -p "${GENERATED_ROOT}" "${ARTIFACTS_DIR}" "${PROJECT_ROOT}/models"
WORK_DIR="$(mktemp -d "${GENERATED_ROOT}/.ci-fixture.XXXXXX")"
MODEL_FIXTURE_DIR="$(mktemp -d "${PROJECT_ROOT}/models/.ci-fixture.XXXXXX")"
MODEL_FIXTURE="${MODEL_FIXTURE_DIR}/fixture.gguf"
trap 'rm -rf -- "${WORK_DIR}" "${MODEL_FIXTURE_DIR}"' EXIT HUP INT TERM

OUTPUT_DIR="${WORK_DIR}/workspace"
: > "${MODEL_FIXTURE}"

cd "${PROJECT_ROOT}"

python3 -m pip check
python3 -m compileall -q ai_server_generator tests scripts
python3 -m unittest
python3 -m coverage erase
python3 -m coverage run --branch -m unittest
python3 -m coverage combine
python3 -m coverage report --fail-under=80
python3 -m coverage xml -o "${ARTIFACTS_DIR}/coverage.xml"
python3 -m ruff check ai_server_generator tests
python3 -m mypy ai_server_generator

python3 -m ai_server_generator matrix \
  --preset ornith-9b \
  --profile medium \
  --access localhost
python3 -m ai_server_generator generate \
  --preset ornith-9b \
  --profile medium \
  --access localhost \
  --model-path "${MODEL_FIXTURE}" \
  --out "${OUTPUT_DIR}"
python3 -m ai_server_generator validate "${OUTPUT_DIR}"
python3 -m ai_server_generator doctor --no-write
python3 -m ai_server_generator doctor --no-write --format json >/dev/null

OUTPUT_DIR="${OUTPUT_DIR}" python3 - <<'PY'
import json
import os
from pathlib import Path

from ai_server_generator.render import planned_files

output = Path(os.environ["OUTPUT_DIR"])
manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
expected = set(planned_files())
actual = {
    path.relative_to(output).as_posix()
    for path in output.rglob("*")
    if path.is_file()
}
if actual != expected:
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    raise SystemExit(
        f"generated fixture drift: missing={missing!r}, unexpected={unexpected!r}"
    )
if not set(manifest["required_files"]).issubset(actual):
    raise SystemExit("generated fixture does not contain every manifest-required file")
print("Generated fixture is structurally complete.")
PY

# Byte-for-byte drift against the committed golden fixture, plus the supply
# chain inventory that pins what actually runs.
python3 scripts/update_golden_fixture.py --check
python3 scripts/generate_sbom.py --check

# Functional sweep: every preset in the catalog must render, validate, and
# produce a Compose file the parser accepts. The single ornith build above feeds
# the drift check; this catches a preset or template that breaks for any other
# entry. The preset list comes from the CLI so it cannot drift from the code.
while IFS= read -r preset; do
  [ -n "${preset}" ] || continue
  sweep_dir="${WORK_DIR}/sweep-${preset}"
  python3 -m ai_server_generator matrix --preset "${preset}" --access localhost >/dev/null
  python3 -m ai_server_generator generate \
    --preset "${preset}" \
    --access localhost \
    --model-path "${MODEL_FIXTURE}" \
    --out "${sweep_dir}"
  python3 -m ai_server_generator validate "${sweep_dir}"
  docker compose \
    --project-directory "${sweep_dir}" \
    --env-file "${sweep_dir}/.env" \
    -f "${sweep_dir}/docker-compose.yml" \
    config --quiet
done < <(python3 -m ai_server_generator list models | cut -f1)

docker compose \
  --project-directory "${OUTPUT_DIR}" \
  --env-file "${OUTPUT_DIR}/.env" \
  -f "${OUTPUT_DIR}/docker-compose.yml" \
  config --quiet
docker compose \
  --project-directory "${PROJECT_ROOT}" \
  --env-file /dev/null \
  -f "${PROJECT_ROOT}/docker-compose.yml" \
  config --quiet

while IFS= read -r -d '' script; do
  bash -n "${script}"
  shellcheck "${script}"
done < <(find scripts "${OUTPUT_DIR}/scripts" -type f -name '*.sh' -print0)

# The PM Harness lives entirely under .pm-harness/, which is intentionally not
# committed (project-isolation invariant). It is present in a developer checkout
# but absent on a clean CI clone, so run its gates only when it exists.
if [ -f .pm-harness/bin/harness.py ]; then
  python3 .pm-harness/bin/harness.py validate
  python3 .pm-harness/bin/harness.py agents check
  python3 .pm-harness/bin/harness.py wiki check
  if [ -n "${HARNESS_PLAN_TASK:-}" ]; then
    python3 .pm-harness/bin/harness.py plan check "${HARNESS_PLAN_TASK}"
  fi
  python3 - <<'PY'
import json
import subprocess
from pathlib import Path

for manifest_path in sorted(Path('.pm-harness/state').glob('TASK-*.json')):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('status') not in {'in_review', 'approved', 'closed'}:
        continue
    subprocess.run(
        ['python3', '.pm-harness/bin/harness.py', 'plan', 'check', manifest['id']],
        check=True,
    )
PY
else
  echo "PM Harness not present in this checkout; skipping harness gates."
fi

shasum -a 256 -c \
  audits/audit_opencode_default_gpt-5_24-07-2026/pre-remediation.sha256

python3 -m pip_audit \
  --strict \
  --progress-spinner off \
  --format json \
  --output "${ARTIFACTS_DIR}/pip-audit.json" \
  --requirement requirements.txt
