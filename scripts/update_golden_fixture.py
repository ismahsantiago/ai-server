#!/usr/bin/env python3
"""Maintain the committed golden fixture for a generated workspace.

The fixture asserts byte-for-byte what the generator emits, so template or
context changes cannot land unnoticed. Two values are machine-specific and are
replaced by placeholders before comparison:

* the absolute project root, which appears in host paths, and
* the generation fingerprint, which is a hash over a context containing that
  absolute root.

Everything else is compared literally. Template edits still surface here,
because they change the rendered text itself.

Usage:
    python3 scripts/update_golden_fixture.py            # refresh the fixture
    python3 scripts/update_golden_fixture.py --check    # fail if it drifted
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai_server_generator.render import planned_files, render_workspace  # noqa: E402

FIXTURE_DIR = PROJECT_ROOT / "tests" / "golden" / "chat-ornith-medium-localhost"
ROOT_PLACEHOLDER = "{PROJECT_ROOT}"
FINGERPRINT_PLACEHOLDER = "{GENERATION_FINGERPRINT}"
FINGERPRINT_PATTERN = re.compile(r"\b[0-9a-f]{64}\b")

FIXTURE_ARGUMENTS = {
    "setup_name": "chat",
    "profile_name": "medium",
    "access": "localhost",
    "model_path": "./models/ornith-9b.gguf",
    "preset_alias": "ornith-9b",
    "preset_name": "Ornith 1.0 (9B)",
    "preset_summary": "agentic code specialist",
    "capability_tags": "code, agentic, tool-use",
    "memory_guidance": "Recommended: 7-9 GB RAM budget for stable local serving.",
    "shorthand_mode": True,
}


def _normalize(text: str) -> str:
    text = text.replace(str(PROJECT_ROOT), ROOT_PLACEHOLDER)
    return FINGERPRINT_PATTERN.sub(FINGERPRINT_PLACEHOLDER, text)


def _render_normalized() -> dict[str, str]:
    generated_root = PROJECT_ROOT / "generated"
    generated_root.mkdir(parents=True, exist_ok=True)
    workspace_parent = Path(
        tempfile.mkdtemp(prefix=".golden-fixture-", dir=str(generated_root))
    )
    try:
        out = workspace_parent / "workspace"
        # The preset carries the real model contract; passing it explicitly here
        # would duplicate presets.py and let the two drift apart.
        from ai_server_generator.presets import resolve_preset

        preset = resolve_preset(FIXTURE_ARGUMENTS["preset_alias"])
        render_workspace(
            out=str(out.relative_to(PROJECT_ROOT)),
            force=False,
            dry_run=False,
            model_contract={
                "contract_version": preset.contract_version,
                "metadata_status": preset.metadata_status,
                "artifact_repository": preset.artifact_repository,
                "artifact_revision": preset.artifact_revision,
                "artifact_filename": preset.artifact_filename,
                "artifact_size_bytes": preset.artifact_size_bytes,
                "artifact_sha256": preset.artifact_sha256,
                "chat_template": preset.chat_template,
                "architecture": preset.architecture,
                "parameter_billions": preset.parameter_billions,
                "quantization_assumption": preset.quantization_assumption,
                "estimated_model_gb": preset.estimated_model_gb,
                "kv_cache_gb_at_default_context": preset.kv_cache_gb_at_default_context,
                "runtime_buffer_gb": preset.runtime_buffer_gb,
                "minimum_host_ram_gb": preset.minimum_host_ram_gb,
                "recommended_host_ram_gb": preset.recommended_host_ram_gb,
                "default_context": preset.default_context,
            },
            **FIXTURE_ARGUMENTS,
        )
        return {
            relative: _normalize((out / relative).read_text(encoding="utf-8"))
            for relative in sorted(planned_files())
        }
    finally:
        shutil.rmtree(workspace_parent, ignore_errors=True)


def _read_fixture() -> dict[str, str]:
    if not FIXTURE_DIR.is_dir():
        return {}
    return {
        path.relative_to(FIXTURE_DIR).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(FIXTURE_DIR.rglob("*"))
        if path.is_file()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintain the golden workspace fixture.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed fixture matches current output.",
    )
    args = parser.parse_args(argv)

    rendered = _render_normalized()

    if args.check:
        committed = _read_fixture()
        if not committed:
            print(
                "ERROR: golden fixture is missing; run scripts/update_golden_fixture.py",
                file=sys.stderr,
            )
            return 1
        missing = sorted(set(rendered) - set(committed))
        unexpected = sorted(set(committed) - set(rendered))
        changed = sorted(
            name
            for name in set(rendered) & set(committed)
            if rendered[name] != committed[name]
        )
        if missing or unexpected or changed:
            print("ERROR: generated output drifted from the golden fixture", file=sys.stderr)
            for name in missing:
                print(f"  missing from fixture: {name}", file=sys.stderr)
            for name in unexpected:
                print(f"  no longer generated:  {name}", file=sys.stderr)
            for name in changed:
                print(f"  content changed:      {name}", file=sys.stderr)
            print(
                "\nIf the change is intended, run scripts/update_golden_fixture.py "
                "and review the diff.",
                file=sys.stderr,
            )
            return 1
        print(f"golden fixture is current ({len(rendered)} files)")
        return 0

    shutil.rmtree(FIXTURE_DIR, ignore_errors=True)
    for relative, content in rendered.items():
        destination = FIXTURE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    print(f"Wrote {len(rendered)} files to {FIXTURE_DIR.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
