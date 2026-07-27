---
id: mem-pm-orchestrator-0010
type: decision
scope: project
created: 2026-07-25
ttl_days: null
importance: 5
tags: [posture, security, lan, product-direction]
signature: "d163a45b"
---

KICK-0002 (2026-07-25): the Director reversed the localhost-only posture. LAN exposure and bearer-token auth are now authorized and become Phase N, implemented as the TLS-terminating gateway with bearer-token verification and a gateway-enforced client allowlist that the repo had already documented as its exit condition. TLS and token ship together; a bearer token over plaintext HTTP is never acceptable. Localhost stays the default, LAN is explicit opt-in, and validate must fail closed if a workspace claims LAN without a working gateway. Public-internet exposure is out of scope this iteration (unknown user infrastructure: CGNAT, dynamic IPs, provider-locked modems), but the gateway must not assume clients share the subnet, so adding it later is configuration and hardening rather than a rewrite.
