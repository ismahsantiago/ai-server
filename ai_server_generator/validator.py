from __future__ import annotations

import json
from pathlib import Path

from .data import PROJECT_ROOT
from .render import resolve_output_path


REQUIRED_MANIFEST_KEYS = {
    "schema",
    "setup",
    "profile",
    "access",
    "model_path",
    "preset_alias",
    "preset_name",
    "preset_summary",
    "capability_tags",
    "memory_guidance",
    "shorthand_mode",
    "resolved_setup",
    "resolved_profile",
    "resolved_access",
    "quick_commands",
    "host_port",
    "auth",
    "required_files",
}


def validate_workspace(path_text: str) -> list[str]:
    workspace = resolve_output_path(path_text)
    errors: list[str] = []
    if not workspace.is_dir():
        return [f"generated directory does not exist: {workspace.relative_to(PROJECT_ROOT)}"]

    manifest_path = workspace / "manifest.json"
    if not manifest_path.is_file():
        return ["missing manifest.json"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"manifest.json is invalid JSON: {exc}"]

    missing_keys = sorted(REQUIRED_MANIFEST_KEYS - set(manifest))
    for key in missing_keys:
        errors.append(f"manifest missing key: {key}")

    for rel in manifest.get("required_files", []):
        if not (workspace / rel).is_file():
            errors.append(f"missing required file: {rel}")

    quick_commands = manifest.get("quick_commands")
    if not isinstance(quick_commands, dict):
        errors.append("manifest quick_commands must be an object")
    else:
        for key in ["validate", "start", "smoke"]:
            if not quick_commands.get(key):
                errors.append(f"manifest quick_commands missing {key}")

    access = manifest.get("access")
    compose_path = workspace / "docker-compose.yml"
    compose_text = compose_path.read_text(encoding="utf-8") if compose_path.is_file() else ""
    host_port = manifest.get("host_port", "8000")
    if access == "localhost":
        if f"127.0.0.1:{host_port}:8000" not in compose_text:
            errors.append("localhost workspace must bind to 127.0.0.1")
        if f"0.0.0.0:{host_port}:8000" in compose_text:
            errors.append("localhost workspace must not bind to 0.0.0.0")
    elif access == "lan":
        if manifest.get("auth") != "bearer-token":
            errors.append("LAN workspace requires bearer-token auth")
        if not manifest.get("lan_allowlist"):
            errors.append("LAN workspace requires lan_allowlist")
    else:
        errors.append(f"unknown access mode: {access}")

    return errors
