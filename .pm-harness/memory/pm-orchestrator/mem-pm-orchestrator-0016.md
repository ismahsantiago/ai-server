---
id: mem-pm-orchestrator-0016
type: decision
scope: project
created: 2026-07-25
ttl_days: null
importance: 5
tags: [legal, license, distribution, apache-2.0]
signature: "1430c4a5"
---

Director decision 2026-07-25 (ESC-0002, resolved): ai-server is licensed Apache-2.0. Origin: the repo declared itself private and unlicensed (pyproject.toml lines 10-15 plus the 'Private :: Do Not Upload' classifier, no LICENSE file) while KICK-0002 defines the product as clone-and-run software handed to entrepreneurs and small teams. Recorded as audit finding LEG-001 on 2026-07-24 and never put to the Director until now. Apache-2.0 chosen over MIT for the explicit patent grant and contribution framework, given we ship a security gateway and integrate third-party inference runtimes; AGPL-3.0 rejected because its network copyleft would deter the small development teams the Director named as target users. Implementation is TASK-0011. NOT discharged by that task: the third-party notice review, which belongs to whichever phase closes the runtime decision (TASK-0009), since we ship a pinned upstream llama.cpp image and may add Docker Model Runner or Ollama.
