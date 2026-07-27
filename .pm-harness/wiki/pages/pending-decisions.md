---
title: Pending Phase R runtime decision
kind: decision
sources:
  - docs/runtime-decision-phase-r.md
  - .pm-harness/wiki/pages/security-posture.md
updated: 2026-07-25
---

# Pending Phase R runtime decision

The engineering recommendation for TASK-0009 is **Status quo (llama.cpp)**,
pending Director decision ceremony. The recommendation preserves the
repository's demonstrated image digest pinning, SBOM integration, Compose
resource controls, offline-after-cache behavior, and available llama.cpp API
key mechanism while accepting the current model-acquisition gap as follow-up
work (source: `docs/runtime-decision-phase-r.md` §§Per-criterion scoring table,
Recommendation).

Docker Model Runner is not recommended because hands-on Docker Desktop testing
found unauthenticated API reachability independent of Docker network membership;
Ollama in container is not recommended because its documented container image
binds broadly without a documented native API authentication mechanism and the
repository has no equivalent hardened template (source:
`docs/runtime-decision-phase-r.md` §§DMR blast radius, Recommendation).

This page records an engineering recommendation, pending Director decision
ceremony. It is not an accepted product decision and must not be read as a
security-engineer sign-off.

## Contradiction

No contradiction was found between this pending recommendation and the current
security posture: the recommendation retains the documented localhost default
and treats LAN exposure as requiring a future gateway, bearer-token, allowlist,
and firewall topology (sources: `docs/runtime-decision-phase-r.md` §Behind the
Phase N gateway; `.pm-harness/wiki/pages/security-posture.md`). The Phase R
document's LAN-server evaluation target is therefore recorded as a future
engineering gate, not as permission to bypass the existing fail-closed
default.

Related: [[security-posture]], [[accepted-decisions]], [[generator-workflow]].
