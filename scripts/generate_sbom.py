#!/usr/bin/env python3
"""Generate a CycloneDX SBOM for this project's pinned inputs.

The inventory covers what actually determines what runs: the pinned Python
dependencies and the digest-pinned serving container image. Output is
deterministic so CI can assert it matches the committed ``sbom.json``.

Usage:
    python3 scripts/generate_sbom.py            # write sbom.json
    python3 scripts/generate_sbom.py --check    # fail if sbom.json is stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai_server_generator.render import (  # noqa: E402
    SERVING_IMAGE_DIGEST,
    SERVING_IMAGE_REPOSITORY,
    SERVING_IMAGE_TAG,
)

SBOM_PATH = PROJECT_ROOT / "sbom.json"
REQUIREMENT_FILES = ("requirements.txt", "requirements-dev.txt")
PIN_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.+!-]*)$")


def _read_pinned_requirements() -> dict[str, str]:
    """Collect ``name==version`` pins, rejecting anything unpinned."""
    pins: dict[str, str] = {}
    for file_name in REQUIREMENT_FILES:
        path = PROJECT_ROOT / file_name
        if not path.is_file():
            raise SystemExit(f"missing requirements file: {file_name}")
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                # ``-r requirements.txt`` style includes are followed separately
                # because every referenced file is already in REQUIREMENT_FILES.
                continue
            match = PIN_PATTERN.match(line)
            if match is None:
                raise SystemExit(
                    f"{file_name}:{line_number}: requirement is not pinned with '==': {line}"
                )
            name, version = match.group(1), match.group(2)
            existing = pins.get(name.lower())
            if existing is not None and existing != version:
                raise SystemExit(
                    f"{name} is pinned to conflicting versions: {existing} and {version}"
                )
            pins[name.lower()] = version
    return pins


def build_sbom() -> dict[str, object]:
    components: list[dict[str, object]] = []
    pins = _read_pinned_requirements()
    for name in sorted(pins):
        version = pins[name]
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name}@{version}",
                "scope": "required",
            }
        )

    image_reference = f"{SERVING_IMAGE_REPOSITORY}:{SERVING_IMAGE_TAG}@{SERVING_IMAGE_DIGEST}"
    components.append(
        {
            "type": "container",
            "name": SERVING_IMAGE_REPOSITORY,
            "version": SERVING_IMAGE_TAG,
            "purl": (
                f"pkg:oci/{SERVING_IMAGE_REPOSITORY.rsplit('/', 1)[-1]}"
                f"?repository_url={SERVING_IMAGE_REPOSITORY}&tag={SERVING_IMAGE_TAG}"
            ),
            "scope": "required",
            "hashes": [
                {
                    "alg": "SHA-256",
                    "content": SERVING_IMAGE_DIGEST.removeprefix("sha256:"),
                }
            ],
            "externalReferences": [
                {"type": "distribution", "url": f"https://{image_reference}"}
            ],
        }
    )

    # No timestamp or serial number: the SBOM must be a pure function of the
    # pinned inputs so CI can diff it without spurious churn.
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "ai-server",
                "description": (
                    "Generator-first local AI server workspace builder. "
                    "Private project; not distributed."
                ),
            },
            "properties": [
                {
                    "name": "ai-server:inventory-scope",
                    "value": (
                        "Pinned Python dependencies and the digest-pinned serving "
                        "image. Transitive OS packages inside the container image "
                        "are not enumerated."
                    ),
                }
            ],
        },
        "components": components,
    }


def render(sbom: dict[str, object]) -> str:
    return json.dumps(sbom, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the CycloneDX SBOM.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed sbom.json is current instead of rewriting it.",
    )
    args = parser.parse_args(argv)

    content = render(build_sbom())
    if args.check:
        if not SBOM_PATH.is_file():
            print("ERROR: sbom.json is missing; run scripts/generate_sbom.py", file=sys.stderr)
            return 1
        if SBOM_PATH.read_text(encoding="utf-8") != content:
            print(
                "ERROR: sbom.json is stale; run scripts/generate_sbom.py to refresh it",
                file=sys.stderr,
            )
            return 1
        print("sbom.json is current")
        return 0

    SBOM_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {SBOM_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
