---
id: mem-ml-systems-engineer-0003
type: decision
scope: TASK-0009
created: 2026-07-26
ttl_days: null
importance: 4
tags: []
signature: "6fc281d1"
---

Third-party licensing verdict (criterion 4 subsection), Pass B: llama.cpp is MIT (confirmed via fetched LICENSE), compatible with Apache-2.0 distribution; status quo ships no model weights so weight licensing is N/A on our side. DMR runtime tooling (docker/model-runner, docker/model-cli) is Apache-2.0 (confirmed via GitHub license API), compatible, but DMR itself is delivered via Docker Desktop/Engine under Docker Inc.'s own EULA (Docker Subscription Service Agreement) which we neither vendor nor redistribute. Ollama runtime is MIT (confirmed via fetched LICENSE), compatible. Critically: model ARTIFACTS pulled via DMR's Docker Hub 'ai/' namespace or Ollama's model library carry their OWN upstream licenses independent of the runtime license -- confirmed hands-on for ai/gemma3, which repackages Google's Gemma weights under Google's Gemma Terms of Use, not a permissive OSS license. Verdict for both DMR and Ollama model-artifact paths: needs-notice, evaluated per model actually chosen, not blanket-compatible. Could not fetch a confirming example from Ollama's own library this run (structural point stands, but no second hands-on example beyond DMR's gemma3).
