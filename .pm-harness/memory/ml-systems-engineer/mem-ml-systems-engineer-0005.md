---
id: mem-ml-systems-engineer-0005
type: decision
scope: /ai-server/engineering/ml-systems-engineer
created: 2026-07-26
ttl_days: null
importance: 4
tags: [host-inspection, probes, degradation]
signature: "ccd8044a"
---

TASK-0008 decision: host inspection remains stdlib-only and performs no host installation. Subprocess probing is restricted to the fixed HOST_BINARY_ALLOWLIST: docker, nvidia-smi, sysctl, vm_stat, sw_vers, system_profiler.
