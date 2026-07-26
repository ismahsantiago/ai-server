import ast
import contextlib
import io
import json
import shutil
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from ai_server_generator import cli, doctor, hostprobe
from ai_server_generator.containercheck import SKIPPED, validate_output
from ai_server_generator.hostprobe import Fact
from ai_server_generator.hostprofile import assemble
from ai_server_generator.readiness import GAP_REGISTRY, evaluate
from ai_server_generator.tiering import boundaries, recommend


def facts(available=16.0, disk=100.0):
    return {
        "memory.available_gb": Fact(available, "GiB", "measured", "fixture"),
        "memory.total_gb": Fact(available, "GiB", "measured", "fixture"),
        "memory.cgroup_limit_gb": Fact(None, "GiB", "not-applicable", "fixture"),
        "disk.free_gb": Fact(disk, "GiB", "measured", "fixture"),
        "docker.cli_present": Fact(True, "bool", "measured", "fixture"),
        "docker.daemon_reachable": Fact(True, "bool", "measured", "fixture"),
        "docker.compose_version": Fact("v2", "text", "measured", "fixture"),
        "execution.machine_observable": Fact(True, "bool", "measured", "fixture"),
    }


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = Path(__file__).parents[1] / "artifacts" / "test-doctor-security"
        shutil.rmtree(self.artifacts, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(self.artifacts, ignore_errors=True)

    def test_approved_boundaries_are_contract_derived(self):
        self.assertEqual(boundaries(), [3.25, 6.8, 7.5, 11.75, 17.5])

    def test_default_profile_envelope_is_non_fit(self):
        profile = assemble(facts(available=64.0))
        runnable, excluded = recommend(profile)
        self.assertIn("smollm3-3b", [item["alias"] for item in runnable])
        reasons = {item["alias"]: item["reason"] for item in excluded}
        self.assertEqual(reasons["devstral-small-v25.07"], "profile-envelope")
        self.assertEqual(reasons["phi-4-14b"], "profile-envelope")

    def test_tiering_is_catalog_derived_and_apple_unified_memory_is_complete(self):
        synthetic = type(
            "Preset",
            (),
            {
                "estimated_model_gb": 1.0,
                "kv_cache_gb_at_default_context": 0.25,
                "runtime_buffer_gb": 0.5,
            },
        )()
        with mock.patch("ai_server_generator.tiering.ordered_presets", return_value=[synthetic]):
            self.assertEqual(boundaries(), [1.75])
        apple = facts()
        apple.update(
            {
                "gpu.vendor": Fact("apple", "enum", "measured", "fixture"),
                "gpu.vram_gb": Fact(None, "GiB", "not-applicable", "fixture"),
                "cpu.performance_cores": Fact(6, "cores", "measured", "fixture"),
            }
        )
        profile = assemble(apple)
        tier = profile["recommendations"]["tier"]
        self.assertEqual(tier["confidence"], "high")
        self.assertEqual(tier["basis"]["cpu.performance_cores"], 6)
        self.assertNotIn("gpu.vram_gb", tier["undetermined_inputs"])

    def test_recommendation_partition_preserves_profiles_context_and_basis(self):
        expected = {
            6.0: {"smollm3-3b"},
            16.0: {"smollm3-3b", "qwen3-coder-7b", "ornith-9b"},
            64.0: {"smollm3-3b", "qwen3-coder-7b", "ornith-9b"},
        }
        for available, aliases in expected.items():
            profile = assemble(facts(available=available))
            runnable = profile["recommendations"]["runnable_presets"]
            self.assertEqual({entry["alias"] for entry in runnable}, aliases)
            for entry in runnable + profile["recommendations"]["excluded_presets"]:
                self.assertTrue(
                    {
                        "estimated_model_gb",
                        "kv_cache_gb_at_default_context",
                        "runtime_buffer_gb",
                        "footprint_gb",
                        "disk_free_gb",
                    }.issubset(entry["basis"])
                )
                self.assertIn("selected_profile", entry)
                self.assertIn("context", entry)
                self.assertIn("mem_limit", entry)
                self.assertIn("cpus", entry)
                self.assertEqual(entry["pids_limit"], 256)

    def test_unknown_memory_withholds_fit(self):
        values = facts()
        values["memory.available_gb"] = Fact(None, "GiB", "unknown", "fixture")
        profile = assemble(values)
        self.assertEqual(profile["recommendations"]["runnable_presets"], [])
        self.assertEqual(
            profile["recommendations"]["excluded_presets"][0]["reason"], "usable-memory-unknown"
        )

    def test_cli_writes_profile_and_json_does_not_write(self):
        output = "artifacts/test-doctor-security/host.json"
        path = Path(__file__).parents[1] / output
        profile = assemble(facts())
        with mock.patch("ai_server_generator.doctor.collect", return_value=profile):
            self.assertEqual(cli.main(["doctor", "--out", output]), 0)
            self.assertEqual(json.loads(path.read_text())["host_profile_version"], 1)
        json_path = self.artifacts / "json.json"
        output_text = io.StringIO()
        with (
            mock.patch("ai_server_generator.doctor.collect", return_value=profile),
            contextlib.redirect_stdout(output_text),
        ):
            self.assertEqual(
                cli.main(
                    [
                        "doctor",
                        "--format",
                        "json",
                        "--out",
                        "artifacts/test-doctor-security/json.json",
                    ]
                ),
                0,
            )
        self.assertFalse(json_path.exists())
        self.assertEqual(json.loads(output_text.getvalue()), profile)
        no_write = self.artifacts / "no-write.json"
        with mock.patch("ai_server_generator.doctor.collect", return_value=profile):
            self.assertEqual(
                cli.main(
                    [
                        "doctor",
                        "--no-write",
                        "--out",
                        "artifacts/test-doctor-security/no-write.json",
                    ]
                ),
                0,
            )
        self.assertFalse(no_write.exists())

    def test_output_path_rejects_escapes_and_symlinks_and_uses_private_modes(self):
        for value in ("/tmp/host.json", "../host.json", "outside.json", "artifacts/../host.json"):
            with self.assertRaises(ValueError):
                doctor.resolve_output_path(value)
        self.artifacts.parent.mkdir(parents=True, exist_ok=True)
        link = self.artifacts.parent / "test-doctor-security"
        link.symlink_to(Path("/tmp"))
        with self.assertRaises(ValueError):
            doctor.resolve_output_path("artifacts/test-doctor-security/host.json")
        link.unlink()
        self.artifacts.parent.chmod(0o755)
        target = doctor.resolve_output_path("artifacts/test-doctor-security/private/host.json")
        doctor.write_atomic(target, "{}")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(target.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.artifacts.parent.stat().st_mode), 0o700)

    def test_command_output_is_capped_for_normal_error_and_timeout(self):
        payload = "x" * (hostprobe.MAX_COMMAND_OUTPUT_BYTES + 100)
        with mock.patch.object(hostprobe, "HOST_BINARY_ALLOWLIST", frozenset({sys.executable})):
            normal = hostprobe.run_command([sys.executable, "-c", f"print({payload!r})"])
            error = hostprobe.run_command(
                [
                    sys.executable,
                    "-c",
                    f"import sys; sys.stderr.write({payload!r}); raise SystemExit(2)",
                ]
            )
            timeout = hostprobe.run_command(
                [
                    sys.executable,
                    "-c",
                    f"import sys,time; sys.stdout.write({payload!r}); sys.stdout.flush(); time.sleep(1)",
                ],
                timeout=0.01,
            )
        self.assertEqual(normal.status, "ok")
        self.assertTrue(normal.stdout_truncated)
        self.assertEqual(error.status, "error")
        self.assertTrue(error.stderr_truncated)
        self.assertEqual(timeout.status, "timeout")
        self.assertLessEqual(len(timeout.stdout.encode()), hostprobe.MAX_COMMAND_OUTPUT_BYTES)
        self.assertEqual(
            hostprobe.run_command(["definitely-not-an-allowlisted-binary"]).status, "missing"
        )

    def test_cpu_proc_fallback_unknown_and_intel_mac_contract(self):
        x86 = hostprobe.probe_cpu(
            lambda path: "model name : Xeon\nphysical id : 0\ncore id : 0\n\nmodel name : Xeon\nphysical id : 1\ncore id : 0\n"
            if path == "/proc/cpuinfo"
            else None,
            lambda _: [],
            system="Linux",
            cpu_count=lambda: 4,
        )
        self.assertEqual(x86["cpu.physical_cores"].value, 2.0)
        self.assertEqual(x86["cpu.model"].status, "measured")
        absent = hostprobe.probe_cpu(
            lambda _: None, lambda _: [], system="Linux", cpu_count=lambda: None
        )
        self.assertEqual(absent["cpu.physical_cores"].status, "unknown")
        values = {
            "machdep.cpu.brand_string": "Intel Core i7",
            "hw.model": "MacBookPro16,1",
            "hw.physicalcpu": "4",
            "hw.logicalcpu": "8",
        }
        intel = hostprobe.probe_cpu(
            runner=lambda argv: hostprobe.CommandResult("ok", 0, values.get(argv[-1], ""), ""),
            system="Darwin",
            machine="x86_64",
        )
        self.assertEqual(intel["cpu.physical_cores"].value, 4.0)
        self.assertEqual(intel["cpu.logical_cores"].value, 8.0)
        self.assertEqual(intel["cpu.performance_cores"].status, "not-applicable")
        self.assertEqual(intel["cpu.efficiency_cores"].status, "not-applicable")

    def test_timeout_kills_child_that_keeps_inherited_pipe_open(self):
        child = "import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)']); time.sleep(10)"
        with mock.patch.object(hostprobe, "HOST_BINARY_ALLOWLIST", frozenset({sys.executable})):
            started = time.monotonic()
            result = hostprobe.run_command([sys.executable, "-c", child], timeout=0.05)
        self.assertEqual(result.status, "timeout")
        self.assertLess(time.monotonic() - started, 2.0)

    def test_external_models_and_absolute_facts_are_redacted(self):
        disk = hostprobe.probe_disk(
            "/Users/example/models",
            disk_usage=lambda _: type("Usage", (), {"free": 10 * 1024**3})(),
        )
        self.assertEqual(disk["disk.models_path"].value, "external-models-path (redacted)")
        values = facts()
        values["cpu.model"] = Fact(
            "/Users/example/private", "text", "measured", "/home/example/source"
        )
        profile = assemble(values)
        serialized = json.dumps(profile)
        self.assertNotIn("/Users/example", serialized)
        self.assertNotIn("/home/example", serialized)
        self.assertNotIn("/Users/example", doctor.render_text(profile))

    def test_disk_error_path_is_redacted(self):
        disk = hostprobe.probe_disk(
            "/Users/example/models", disk_usage=lambda _: (_ for _ in ()).throw(OSError("nope"))
        )
        self.assertEqual(disk["disk.models_path"].value, "external-models-path (redacted)")
        self.assertNotIn("/Users/example", disk["disk.models_path"].source)

    def test_disk_probe_existing_missing_parent_and_error(self):
        def usage(_):
            return type("Usage", (), {"free": 5 * 1024**3})()
        existing = hostprobe.probe_disk("models", disk_usage=usage)
        missing = hostprobe.probe_disk("models/not-yet-created/weights", disk_usage=usage)
        failed = hostprobe.probe_disk(
            "models", disk_usage=lambda _: (_ for _ in ()).throw(OSError("unavailable"))
        )
        self.assertEqual(existing["disk.free_gb"].status, "measured")
        self.assertIn("nearest existing ancestor substituted", missing["disk.free_gb"].source)
        self.assertEqual(failed["disk.free_gb"].status, "unknown")

    def test_descriptor_relative_write_survives_parent_swap(self):
        path = doctor.resolve_output_path("artifacts/test-doctor-security/swap/host.json")
        original = doctor._open_private_parent
        moved = self.artifacts / "moved"

        def swap_after_open(target):
            descriptor, filename = original(target)
            parent = target.parent
            parent.rename(moved)
            parent.symlink_to("/tmp")
            return descriptor, filename

        with mock.patch(
            "ai_server_generator.doctor._open_private_parent", side_effect=swap_after_open
        ):
            doctor.write_atomic(path, "contained")
        self.assertEqual((moved / "host.json").read_text(), "contained")
        self.assertFalse((Path("/tmp") / "host.json").exists())

    def test_linux_arm_cpu_memory_cgroup_gpu_and_docker_fixtures(self):
        fixture = {
            "/proc/cpuinfo": "processor : 0\nCPU implementer : 0x61\nCPU part : 0x000\n",
            "/sys/devices/system/cpu/cpu0/topology/core_id": "0",
            "/sys/devices/system/cpu/cpu0/topology/physical_package_id": "0",
            "/sys/devices/system/cpu/cpu1/topology/core_id": "1",
            "/sys/devices/system/cpu/cpu1/topology/physical_package_id": "0",
            "/proc/meminfo": "MemTotal:       8388608 kB\nMemAvailable:   4194304 kB\n",
            "/.dockerenv": "",
            "/proc/1/cgroup": "0::/\n",
            "/sys/fs/cgroup/memory.max": "2147483648",
            "/sys/fs/cgroup/cpu.max": "max 100000",
            "/sys/class/drm/card0/device/vendor": "0x10de",
        }
        def reader(path):
            return fixture.get(path)
        def lister(pattern):
            return [
                    path for path in fixture if path.endswith("core_id") or path.endswith("vendor")
                ]
        def runner(argv):
            return hostprobe.CommandResult("missing", None, "", "")
        cpu = hostprobe.probe_cpu(
            reader, lister, runner, system="Linux", machine="aarch64", cpu_count=lambda: 2
        )
        memory = hostprobe.probe_memory(reader, runner, lambda _: 0, system="Linux")
        context = hostprobe.probe_execution_context(reader)
        gpu = hostprobe.probe_gpu(
            reader, runner, lister, system="Linux", observation_scope="container"
        )
        self.assertEqual(cpu["cpu.physical_cores"].value, 2.0)
        self.assertEqual(cpu["cpu.arm_ids"].value, "implementer=0x61 part=0x000")
        self.assertEqual(memory["memory.available_gb"].value, 4.0)
        self.assertEqual(context["memory.cgroup_limit_gb"].value, 2.0)
        self.assertEqual(context["cpu.cgroup_quota_cores"].status, "not-applicable")
        self.assertEqual(gpu["gpu.vendor"].value, "nvidia")

    def test_darwin_memory_cpu_and_backend_fixtures(self):
        values = {
            "hw.memsize": "17179869184",
            "machdep.cpu.brand_string": "Apple M1 Pro",
            "hw.model": "MacBookPro18,3",
            "hw.physicalcpu": "8",
            "hw.logicalcpu": "8",
            "hw.perflevel0.physicalcpu": "6",
            "hw.perflevel1.physicalcpu": "2",
        }
        vm = "Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 100.\nPages inactive: 100.\nPages speculative: 100.\n"

        def runner(argv):
            key = argv[-1]
            return hostprobe.CommandResult(
                "ok", 0, vm if key == "vm_stat" else values.get(key, ""), ""
            )

        memory = hostprobe.probe_memory(runner=runner, system="Darwin")
        cpu = hostprobe.probe_cpu(runner=runner, system="Darwin", machine="arm64")
        docker = hostprobe.probe_docker(
            runner=runner, system="Darwin", machine="arm64", gpu_vendor="nvidia"
        )
        self.assertEqual(memory["memory.total_gb"].value, 16.0)
        self.assertEqual(cpu["cpu.performance_cores"].value, 6.0)
        self.assertIn("metal", docker["backends"].value["host_capable"])

    def test_memory_probe_linux_and_darwin_degradations(self):
        def full(path):
            return ("MemTotal:       8388608 kB\nMemAvailable:   4194304 kB\n"
                    if path == "/proc/meminfo"
                    else None)
        def missing_available(path):
            return ("MemTotal:       8388608 kB\n" if path == "/proc/meminfo" else None)
        def absent(_):
            return None
        def runner(argv):
            return hostprobe.CommandResult("missing", None, "", "")
        self.assertEqual(
            hostprobe.probe_memory(full, runner, lambda _: 0, system="Linux")[
                "memory.total_gb"
            ].value,
            8.0,
        )
        self.assertEqual(
            hostprobe.probe_memory(missing_available, runner, lambda _: 0, system="Linux")[
                "memory.available_gb"
            ].status,
            "unknown",
        )
        fallback = hostprobe.probe_memory(
            absent,
            runner,
            lambda key: {"SC_PHYS_PAGES": 1024, "SC_PAGE_SIZE": 1024 * 1024}[key],
            system="Linux",
        )
        self.assertEqual(fallback["memory.total_gb"].value, 1.0)
        failed = hostprobe.probe_memory(
            absent, runner, lambda _: (_ for _ in ()).throw(ValueError()), system="Linux"
        )
        self.assertEqual(failed["memory.total_gb"].status, "unknown")

        def darwin(vm):
            def run(argv):
                key = argv[-1]
                return hostprobe.CommandResult(
                    "ok", 0, "17179869184" if key == "hw.memsize" else vm, ""
                )

            return run

        good = hostprobe.probe_memory(
            runner=darwin(
                "Mach Virtual Memory Statistics: (page size of 4096 bytes)\nPages free: 100.\nPages inactive: 100.\nPages speculative: 100.\n"
            ),
            system="Darwin",
        )
        self.assertEqual(good["memory.total_gb"].value, 16.0)
        self.assertEqual(good["memory.available_gb"].status, "measured")
        malformed = hostprobe.probe_memory(runner=darwin("bad header\n"), system="Darwin")
        self.assertEqual(malformed["memory.available_gb"].status, "unknown")
        nonnumeric = hostprobe.probe_memory(
            runner=darwin(
                "Mach Virtual Memory Statistics: (page size of 4096 bytes)\nPages free: nope\nPages inactive: 100.\nPages speculative: 100.\n"
            ),
            system="Darwin",
        )
        self.assertEqual(nonnumeric["memory.available_gb"].status, "unknown")

    def test_execution_context_cgroup_ladder_and_limits(self):
        host = hostprobe.probe_execution_context(lambda _: None)
        self.assertEqual(host["execution.observation_scope"].value, "host")
        self.assertEqual(host["memory.cgroup_limit_gb"].status, "not-applicable")
        cgroup_v2 = (
            Path(__file__).parent / "fixtures" / "cgroup-v2-docker-memory-2g.txt"
        ).read_text()
        self.assertEqual(cgroup_v2.encode(), b"0::/\n")
        v2 = {
            "/.dockerenv": "",
            "/proc/1/cgroup": cgroup_v2,
            "/sys/fs/cgroup/memory.max": "2147483648",
            "/sys/fs/cgroup/cpu.max": "max 100000",
        }
        inside = hostprobe.probe_execution_context(lambda path: v2.get(path))
        self.assertTrue(inside["execution.in_container"].value)
        self.assertIn("dockerenv", inside["execution.in_container"].source)
        self.assertEqual(inside["memory.cgroup_limit_gb"].value, 2.0)
        self.assertEqual(inside["cpu.cgroup_quota_cores"].status, "not-applicable")
        rung_four = dict(v2)
        rung_four["/.dockerenv"] = None
        self.assertIn(
            "cgroup-v2-cap",
            hostprobe.probe_execution_context(lambda path: rung_four.get(path))[
                "execution.in_container"
            ].source,
        )
        unlimited = dict(v2)
        unlimited["/.dockerenv"] = None
        unlimited["/sys/fs/cgroup/memory.max"] = "max"
        unlimited["/proc/1/cgroup"] = "none"
        self.assertEqual(
            hostprobe.probe_execution_context(lambda path: unlimited.get(path))[
                "memory.cgroup_limit_gb"
            ].status,
            "not-applicable",
        )
        v1 = {
            "/proc/1/cgroup": "10:memory:/docker/x",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes": str(3 * 1024**3),
            "/sys/fs/cgroup/cpu/cpu.cfs_quota_us": "200000",
            "/sys/fs/cgroup/cpu/cpu.cfs_period_us": "100000",
        }
        legacy = hostprobe.probe_execution_context(lambda path: v1.get(path))
        self.assertEqual(legacy["memory.cgroup_limit_gb"].value, 3.0)
        self.assertEqual(legacy["cpu.cgroup_quota_cores"].value, 2.0)
        sentinel = dict(v1)
        sentinel["/sys/fs/cgroup/memory/memory.limit_in_bytes"] = "9223372036854771712"
        sentinel["/sys/fs/cgroup/cpu/cpu.cfs_quota_us"] = "-1"
        legacy_unlimited = hostprobe.probe_execution_context(lambda path: sentinel.get(path))
        self.assertEqual(legacy_unlimited["memory.cgroup_limit_gb"].status, "not-applicable")
        self.assertEqual(legacy_unlimited["cpu.cgroup_quota_cores"].status, "not-applicable")
        podman = {"/run/.containerenv": ""}
        self.assertIn(
            "containerenv",
            hostprobe.probe_execution_context(lambda path: podman.get(path))[
                "execution.in_container"
            ].source,
        )
        unreadable = hostprobe.probe_execution_context(
            lambda path: "" if path == "/.dockerenv" else None
        )
        self.assertEqual(unreadable["execution.observation_scope"].value, "container")
        self.assertEqual(unreadable["memory.cgroup_limit_gb"].status, "not-applicable")
        overlay = {"/proc/self/mountinfo": "36 25 0:32 / / rw - overlay overlay rw"}
        self.assertIn(
            "overlay-root",
            hostprobe.probe_execution_context(lambda path: overlay.get(path))[
                "execution.in_container"
            ].source,
        )
        meminfo = "MemTotal:        8388608 kB\nMemAvailable:     4194304 kB\n"
        memory = hostprobe.probe_memory(
            lambda path: meminfo if path == "/proc/meminfo" else None, system="Linux"
        )
        merged = {**memory, **inside}
        self.assertEqual(merged["memory.total_gb"].value, 8.0)
        self.assertEqual(merged["memory.cgroup_limit_gb"].value, 2.0)

    def test_virtualization_rekeys_vm_values_and_never_claims_machine_ram(self):
        captured = {
            "/.dockerenv": "",
            "/proc/1/cgroup": "0::/\n",
            "/sys/fs/cgroup/memory.max": "2147483648",
            "/proc/meminfo": "MemTotal:       8126756 kB\nMemAvailable:   7439816 kB\n",
            "/proc/sys/kernel/osrelease": "6.10.14-linuxkit\n",
        }
        def reader(path):
            return captured.get(path)
        values = facts()
        values.update(hostprobe.probe_memory(reader, system="Linux"))
        values.update(
            {
                "cpu.physical_cores": Fact(4, "cores", "measured", "fixture"),
                "cpu.logical_cores": Fact(8, "cores", "measured", "fixture"),
                "cpu.performance_cores": Fact(None, "cores", "not-applicable", "fixture"),
                "cpu.efficiency_cores": Fact(None, "cores", "not-applicable", "fixture"),
            }
        )
        values.update(hostprobe.probe_execution_context(reader))
        values.update(hostprobe.probe_virtualization(values, reader))
        profile = assemble(values)
        emitted = profile["infrastructure"]["facts"]
        self.assertEqual(
            emitted["execution.observation_scope"]["value"], "container-on-virtualized-host"
        )
        self.assertEqual(emitted["memory.total_gb"]["status"], "unknown")
        self.assertEqual(emitted["memory.vm_total_gb"]["value"], 7.75)
        self.assertEqual(emitted["memory.cgroup_limit_gb"]["value"], 2.0)
        self.assertEqual(emitted["cpu.logical_cores"]["status"], "unknown")
        self.assertEqual(emitted["cpu.vm_logical_cores"]["value"], 8)
        self.assertIn(
            "execution.host_not_observable",
            {gap["gap_id"] for gap in profile["software_readiness"]["gaps"]},
        )
        self.assertEqual(profile["recommendations"]["tier"]["confidence"], "reduced")
        self.assertEqual(
            profile["recommendations"]["tier"]["undetermined_inputs"], ["memory.total_gb"]
        )
        self.assertTrue(all("vm_" in key for key, fact in emitted.items() if fact["value"] == 7.75))

    def test_container_check_shared_assertions_cover_profile_and_skip(self):
        profile = {
            "infrastructure": {
                "facts": {
                    "execution.in_container": {
                        "value": True,
                        "source": "container detection rung: dockerenv",
                    },
                    "execution.observation_scope": {"value": "container-on-virtualized-host"},
                    "memory.cgroup_limit_gb": {"status": "measured", "value": 2.0},
                    "memory.total_gb": {"status": "unknown", "value": None},
                    "memory.vm_total_gb": {"status": "measured", "value": 7.75},
                }
            }
        }
        self.assertEqual(
            validate_output(json.dumps(profile)),
            "doctor container check: cgroup memory limit 2.0 scope container-on-virtualized-host",
        )
        self.assertEqual(validate_output(SKIPPED), SKIPPED)

    def test_virtualization_ladder_host_container_and_unreadable_cases(self):
        base = {
            "execution.in_container": Fact(False, "bool", "measured", "fixture"),
            "execution.observation_scope": Fact("host", "enum", "measured", "fixture"),
        }
        host = hostprobe.probe_virtualization(
            base, lambda path: "6.8.0-generic" if path == "/proc/sys/kernel/osrelease" else None
        )
        self.assertEqual(host["execution.virtualization"].value, "none")
        self.assertTrue(host["execution.machine_observable"].value)
        self.assertFalse(any(key.startswith("memory.vm_") for key in host))
        container_facts = {
            **base,
            "execution.in_container": Fact(True, "bool", "measured", "fixture"),
            "execution.observation_scope": Fact("container", "enum", "measured", "fixture"),
            "memory.total_gb": Fact(8, "GiB", "measured", "fixture"),
        }
        container = hostprobe.probe_virtualization(
            container_facts,
            lambda path: "6.8.0-generic" if path == "/proc/sys/kernel/osrelease" else None,
        )
        self.assertEqual(container["execution.virtualization"].value, "none")
        self.assertEqual(container_facts["memory.total_gb"].status, "measured")
        rungs = {
            "docker-desktop": {
                "/proc/sys/kernel/osrelease": "linux",
                "/etc/hostname": "docker-desktop",
            },
            "virtiofs": {
                "/proc/sys/kernel/osrelease": "linux",
                "/proc/self/mountinfo": "- virtiofs host /mnt",
            },
            "grpcfuse": {
                "/proc/sys/kernel/osrelease": "linux",
                "/proc/self/mountinfo": "- grpcfuse host /mnt",
            },
            "fakeowner": {
                "/proc/sys/kernel/osrelease": "linux",
                "/proc/self/mountinfo": "- fakeowner host /mnt",
            },
            "hypervisor": {"/proc/sys/kernel/osrelease": "linux", "/sys/hypervisor/type": "xen"},
            "dmi-hypervisor": {
                "/proc/sys/kernel/osrelease": "linux",
                "/sys/class/dmi/id/product_name": "KVM",
            },
        }
        for signal, fixture in rungs.items():
            result = hostprobe.probe_virtualization(
                container_facts, lambda path, fixture=fixture: fixture.get(path)
            )
            self.assertEqual(result["execution.virtualization_signal"].value, signal)
        unreadable = hostprobe.probe_virtualization(base, lambda _: None)
        self.assertEqual(unreadable["execution.virtualization"].status, "unknown")
        self.assertFalse(unreadable["execution.machine_observable"].value)

    def test_gpu_probe_resolution_and_container_reachability(self):
        def valid(argv):
            return hostprobe.CommandResult("ok", 0, "NVIDIA A100, 40960\n", "")
        nvidia = hostprobe.probe_gpu(
            runner=valid, lister=lambda _: [], system="Linux", observation_scope="container"
        )
        self.assertEqual(nvidia["gpu.vendor"].value, "nvidia")
        self.assertEqual(nvidia["gpu.vram_gb"].value, 40.0)
        self.assertTrue(nvidia["gpu.container_reachable"].value)
        garbage = hostprobe.probe_gpu(
            runner=lambda _: hostprobe.CommandResult("ok", 0, "nonsense", ""),
            lister=lambda _: [],
            system="Linux",
        )
        self.assertEqual(garbage["gpu.vendor"].value, "none")
        missing = hostprobe.probe_gpu(
            runner=lambda _: hostprobe.CommandResult("missing", None, "", ""),
            lister=lambda _: [],
            system="Linux",
        )
        timeout = hostprobe.probe_gpu(
            runner=lambda _: hostprobe.CommandResult("timeout", None, "", ""),
            lister=lambda _: [],
            system="Linux",
        )
        self.assertEqual(missing["gpu.vendor"].value, "none")
        self.assertEqual(timeout["gpu.vendor"].value, "none")
        for pci, expected in (("0x1002", "amd"), ("0x8086", "intel")):
            path = "/sys/class/drm/card0/device/vendor"
            def reader(value, wanted=path, pci=pci):
                return (pci
                            if value == wanted
                            else (str(8 * 1024**3) if value.endswith("mem_info_vram_total") else None))
            gpu = hostprobe.probe_gpu(
                reader,
                lambda _: hostprobe.CommandResult("missing", None, "", ""),
                lambda _: [path],
                system="Linux",
            )
            self.assertEqual(gpu["gpu.vendor"].value, expected)
            self.assertEqual(gpu["gpu.vram_gb"].value, 8.0)
        unknown = hostprobe.probe_gpu(
            runner=lambda _: hostprobe.CommandResult("missing", None, "", ""),
            lister=lambda _: ["/sys/class/drm/card0/device/vendor"],
            system="Linux",
        )
        unreadable = hostprobe.probe_gpu(
            runner=lambda _: hostprobe.CommandResult("missing", None, "", ""),
            lister=lambda _: (_ for _ in ()).throw(OSError()),
            system="Linux",
        )
        self.assertEqual(unknown["gpu.vendor"].status, "unknown")
        self.assertEqual(unreadable["gpu.vendor"].status, "unknown")
        apple = hostprobe.probe_gpu(system="Darwin", machine="arm64")
        self.assertEqual(apple["gpu.vendor"].value, "apple")
        self.assertTrue(apple["gpu.unified_memory"].value)
        self.assertEqual(apple["gpu.vram_gb"].status, "not-applicable")
        container_mac = hostprobe.probe_gpu(
            runner=lambda _: hostprobe.CommandResult("missing", None, "", ""),
            lister=lambda _: [],
            system="Darwin",
            machine="arm64",
            observation_scope="container-on-virtualized-host",
        )
        self.assertEqual(container_mac["gpu.vendor"].value, "none")
        self.assertFalse(container_mac["gpu.container_reachable"].value)
        self.assertIn("no /dev/dri", container_mac["gpu.container_reachable"].source)
        self.assertEqual(container_mac["gpu.vram_gb"].status, "not-applicable")
        self.assertIn("no GPU is reachable", container_mac["gpu.vram_gb"].source)

    def test_docker_inventory_captures_capability_not_runtime_preference(self):
        def healthy(argv):
            if argv[:2] == ["docker", "version"]:
                return hostprobe.CommandResult("ok", 0, "29.6.1\n", "")
            if argv[:2] == ["docker", "info"]:
                return hostprobe.CommandResult(
                    "ok", 0, "Runtimes: runc nvidia\nContext: desktop-linux", ""
                )
            return hostprobe.CommandResult("ok", 0, "Docker Compose version v5.3.0\n", "")

        inventory = hostprobe.probe_docker(healthy, gpu_vendor="nvidia", gpu_nvidia_smi=True)
        self.assertTrue(inventory["docker.daemon_reachable"].value)
        self.assertEqual(inventory["docker.engine_version"].value, "29.6.1")
        self.assertIn("cuda", inventory["backends"].value["container_reachable"])
        unreachable = hostprobe.probe_docker(lambda _: hostprobe.CommandResult("error", 1, "", ""))
        absent = hostprobe.probe_docker(lambda _: hostprobe.CommandResult("missing", None, "", ""))
        timed_out = hostprobe.probe_docker(
            lambda _: hostprobe.CommandResult("timeout", None, "", "")
        )
        for result in (unreachable, absent, timed_out):
            self.assertEqual(result["backends"].value["host_capable"], [])
            self.assertEqual(result["backends"].value["container_reachable"], [])
        mac = hostprobe.probe_docker(healthy, system="Darwin", machine="arm64")
        self.assertIn("metal", mac["backends"].value["host_capable"])
        self.assertNotIn("metal", mac["backends"].value["container_reachable"])
        no_toolkit = hostprobe.probe_docker(
            lambda argv: hostprobe.CommandResult(
                "ok",
                0,
                "29"
                if argv[:2] == ["docker", "version"]
                else ("Runtimes: runc" if argv[:2] == ["docker", "info"] else "v2"),
                "",
            ),
            gpu_vendor="nvidia",
            gpu_nvidia_smi=True,
        )
        self.assertIn("cuda", no_toolkit["backends"].value["host_capable"])
        self.assertNotIn("cuda", no_toolkit["backends"].value["container_reachable"])
        profile = assemble(
            {**facts(), **no_toolkit, "gpu.vendor": Fact("nvidia", "enum", "measured", "fixture")}
        )
        self.assertIn(
            "gpu.container_runtime_missing",
            {gap["gap_id"] for gap in profile["software_readiness"]["gaps"]},
        )
        source = (
            (Path(__file__).parents[1] / "ai_server_generator" / "hostprobe.py").read_text().lower()
        )
        for prohibited in ("ollama", "model runner", "recommend"):
            self.assertNotIn(prohibited, source)

    def test_readiness_registry_is_stable_and_renderer_prints_each_gap(self):
        expected = {
            "platform.unsupported",
            "docker.cli_missing",
            "docker.daemon_unreachable",
            "docker.compose_missing",
            "docker.engine_version_unknown",
            "gpu.driver_missing",
            "gpu.container_runtime_missing",
            "gpu.unreachable_from_container",
            "memory.unobservable",
            "memory.insufficient_for_any_preset",
            "cgroup.limit_below_preset_requirement",
            "execution.host_not_observable",
            "disk.free_space_unknown",
            "disk.insufficient_free_space",
        }
        self.assertEqual(set(GAP_REGISTRY), expected)
        for identifier, spec in GAP_REGISTRY.items():
            self.assertIn(spec.severity, {"blocking", "degraded", "advisory"}, identifier)
            self.assertGreaterEqual(len(spec.remediation["summary"] or ""), 40, identifier)
            self.assertTrue(spec.remediation["linux"] or spec.remediation["macos"], identifier)
            self.assertRegex(identifier, r"^[a-z_]+\.[a-z_]+$")
            self.assertRegex(
                spec.remediation["summary"].lower(),
                r"install|start|enable|free|re-run|increase|run",
            )
        healthy = facts()
        healthy.update(
            {
                "docker.engine_version": Fact("29", "text", "measured", "fixture"),
                "docker.gpu_runtimes": Fact([], "list", "measured", "fixture"),
                "gpu.vendor": Fact("none", "enum", "measured", "fixture"),
                "gpu.vram_gb": Fact(None, "GiB", "not-applicable", "fixture"),
                "gpu.container_reachable": Fact(None, "bool", "not-applicable", "fixture"),
            }
        )
        self.assertEqual(evaluate(assemble(healthy)), [])
        profile = assemble(facts())
        profile["software_readiness"]["gaps"] = [
            {
                "gap_id": key,
                "severity": spec.severity,
                "title": spec.title,
                "remediation": spec.remediation,
                "triggered_by": [],
                "blocks": spec.blocks,
            }
            for key, spec in GAP_REGISTRY.items()
        ]
        text = doctor.render_text(profile)
        for spec in GAP_REGISTRY.values():
            self.assertIn(spec.remediation["summary"], text)

    def test_renderer_sections_windows_and_container_scope_contract(self):
        healthy = facts()
        healthy.update(
            {
                "docker.engine_version": Fact("29", "text", "measured", "fixture"),
                "docker.gpu_runtimes": Fact([], "list", "measured", "fixture"),
                "gpu.vendor": Fact("none", "enum", "measured", "fixture"),
                "gpu.vram_gb": Fact(None, "GiB", "not-applicable", "fixture"),
                "gpu.container_reachable": Fact(None, "bool", "not-applicable", "fixture"),
            }
        )
        unknown = {
            key: Fact(None, "unknown", "unknown", "fixture unavailable")
            for key in ("memory.available_gb", "memory.total_gb", "disk.free_gb")
        }
        unknown.update(
            {
                "memory.cgroup_limit_gb": Fact(None, "GiB", "not-applicable", "fixture"),
                "docker.cli_present": Fact(False, "bool", "measured", "fixture"),
                "docker.daemon_reachable": Fact(False, "bool", "measured", "fixture"),
                "docker.compose_version": Fact(None, "text", "unknown", "fixture"),
                "execution.machine_observable": Fact(True, "bool", "measured", "fixture"),
            }
        )
        bare_container = dict(healthy)
        bare_container.update(
            {"execution.observation_scope": Fact("container", "enum", "measured", "fixture")}
        )
        vm_container = dict(unknown)
        vm_container.update(
            {
                "execution.observation_scope": Fact(
                    "container-on-virtualized-host", "enum", "measured", "fixture"
                ),
                "execution.machine_observable": Fact(False, "bool", "measured", "fixture"),
            }
        )
        profiles = [
            assemble(healthy),
            assemble(unknown),
            doctor.unsupported_profile(),
            assemble(bare_container),
            assemble(vm_container),
        ]
        reports = [doctor.render_text(profile) for profile in profiles]
        headers = ("INFRASTRUCTURE (measured)", "SOFTWARE READINESS", "DERIVED (recommendations)")
        for profile, report in zip(profiles, reports):
            positions = [report.index(header) for header in headers]
            self.assertEqual(positions, sorted(positions))
            derived = report[positions[-1] :]
            self.assertNotIn("16.0", derived)
            for gap in profile["software_readiness"]["gaps"]:
                self.assertIn(gap["remediation"]["summary"], report)
        self.assertNotIn("CONTAINER", reports[0])
        self.assertNotIn("CONTAINER", reports[1])
        self.assertNotIn("CONTAINER", reports[2])
        self.assertIn("CONTAINER", reports[3])
        self.assertIn("CONTAINER", reports[4])
        self.assertIn(
            "This is a virtual machine — the physical machine's RAM and CPU cannot be seen from here. Re-run doctor on the host for an accurate tier.",
            reports[4],
        )
        self.assertIn(
            "Install or run doctor on a supported Linux or macOS host before serving a model.",
            reports[2],
        )
        self.assertNotIn("Tier:", reports[2])
        self.assertNotIn("FIT:", reports[2])

    def test_hostprofile_serialization_is_deterministic_and_complete(self):
        first = assemble(facts(), generated_at="2026-01-01T00:00:00+00:00")
        second = assemble(facts(), generated_at="2026-01-01T00:00:00+00:00")
        from ai_server_generator.hostprofile import serialize

        self.assertEqual(serialize(first), serialize(second))
        self.assertEqual(
            set(first),
            {
                "host_profile_version",
                "generated_at",
                "platform",
                "infrastructure",
                "software_readiness",
                "recommendations",
                "notes",
            },
        )
        self.assertTrue(serialize(first).endswith("\n"))

    def test_synthetic_hostprofile_fixture_matches_exact_serialized_document(self):
        from ai_server_generator.hostprofile import serialize

        fixture = Path(__file__).parent / "fixtures" / "host-profile-synthetic.json"
        values = facts()
        values.update(
            {
                "docker.engine_version": Fact("29", "text", "measured", "fixture"),
                "docker.gpu_runtimes": Fact([], "list", "measured", "fixture"),
            }
        )
        document = assemble(
            values,
            generated_at="2026-01-01T00:00:00+00:00",
            platform_info={"system": "FixtureOS", "machine": "fixture", "python_version": "3.10"},
        )
        self.assertEqual(serialize(document), fixture.read_text())
        self.assertTrue(fixture.read_bytes().endswith(b"\n"))

    def test_all_failing_profile_retains_complete_unknown_fact_set_and_windows_empty_facts(self):
        expected_keys = {
            "backends",
            "cpu.arm_ids",
            "cpu.cgroup_quota_cores",
            "cpu.efficiency_cores",
            "cpu.generation",
            "cpu.hw_model",
            "cpu.logical_cores",
            "cpu.model",
            "cpu.performance_cores",
            "cpu.physical_cores",
            "disk.free_gb",
            "disk.models_path",
            "docker.cli_present",
            "docker.compose_version",
            "docker.daemon_reachable",
            "docker.engine_version",
            "docker.gpu_runtimes",
            "execution.in_container",
            "execution.machine_observable",
            "execution.observation_scope",
            "execution.virtualization",
            "execution.virtualization_signal",
            "gpu.container_reachable",
            "gpu.name",
            "gpu.unified_memory",
            "gpu.vendor",
            "gpu.vram_gb",
            "memory.available_gb",
            "memory.cgroup_limit_gb",
            "memory.total_gb",
        }
        failed = assemble(
            {
                key: Fact(None, "unknown", "unknown", "synthetic probe failed")
                for key in expected_keys
            }
        )
        facts_map = failed["infrastructure"]["facts"]
        self.assertEqual(set(facts_map), expected_keys)
        self.assertTrue(all(fact["status"] == "unknown" for fact in facts_map.values()))
        self.assertTrue(failed["software_readiness"]["gaps"])
        self.assertTrue(
            {
                "host_profile_version",
                "platform",
                "infrastructure",
                "software_readiness",
                "recommendations",
                "notes",
            }.issubset(failed)
        )
        windows = assemble(
            {},
            supported=False,
            platform_info={"system": "Windows", "machine": "fixture", "python_version": "3.10"},
        )
        self.assertEqual(windows["infrastructure"]["facts"], {})
        self.assertEqual(windows["recommendations"]["runnable_presets"], [])
        self.assertNotIn("tier", windows["recommendations"])

    def test_no_fail_cli_writes_complete_unknown_profile(self):
        expected_keys = {
            "backends",
            "cpu.arm_ids",
            "cpu.cgroup_quota_cores",
            "cpu.efficiency_cores",
            "cpu.generation",
            "cpu.hw_model",
            "cpu.logical_cores",
            "cpu.model",
            "cpu.performance_cores",
            "cpu.physical_cores",
            "disk.free_gb",
            "disk.models_path",
            "docker.cli_present",
            "docker.compose_version",
            "docker.daemon_reachable",
            "docker.engine_version",
            "docker.gpu_runtimes",
            "execution.in_container",
            "execution.machine_observable",
            "execution.observation_scope",
            "execution.virtualization",
            "execution.virtualization_signal",
            "gpu.container_reachable",
            "gpu.name",
            "gpu.unified_memory",
            "gpu.vendor",
            "gpu.vram_gb",
            "memory.available_gb",
            "memory.cgroup_limit_gb",
            "memory.total_gb",
        }
        def reader(_):
            return None
        def runner(_):
            return hostprobe.CommandResult("missing", None, "", "")

        def injected_collect(models_path=None):
            observed = {}
            observed.update(
                hostprobe.probe_cpu(
                    reader, lambda _: [], runner, system="Linux", cpu_count=lambda: None
                )
            )
            observed.update(
                hostprobe.probe_memory(
                    reader, runner, lambda _: (_ for _ in ()).throw(ValueError()), system="Linux"
                )
            )
            observed.update(hostprobe.probe_execution_context(reader))
            observed.update(hostprobe.probe_virtualization(observed, reader, runner))
            observed.update(
                hostprobe.probe_gpu(
                    reader,
                    runner,
                    lambda _: (_ for _ in ()).throw(OSError()),
                    system="Linux",
                    observation_scope="host",
                )
            )
            observed.update(
                hostprobe.probe_disk(
                    models_path, disk_usage=lambda _: (_ for _ in ()).throw(OSError())
                )
            )
            observed.update(hostprobe.probe_docker(runner))
            self.assertTrue(set(observed))
            return assemble(
                {
                    key: Fact(None, "unknown", "unknown", "injected unavailable")
                    for key in expected_keys
                }
            )

        output = "artifacts/test-doctor-security/no-fail.json"
        path = Path(__file__).parents[1] / output
        with mock.patch("ai_server_generator.doctor.collect", side_effect=injected_collect):
            self.assertEqual(cli.main(["doctor", "--out", output]), 0)
        document = json.loads(path.read_text())
        self.assertEqual(set(document["infrastructure"]["facts"]), expected_keys)
        self.assertTrue(
            all(
                fact["status"] == "unknown" for fact in document["infrastructure"]["facts"].values()
            )
        )
        self.assertEqual(len(document["notes"]), len(expected_keys))

    def test_headless_no_fail_and_parser_contract(self):
        unknown = {
            key: Fact(None, "unknown", "unknown", "fixture unavailable")
            for key in ("memory.available_gb", "memory.total_gb", "disk.free_gb")
        }
        unknown.update(
            {
                "memory.cgroup_limit_gb": Fact(None, "GiB", "not-applicable", "fixture"),
                "docker.cli_present": Fact(False, "bool", "measured", "fixture"),
                "docker.daemon_reachable": Fact(False, "bool", "measured", "fixture"),
                "docker.compose_version": Fact(None, "text", "unknown", "fixture"),
                "execution.machine_observable": Fact(False, "bool", "measured", "fixture"),
            }
        )
        captured = io.StringIO()
        with (
            mock.patch("ai_server_generator.doctor.collect", return_value=assemble(unknown)),
            mock.patch("ai_server_generator.cli._read_line", side_effect=AssertionError),
            mock.patch("sys.stdin.isatty", return_value=False),
            mock.patch("sys.stdout.isatty", return_value=False),
            contextlib.redirect_stdout(captured),
        ):
            self.assertEqual(cli.main(["doctor", "--no-write"]), 0)
            self.assertEqual(cli.main(["doctor", "--no-write", "--format", "json"]), 0)
        self.assertIn("INFRASTRUCTURE (measured)", captured.getvalue())
        self.assertNotIn("\x1b[", captured.getvalue())
        parser = cli.build_parser()
        for command in (
            ["list", "models"],
            ["matrix"],
            ["generate", "--out", "generated/x"],
            ["validate", "generated/x"],
            ["wizard", "--run", "no"],
            ["doctor"],
        ):
            self.assertIsNotNone(parser.parse_args(command))

    def test_dependency_and_allowlist_contract(self):
        root = Path(__file__).parents[1]
        self.assertEqual(
            (root / "requirements.txt").read_text().splitlines(),
            ["Jinja2==3.1.6", "MarkupSafe==3.0.3"],
        )
        self.assertEqual(
            hostprobe.HOST_BINARY_ALLOWLIST,
            frozenset({"docker", "nvidia-smi", "sysctl", "vm_stat", "sw_vers", "system_profiler"}),
        )
        allowed_imports = {
            "__future__",
            "dataclasses",
            "os",
            "pathlib",
            "platform",
            "re",
            "shutil",
            "subprocess",
            "threading",
            "signal",
            "typing",
            "json",
            "datetime",
            "secrets",
            "sys",
        }

        def assert_stdlib_only(source):
            for node in ast.walk(ast.parse(source.read_text())):
                if isinstance(node, ast.Import):
                    self.assertTrue(
                        all(name.name.split(".")[0] in allowed_imports for name in node.names),
                        source,
                    )
                if isinstance(node, ast.ImportFrom) and node.level == 0:
                    self.assertIn(node.module.split(".")[0], allowed_imports, source)

        for source in (root / "ai_server_generator").glob("*.py"):
            if source.name not in {
                "hostprobe.py",
                "hostprofile.py",
                "readiness.py",
                "tiering.py",
                "doctor.py",
                "containercheck.py",
            }:
                continue
            assert_stdlib_only(source)
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "ai_server_generator"
            shutil.copytree(root / "ai_server_generator", copied)
            injected = copied / "hostprobe.py"
            injected.write_text(injected.read_text() + "\nimport third_party_probe\n")
            with self.assertRaises(AssertionError):
                assert_stdlib_only(injected)

    def test_ci_doctor_contract(self):
        script = (Path(__file__).parents[1] / "scripts" / "ci.sh").read_text()
        self.assertNotIn("TASK-0007", script)
        self.assertNotRegex(script, r"TASK-[0-9]")
        self.assertIn("ai_server_generator doctor --no-write", script)
        self.assertIn("ai_server_generator doctor --no-write --format json", script)

    def test_every_readiness_gap_has_a_trigger_and_literal_fact_basis(self):
        base = facts(available=16.0, disk=100.0)
        base.update(
            {
                "docker.engine_version": Fact("29", "text", "measured", "fixture"),
                "docker.gpu_runtimes": Fact(["nvidia"], "list", "measured", "fixture"),
                "gpu.vendor": Fact("none", "enum", "measured", "fixture"),
                "gpu.vram_gb": Fact(1.0, "GiB", "measured", "fixture"),
                "gpu.container_reachable": Fact(True, "bool", "measured", "fixture"),
            }
        )
        mutations = {
            "platform.unsupported": lambda p: p.update({}),
            "docker.cli_missing": lambda p: p.update(
                {"docker.cli_present": Fact(False, "bool", "measured", "fixture")}
            ),
            "docker.daemon_unreachable": lambda p: p.update(
                {"docker.daemon_reachable": Fact(False, "bool", "measured", "fixture")}
            ),
            "docker.compose_missing": lambda p: p.update(
                {"docker.compose_version": Fact(None, "text", "unknown", "fixture")}
            ),
            "docker.engine_version_unknown": lambda p: p.update(
                {"docker.engine_version": Fact(None, "text", "unknown", "fixture")}
            ),
            "gpu.driver_missing": lambda p: p.update(
                {
                    "gpu.vendor": Fact("nvidia", "enum", "measured", "fixture"),
                    "gpu.vram_gb": Fact(None, "GiB", "unknown", "fixture"),
                }
            ),
            "gpu.container_runtime_missing": lambda p: p.update(
                {
                    "gpu.vendor": Fact("nvidia", "enum", "measured", "fixture"),
                    "docker.gpu_runtimes": Fact([], "list", "measured", "fixture"),
                }
            ),
            "gpu.unreachable_from_container": lambda p: p.update(
                {"gpu.container_reachable": Fact(False, "bool", "measured", "fixture")}
            ),
            "memory.unobservable": lambda p: p.update(
                {"memory.available_gb": Fact(None, "GiB", "unknown", "fixture")}
            ),
            "memory.insufficient_for_any_preset": lambda p: p.update(
                {"memory.available_gb": Fact(1.0, "GiB", "measured", "fixture")}
            ),
            "cgroup.limit_below_preset_requirement": lambda p: p.update(
                {"memory.cgroup_limit_gb": Fact(1.0, "GiB", "measured", "fixture")}
            ),
            "execution.host_not_observable": lambda p: p.update(
                {"execution.machine_observable": Fact(False, "bool", "measured", "fixture")}
            ),
            "disk.free_space_unknown": lambda p: p.update(
                {"disk.free_gb": Fact(None, "GiB", "unknown", "fixture")}
            ),
            "disk.insufficient_free_space": lambda p: p.update(
                {"disk.free_gb": Fact(1.0, "GiB", "measured", "fixture")}
            ),
        }
        for identifier, mutate in mutations.items():
            if identifier == "platform.unsupported":
                profile = assemble({}, supported=False)
            else:
                values = dict(base)
                mutate(values)
                profile = assemble(values)
            gaps = {gap.gap_id: gap for gap in evaluate(profile)}
            self.assertIn(identifier, gaps, identifier)
            for trigger in gaps[identifier].triggered_by:
                self.assertEqual(
                    trigger["observed_value"],
                    profile["infrastructure"]["facts"][trigger["fact_key"]]["value"],
                )

    def test_six_row_matrix_schema_and_union_cover_all_emitted_fact_keys(self):
        common = facts()
        common.update(
            {
                "cpu.model": Fact("CPU family (redacted)", "text", "measured", "fixture"),
                "cpu.physical_cores": Fact(8, "cores", "measured", "fixture"),
                "cpu.logical_cores": Fact(8, "cores", "measured", "fixture"),
                "cpu.performance_cores": Fact(None, "cores", "not-applicable", "fixture"),
                "cpu.efficiency_cores": Fact(None, "cores", "not-applicable", "fixture"),
                "cpu.generation": Fact(None, "text", "unknown", "fixture"),
                "cpu.hw_model": Fact(None, "text", "unknown", "fixture"),
                "cpu.arm_ids": Fact(None, "text", "not-applicable", "fixture"),
                "cpu.cgroup_quota_cores": Fact(None, "cores", "not-applicable", "fixture"),
                "execution.in_container": Fact(False, "bool", "measured", "fixture"),
                "execution.observation_scope": Fact("host", "enum", "measured", "fixture"),
                "execution.virtualization": Fact("none", "enum", "measured", "fixture"),
                "execution.virtualization_signal": Fact(None, "text", "not-applicable", "fixture"),
                "gpu.vendor": Fact("none", "enum", "measured", "fixture"),
                "gpu.name": Fact(None, "text", "unknown", "fixture"),
                "gpu.vram_gb": Fact(None, "GiB", "unknown", "fixture"),
                "gpu.unified_memory": Fact(False, "bool", "measured", "fixture"),
                "gpu.container_reachable": Fact(None, "bool", "unknown", "fixture"),
                "docker.engine_version": Fact("29", "text", "measured", "fixture"),
                "docker.gpu_runtimes": Fact([], "list", "measured", "fixture"),
                "backends": Fact({}, "object", "measured", "fixture"),
            }
        )
        rows = []
        for name in (
            "linux-x86",
            "linux-arm",
            "linux-container-mac",
            "darwin-arm",
            "darwin-intel",
            "windows",
        ):
            if name == "windows":
                rows.append(assemble({}, supported=False))
                continue
            row = dict(common)
            if name == "linux-arm":
                row.update(
                    {
                        "cpu.model": Fact(
                            None, "text", "unknown", "no model name or DMI on ARM Linux"
                        ),
                        "cpu.arm_ids": Fact(
                            "implementer=0x61 part=0x000", "text", "measured", "fixture"
                        ),
                    }
                )
            if name == "linux-container-mac":
                row.update(
                    {
                        "cpu.model": Fact(
                            None, "text", "unknown", "no model name or DMI on ARM Linux"
                        ),
                        "execution.observation_scope": Fact(
                            "container-on-virtualized-host",
                            "enum",
                            "measured",
                            "virtualization signal: linuxkit",
                        ),
                        "execution.machine_observable": Fact(
                            False, "bool", "measured", "physical machine is not observable"
                        ),
                        "memory.total_gb": Fact(
                            None, "GiB", "unknown", "physical machine is not observable"
                        ),
                        "memory.available_gb": Fact(
                            None, "GiB", "unknown", "physical machine is not observable"
                        ),
                        "memory.vm_total_gb": Fact(
                            7.75, "GiB", "measured", "VM-scoped observation"
                        ),
                        "memory.vm_available_gb": Fact(
                            7.0, "GiB", "measured", "VM-scoped observation"
                        ),
                        "memory.cgroup_limit_gb": Fact(
                            2.0, "GiB", "measured", "cgroup memory limit"
                        ),
                        "gpu.vram_gb": Fact(
                            None, "GiB", "not-applicable", "no GPU is reachable from this container"
                        ),
                        "gpu.container_reachable": Fact(
                            False,
                            "bool",
                            "measured",
                            "no /dev/dri or working nvidia-smi in container",
                        ),
                    }
                )
            if name == "darwin-arm":
                row.update(
                    {
                        "cpu.performance_cores": Fact(6, "cores", "measured", "fixture"),
                        "cpu.efficiency_cores": Fact(2, "cores", "measured", "fixture"),
                        "gpu.vendor": Fact("apple", "enum", "measured", "fixture"),
                        "gpu.vram_gb": Fact(None, "GiB", "not-applicable", "fixture"),
                    }
                )
            rows.append(assemble(row))
        non_windows = [set(row["infrastructure"]["facts"]) for row in rows[:-1]]
        self.assertEqual(rows[-1]["infrastructure"]["facts"], {})
        self.assertTrue(all(row["platform"]["supported"] for row in rows[:-1]))
        for row in rows[:-1]:
            for key, fact in row["infrastructure"]["facts"].items():
                self.assertIn(fact["status"], {"measured", "unknown", "not-applicable"}, key)
                self.assertTrue(fact["source"], key)
        self.assertEqual(rows[2]["infrastructure"]["facts"]["memory.total_gb"]["status"], "unknown")
        self.assertEqual(
            rows[2]["infrastructure"]["facts"]["memory.vm_total_gb"]["status"], "measured"
        )
        self.assertEqual(
            rows[3]["infrastructure"]["facts"]["gpu.vram_gb"]["status"], "not-applicable"
        )
        self.assertEqual(rows[1]["infrastructure"]["facts"]["cpu.arm_ids"]["status"], "measured")
        self.assertEqual(
            set.union(*non_windows),
            set.union(*(set(row["infrastructure"]["facts"]) for row in rows[:-1])),
        )
        self.assertIn("memory.vm_total_gb", set.union(*non_windows))
        expected = {
            "linux-x86": {
                "cpu.model": "measured",
                "cpu.arm_ids": "not-applicable",
                "memory.total_gb": "measured",
                "memory.cgroup_limit_gb": "not-applicable",
                "execution.observation_scope": "measured",
                "gpu.unified_memory": "measured",
            },
            "linux-arm": {
                "cpu.model": "unknown",
                "cpu.arm_ids": "measured",
                "cpu.physical_cores": "measured",
                "memory.total_gb": "measured",
            },
            "linux-container-mac": {
                "memory.total_gb": "unknown",
                "memory.available_gb": "unknown",
                "memory.vm_total_gb": "measured",
                "memory.vm_available_gb": "measured",
                "memory.cgroup_limit_gb": "measured",
                "gpu.vram_gb": "not-applicable",
                "gpu.container_reachable": "measured",
            },
            "darwin-arm": {
                "cpu.performance_cores": "measured",
                "cpu.efficiency_cores": "measured",
                "gpu.vendor": "measured",
                "gpu.vram_gb": "not-applicable",
            },
            "darwin-intel": {
                "cpu.performance_cores": "not-applicable",
                "cpu.efficiency_cores": "not-applicable",
                "gpu.unified_memory": "measured",
            },
        }
        for name, profile in zip(
            ("linux-x86", "linux-arm", "linux-container-mac", "darwin-arm", "darwin-intel"),
            rows[:-1],
        ):
            emitted = profile["infrastructure"]["facts"]
            for key, status in expected[name].items():
                self.assertEqual(emitted[key]["status"], status, f"{name}:{key}")
                self.assertTrue(emitted[key]["source"], f"{name}:{key}")
        self.assertEqual(
            rows[2]["infrastructure"]["facts"]["execution.observation_scope"]["value"],
            "container-on-virtualized-host",
        )
        self.assertFalse(
            rows[2]["infrastructure"]["facts"]["execution.machine_observable"]["value"]
        )
        self.assertEqual(rows[2]["infrastructure"]["facts"]["memory.cgroup_limit_gb"]["value"], 2.0)
        self.assertEqual(rows[3]["infrastructure"]["facts"]["gpu.vendor"]["value"], "apple")

    def test_platform_matrix_uses_injected_probe_scenarios(self):
        def runner(values):
            def run(argv):
                key = argv[-1]
                if argv[0] == "docker":
                    if argv[1] == "info":
                        return hostprobe.CommandResult("ok", 0, "Runtimes: runc\n", "")
                    if argv[1] == "version":
                        return hostprobe.CommandResult("ok", 0, "29\n", "")
                    return hostprobe.CommandResult("ok", 0, "v2\n", "")
                if argv[0] == "nvidia-smi":
                    return hostprobe.CommandResult("missing", None, "", "")
                return hostprobe.CommandResult("ok", 0, values.get(key, ""), "")

            return run

        def compose(system, machine, fixture, values, lister=lambda _: []):
            def read(path):
                return fixture.get(path)
            run = runner(values)
            observed = {}
            observed.update(
                hostprobe.probe_cpu(
                    read, lister, run, system=system, machine=machine, cpu_count=lambda: 8
                )
            )
            observed.update(hostprobe.probe_memory(read, run, lambda _: 0, system=system))
            observed.update(hostprobe.probe_execution_context(read))
            observed.update(hostprobe.probe_virtualization(observed, read, run))
            observed.update(
                hostprobe.probe_gpu(
                    read,
                    run,
                    lambda pattern: [] if "drm" in pattern else lister(pattern),
                    system=system,
                    machine=machine,
                    observation_scope=str(observed["execution.observation_scope"].value),
                )
            )
            observed.update(
                hostprobe.probe_disk(
                    "models", disk_usage=lambda _: type("Usage", (), {"free": 100 * 1024**3})()
                )
            )
            gpu = observed["gpu.vendor"]
            observed.update(
                hostprobe.probe_docker(
                    run,
                    system=system,
                    machine=machine,
                    gpu_vendor=str(gpu.value),
                    gpu_nvidia_smi=gpu.source == "nvidia-smi",
                )
            )
            return assemble(
                observed,
                platform_info={"system": system, "machine": machine, "python_version": "fixture"},
            )

        x86 = compose(
            "Linux",
            "x86_64",
            {
                "/proc/cpuinfo": "model name : Xeon\nphysical id : 0\ncore id : 0\n",
                "/proc/meminfo": "MemTotal: 16777216 kB\nMemAvailable: 8388608 kB\n",
                "/proc/sys/kernel/osrelease": "6.8",
            },
            {},
        )
        arm_fixture = {
            "/proc/cpuinfo": "CPU implementer : 0x61\nCPU part : 0x000\n",
            "/proc/meminfo": "MemTotal: 8388608 kB\nMemAvailable: 4194304 kB\n",
            "/proc/sys/kernel/osrelease": "6.8",
            "/sys/devices/system/cpu/cpu0/topology/core_id": "0",
            "/sys/devices/system/cpu/cpu0/topology/physical_package_id": "0",
        }
        arm = compose(
            "Linux",
            "aarch64",
            arm_fixture,
            {},
            lambda _: ["/sys/devices/system/cpu/cpu0/topology/core_id"],
        )
        container_fixture = {
            **arm_fixture,
            "/.dockerenv": "",
            "/proc/1/cgroup": "0::/\n",
            "/sys/fs/cgroup/memory.max": "2147483648",
            "/sys/fs/cgroup/cpu.max": "max 100000",
            "/proc/sys/kernel/osrelease": "linuxkit",
        }
        container = compose(
            "Linux",
            "aarch64",
            container_fixture,
            {},
            lambda _: ["/sys/devices/system/cpu/cpu0/topology/core_id"],
        )
        darwin_values = {
            "hw.memsize": "17179869184",
            "machdep.cpu.brand_string": "Apple M1 Pro",
            "hw.model": "MacBookPro18,3",
            "hw.physicalcpu": "8",
            "hw.logicalcpu": "8",
            "hw.perflevel0.physicalcpu": "6",
            "hw.perflevel1.physicalcpu": "2",
            "vm_stat": "Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 100.\nPages inactive: 100.\nPages speculative: 100.\n",
        }
        apple = compose("Darwin", "arm64", {"/proc/sys/kernel/osrelease": "Darwin"}, darwin_values)
        intel_values = {
            **darwin_values,
            "machdep.cpu.brand_string": "Intel Core i7",
            "hw.model": "MacBookPro16,1",
            "hw.perflevel0.physicalcpu": "",
            "hw.perflevel1.physicalcpu": "",
            "vm_stat": "Mach Virtual Memory Statistics: (page size of 4096 bytes)\nPages free: 100.\nPages inactive: 100.\nPages speculative: 100.\n",
        }
        intel = compose("Darwin", "x86_64", {"/proc/sys/kernel/osrelease": "Darwin"}, intel_values)
        rows = (x86, arm, container, apple, intel)
        self.assertEqual(x86["infrastructure"]["facts"]["cpu.model"]["status"], "measured")
        self.assertEqual(
            arm["infrastructure"]["facts"]["cpu.arm_ids"]["value"], "implementer=0x61 part=0x000"
        )
        self.assertEqual(
            container["infrastructure"]["facts"]["execution.observation_scope"]["value"],
            "container-on-virtualized-host",
        )
        self.assertEqual(
            container["infrastructure"]["facts"]["gpu.vram_gb"]["status"], "not-applicable"
        )
        self.assertEqual(apple["infrastructure"]["facts"]["gpu.vendor"]["value"], "apple")
        self.assertEqual(apple["infrastructure"]["facts"]["cpu.performance_cores"]["value"], 6.0)
        self.assertEqual(
            intel["infrastructure"]["facts"]["cpu.performance_cores"]["status"], "not-applicable"
        )
        with (
            mock.patch("platform.system", return_value="Windows"),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(cli.main(["doctor", "--no-write", "--format", "json"]), 0)
        windows = json.loads(stdout.getvalue())
        self.assertEqual(windows["infrastructure"]["facts"], {})
        facts_by_row = [row["infrastructure"]["facts"] for row in rows]
        self.assertIn("proc/cpuinfo", facts_by_row[0]["cpu.model"]["source"])
        self.assertIn("raw ARM ids", facts_by_row[1]["cpu.arm_ids"]["source"])
        self.assertIn("sysfs topology", facts_by_row[1]["cpu.physical_cores"]["source"])
        self.assertIn("linuxkit", facts_by_row[2]["execution.observation_scope"]["source"])
        self.assertIn(
            "physical machine is not observable", facts_by_row[2]["memory.total_gb"]["source"]
        )
        self.assertIn("VM-scoped", facts_by_row[2]["memory.vm_total_gb"]["source"])
        self.assertIn("cgroup memory limit", facts_by_row[2]["memory.cgroup_limit_gb"]["source"])
        self.assertIn("no GPU is reachable", facts_by_row[2]["gpu.vram_gb"]["source"])
        self.assertIn(
            "sysctl machdep.cpu.brand_string", facts_by_row[3]["cpu.generation"]["source"]
        )
        self.assertIn("sysctl hw.memsize", facts_by_row[3]["memory.total_gb"]["source"])
        self.assertIn(
            "perflevel keys are Apple Silicon only",
            facts_by_row[4]["cpu.performance_cores"]["source"],
        )
        expected_keys = {
            "backends",
            "cpu.arm_ids",
            "cpu.cgroup_quota_cores",
            "cpu.efficiency_cores",
            "cpu.generation",
            "cpu.hw_model",
            "cpu.logical_cores",
            "cpu.model",
            "cpu.performance_cores",
            "cpu.physical_cores",
            "cpu.vm_logical_cores",
            "disk.free_gb",
            "disk.models_path",
            "docker.cli_present",
            "docker.compose_version",
            "docker.daemon_reachable",
            "docker.engine_version",
            "docker.gpu_runtimes",
            "execution.in_container",
            "execution.machine_observable",
            "execution.observation_scope",
            "execution.virtualization",
            "execution.virtualization_signal",
            "gpu.container_reachable",
            "gpu.name",
            "gpu.unified_memory",
            "gpu.vendor",
            "gpu.vram_gb",
            "memory.available_gb",
            "memory.cgroup_limit_gb",
            "memory.total_gb",
            "memory.vm_available_gb",
            "memory.vm_total_gb",
        }
        self.assertEqual(set.union(*(set(facts) for facts in facts_by_row)), expected_keys)
        matrix_statuses = (
            {
                "cpu.physical_cores": "measured",
                "cpu.logical_cores": "measured",
                "cpu.performance_cores": "not-applicable",
                "cpu.efficiency_cores": "not-applicable",
                "cpu.generation": "unknown",
                "cpu.hw_model": "unknown",
                "memory.total_gb": "measured",
                "memory.available_gb": "measured",
                "memory.cgroup_limit_gb": "not-applicable",
                "cpu.cgroup_quota_cores": "not-applicable",
                "execution.machine_observable": "measured",
                "gpu.vendor": "measured",
                "gpu.vram_gb": "unknown",
                "gpu.unified_memory": "measured",
                "gpu.container_reachable": "not-applicable",
                "disk.free_gb": "measured",
                "docker.cli_present": "measured",
                "docker.daemon_reachable": "measured",
                "backends": "measured",
            },
            {
                "cpu.physical_cores": "measured",
                "cpu.logical_cores": "measured",
                "cpu.performance_cores": "not-applicable",
                "cpu.efficiency_cores": "not-applicable",
                "cpu.generation": "unknown",
                "cpu.hw_model": "unknown",
                "memory.total_gb": "measured",
                "memory.available_gb": "measured",
                "memory.cgroup_limit_gb": "not-applicable",
                "cpu.cgroup_quota_cores": "not-applicable",
                "execution.machine_observable": "measured",
                "gpu.unified_memory": "measured",
                "disk.free_gb": "measured",
                "docker.cli_present": "measured",
                "docker.daemon_reachable": "measured",
                "backends": "measured",
            },
            {
                "cpu.physical_cores": "unknown",
                "cpu.logical_cores": "unknown",
                "cpu.performance_cores": "unknown",
                "cpu.efficiency_cores": "unknown",
                "cpu.generation": "unknown",
                "cpu.hw_model": "unknown",
                "memory.cgroup_limit_gb": "measured",
                "cpu.cgroup_quota_cores": "not-applicable",
                "execution.machine_observable": "measured",
                "gpu.vendor": "measured",
                "gpu.unified_memory": "measured",
                "gpu.container_reachable": "measured",
                "disk.free_gb": "measured",
                "docker.cli_present": "measured",
                "docker.daemon_reachable": "measured",
                "backends": "measured",
            },
            {
                "cpu.model": "measured",
                "cpu.arm_ids": "not-applicable",
                "cpu.physical_cores": "measured",
                "cpu.logical_cores": "measured",
                "cpu.performance_cores": "measured",
                "cpu.efficiency_cores": "measured",
                "cpu.generation": "measured",
                "cpu.hw_model": "measured",
                "memory.total_gb": "measured",
                "memory.available_gb": "measured",
                "memory.cgroup_limit_gb": "not-applicable",
                "cpu.cgroup_quota_cores": "not-applicable",
                "execution.machine_observable": "measured",
                "gpu.vendor": "measured",
                "gpu.vram_gb": "not-applicable",
                "gpu.unified_memory": "measured",
                "gpu.container_reachable": "not-applicable",
                "disk.free_gb": "measured",
                "docker.cli_present": "measured",
                "docker.daemon_reachable": "measured",
                "backends": "measured",
            },
            {
                "cpu.model": "measured",
                "cpu.arm_ids": "not-applicable",
                "cpu.physical_cores": "measured",
                "cpu.logical_cores": "measured",
                "cpu.performance_cores": "not-applicable",
                "cpu.efficiency_cores": "not-applicable",
                "cpu.generation": "measured",
                "cpu.hw_model": "measured",
                "memory.total_gb": "measured",
                "memory.available_gb": "measured",
                "memory.cgroup_limit_gb": "not-applicable",
                "cpu.cgroup_quota_cores": "not-applicable",
                "execution.machine_observable": "measured",
                "gpu.unified_memory": "measured",
                "gpu.container_reachable": "not-applicable",
                "disk.free_gb": "measured",
                "docker.cli_present": "measured",
                "docker.daemon_reachable": "measured",
                "backends": "measured",
            },
        )
        for facts, expectations in zip(facts_by_row, matrix_statuses):
            for key, status in expectations.items():
                self.assertEqual(facts[key]["status"], status, key)
                self.assertTrue(facts[key]["source"], key)
            self.assertEqual(facts["disk.free_gb"]["value"], 100.0)
            self.assertTrue(facts["docker.cli_present"]["value"])
            self.assertTrue(facts["docker.daemon_reachable"]["value"])

    def test_probe_runner_calls_use_literal_allowlisted_binaries(self):
        tree = ast.parse(
            (Path(__file__).parents[1] / "ai_server_generator" / "hostprobe.py").read_text()
        )
        binaries = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "runner"
                and node.args
                and isinstance(node.args[0], ast.List)
            ):
                first = node.args[0].elts[0]
                self.assertIsInstance(first, ast.Constant)
                binaries.add(first.value)
        self.assertTrue(binaries.issubset(hostprobe.HOST_BINARY_ALLOWLIST))

    def test_unsupported_platform_does_not_probe(self):
        probes = {
            name: mock.patch.object(hostprobe, name, side_effect=AssertionError(name))
            for name in dir(hostprobe)
            if name.startswith("probe_")
        }
        captured = io.StringIO()
        with (
            mock.patch("platform.system", return_value="Windows"),
            contextlib.ExitStack() as stack,
            contextlib.redirect_stdout(captured),
        ):
            for patch in probes.values():
                stack.enter_context(patch)
            self.assertEqual(cli.main(["doctor", "--no-write", "--format", "json"]), 0)
        document = json.loads(captured.getvalue())
        self.assertFalse(document["platform"]["supported"])
        self.assertEqual(document["infrastructure"]["facts"], {})
        self.assertEqual(document["recommendations"]["runnable_presets"], [])
        self.assertNotIn("tier", document["recommendations"])
        self.assertEqual(len(document["software_readiness"]["gaps"]), 1)
        gap = document["software_readiness"]["gaps"][0]
        self.assertEqual((gap["gap_id"], gap["severity"]), ("platform.unsupported", "blocking"))
        self.assertEqual(
            gap["remediation"]["summary"],
            GAP_REGISTRY["platform.unsupported"].remediation["summary"],
        )
