---
id: mem-pm-orchestrator-0014
type: project-fact
scope: project
created: 2026-07-25
ttl_days: null
importance: 4
tags: [macos, metal, docker, runtime, risk]
signature: "8c88f4ca"
---

Open technical risk raised 2026-07-25 and routed to TASK-0008 (verify) and TASK-0009 (evaluate): on macOS, Linux containers run in a VM with no GPU passthrough, so a model served inside a container on a reused Mac runs CPU-only regardless of its Metal hardware. If confirmed, doctor must never report metal as available to containerized serving (host capability and container-reachable capability are different fields), and the Docker-only thesis is weaker on the macOS half of the fleet. Docker Model Runner may sidestep this by running the inference engine as a host-side process on Docker Desktop — treated as a hypothesis to verify, not established fact. Trade-off to watch: a host-side inference process is not confined by our container controls (cap_drop, read-only rootfs, pids_limit, network isolation) and sits outside what the Phase N gateway can enforce, so DMR may win on Mac acceleration and lose on containment.
