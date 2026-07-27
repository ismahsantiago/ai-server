---
id: mem-pm-orchestrator-0013
type: project-fact
scope: project
created: 2026-07-25
ttl_days: null
importance: 5
tags: [platforms, scope, constraints]
signature: "6a89bff8"
---

Director, 2026-07-25 (KICK-0002 round 3): supported platforms fixed as Linux (primary, freshly formatted plain distro) and macOS (secondary but genuine deployment target — reset Macs). Windows is out of scope; users are asked to install Linux for performance. Assume a freshly formatted machine, never accumulated tooling. Product identity restated by the Director: 'we should only function as a package installer that adapts to each need, which is why our requirements must be minimal and preferably already available in the Docker images we use' — so no probe or feature may require installing anything on the host beyond Docker and git; degrade to unknown instead. doctor must report software READINESS (can this machine execute a model today, what is missing, what fixes it) as well as hardware resources: presence is not readiness.
