---
id: mem-ml-systems-engineer-0004
type: project-fact
scope: TASK-0009
created: 2026-07-26
ttl_days: null
importance: 4
tags: []
signature: "256a578c"
---

Criterion 1 finding that complicates the minimal-requirements framing: the status quo, AS CURRENTLY WIRED via ai_server_generator, is NOT 'nothing beyond Docker and git' -- README.md:19-27 states Python 3.10+ plus 'pip install -r requirements.txt' (Jinja2, MarkupSafe) as hard prerequisites, because workspace generation (matrix/generate/validate) is a Python CLI, not something that runs inside the pinned llama.cpp image. A fresh Linux/reset Mac does not ship Python 3.10+ by default. Only the bare llama.cpp runtime itself, decoupled from this repo's generator tooling, satisfies 'nothing beyond Docker+git'. Separately: DMR on Docker Engine (the primary target platform) requires installing the docker-model-plugin host package via apt/dnf -- a real extra step not shared by Ollama-in-container, which needs nothing beyond Docker+git since the ollama/ollama image ships both server and CLI. Flagging because Pass C's recommendation and Docker-mandatory-vs-no-Docker sections must not assume the status quo is already minimal by default; it currently is not, as packaged.
