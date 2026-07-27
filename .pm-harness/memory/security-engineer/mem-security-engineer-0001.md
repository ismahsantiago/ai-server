---
id: mem-security-engineer-0001
type: decision
scope: TASK-0009
created: 2026-07-26
ttl_days: null
importance: 4
tags: [phase-r, dmr, llama.cpp, security-review]
signature: "d1a16950"
---

On 2026-07-25, security review for TASK-0009 approved the documented Phase R recommendation of status-quo llama.cpp, while preserving the condition that Phase N exposure is not approved until the gateway is the sole published LAN ingress, llama.cpp is on a private gateway-only network, LLAMA_API_KEY or --api-key is enabled, and host firewall/allowlist rules plus direct-bypass denial tests are evidenced. DMR remains rejected for this decision because its unauthenticated Docker Desktop API was hands-on reachable across Docker networks and its host-side Metal path removes ordinary container-network isolation; Linux containment remains documentation-only.
