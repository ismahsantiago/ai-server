from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .data import PROJECT_ROOT, load_profiles, load_setups, templates_dir


TEMPLATE_MAP = {
    "docker-compose.yml": "docker-compose.yml.j2",
    ".env": "env.j2",
    "manifest.json": "manifest.json.j2",
    "README.md": "README.md.j2",
    "runbook.md": "runbook.md.j2",
    "scripts/start.sh": "scripts/start.sh.j2",
    "scripts/validate.sh": "scripts/validate.sh.j2",
    "scripts/smoke.sh": "scripts/smoke.sh.j2",
    "scripts/start_serving.sh": "scripts/start_serving.sh.j2",
    "scripts/smoke_benchmark.sh": "scripts/smoke_benchmark.sh.j2",
    "scripts/validate_host.sh": "scripts/validate_host.sh.j2",
}

SCRIPT_FILES = {
    "scripts/start.sh",
    "scripts/validate.sh",
    "scripts/smoke.sh",
    "scripts/start_serving.sh",
    "scripts/smoke_benchmark.sh",
    "scripts/validate_host.sh",
}


def resolve_output_path(out: str) -> Path:
    candidate = Path(out)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.resolve()
    root = PROJECT_ROOT.resolve()
    if resolved == root:
        raise ValueError("output path must not be the project root")
    if root not in resolved.parents:
        raise ValueError("output path must stay inside the project")
    protected = {".pm-harness", "ai_server_generator", "templates", "profiles", "manifests", "tests"}
    rel_parts = resolved.relative_to(root).parts
    if rel_parts and rel_parts[0] in protected:
        raise ValueError(f"output path must not be inside protected directory: {rel_parts[0]}")
    return resolved


def _container_model_path(model_path: str) -> str:
    raw = Path(model_path)
    if raw.is_absolute():
        return str(raw)
    if raw.parts and raw.parts[0] == "models":
        return "/" + "/".join(raw.parts)
    if raw.parts[:2] == (".", "models"):
        return "/" + "/".join(raw.parts[1:])
    text = model_path[2:] if model_path.startswith("./") else model_path
    if text.startswith("models/"):
        return "/" + text
    return model_path


def build_context(
    *,
    setup_name: str,
    profile_name: str,
    access: str,
    model_path: str,
    auth: str,
    lan_allowlist: str,
    preset_alias: str = "",
    preset_name: str = "",
    preset_summary: str = "",
    capability_tags: str = "custom",
    memory_guidance: str = "Custom model path; verify host memory before launch.",
    shorthand_mode: bool = False,
) -> dict[str, Any]:
    profiles = load_profiles()
    setups = load_setups()
    if profile_name not in profiles:
        raise ValueError(f"unknown profile: {profile_name}")
    if setup_name not in setups:
        raise ValueError(f"unknown setup: {setup_name}")
    setup = setups[setup_name]
    if profile_name not in setup.get("supported_profiles", []):
        raise ValueError(f"profile {profile_name} is not supported by setup {setup_name}")
    if access not in setup.get("supported_access", []):
        raise ValueError(f"access {access} is not supported by setup {setup_name}")
    normalized_allowlist = lan_allowlist.strip()
    if access == "lan" and (auth != "bearer-token" or not normalized_allowlist):
        raise ValueError("LAN generation requires --auth bearer-token and --lan-allowlist")

    profile = profiles[profile_name]
    context: dict[str, Any] = dict(profile)
    context.update(
        {
            "setup": setup_name,
            "profile": profile_name,
            "access": access,
            "model_path": model_path,
            "container_model_path": _container_model_path(model_path),
            "auth": auth,
            "auth_token": "change-me-strong-token" if auth == "bearer-token" else "",
            "lan_allowlist": normalized_allowlist,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "required_files": setup["required_files"],
            "preset_alias": preset_alias,
            "preset_name": preset_name,
            "preset_summary": preset_summary,
            "capability_tags": capability_tags,
            "memory_guidance": memory_guidance,
            "shorthand_mode": shorthand_mode,
            "resolved_setup": setup_name,
            "resolved_profile": profile_name,
            "resolved_access": access,
            "quick_start_command": "./scripts/start.sh",
            "quick_validate_command": "./scripts/validate.sh",
            "quick_smoke_command": "./scripts/smoke.sh",
        }
    )
    return context


def planned_files() -> list[str]:
    return list(TEMPLATE_MAP.keys())


def render_workspace(
    *,
    setup_name: str,
    profile_name: str,
    access: str,
    model_path: str,
    out: str,
    force: bool,
    dry_run: bool,
    auth: str = "none",
    lan_allowlist: str = "",
    preset_alias: str = "",
    preset_name: str = "",
    preset_summary: str = "",
    capability_tags: str = "custom",
    memory_guidance: str = "Custom model path; verify host memory before launch.",
    shorthand_mode: bool = False,
) -> tuple[Path, list[str]]:
    out_path = resolve_output_path(out)
    context = build_context(
        setup_name=setup_name,
        profile_name=profile_name,
        access=access,
        model_path=model_path,
        auth=auth,
        lan_allowlist=lan_allowlist,
        preset_alias=preset_alias,
        preset_name=preset_name,
        preset_summary=preset_summary,
        capability_tags=capability_tags,
        memory_guidance=memory_guidance,
        shorthand_mode=shorthand_mode,
    )
    files = planned_files()
    if dry_run:
        return out_path, files

    if out_path.exists():
        if not force:
            raise ValueError(f"output path already exists; use --force to overwrite: {out_path}")
        if not out_path.is_dir():
            raise ValueError(f"output path exists and is not a directory: {out_path}")
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True, exist_ok=False)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir() / setup_name)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    for rel_path, template_name in TEMPLATE_MAP.items():
        destination = out_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        rendered = env.get_template(template_name).render(**context)
        destination.write_text(rendered, encoding="utf-8")
        if rel_path in SCRIPT_FILES:
            os.chmod(destination, 0o755)
    return out_path, files
