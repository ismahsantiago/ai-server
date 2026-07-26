"""Stable software-readiness gaps derived only from recorded facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GapSpec:
    severity: str
    title: str
    remediation: dict[str, str | None]
    blocks: list[str]


@dataclass(frozen=True)
class Gap:
    gap_id: str
    severity: str
    title: str
    triggered_by: list[dict[str, object]]
    remediation: dict[str, str | None]
    blocks: list[str]

    def json(self) -> dict[str, object]:
        return asdict(self)


def _spec(severity: str, title: str, summary: str, blocks: list[str]) -> GapSpec:
    return GapSpec(
        severity, title, {"summary": summary, "linux": summary, "macos": summary}, blocks
    )


GAP_REGISTRY = {
    "platform.unsupported": _spec(
        "blocking",
        "Unsupported platform",
        "Install or run doctor on a supported Linux or macOS host before serving a model.",
        ["run-any-model"],
    ),
    "docker.cli_missing": _spec(
        "blocking",
        "Docker is missing",
        "Install Docker, start it once, and re-run doctor before serving a model.",
        ["run-any-model"],
    ),
    "docker.daemon_unreachable": _spec(
        "blocking",
        "Docker daemon is unreachable",
        "Start Docker Desktop or Docker Engine and re-run doctor before serving a model.",
        ["run-any-model"],
    ),
    "docker.compose_missing": _spec(
        "blocking",
        "Docker Compose is missing",
        "Install or update Docker Compose v2, then re-run doctor before serving a model.",
        ["run-any-model"],
    ),
    "docker.engine_version_unknown": _spec(
        "advisory",
        "Docker version is unknown",
        "Run docker version manually and update Docker if it is older than the supported runtime.",
        [],
    ),
    "gpu.driver_missing": _spec(
        "degraded",
        "GPU driver is unavailable",
        "Install the vendor GPU driver, reboot if required, and re-run doctor for acceleration.",
        ["gpu-acceleration"],
    ),
    "gpu.container_runtime_missing": _spec(
        "degraded",
        "GPU is not available to Docker",
        "Install and configure the container GPU runtime, then re-run doctor for acceleration.",
        ["gpu-acceleration"],
    ),
    "gpu.unreachable_from_container": _spec(
        "advisory",
        "GPU is not reachable from this container",
        "Run on the host or use a supported GPU-enabled Linux container runtime for acceleration.",
        ["gpu-acceleration"],
    ),
    "memory.unobservable": _spec(
        "advisory",
        "Usable memory is unknown",
        "Re-run doctor on the host after usable memory measurement is available; recommendations are withheld.",
        ["recommendations"],
    ),
    "memory.insufficient_for_any_preset": _spec(
        "blocking",
        "Memory is below the smallest preset",
        "Free memory or use a machine with more usable memory, then re-run doctor.",
        ["run-any-model"],
    ),
    "cgroup.limit_below_preset_requirement": _spec(
        "degraded",
        "Container memory limit is too low",
        "Increase the container memory limit or Docker Desktop memory allocation, then re-run doctor.",
        ["run-any-model"],
    ),
    "execution.host_not_observable": _spec(
        "advisory",
        "Physical host is not observable",
        "Run doctor directly on the host, outside the virtualized container, for an accurate tier.",
        ["recommendations"],
    ),
    "disk.free_space_unknown": _spec(
        "advisory",
        "Free model storage is unknown",
        "Check free space on the models drive and re-run doctor before downloading model weights.",
        [],
    ),
    "disk.insufficient_free_space": _spec(
        "blocking",
        "Model storage is insufficient",
        "Free storage on the models drive or choose a larger models path, then re-run doctor.",
        ["run-any-model"],
    ),
}


def _fact(profile: dict[str, Any], key: str) -> dict[str, Any]:
    return profile.get("infrastructure", {}).get("facts", {}).get(key, {})


def _value(profile: dict[str, Any], key: str) -> Any:
    return _fact(profile, key).get("value")


def _measured(profile: dict[str, Any], key: str) -> bool:
    return _fact(profile, key).get("status") == "measured"


def _gap(identifier: str, profile: dict[str, Any], *keys: str) -> Gap:
    spec = GAP_REGISTRY[identifier]
    return Gap(
        identifier,
        spec.severity,
        spec.title,
        [{"fact_key": key, "observed_value": _value(profile, key)} for key in keys],
        spec.remediation,
        spec.blocks,
    )


def evaluate(profile: dict[str, Any]) -> list[Gap]:
    profile.get("infrastructure", {}).get("facts", {})
    if not profile.get("platform", {}).get("supported", True):
        return [_gap("platform.unsupported", profile)]
    gaps: list[Gap] = []
    if _value(profile, "docker.cli_present") is False:
        gaps.append(_gap("docker.cli_missing", profile, "docker.cli_present"))
    elif _value(profile, "docker.daemon_reachable") is False:
        gaps.append(_gap("docker.daemon_unreachable", profile, "docker.daemon_reachable"))
    if not _measured(profile, "docker.compose_version"):
        gaps.append(_gap("docker.compose_missing", profile, "docker.compose_version"))
    if not _measured(profile, "docker.engine_version"):
        gaps.append(_gap("docker.engine_version_unknown", profile, "docker.engine_version"))
    if _value(profile, "gpu.vendor") in {"nvidia", "amd", "intel"} and not _measured(
        profile, "gpu.vram_gb"
    ):
        gaps.append(_gap("gpu.driver_missing", profile, "gpu.vendor", "gpu.vram_gb"))
    runtimes = _value(profile, "docker.gpu_runtimes") or []
    if _value(profile, "gpu.vendor") == "nvidia" and "nvidia" not in runtimes:
        gaps.append(
            _gap("gpu.container_runtime_missing", profile, "gpu.vendor", "docker.gpu_runtimes")
        )
    if not _measured(profile, "memory.available_gb"):
        gaps.append(_gap("memory.unobservable", profile, "memory.available_gb"))
    else:
        from .tiering import boundaries

        minimum = boundaries()[0]
        if float(_value(profile, "memory.available_gb")) < minimum:
            gaps.append(_gap("memory.insufficient_for_any_preset", profile, "memory.available_gb"))
        if (
            _measured(profile, "memory.cgroup_limit_gb")
            and float(_value(profile, "memory.cgroup_limit_gb")) < minimum
        ):
            gaps.append(
                _gap("cgroup.limit_below_preset_requirement", profile, "memory.cgroup_limit_gb")
            )
    if not _measured(profile, "disk.free_gb"):
        gaps.append(_gap("disk.free_space_unknown", profile, "disk.free_gb"))
    elif float(_value(profile, "disk.free_gb")) < 2.2:
        gaps.append(_gap("disk.insufficient_free_space", profile, "disk.free_gb"))
    if _value(profile, "gpu.container_reachable") is False:
        gaps.append(_gap("gpu.unreachable_from_container", profile, "gpu.container_reachable"))
    if _value(profile, "execution.machine_observable") is False:
        gaps.append(_gap("execution.host_not_observable", profile, "execution.machine_observable"))
    return gaps
