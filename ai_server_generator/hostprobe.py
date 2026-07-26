"""Bounded, stdlib-only host observations used by ``doctor``.

Every probe is deliberately best-effort: an absent or malformed platform
surface becomes an ``unknown`` fact, never a failing doctor invocation.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import signal
import subprocess
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal

FactStatus = Literal["measured", "unknown", "not-applicable"]
CommandStatus = Literal["ok", "missing", "timeout", "error"]
TextReader = Callable[[str], str | None]
CommandRunner = Callable[[list[str]], "CommandResult"]
PathLister = Callable[[str], list[str]]
HOST_BINARY_ALLOWLIST = frozenset(
    {"docker", "nvidia-smi", "sysctl", "vm_stat", "sw_vers", "system_profiler"}
)
MAX_COMMAND_OUTPUT_BYTES = 64 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Fact:
    value: object
    unit: str
    status: FactStatus
    source: str

    def json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CommandResult:
    status: CommandStatus
    returncode: int | None
    stdout: str
    stderr: str
    stdout_truncated: bool = False
    stderr_truncated: bool = False


def unknown(unit: str, source: str) -> Fact:
    return Fact(None, unit, "unknown", source)


def not_applicable(unit: str, source: str) -> Fact:
    return Fact(None, unit, "not-applicable", source)


def read_text_file(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def run_command(argv: list[str], timeout: float = 5.0) -> CommandResult:
    if not argv or argv[0] not in HOST_BINARY_ALLOWLIST:
        return CommandResult("missing", None, "", "binary is not allowlisted")
    binary = shutil.which(argv[0])
    if binary is None:
        return CommandResult("missing", None, "", f"{argv[0]} not found")
    captured: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = {"stdout": False, "stderr": False}

    def drain(name: str, stream: object) -> None:
        reader = stream
        try:
            while True:
                chunk = reader.read(8192)  # type: ignore[attr-defined]
                if not chunk:
                    return
                remaining = MAX_COMMAND_OUTPUT_BYTES - len(captured[name])
                if remaining > 0:
                    captured[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[name] = True
        except (OSError, ValueError):
            return

    try:
        process = subprocess.Popen(
            [binary, *argv[1:]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=(os.name == "posix"),
        )
        assert process.stdout is not None and process.stderr is not None
        threads = [
            threading.Thread(target=drain, args=("stdout", process.stdout)),
            threading.Thread(target=drain, args=("stderr", process.stderr)),
        ]
        for thread in threads:
            thread.start()
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()
            status: CommandStatus = "timeout"
            returncode = None
        else:
            status = "ok" if returncode == 0 else "error"
        for thread in threads:
            thread.join(timeout=1.0)
        process.stdout.close()
        process.stderr.close()
        for thread in threads:
            thread.join(timeout=1.0)
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return CommandResult("error", None, "", str(exc))
    return CommandResult(
        status,
        returncode,
        captured["stdout"].decode("utf-8", "replace"),
        captured["stderr"].decode("utf-8", "replace"),
        truncated["stdout"],
        truncated["stderr"],
    )


def _number_fact(value: float | None, unit: str, source: str) -> Fact:
    return (
        unknown(unit, source)
        if value is None or value <= 0
        else Fact(round(value, 3), unit, "measured", source)
    )


def _meminfo_value(text: str | None, key: str) -> float | None:
    if not text:
        return None
    match = re.search(rf"^{re.escape(key)}:\s*(\d+)\s*kB", text, re.MULTILINE)
    return int(match.group(1)) / (1024 * 1024) if match else None


def _sysctl(runner: CommandRunner, key: str) -> str | None:
    result = runner(["sysctl", "-n", key])
    return result.stdout.strip() if result.status == "ok" and result.stdout.strip() else None


def _default_lister(pattern: str) -> list[str]:
    return [str(path) for path in Path("/").glob(pattern.lstrip("/"))]


def probe_memory(
    reader: TextReader = read_text_file,
    runner: CommandRunner = run_command,
    sysconf: Callable[[str], int] = os.sysconf,
    system: str | None = None,
) -> dict[str, Fact]:
    system = system or platform.system()
    if system == "Darwin":
        raw_total = _sysctl(runner, "hw.memsize")
        try:
            total = int(raw_total) / (1024**3) if raw_total else None
        except ValueError:
            total = None
        if total is None:
            try:
                total = sysconf("SC_PHYS_PAGES") * sysconf("SC_PAGE_SIZE") / (1024**3)
            except (OSError, ValueError, KeyError):
                total = None
        vm = runner(["vm_stat"])
        pages = None
        if vm.status == "ok":
            page = re.search(r"page size of (\d+) bytes", vm.stdout)
            values = {
                name: re.search(rf"^{name}:\s+(\d+)", vm.stdout, re.MULTILINE)
                for name in ("Pages free", "Pages inactive", "Pages speculative")
            }
            if page and all(values.values()):
                pages = (
                    sum(int(match.group(1)) for match in values.values() if match)
                    * int(page.group(1))
                    / (1024**3)
                )
        return {
            "memory.total_gb": _number_fact(total, "GiB", "sysctl hw.memsize"),
            "memory.available_gb": _number_fact(
                pages, "GiB", "vm_stat free+inactive+speculative; conservative floor"
            ),
        }
    text = reader("/proc/meminfo")
    total = _meminfo_value(text, "MemTotal")
    if total is None:
        try:
            total = sysconf("SC_PHYS_PAGES") * sysconf("SC_PAGE_SIZE") / (1024**3)
        except (OSError, ValueError, KeyError):
            pass
    return {
        "memory.total_gb": _number_fact(total, "GiB", "/proc/meminfo MemTotal or sysconf"),
        "memory.available_gb": _number_fact(
            _meminfo_value(text, "MemAvailable"), "GiB", "/proc/meminfo MemAvailable"
        ),
    }


def probe_execution_context(reader: TextReader = read_text_file) -> dict[str, Fact]:
    docker = reader("/.dockerenv") is not None
    podman = reader("/run/.containerenv") is not None
    cgroup = reader("/proc/1/cgroup") or ""
    memory_max = reader("/sys/fs/cgroup/memory.max")
    v1_limit = reader("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    mountinfo = reader("/proc/self/mountinfo") or ""
    rung = "host"
    if docker:
        rung = "dockerenv"
    elif podman:
        rung = "containerenv"
    elif any(item in cgroup for item in ("docker", "containerd", "kubepods", "lxc")):
        rung = "cgroup-name"
    elif cgroup.strip() == "0::/" and memory_max and memory_max.strip() != "max":
        rung = "cgroup-v2-cap"
    elif " - overlay " in mountinfo:
        rung = "overlay-root"
    in_container = rung != "host"
    raw_limit = memory_max or v1_limit
    limit = None
    if raw_limit and raw_limit.strip() not in {"max", "9223372036854771712"}:
        try:
            limit = int(raw_limit.strip()) / (1024**3)
        except ValueError:
            pass
    cpu_max = reader("/sys/fs/cgroup/cpu.max")
    v1_quota, v1_period = (
        reader("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
        reader("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),
    )
    quota = None
    if cpu_max:
        fields = cpu_max.split()
        if len(fields) == 2 and fields[0] != "max":
            try:
                quota = int(fields[0]) / int(fields[1])
            except (ValueError, ZeroDivisionError):
                pass
    elif v1_quota and v1_period and v1_quota.strip() != "-1":
        try:
            quota = int(v1_quota.strip()) / int(v1_period.strip())
        except (ValueError, ZeroDivisionError):
            pass
    return {
        "execution.in_container": Fact(
            in_container, "bool", "measured", f"container detection rung: {rung}"
        ),
        "execution.observation_scope": Fact(
            "container" if in_container else "host",
            "enum",
            "measured",
            f"container detection rung: {rung}",
        ),
        "memory.cgroup_limit_gb": _number_fact(limit, "GiB", "cgroup memory limit")
        if limit
        else not_applicable("GiB", "no cgroup memory limit set"),
        "cpu.cgroup_quota_cores": _number_fact(quota, "cores", "cgroup cpu.max")
        if quota
        else not_applicable("cores", "no cgroup CPU quota set"),
    }


def probe_virtualization(
    facts: dict[str, Fact], reader: TextReader = read_text_file, runner: CommandRunner = run_command
) -> dict[str, Fact]:
    """Prevent VM-scoped observations from being presented as machine facts."""
    del runner  # Kept injectable with the other probes; this ladder uses kernel files.
    osrelease = reader("/proc/sys/kernel/osrelease")
    hostname = reader("/etc/hostname") or ""
    mountinfo = reader("/proc/self/mountinfo") or ""
    hypervisor = reader("/sys/hypervisor/type") or ""
    product = reader("/sys/class/dmi/id/product_name") or ""
    candidates = (
        ("linuxkit", osrelease or "", "linuxkit"),
        ("docker-desktop", hostname, "docker-desktop"),
        ("virtiofs", mountinfo, "virtiofs"),
        ("grpcfuse", mountinfo, "grpcfuse"),
        ("fakeowner", mountinfo, "fakeowner"),
        ("hypervisor", hypervisor, None),
        (
            "dmi-hypervisor",
            product,
            "kvm|vmware|virtualbox|hyper-v|qemu|bochs|xen|parallels|virtual machine",
        ),
    )
    signal = next(
        (
            name
            for name, value, needle in candidates
            if value and (needle is None or re.search(needle, value, re.IGNORECASE))
        ),
        None,
    )
    if signal is None and osrelease is None:
        return {
            "execution.virtualization": unknown(
                "enum", "virtualization status unavailable: /proc/sys/kernel/osrelease unreadable"
            ),
            "execution.virtualization_signal": unknown(
                "text", "virtualization status unavailable: /proc/sys/kernel/osrelease unreadable"
            ),
            "execution.machine_observable": Fact(
                False,
                "bool",
                "measured",
                "physical machine is conservatively unobservable when virtualization status is unknown",
            ),
        }
    if signal is None:
        return {
            "execution.virtualization": Fact(
                "none", "enum", "measured", "no virtualization signal"
            ),
            "execution.virtualization_signal": not_applicable("text", "no virtualization signal"),
            "execution.machine_observable": Fact(
                True, "bool", "measured", "no virtualization signal"
            ),
        }
    source = "the physical machine is not observable from inside a virtual machine; re-run doctor on the host for an accurate tier"
    result = {
        "execution.virtualization": Fact(
            "virtual-machine", "enum", "measured", f"virtualization signal: {signal}"
        ),
        "execution.virtualization_signal": Fact(
            signal, "text", "measured", "virtualization ladder"
        ),
        "execution.machine_observable": Fact(False, "bool", "measured", source),
        "execution.observation_scope": Fact(
            "container-on-virtualized-host", "enum", "measured", f"virtualization signal: {signal}"
        ),
    }
    for key in ("memory.total_gb", "memory.available_gb"):
        old = facts.get(key)
        if old and old.status == "measured":
            result[key.replace("memory.", "memory.vm_")] = Fact(
                old.value, old.unit, "measured", "VM-scoped observation; not physical machine"
            )
        result[key] = unknown("GiB", source)
    for key in (
        "cpu.physical_cores",
        "cpu.logical_cores",
        "cpu.performance_cores",
        "cpu.efficiency_cores",
    ):
        old = facts.get(key)
        if key == "cpu.logical_cores" and old and old.status == "measured":
            result["cpu.vm_logical_cores"] = Fact(
                old.value, old.unit, "measured", "VM-scoped observation; not physical machine"
            )
        result[key] = unknown("cores", source)
    return result


def probe_cpu(
    reader: TextReader = read_text_file,
    lister: PathLister = _default_lister,
    runner: CommandRunner = run_command,
    system: str | None = None,
    machine: str | None = None,
    cpu_count: Callable[[], int | None] = os.cpu_count,
) -> dict[str, Fact]:
    system, machine = system or platform.system(), (machine or platform.machine()).lower()
    if system == "Darwin":
        generation, hardware = (
            _sysctl(runner, "machdep.cpu.brand_string"),
            _sysctl(runner, "hw.model"),
        )
        physical, logical = _sysctl(runner, "hw.physicalcpu"), _sysctl(runner, "hw.logicalcpu")
        perf, efficiency = (
            _sysctl(runner, "hw.perflevel0.physicalcpu"),
            _sysctl(runner, "hw.perflevel1.physicalcpu"),
        )
        apple = machine in {"arm64", "aarch64"}
        return {
            "cpu.model": Fact("CPU family (redacted)", "text", "measured", "Darwin CPU family")
            if generation
            else unknown("text", "sysctl CPU model unavailable"),
            "cpu.generation": Fact(
                generation, "text", "measured", "sysctl machdep.cpu.brand_string"
            )
            if generation
            else unknown("text", "sysctl CPU generation unavailable"),
            "cpu.hw_model": Fact(hardware, "text", "measured", "sysctl hw.model")
            if hardware
            else unknown("text", "sysctl hardware model unavailable"),
            "cpu.physical_cores": _number_fact(
                float(physical) if physical and physical.isdigit() else None,
                "cores",
                "sysctl hw.physicalcpu",
            ),
            "cpu.logical_cores": _number_fact(
                float(logical) if logical and logical.isdigit() else None,
                "cores",
                "sysctl hw.logicalcpu",
            ),
            "cpu.performance_cores": _number_fact(
                float(perf) if perf and perf.isdigit() else None, "cores", "sysctl perflevel0"
            )
            if apple
            else not_applicable(
                "cores", "perflevel keys are Apple Silicon only; see cpu.physical_cores"
            ),
            "cpu.efficiency_cores": _number_fact(
                float(efficiency) if efficiency and efficiency.isdigit() else None,
                "cores",
                "sysctl perflevel1",
            )
            if apple
            else not_applicable(
                "cores", "perflevel keys are Apple Silicon only; see cpu.physical_cores"
            ),
            "cpu.arm_ids": not_applicable("text", "ARM ids apply only to Linux ARM"),
        }
    text = reader("/proc/cpuinfo") or ""
    topology: set[tuple[str, str]] = set()
    for topology_path in lister("/sys/devices/system/cpu/cpu*/topology/core_id"):
        core = reader(topology_path)
        package = reader(topology_path.rsplit("/", 1)[0] + "/physical_package_id")
        if core is not None and package is not None:
            topology.add((package.strip(), core.strip()))
    pairs = re.findall(r"physical id\s*:\s*(\S+).*?core id\s*:\s*(\S+)", text, re.DOTALL)
    model = re.search(r"^model name\s*:\s*(.+)$", text, re.MULTILINE)
    arm_implementer, arm_part = (
        re.search(r"^CPU implementer\s*:\s*(\S+)", text, re.MULTILINE),
        re.search(r"^CPU part\s*:\s*(\S+)", text, re.MULTILINE),
    )
    raw_model = model.group(1).strip() if model else None
    model_source = "proc/cpuinfo model name"
    if not raw_model:
        raw_model = (
            reader("/sys/firmware/devicetree/base/model")
            or reader("/sys/class/dmi/id/product_name")
            or ""
        ).strip() or None
        model_source = "device tree or DMI model"
    return {
        "cpu.model": Fact("CPU family (redacted)", "text", "measured", model_source)
        if raw_model
        else unknown("text", "Linux CPU model unavailable"),
        "cpu.generation": unknown("text", "generation unavailable on Linux"),
        "cpu.hw_model": unknown("text", "hardware model unavailable on Linux"),
        "cpu.physical_cores": _number_fact(
            float(len(topology) or len(set(pairs))) if (topology or pairs) else None,
            "cores",
            "sysfs topology or /proc/cpuinfo",
        ),
        "cpu.logical_cores": _number_fact(float(cpu_count() or 0), "cores", "os.cpu_count"),
        "cpu.performance_cores": not_applicable("cores", "not an Apple Silicon host"),
        "cpu.efficiency_cores": not_applicable("cores", "not an Apple Silicon host"),
        "cpu.arm_ids": Fact(
            f"implementer={arm_implementer.group(1)} part={arm_part.group(1)}",
            "text",
            "measured",
            "proc/cpuinfo raw ARM ids",
        )
        if arm_implementer and arm_part
        else not_applicable("text", "raw ARM ids unavailable"),
    }


def probe_disk(
    models_path: str | None = None,
    disk_usage: Callable[[str], shutil._ntuple_diskusage] = shutil.disk_usage,
) -> dict[str, Fact]:
    path = Path(models_path) if models_path else Path(__file__).resolve().parents[1] / "models"
    observed = path
    while not observed.exists() and observed.parent != observed:
        observed = observed.parent
    try:
        free = disk_usage(str(observed)).free / (1024**3)
        try:
            logical = (
                "models"
                if path.resolve().is_relative_to(PROJECT_ROOT / "models")
                else "external-models-path (redacted)"
            )
        except OSError:
            logical = "external-models-path (redacted)"
        source = "disk usage from configured models storage"
        if observed != path:
            source += "; nearest existing ancestor substituted"
        return {
            "disk.models_path": Fact(logical, "path", "measured", source),
            "disk.free_gb": _number_fact(free, "GiB", source),
        }
    except OSError:
        return {
            "disk.models_path": Fact(
                "external-models-path (redacted)", "path", "measured", "configured models storage"
            ),
            "disk.free_gb": unknown("GiB", "disk usage unavailable"),
        }


def probe_gpu(
    reader: TextReader = read_text_file,
    runner: CommandRunner = run_command,
    lister: PathLister = _default_lister,
    system: str | None = None,
    machine: str | None = None,
    observation_scope: str = "host",
) -> dict[str, Fact]:
    system, machine = system or platform.system(), machine or platform.machine()
    if (
        system == "Darwin"
        and machine.lower() in {"arm64", "aarch64"}
        and observation_scope == "host"
    ):
        return {
            "gpu.vendor": Fact("apple", "enum", "measured", "Darwin Apple Silicon"),
            "gpu.name": Fact("Apple GPU", "text", "measured", "unified Apple Silicon GPU"),
            "gpu.vram_gb": not_applicable("GiB", "Apple GPU uses unified memory"),
            "gpu.unified_memory": Fact(True, "bool", "measured", "Apple Silicon unified memory"),
            "gpu.container_reachable": not_applicable("bool", "host observation"),
        }
    nvidia = runner(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
    )
    if nvidia.status == "ok":
        parts = (
            [part.strip() for part in nvidia.stdout.splitlines()[0].split(",")]
            if nvidia.stdout.splitlines()
            else []
        )
        try:
            vram = float(parts[1]) / 1024
        except (IndexError, ValueError):
            vram = None
        if vram is not None:
            return {
                "gpu.vendor": Fact("nvidia", "enum", "measured", "nvidia-smi"),
                "gpu.name": Fact(
                    "NVIDIA GPU family", "text", "measured", "nvidia-smi redacted family"
                ),
                "gpu.vram_gb": _number_fact(vram, "GiB", "nvidia-smi memory total"),
                "gpu.unified_memory": Fact(False, "bool", "measured", "discrete GPU"),
                "gpu.container_reachable": Fact(True, "bool", "measured", "working nvidia-smi")
                if observation_scope != "host"
                else not_applicable("bool", "host observation"),
            }
    try:
        cards = lister("/sys/class/drm/card*/device/vendor")
    except OSError:
        cards = None
    vendors = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}
    matched_card = next(
        (card for card in (cards or []) if vendors.get((reader(card) or "").strip())), None
    )
    vendor_name = vendors.get((reader(matched_card) or "").strip()) if matched_card else None
    if vendor_name and matched_card:
        vram_path = matched_card.rsplit("/", 1)[0] + "/mem_info_vram_total"
        raw_vram = reader(vram_path)
        try:
            vram = int(raw_vram.strip()) / (1024**3) if raw_vram else None
        except ValueError:
            vram = None
        return {
            "gpu.vendor": Fact(vendor_name, "enum", "measured", "DRM PCI vendor id"),
            "gpu.name": Fact(
                f"{vendor_name} GPU family", "text", "measured", "DRM redacted family"
            ),
            "gpu.vram_gb": _number_fact(vram, "GiB", "DRM mem_info_vram_total"),
            "gpu.unified_memory": Fact(False, "bool", "measured", "not Apple Silicon"),
            "gpu.container_reachable": Fact(
                False, "bool", "measured", "no working nvidia-smi in container"
            )
            if observation_scope != "host"
            else not_applicable("bool", "host observation"),
        }
    if cards is None:
        vendor = unknown("enum", "DRM enumeration unavailable")
    elif cards:
        vendor = unknown("enum", "unrecognised DRM PCI vendor id")
    else:
        vendor = Fact("none", "enum", "measured", "DRM enumeration found no GPU")
    vram_fact = (
        not_applicable("GiB", "no GPU is reachable from this container")
        if observation_scope != "host" and vendor.value == "none"
        else unknown("GiB", "GPU VRAM unavailable")
    )
    return {
        "gpu.vendor": vendor,
        "gpu.name": unknown("text", "GPU name unavailable"),
        "gpu.vram_gb": vram_fact,
        "gpu.unified_memory": Fact(False, "bool", "measured", "not Apple Silicon"),
        "gpu.container_reachable": Fact(
            False, "bool", "measured", "no /dev/dri or working nvidia-smi in container"
        )
        if observation_scope != "host"
        else not_applicable("bool", "host observation"),
    }


def probe_docker(
    runner: CommandRunner = run_command,
    system: str | None = None,
    machine: str | None = None,
    gpu_vendor: str | None = None,
    gpu_nvidia_smi: bool = False,
) -> dict[str, Fact]:
    version, info, compose = (
        runner(["docker", "version", "--format", "{{.Server.Version}}"]),
        runner(["docker", "info"]),
        runner(["docker", "compose", "version"]),
    )
    present = version.status != "missing"
    reachable = info.status == "ok"
    runtimes = ["nvidia"] if reachable and "nvidia" in info.stdout.lower() else []
    host, container = (["cpu"] if reachable else []), (["cpu"] if reachable else [])
    if (
        reachable
        and (system or platform.system()) == "Darwin"
        and (machine or platform.machine()).lower() in {"arm64", "aarch64"}
    ):
        host.append("metal")
    if gpu_vendor == "nvidia" and gpu_nvidia_smi:
        host.append("cuda")
        if "nvidia" in runtimes:
            container.append("cuda")
    backends = {
        "host_capable": host,
        "container_reachable": container,
        "basis": {
            "docker_daemon_reachable": reachable,
            "gpu_vendor": gpu_vendor,
            "nvidia_smi_working": gpu_nvidia_smi,
            "nvidia_runtime_reported": "nvidia" in runtimes,
        },
    }
    return {
        "docker.cli_present": Fact(present, "bool", "measured", "docker command lookup"),
        "docker.daemon_reachable": Fact(reachable, "bool", "measured", "docker info"),
        "docker.engine_version": Fact(version.stdout.strip(), "text", "measured", "docker version")
        if version.status == "ok"
        else unknown("text", "docker version unavailable"),
        "docker.compose_version": Fact(
            compose.stdout.strip(), "text", "measured", "docker compose version"
        )
        if compose.status == "ok"
        else unknown("text", "docker compose unavailable"),
        "docker.gpu_runtimes": Fact(runtimes, "list", "measured", "docker info inventory")
        if reachable
        else unknown("list", "docker daemon unavailable"),
        "backends": Fact(backends, "object", "measured", "docker backend inventory"),
    }
