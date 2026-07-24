from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import shutil
import tempfile
import unicodedata
import uuid
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
    "scripts/stop.sh": "scripts/stop.sh.j2",
    "scripts/start_serving.sh": "scripts/start_serving.sh.j2",
    "scripts/smoke_benchmark.sh": "scripts/smoke_benchmark.sh.j2",
    "scripts/validate_host.sh": "scripts/validate_host.sh.j2",
}

SCRIPT_FILES = {
    "scripts/start.sh",
    "scripts/validate.sh",
    "scripts/smoke.sh",
    "scripts/stop.sh",
    "scripts/start_serving.sh",
    "scripts/smoke_benchmark.sh",
    "scripts/validate_host.sh",
}

# Serving image pinned by digest so a moved tag cannot change what runs. The
# tag is kept alongside the digest for readability only; Docker resolves the
# digest. This is the multi-arch OCI index (linux/amd64, arm64, s390x) for
# ghcr.io/ggml-org/llama.cpp:server, resolved 2026-07-24. The previously used
# ghcr.io/ggerganov/llama.cpp repository no longer exists and returns 404.
# To update, run scripts/resolve_image_digest.sh and paste the result here.
SERVING_IMAGE_REPOSITORY = "ghcr.io/ggml-org/llama.cpp"
SERVING_IMAGE_TAG = "server"
SERVING_IMAGE_DIGEST = (
    "sha256:4f02c560799a1569be08b0183d52b94b0d4a6e4b88f52f20562d2334c73837d4"
)
SERVING_IMAGE = f"{SERVING_IMAGE_REPOSITORY}:{SERVING_IMAGE_TAG}@{SERVING_IMAGE_DIGEST}"

OWNERSHIP_FILE = ".ai-server-generated.json"
OWNERSHIP_SCHEMA = "ai-server-workspace-owner-v1"
MANIFEST_SCHEMA = "ai-server-generated-v1"
LEGACY_REQUIRED_FILES = {
    "docker-compose.yml",
    ".env",
    "manifest.json",
    "README.md",
    "runbook.md",
    "scripts/start_serving.sh",
    "scripts/smoke_benchmark.sh",
    "scripts/validate_host.sh",
}
LOCALHOST_SECURITY_POSTURE = {
    "exposure": "localhost-only",
    "host_bind": "127.0.0.1",
    "authentication": "not-applicable-localhost",
    "tls": "not-configured-localhost",
    "allowlist_enforcement": "not-configured-localhost",
    "lan_status": "disabled-pending-secure-gateway",
}


def _reject_symlink_components(path: Path) -> None:
    root = PROJECT_ROOT.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError("output path must stay inside the project") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"output path must not traverse a symlink: {current}")


def resolve_output_path(out: str) -> Path:
    if not isinstance(out, str):
        raise ValueError("output path must be text")
    _validate_text("output path", out)
    candidate = Path(out)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    # abspath normalizes "." and ".." without following symlinks, allowing us
    # to reject symlink traversal explicitly before resolving the final path.
    candidate = Path(os.path.abspath(candidate))
    generated_root = (PROJECT_ROOT / "generated").resolve()
    if candidate == generated_root:
        raise ValueError("output path must be a strict descendant of generated/")
    if generated_root not in candidate.parents:
        raise ValueError("output path must be a strict descendant of generated/")
    _reject_symlink_components(candidate)
    resolved = candidate.resolve(strict=False)
    if generated_root not in resolved.parents:
        raise ValueError("output path must stay inside generated/ after resolving symlinks")
    return resolved


def _validate_text(name: str, value: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    if not value and not allow_empty:
        raise ValueError(f"{name} must not be empty")
    for char in value:
        if char in "\x00\r\n" or unicodedata.category(char) in {"Cc", "Cf", "Cs"}:
            raise ValueError(f"{name} must not contain control characters")
    return value


def _validate_model_path(model_path: str) -> str:
    value = _validate_text("model path", model_path)
    if any(part == ".." for part in Path(value).parts):
        raise ValueError("model path must not contain parent traversal")
    return value


def _normalize_allowlist(value: str) -> str:
    value = _validate_text("LAN allowlist", value, allow_empty=True).strip()
    if not value:
        return ""
    try:
        return str(ipaddress.ip_network(value, strict=False))
    except ValueError as exc:
        raise ValueError("LAN allowlist must be a valid IPv4 or IPv6 CIDR") from exc


def _compose_yaml_scalar(value: Any) -> str:
    # A JSON string scalar is also a YAML 1.2 string scalar. Emitting this one
    # context with json.dumps gives deterministic quoting without adding a
    # second serialization dependency to the generator. Compose performs a
    # separate dollar-expansion pass, so double dollars before YAML emission.
    return json.dumps(str(value).replace("$", "$$"), ensure_ascii=False)


def _dotenv_quote(value: Any) -> str:
    text = str(value)
    _validate_text("dotenv value", text, allow_empty=True)
    # Compose treats single-quoted dotenv values literally. Backslash escaping
    # keeps apostrophes and backslashes inside that single scalar.
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _host_model_path(model_path: str) -> str:
    raw = Path(model_path).expanduser()
    if not raw.is_absolute():
        raw = PROJECT_ROOT / raw
    return str(raw.resolve(strict=False))


def _generation_fingerprint(context: dict[str, Any], setup_name: str) -> str:
    digest = hashlib.sha256()
    canonical_context = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest.update(canonical_context)
    template_root = templates_dir() / setup_name
    for rel_path, template_name in sorted(TEMPLATE_MAP.items()):
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((template_root / template_name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _manifest_object(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "setup": context["setup"],
        "profile": context["profile"],
        "access": context["access"],
        "model_path": context["host_model_path"],
        "host_model_path": context["host_model_path"],
        "container_model_path": context["container_model_path"],
        "model_contract": context["model_contract"],
        "serving_image": context["serving_image"],
        "preset_alias": context["preset_alias"],
        "preset_name": context["preset_name"],
        "preset_summary": context["preset_summary"],
        "capability_tags": context["capability_tags"],
        "memory_guidance": context["memory_guidance"],
        "shorthand_mode": context["shorthand_mode"],
        "resolved_setup": context["resolved_setup"],
        "resolved_profile": context["resolved_profile"],
        "resolved_access": context["resolved_access"],
        "host_port": str(context["host_port"]),
        "auth": context["auth"],
        "lan_allowlist": context["lan_allowlist"],
        "security_posture": context["security_posture"],
        "quick_commands": {
            "validate": context["quick_validate_command"],
            "start": context["quick_start_command"],
            "smoke": context["quick_smoke_command"],
            "stop": context["quick_stop_command"],
        },
        "required_files": context["required_files"],
        "generation_fingerprint": context["generation_fingerprint"],
    }


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
    model_contract: dict[str, Any] | None = None,
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

    model_path = _validate_model_path(model_path)
    normalized_allowlist = _normalize_allowlist(lan_allowlist)
    for name, value in (
        ("auth", auth),
        ("preset alias", preset_alias),
        ("preset name", preset_name),
        ("preset summary", preset_summary),
        ("capability tags", capability_tags),
        ("memory guidance", memory_guidance),
    ):
        _validate_text(name, value, allow_empty=True)
    if access == "lan":
        raise ValueError(
            "LAN generation requires an authenticated TLS gateway with mechanically "
            "enforced client allowlisting and is disabled until that work is complete. "
            "Generate with --access localhost; do not expose the generated service "
            "through a LAN bind or port forward."
        )
    if auth != "none":
        raise ValueError(
            "bearer-token auth is not supported for localhost generation; "
            "no credential will be generated or embedded"
        )
    if normalized_allowlist:
        raise ValueError(
            "--lan-allowlist is not enforced in localhost mode; remove it rather than "
            "relying on an inert network-policy claim"
        )

    profile = profiles[profile_name]
    context: dict[str, Any] = dict(profile)
    context.update(
        {
            "setup": setup_name,
            "profile": profile_name,
            "access": access,
            "model_path": _host_model_path(model_path),
            "host_model_path": _host_model_path(model_path),
            "container_model_path": "/models/model.gguf",
            "model_contract": model_contract or {
                "contract_version": 1,
                "metadata_status": "custom-artifact-unverified",
                "architecture": "unknown",
                "parameter_billions": None,
                "quantization_assumption": "unknown",
                "estimated_model_gb": None,
                "kv_cache_gb_at_default_context": None,
                "runtime_buffer_gb": None,
                "minimum_host_ram_gb": None,
                "recommended_host_ram_gb": None,
                "default_context": None,
            },
            "serving_image": SERVING_IMAGE,
            "auth": "none",
            "lan_allowlist": "",
            "security_posture": dict(LOCALHOST_SECURITY_POSTURE),
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
            "quick_stop_command": "./scripts/stop.sh",
        }
    )
    context["generation_fingerprint"] = _generation_fingerprint(context, setup_name)
    context["manifest_json"] = json.dumps(
        _manifest_object(context),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    for name in (
        "profile",
        "host_port",
        "container_model_path",
        "host_model_path",
        "ctx_size",
        "batch_size",
        "threads",
        "n_predict",
        "mem_limit",
        "cpu_limit",
    ):
        context[f"{name}_env"] = _dotenv_quote(context[name])
    context["container_model_path_yaml"] = _compose_yaml_scalar(context["container_model_path"])
    context["host_model_path_yaml"] = _compose_yaml_scalar(context["host_model_path"])
    return context


def planned_files() -> list[str]:
    return [*TEMPLATE_MAP.keys(), OWNERSHIP_FILE]


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _is_owned_workspace(path: Path) -> bool:
    marker_path = path / OWNERSHIP_FILE
    marker = _read_json_object(marker_path)
    manifest = _read_json_object(path / "manifest.json")
    if manifest is None or manifest.get("schema") != MANIFEST_SCHEMA:
        return False
    if marker_path.exists():
        if marker is None:
            return False
        return (
            marker.get("schema") == OWNERSHIP_SCHEMA
            and marker.get("manifest_schema") == MANIFEST_SCHEMA
            and marker.get("generation_fingerprint") == manifest.get("generation_fingerprint")
        )

    # Controlled legacy rule: pre-marker workspaces are recognized only when
    # their v1 manifest names a known setup and every declared required file
    # is a safe, existing regular file under that directory.
    setup_name = manifest.get("setup")
    required_files = manifest.get("required_files")
    if setup_name not in load_setups() or not isinstance(required_files, list) or not required_files:
        return False
    if any(not isinstance(item, str) for item in required_files):
        return False
    if not LEGACY_REQUIRED_FILES.issubset(set(required_files)):
        return False
    for rel_text in required_files:
        if not isinstance(rel_text, str) or not rel_text:
            return False
        rel = Path(rel_text)
        if rel.is_absolute() or ".." in rel.parts:
            return False
        item = path / rel
        if item.is_symlink() or not item.is_file():
            return False
    return True


def _write_text_file(path: Path, content: str, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    os.chmod(path, mode)


def _render_to_staging(staging: Path, setup_name: str, context: dict[str, Any]) -> None:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir() / setup_name)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    for rel_path, template_name in TEMPLATE_MAP.items():
        destination = staging / rel_path
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        rendered = env.get_template(template_name).render(**context)
        mode = 0o755 if rel_path in SCRIPT_FILES else (0o600 if rel_path == ".env" else 0o644)
        _write_text_file(destination, rendered, mode)

    marker = json.dumps(
        {
            "schema": OWNERSHIP_SCHEMA,
            "manifest_schema": MANIFEST_SCHEMA,
            "generation_fingerprint": context["generation_fingerprint"],
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    _write_text_file(staging / OWNERSHIP_FILE, marker + "\n", 0o644)


def _backup_path(out_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return out_path.with_name(f".{out_path.name}.backup-{timestamp}-{uuid.uuid4().hex[:8]}")


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
    model_contract: dict[str, Any] | None = None,
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
        model_contract=model_contract,
        shorthand_mode=shorthand_mode,
    )
    files = planned_files()
    if dry_run:
        return out_path, files

    generated_root = (PROJECT_ROOT / "generated").resolve()
    generated_root.mkdir(mode=0o755, parents=True, exist_ok=True)
    out_path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if out_path.exists():
        if not force:
            raise ValueError(f"output path already exists; use --force to overwrite: {out_path}")
        if out_path.is_symlink() or not out_path.is_dir():
            raise ValueError(f"output path exists and is not a safe directory: {out_path}")
        if not _is_owned_workspace(out_path):
            raise ValueError(
                "refusing to overwrite unrecognized directory; "
                f"missing a valid generated ownership marker or legacy manifest: {out_path}"
            )

    staging = Path(
        tempfile.mkdtemp(prefix=f".{out_path.name}.staging-", dir=str(out_path.parent))
    )
    os.chmod(staging, 0o755)
    backup: Path | None = None
    try:
        _render_to_staging(staging, setup_name, context)
        # Late import avoids a module cycle: validator uses resolve_output_path.
        from .validator import validate_workspace

        validation_errors = validate_workspace(str(staging))
        if validation_errors:
            raise ValueError(
                "generated staging workspace failed validation: " + "; ".join(validation_errors)
            )

        if out_path.exists():
            backup = _backup_path(out_path)
            os.replace(out_path, backup)
        try:
            os.replace(staging, out_path)
        except BaseException:
            if backup is not None and backup.exists() and not out_path.exists():
                os.replace(backup, out_path)
                backup = None
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return out_path, files
