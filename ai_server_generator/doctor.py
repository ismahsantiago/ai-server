"""The non-invasive ``doctor`` command implementation."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

from . import hostprobe
from .hostprofile import assemble, serialize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts"


def collect(models_path: str | None = None) -> dict[str, Any]:
    facts: dict[str, hostprobe.Fact] = {}
    facts.update(hostprobe.probe_cpu())
    facts.update(hostprobe.probe_memory())
    facts.update(hostprobe.probe_execution_context())
    facts.update(hostprobe.probe_virtualization(facts))
    facts.update(
        hostprobe.probe_gpu(observation_scope=str(facts["execution.observation_scope"].value))
    )
    facts.update(hostprobe.probe_disk(models_path))
    gpu = facts["gpu.vendor"]
    facts.update(
        hostprobe.probe_docker(gpu_vendor=str(gpu.value), gpu_nvidia_smi=gpu.source == "nvidia-smi")
    )
    return assemble(facts)


def unsupported_profile() -> dict[str, Any]:
    return assemble({}, supported=False)


def render_text(profile: dict[str, Any]) -> str:
    lines = ["INFRASTRUCTURE (measured)"]
    for key, fact in sorted(profile["infrastructure"]["facts"].items()):
        lines.append(
            f"{key}: {fact['value'] if fact['status'] == 'measured' else fact['status']} ({fact['source']})"
        )
    lines.append("SOFTWARE READINESS")
    gaps = profile["software_readiness"]["gaps"]
    if not gaps:
        lines.append("OK")
    for gap in gaps:
        lines.extend((f"{gap['severity'].upper()}: {gap['title']}", gap["remediation"]["summary"]))
    lines.append("DERIVED (recommendations)")
    tier = profile["recommendations"].get("tier")
    if tier:
        lines.append(
            "Provisional tier; recommendations are derived planning assumptions, not runtime verification."
        )
        lines.append(f"Tier: {tier['tier_label']} ({tier['confidence']})")
        for item in profile["recommendations"]["runnable_presets"]:
            lines.append(
                f"FIT: {item['alias']} ({item['selected_profile']}, context {item['context']})"
            )
        for item in profile["recommendations"]["excluded_presets"]:
            lines.append(f"NO-FIT: {item.get('alias', 'catalog')} ({item['reason']})")
    scope = profile["infrastructure"]["facts"].get("execution.observation_scope", {}).get("value")
    if scope in {"container", "container-on-virtualized-host"}:
        lines.append("CONTAINER")
        lines.append("Cgroup limits are reported separately from physical-machine observations.")
        if scope == "container-on-virtualized-host":
            lines.append(
                "This is a virtual machine — the physical machine's RAM and CPU cannot be seen from here. Re-run doctor on the host for an accurate tier."
            )
    return "\n".join(lines) + "\n"


def resolve_output_path(output: str) -> Path:
    candidate = Path(output)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or not candidate.parts
        or candidate.parts[0] != "artifacts"
    ):
        raise ValueError("doctor --out must be a relative path beneath artifacts/")
    path = PROJECT_ROOT / candidate
    try:
        path.relative_to(ARTIFACTS_ROOT)
    except ValueError as exc:
        raise ValueError("doctor --out must be a strict artifacts/ descendant") from exc
    current = PROJECT_ROOT
    for component in candidate.parts:
        current = current / component
        if current.exists() and current.is_symlink():
            raise ValueError("doctor --out may not traverse a symlink")
    if path == ARTIFACTS_ROOT:
        raise ValueError("doctor --out must name a file beneath artifacts/")
    return path


def _open_private_parent(path: Path) -> tuple[int, str]:
    """Open the output parent without following any path component symlink."""
    relative = path.relative_to(PROJECT_ROOT)
    flags = os.O_RDONLY | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(PROJECT_ROOT, flags)
    try:
        for component in relative.parts[:-1]:
            try:
                child_fd = os.open(component, flags | nofollow, dir_fd=directory_fd)
            except FileNotFoundError:
                os.mkdir(component, mode=0o700, dir_fd=directory_fd)
                child_fd = os.open(component, flags | nofollow, dir_fd=directory_fd)
            os.chmod(component, 0o700, dir_fd=directory_fd, follow_symlinks=False)
            os.close(directory_fd)
            directory_fd = child_fd
        return directory_fd, relative.name
    except BaseException:
        os.close(directory_fd)
        raise


def write_atomic(path: Path, content: str) -> None:
    directory_fd, final_name = _open_private_parent(path)
    temporary = f".host-profile-{secrets.token_hex(16)}"
    try:
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=directory_fd,
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
        except BaseException:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except OSError:
                pass
            raise
        os.replace(temporary, final_name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


def run(*, output: str, fmt: str, no_write: bool, models_path: str | None) -> int:
    import platform

    destination = resolve_output_path(output)
    profile = (
        unsupported_profile()
        if platform.system() not in {"Linux", "Darwin"}
        else collect(models_path)
    )
    rendered = serialize(profile)
    if not no_write and fmt != "json":
        write_atomic(destination, rendered)
    if fmt == "json":
        print(rendered, end="")
    else:
        print(render_text(profile), end="")
        if not no_write:
            print(f"Host profile written to {destination.relative_to(PROJECT_ROOT)}")
    return 0
