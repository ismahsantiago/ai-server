---
id: mem-pm-orchestrator-0017
type: project-fact
scope: project
created: 2026-07-26
ttl_days: null
importance: 5
tags: [macos, phase-i, packaging, blocker, python]
signature: "3e9dfe52"
---

Measured by TASK-0008 on 2026-07-25 and carried to Phase I: macOS is blocked on BOTH inspection paths. (1) Container view is structurally blind — a container on a Mac reports the Docker Desktop VM's memory (7.75 GiB measured), which is neither the Mac's real RAM (16 GiB) nor the cgroup cap (2 GiB); three levels exist on macOS, not two. (2) Host view has no usable interpreter — on a freshly reset Mac /usr/bin/python3 is a Command Line Tools stub, and when CLT is installed it is Python 3.9.6, below this repo's requires-python '>=3.10' (pyproject.toml:9). Consequence: 're-run doctor on the host for an accurate tier' is NOT a remediation we can offer on macOS today, so no readiness gap text may instruct it. A POSIX-sh host shim looks viable since sysctl, vm_stat and sw_vers are all shell and stock on macOS — Phase I packaging decision owned by ml-platform-engineer, recorded here so Phase I does not re-derive it. Also confirmed: Metal is unreachable from inside a container (no /dev/dri; /sys/class/drm holds only 'version').
