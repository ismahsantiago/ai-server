#!/usr/bin/env python3
"""Validate the opt-in audit checksum manifest before shasum consumes it."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


CHECKSUM_LINE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+([ *]?)(.+)$")


def validate_audit_manifest(audit_dir_arg: str, manifest_arg: str) -> Path:
    audit_dir = Path(audit_dir_arg).resolve()
    manifest = Path(manifest_arg).resolve()

    if not audit_dir.is_dir():
        raise ValueError(f"AUDIT_DIR is not a directory: {audit_dir}")
    if manifest.name != "evidence-manifest.sha256":
        raise ValueError(
            "AUDIT_EVIDENCE_MANIFEST must be named evidence-manifest.sha256"
        )
    if not manifest.is_file():
        raise ValueError(f"audit evidence manifest does not exist: {manifest}")
    try:
        manifest.relative_to(audit_dir)
    except ValueError as exc:
        raise ValueError(
            "AUDIT_EVIDENCE_MANIFEST must be inside the declared AUDIT_DIR"
        ) from exc

    for line_number, raw_line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line or raw_line.startswith("#"):
            continue
        match = CHECKSUM_LINE.fullmatch(raw_line)
        if match is None:
            raise ValueError(f"invalid checksum entry at line {line_number}")
        relative_name = match.group(3)
        candidate = Path(relative_name)
        if candidate.is_absolute():
            raise ValueError(f"absolute checksum path at line {line_number}")
        resolved = (audit_dir / candidate).resolve()
        try:
            resolved.relative_to(audit_dir)
        except ValueError as exc:
            raise ValueError(
                f"checksum path escapes AUDIT_DIR at line {line_number}: "
                f"{relative_name}"
            ) from exc

    return manifest


def main() -> int:
    audit_dir = os.environ.get("AUDIT_DIR")
    manifest = os.environ.get("AUDIT_EVIDENCE_MANIFEST")
    if not audit_dir and not manifest:
        return 0
    if not audit_dir or not manifest:
        print(
            "AUDIT_DIR and AUDIT_EVIDENCE_MANIFEST must be set together",
            file=sys.stderr,
        )
        return 2
    try:
        validate_audit_manifest(audit_dir, manifest)
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
