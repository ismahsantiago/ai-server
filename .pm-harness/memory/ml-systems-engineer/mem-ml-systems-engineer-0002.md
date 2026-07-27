---
id: mem-ml-systems-engineer-0002
type: decision
scope: TASK-0009
created: 2026-07-26
ttl_days: null
importance: 5
tags: []
signature: "a433f186"
---

Criterion 2 (model acquisition/pull path) verdict, Pass B: status quo has NO supported pull path -- operator hand-sources a .gguf and copies it into ./models/ per docs/serving-baseline.md step 4, with no integrity check and no digest. DMR: 'docker model pull ai/<model>' or 'hf.co/<repo>' -- OCI-packaged, cached locally, offline after first pull; digest-pin architecturally plausible (OCI content-addressable) but not confirmed by a documented CLI syntax this run. Ollama: 'docker exec ollama ollama pull <model>' / POST /api/pull -- resumable pulls are explicitly documented (an advantage over DMR's documented behaviour, which does not mention resumability), cached locally, offline after first pull; digest-pin likewise not confirmed documented. Both DMR and Ollama are categorically better than the status quo on this criterion, which is why the kickoff and this document weight it heavily.
