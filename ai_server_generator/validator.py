from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

from .data import PROJECT_ROOT
from .render import (
    LOCALHOST_SECURITY_POSTURE,
    MANIFEST_SCHEMA,
    MODELS_ROOT,
    OWNERSHIP_FILE,
    OWNERSHIP_SCHEMA,
    SERVING_IMAGE,
    resolve_output_path,
)

REQUIRED_MANIFEST_KEYS = {
    "schema",
    "setup",
    "profile",
    "access",
    "model_path",
    "host_model_path",
    "container_model_path",
    "model_contract",
    "serving_image",
    "runtime_contract",
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
    "lan_allowlist",
    "security_posture",
    "required_files",
    "generation_fingerprint",
}

TOKEN_PLACEHOLDERS = {
    "changeme",
    "change-me",
    "change-me-strong-token",
    "default",
    "example",
    "password",
    "placeholder",
    "secret",
    "token",
}


def _load_dotenv(path: Path, errors: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.is_symlink() or not path.is_file():
        errors.append(".env must be a regular file")
        return values
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        errors.append(".env must have mode 0600")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f".env cannot be read as UTF-8: {exc}")
        return values
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in line:
            errors.append(f".env line {line_number} is not a key=value assignment")
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in values:
            errors.append(f".env has an invalid or duplicate key on line {line_number}")
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] == "'":
            encoded = value[1:-1]
            decoded: list[str] = []
            index = 0
            while index < len(encoded):
                if encoded[index] == "\\" and index + 1 < len(encoded):
                    index += 1
                decoded.append(encoded[index])
                index += 1
            value = "".join(decoded)
        elif len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        values[key] = value
    return values


def _compose_config(workspace: Path, errors: list[str]) -> dict[str, Any] | None:
    compose_path = workspace / "docker-compose.yml"
    if compose_path.is_symlink() or not compose_path.is_file():
        errors.append("docker-compose.yml must be a regular file")
        return None
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--project-directory",
                str(workspace),
                "-f",
                str(compose_path),
                "config",
                "--format",
                "json",
            ],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        errors.append(f"docker compose config is unavailable: {exc}")
        return None
    if result.returncode != 0:
        errors.append("docker compose config rejected docker-compose.yml")
        return None
    try:
        config = json.loads(result.stdout)
    except json.JSONDecodeError:
        errors.append("docker compose config did not return valid JSON")
        return None
    if not isinstance(config, dict):
        errors.append("docker compose config must return an object")
        return None
    return config


def _validate_manifest_files(
    workspace: Path, manifest: dict[str, Any], errors: list[str]
) -> None:
    required_files = manifest.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        errors.append("manifest required_files must be a non-empty array")
        return
    for rel_text in required_files:
        if not isinstance(rel_text, str) or not rel_text:
            errors.append("manifest required_files entries must be non-empty strings")
            continue
        rel = Path(rel_text)
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"unsafe required file path: {rel_text}")
            continue
        item = workspace / rel
        if item.is_symlink() or not item.is_file():
            errors.append(f"missing or unsafe required file: {rel_text}")


def _validate_security_posture(manifest: dict[str, Any], errors: list[str]) -> None:
    posture = manifest.get("security_posture")
    if not isinstance(posture, dict):
        errors.append("manifest security_posture must be an object")
        return
    for key, expected in LOCALHOST_SECURITY_POSTURE.items():
        if posture.get(key) != expected:
            errors.append(f"manifest security_posture.{key} must be {expected}")
    if set(posture) != set(LOCALHOST_SECURITY_POSTURE):
        errors.append("manifest security_posture contains unsupported claims")


def _validate_service(
    service: dict[str, Any],
    manifest: dict[str, Any],
    dotenv: dict[str, str],
    errors: list[str],
) -> None:
    host_port = str(manifest.get("host_port", ""))
    ports = service.get("ports")
    if not isinstance(ports, list) or len(ports) != 1:
        errors.append("serving service must publish exactly one localhost port")
    else:
        port = ports[0]
        if (
            not isinstance(port, dict)
            or port.get("host_ip") != "127.0.0.1"
            or str(port.get("published")) != host_port
            or port.get("target") != 8000
        ):
            errors.append("serving port must bind explicitly to 127.0.0.1")

    if service.get("image") != manifest.get("serving_image"):
        errors.append("resolved Compose image must match manifest serving_image")

    user = str(service.get("user", "")).strip().lower()
    if not user or user in {"0", "0:0", "root", "root:root"} or user.startswith("0:"):
        errors.append("serving container must declare a non-root user and group")
    if service.get("privileged") is True:
        errors.append("serving container must not be privileged")
    cap_drop = service.get("cap_drop")
    if not isinstance(cap_drop, list) or "ALL" not in {str(item).upper() for item in cap_drop}:
        errors.append("serving container must drop ALL capabilities")
    security_opt = service.get("security_opt")
    if not isinstance(security_opt, list) or "no-new-privileges:true" not in security_opt:
        errors.append("serving container must set no-new-privileges:true")
    if service.get("read_only") is not True:
        errors.append("serving container root filesystem must be read-only")
    tmpfs = service.get("tmpfs")
    if not isinstance(tmpfs, list) or not any(
        str(item).split(":", 1)[0] == "/tmp" for item in tmpfs
    ):
        errors.append("serving container must provide a bounded /tmp tmpfs")

    pids_limit = service.get("pids_limit")
    if not isinstance(pids_limit, int) or pids_limit <= 0:
        errors.append("serving container must set a positive PID limit")
    for key in ("cpus", "mem_limit"):
        value = service.get(key)
        try:
            bounded = value is not None and float(value) > 0
        except (TypeError, ValueError):
            bounded = False
        if not bounded:
            errors.append(f"serving container must set a positive {key} resource limit")

    volumes = service.get("volumes")
    if not isinstance(volumes, list) or not volumes:
        errors.append("serving container must have a read-only model mount")
    else:
        model_mounts = []
        for mount in volumes:
            if not isinstance(mount, dict):
                errors.append("serving container mount must be structurally valid")
                continue
            if mount.get("type") == "bind" and mount.get("read_only") is not True:
                errors.append("serving container must not have writable host bind mounts")
            if mount.get("target") == "/models/model.gguf":
                model_mounts.append(mount)
        if len(model_mounts) != 1 or model_mounts[0].get("read_only") is not True:
            errors.append(
                "serving container must mount /models/model.gguf exactly once read-only"
            )
        elif str(model_mounts[0].get("source")) != manifest.get("host_model_path"):
            errors.append("serving model bind source must match manifest host_model_path")

    command = service.get("command")
    container_model_path = manifest.get("container_model_path")
    if not isinstance(command, list):
        errors.append("serving command must be an argument array")
    else:
        try:
            model_index = command.index("--model")
            model_value = command[model_index + 1]
        except (ValueError, IndexError):
            errors.append("serving command must declare --model")
        else:
            # Compose retains ``$$`` in its normalized model to represent the
            # literal ``$`` that will reach the container.
            if str(model_value).replace("$$", "$") != container_model_path:
                errors.append("serving command model path must match manifest")
        if "--api-key" in command:
            errors.append("localhost serving command must not enable bearer-token auth")

    if dotenv.get("MODEL_PATH") != container_model_path:
        errors.append(".env MODEL_PATH must match manifest container_model_path")
    if dotenv.get("MODEL_HOST_PATH") != manifest.get("host_model_path"):
        errors.append(".env MODEL_HOST_PATH must match manifest host_model_path")


def _validate_compose_structure(
    workspace: Path,
    manifest: dict[str, Any],
    dotenv: dict[str, str],
    errors: list[str],
) -> None:
    compose_path = workspace / "docker-compose.yml"
    if compose_path.is_symlink() or not compose_path.is_file():
        errors.append("docker-compose.yml must be a regular file")
        return
    try:
        compose = compose_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"docker-compose.yml cannot be read as UTF-8: {exc}")
        return
    required_fragments = {
        '      - "127.0.0.1:': "serving port must bind explicitly to 127.0.0.1",
        '    user: "65532:65532"': "serving container must declare a non-root user and group",
        "    cap_drop:\n      - ALL": "serving container must drop ALL capabilities",
        "      - no-new-privileges:true": "serving container must set no-new-privileges:true",
        "    pids_limit: 256": "serving container must set a positive PID limit",
        "    mem_limit:": "serving container must set a positive mem_limit resource limit",
        "    cpus:": "serving container must set a positive cpus resource limit",
        '    restart: "no"': "serving container restart policy must be bounded",
        "        target: /models/model.gguf": (
            "serving container must mount /models/model.gguf exactly once read-only"
        ),
        "        read_only: true": "serving container must not have writable host bind mounts",
        "      - --model\n      - \"/models/model.gguf\"": (
            "serving command model path must match manifest"
        ),
    }
    for fragment, message in required_fragments.items():
        if fragment not in compose:
            errors.append(message)
    if not re.search(r"^    read_only: true$", compose, flags=re.MULTILINE):
        errors.append("serving container root filesystem must be read-only")
    if "\n    privileged: true" in compose:
        errors.append("serving container must not be privileged")
    host_path = manifest.get("host_model_path")
    if not isinstance(host_path, str) or not Path(host_path).is_absolute():
        errors.append("manifest host_model_path must be absolute")
    else:
        escaped = json.dumps(host_path.replace("$", "$$"), ensure_ascii=False)
        if f"        source: {escaped}" not in compose:
            errors.append("serving model bind source must match manifest host_model_path")
    if manifest.get("container_model_path") != "/models/model.gguf":
        errors.append("manifest container_model_path must be /models/model.gguf")
    if manifest.get("model_path") != host_path:
        errors.append("manifest model_path compatibility field must match host_model_path")
    if dotenv.get("MODEL_PATH") != "/models/model.gguf":
        errors.append(".env MODEL_PATH must match manifest container_model_path")
    if dotenv.get("MODEL_HOST_PATH") != host_path:
        errors.append(".env MODEL_HOST_PATH must match manifest host_model_path")
    if re.search(r'^\s*-\s*["\']?0\.0\.0\.0:', compose, flags=re.MULTILINE):
        errors.append("serving port must bind explicitly to 127.0.0.1")
    _validate_serving_image(manifest, compose, errors)


def _validate_serving_image(manifest: dict[str, Any], compose: str, errors: list[str]) -> None:
    image = manifest.get("serving_image")
    if image != SERVING_IMAGE:
        errors.append("manifest serving_image must match the pinned serving image")
        return
    # A digest is what makes the reference immutable; a bare tag can be moved
    # under the workspace without any file changing.
    if "@sha256:" not in image:
        errors.append("manifest serving_image must be pinned by digest")
        return
    if f"    image: {image}" not in compose:
        errors.append("Compose image must be the digest-pinned serving image")


def _validate_model_contract(manifest: dict[str, Any], errors: list[str]) -> None:
    contract = manifest.get("model_contract")
    if not isinstance(contract, dict):
        errors.append("manifest model_contract must be an object")
        return
    required = {
        "contract_version",
        "metadata_status",
        "artifact_repository",
        "artifact_revision",
        "artifact_filename",
        "artifact_size_bytes",
        "artifact_sha256",
        "chat_template",
        "architecture",
        "parameter_billions",
        "quantization_assumption",
        "estimated_model_gb",
        "kv_cache_gb_at_default_context",
        "runtime_buffer_gb",
        "minimum_host_ram_gb",
        "recommended_host_ram_gb",
        "default_context",
    }
    missing = sorted(required - set(contract))
    if missing:
        errors.append(f"manifest model_contract missing keys: {', '.join(missing)}")
    if contract.get("contract_version") != 2:
        errors.append("manifest model_contract.contract_version must be 2")
    if contract.get("metadata_status") not in {
        "planning-assumption-only",
        "custom-artifact-unverified",
        "verified-artifact",
    }:
        errors.append("manifest model_contract.metadata_status is unsupported")
    if contract.get("metadata_status") == "verified-artifact":
        verified_fields = {
            "artifact_repository": str,
            "artifact_revision": str,
            "artifact_filename": str,
            "artifact_size_bytes": int,
            "artifact_sha256": str,
            "chat_template": str,
        }
        for name, expected_type in verified_fields.items():
            value = contract.get(name)
            if not isinstance(value, expected_type) or isinstance(value, bool) or not value:
                errors.append(f"manifest verified model_contract.{name} is incomplete")
        digest = contract.get("artifact_sha256")
        if isinstance(digest, str) and (
            len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)
        ):
            errors.append("manifest model_contract.artifact_sha256 must be lowercase SHA-256")


def _validate_runtime_contract(manifest: dict[str, Any], errors: list[str]) -> None:
    contract = manifest.get("runtime_contract")
    if not isinstance(contract, dict):
        errors.append("manifest runtime_contract must be an object")
        return
    required = {
        "contract_version",
        "implementation",
        "image_repository",
        "image_tag",
        "image_digest",
        "runtime_version",
        "runtime_revision",
        "flag_schema",
        "compatibility_status",
    }
    missing = sorted(required - set(contract))
    if missing:
        errors.append(f"manifest runtime_contract missing keys: {', '.join(missing)}")
    if contract.get("contract_version") != 1:
        errors.append("manifest runtime_contract.contract_version must be 1")
    if contract.get("compatibility_status") not in {
        "static-template-only",
        "runtime-verified",
    }:
        errors.append("manifest runtime_contract.compatibility_status is unsupported")
    expected_image = (
        f"{contract.get('image_repository')}:{contract.get('image_tag')}"
        f"@{contract.get('image_digest')}"
    )
    if manifest.get("serving_image") != expected_image:
        errors.append("manifest runtime_contract image fields must match serving_image")
    if contract.get("compatibility_status") == "runtime-verified":
        for name in ("runtime_version", "runtime_revision"):
            value = contract.get(name)
            if not isinstance(value, str) or not value:
                errors.append(f"manifest verified runtime_contract.{name} is incomplete")


def _validate_model_source(manifest: dict[str, Any], errors: list[str]) -> None:
    host_path_value = manifest.get("host_model_path")
    if not isinstance(host_path_value, str) or not host_path_value:
        errors.append("manifest host_model_path must be a non-empty string")
        return
    host_path = Path(host_path_value)
    if not host_path.is_absolute():
        errors.append("manifest host_model_path must be absolute")
        return
    resolved = host_path.resolve(strict=False)
    try:
        resolved.relative_to(MODELS_ROOT)
    except ValueError:
        errors.append("manifest host_model_path must resolve inside the repository models/ root")
        return
    if resolved == MODELS_ROOT:
        errors.append("manifest host_model_path must resolve to a file below the repository models/ root")
    elif resolved.exists() and not resolved.is_file():
        errors.append("manifest host_model_path must resolve to a regular file")


def _validate_host(
    workspace: Path,
    manifest: dict[str, Any],
    dotenv: dict[str, str],
    errors: list[str],
) -> None:
    host_path_value = manifest.get("host_model_path")
    if isinstance(host_path_value, str):
        host_path = Path(host_path_value)
        try:
            mode = host_path.stat().st_mode
        except OSError:
            errors.append(f"host model does not exist: {host_path_value}")
        else:
            if not stat.S_ISREG(mode):
                errors.append(f"host model must be a regular file: {host_path_value}")
            if mode & 0o444 == 0 or not os.access(host_path, os.R_OK):
                errors.append(f"host model is not readable: {host_path_value}")
            if host_path.suffix.lower() != ".gguf":
                errors.append(f"host model extension must be .gguf: {host_path_value}")
    try:
        version = subprocess.run(
            ["docker", "compose", "version"],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        errors.append(f"Docker Compose is unavailable: {exc}")
    else:
        if version.returncode != 0:
            errors.append("Docker Compose is unavailable")
        else:
            config = _compose_config(workspace, errors)
            if config is not None:
                services = config.get("services")
                if not isinstance(services, dict) or set(services) != {"llama-server"}:
                    errors.append("Compose must contain exactly the llama-server service")
                elif isinstance(services["llama-server"], dict):
                    _validate_service(services["llama-server"], manifest, dotenv, errors)
                else:
                    errors.append("Compose llama-server service must be an object")


def _validate_runtime(
    workspace: Path, manifest: dict[str, Any], errors: list[str]
) -> None:
    try:
        info = subprocess.run(
            ["docker", "info"],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        errors.append(f"runtime not verified: Docker daemon unavailable: {exc}")
        return
    if info.returncode != 0:
        errors.append("runtime not verified: Docker daemon unavailable")
        return
    endpoint = f"http://127.0.0.1:{manifest.get('host_port', '')}/health"
    try:
        health = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--max-time", "5", endpoint],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        errors.append(f"runtime not verified: health client unavailable: {exc}")
        return
    if health.returncode != 0:
        errors.append(f"runtime not verified: endpoint is not healthy: {endpoint}")


def validate_workspace(path_text: str, *, tier: str = "structure") -> list[str]:
    if tier not in {"structure", "host", "runtime"}:
        raise ValueError(f"unknown validation tier: {tier}")
    workspace = resolve_output_path(path_text)
    errors: list[str] = []
    if not workspace.is_dir():
        return [f"generated directory does not exist: {workspace.relative_to(PROJECT_ROOT)}"]

    manifest_path = workspace / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return ["manifest.json must be a regular file"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"manifest.json is invalid JSON: {exc}"]
    if not isinstance(manifest, dict):
        return ["manifest.json must contain an object"]
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append(f"manifest schema must be {MANIFEST_SCHEMA}")

    marker_path = workspace / OWNERSHIP_FILE
    if marker_path.exists() and (marker_path.is_symlink() or not marker_path.is_file()):
        errors.append(f"{OWNERSHIP_FILE} must be a regular file")
    elif marker_path.is_file():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{OWNERSHIP_FILE} is invalid JSON: {exc}")
        else:
            if not isinstance(marker, dict) or marker.get("schema") != OWNERSHIP_SCHEMA:
                errors.append(f"{OWNERSHIP_FILE} has an invalid ownership schema")
            elif marker.get("manifest_schema") != MANIFEST_SCHEMA:
                errors.append(f"{OWNERSHIP_FILE} has an invalid manifest schema")
            elif marker.get("generation_fingerprint") != manifest.get(
                "generation_fingerprint"
            ):
                errors.append(f"{OWNERSHIP_FILE} does not match manifest.json")

    for key in sorted(REQUIRED_MANIFEST_KEYS - set(manifest)):
        errors.append(f"manifest missing key: {key}")
    _validate_manifest_files(workspace, manifest, errors)

    quick_commands = manifest.get("quick_commands")
    if not isinstance(quick_commands, dict):
        errors.append("manifest quick_commands must be an object")
    else:
        for key in ("validate", "start", "smoke"):
            if not quick_commands.get(key):
                errors.append(f"manifest quick_commands missing {key}")

    if manifest.get("access") != "localhost" or manifest.get("resolved_access") != "localhost":
        errors.append("only localhost generated workspaces are supported")
    if manifest.get("auth") != "none":
        errors.append("localhost workspace auth must be none")
    if manifest.get("lan_allowlist") not in {"", None}:
        errors.append("localhost workspace must not claim a LAN allowlist")
    _validate_security_posture(manifest, errors)
    _validate_model_contract(manifest, errors)
    _validate_runtime_contract(manifest, errors)
    _validate_model_source(manifest, errors)

    dotenv = _load_dotenv(workspace / ".env", errors)
    token = dotenv.get("API_BEARER_TOKEN")
    if token is not None:
        normalized = token.strip().lower()
        if (
            len(token.strip()) < 32
            or normalized in TOKEN_PLACEHOLDERS
            or any(placeholder in normalized for placeholder in TOKEN_PLACEHOLDERS)
        ):
            errors.append(".env contains a blank, weak, or placeholder bearer token")
        errors.append("localhost workspace must not contain a bearer token")
    if "LAN_ALLOWLIST" in dotenv:
        errors.append("localhost workspace must not contain an inert LAN allowlist")

    _validate_compose_structure(workspace, manifest, dotenv, errors)
    if tier in {"host", "runtime"} and not errors:
        _validate_host(workspace, manifest, dotenv, errors)
    if tier == "runtime" and not errors:
        _validate_runtime(workspace, manifest, errors)

    return errors
