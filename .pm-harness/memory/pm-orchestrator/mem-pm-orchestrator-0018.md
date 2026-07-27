---
id: mem-pm-orchestrator-0018
type: decision
scope: project
created: 2026-07-26
ttl_days: null
importance: 4
tags: [engineering-principle, honesty, api-design]
signature: "88dcde9f"
---

Engineering principle ratified 2026-07-25 (TASK-0008), generalizes beyond that task: when a value is unobservable, RE-KEY rather than RE-LABEL. A missing key cannot be ignored by a consumer; an in-band qualifier can. Applied concretely: on macOS a container emits memory.total_gb as unknown and puts the VM reading under a distinct memory.vm_total_gb key, so code asking for machine RAM cannot receive a VM number. Same reasoning underlies emitting facts == {} on unsupported Windows rather than an all-unknown map: 'we tried and failed' (unknown) is a different claim from 'we never try' (absent). Phase I and Phase M will both face the temptation to paper over an unobservable value with a qualified one; this is the standing answer.
