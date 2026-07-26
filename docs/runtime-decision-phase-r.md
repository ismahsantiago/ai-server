# Runtime decision — Phase R (TASK-0009 / KICK-0002)

Comparison of three model-serving runtime options for the reused-consumer-laptop
LAN-server target fixed by KICK-0002: (a) status quo — pinned
`ghcr.io/ggml-org/llama.cpp:server` + generated Compose, (b) Docker Model
Runner (DMR), (c) Ollama in a container. Evaluated against the eight fixed
criteria from the kickoff. This revision consolidates the completed evidence
passes, the remaining documented uncertainty, the engineering recommendation,
and the security handoff. It is a recommendation for review, not a Director
decision or a security-engineer sign-off.

## Evidence status

**What this run can decide, and what it cannot.** Criteria 2 (model
acquisition), 3 (access-control enforceability), 4 (digest-pinnability), 7
(offline behaviour) and 8 (blast radius / default exposure) do not require a
performance benchmark to answer — they are architectural, security, and
supply-chain questions, answerable from configuration, source, and official
documentation. Those are also the criteria that determine whether an option
is viable *at all* for this target. Criterion 5 (GPU/CPU portability) and any
head-to-head performance ranking between viable options are comparatively
smaller questions, are the least evidence-rich in this run, and can be
settled later on representative target hardware (a Linux/Docker-Engine
machine with an integrated GPU) without changing the outcome of this
document. This document is therefore strong on architecture, security,
supply chain, and offline behaviour, and thin on measured performance — by
design, not by omission.

**The pre-existing gap, confirmed.** At the start of this task, `models/`
contained only `README.md` — no `.gguf` file existed anywhere in the
repository. All three pre-existing reports in `logs/benchmarks/` are
placeholder templates, not real measurements. Quoted verbatim from
`logs/benchmarks/smoke-benchmark-20260723-233741.md`:

```
- Profile: unknown
- Model path: /models/placeholder.gguf

| HTTP status | not-tested |
```

The other two pre-existing reports (`smoke-benchmark-20260723-233600.md`,
`smoke-benchmark-20260723-233700.md`) contain the same `Model path:
/models/placeholder.gguf` line and either `placeholder (run after model
mount)` or `not-tested` for `HTTP status`. **No real llama.cpp performance
baseline existed in this repository as of the start of this run.**

**What this run did about it.** Docker Desktop was started successfully this
run (it was down at task start) and a real, non-placeholder llama.cpp
baseline reading was obtained — see "Baseline outcome" below. This closes
the pre-existing gap on this development host only; it does not constitute
evidence about the Linux/Docker-Engine target platform, and it is not a
substitute for a representative-hardware benchmark, which remains deferred
(see the later-pass "Deferred measurement" subsection referenced in the
plan).

### Baseline outcome (branch (a) reached)

Docker Desktop was started (`open -a Docker`; `docker info` succeeded within
~5s of the daemon coming up). A genuinely tiny, real `.gguf` test model
(`stories260K.gguf`, ~1.1 MB, from `ggml-org/models` on Hugging Face — not a
production-representative model, but a real weights file, not a fabricated
one) was downloaded and placed at `generated/phase-r-baseline/probe-model/stories260k-probe.gguf`
(moved there from the originally-written `models/smollm3-3b.gguf` by
engineering-manager after Pass A, because leaving a 260K-parameter toy model
at a real 3B preset's canonical model path would make `validate --tier host`
report SmolLM3-3B as installed when it is not; `models/` again contains only
`README.md`). A workspace was generated with:

```
python3 -m ai_server_generator generate --preset smollm3-3b --profile medium-fast \
  --access localhost --out generated/phase-r-baseline
```

`generated/phase-r-baseline/scripts/start.sh` was run, the container reached
`health: starting` → healthy, and both the generated workspace's own
`scripts/smoke.sh` and the legacy root `scripts/smoke_benchmark.sh` were run
against it once each.

- Canonical repo-root artifact:
  `logs/benchmarks/smoke-benchmark-20260725-142634.md` — **HTTP status: 200**
  (non-placeholder).
- Richer generated-workspace artifact (kept as a throwaway working artifact,
  not required by the plan but retained for traceability):
  `generated/phase-r-baseline/logs/benchmarks/smoke-benchmark-20260725-142623-40594.md`
  — HTTP status 200, TTFB p50 9.816 ms / p95 13.193 ms, total latency p50
  9.985 ms / p95 13.362 ms, container memory 11.796 MB.

**Label, as required:** these readings are **arm64 / Docker Desktop —
indicative only, not the Linux/Docker Engine target platform**. The model
used is a 260K-parameter toy model chosen only to obtain a real, non-fabricated
HTTP 200 reading quickly; its latency/memory numbers are not representative
of any of the five real presets in `ai_server_generator/presets.py` and must
not be read as a performance claim about this project's actual model
offerings. No other numeric latency/memory value appears anywhere else in
this document without this same qualification.

## Status quo (llama.cpp)

Runtime: `ghcr.io/ggml-org/llama.cpp:server@sha256:4f02c...837d4`, pinned by
digest in both `docker-compose.yml` and
`templates/chat/docker-compose.yml.j2`, run this session
(`docker run --rm --entrypoint /app/llama-server ... --version` →
`version: 10108 (0a50d9909), built with GNU 14.2.0 for Linux aarch64`).

**Default network binding and authentication posture (established
independently, not assumed).**

- The upstream `llama-server` binary's own default (confirmed this run via
  `llama-server --help` against the pinned image): `--host` defaults to
  `localhost`, and the binary supports authentication —
  `--api-key KEY` / `--api-key-file FNAME` (env `LLAMA_API_KEY`).
- **This repository's actual configuration does not use either upstream
  default.** `docker-compose.yml:17-18` and
  `templates/chat/docker-compose.yml.j2:14-15` both explicitly pass
  `--host 0.0.0.0`, overriding the safer upstream default. Neither compose
  file sets `--api-key` or `--api-key-file` anywhere (`grep -n
  "api-key|api_key|LLAMA_API_KEY" docker-compose.yml
  templates/chat/docker-compose.yml.j2` returns no matches, confirmed this
  run).
- The only containment in place is a **host-level** control:
  `docker-compose.yml:10` and `templates/chat/docker-compose.yml.j2:7`
  publish the port as `127.0.0.1:${HOST_PORT}:8000`, which prevents reaching
  the server from outside the Docker host but does **not** restrict reachability
  from other containers on the same Docker network.
- **Confirmed hands-on this run**: with `generated/phase-r-baseline`'s
  llama-server container running and attached to Docker network
  `phase-r-baseline_default`, a second, unrelated sibling container reached
  it directly and unauthenticated:
  `docker run --rm --network phase-r-baseline_default curlimages/curl:latest
  -sS http://ai-lab-llama-server-chat:8000/v1/models` returned a full model
  listing (HTTP 200) with no `Authorization` header sent.
- **Verdict**: default binding (as configured in this repo) = `0.0.0.0`
  inside the container, restricted to `127.0.0.1` only at the Docker
  host-port-publish layer; default authentication = **none** — the runtime
  supports `--api-key` but this repository does not enable it anywhere. Any
  container sharing the Docker network with the llama-server container can
  reach its full API unauthenticated today. Resource hardening
  (`cap_drop: ALL`, read-only rootfs, non-root `65532:65532`, `mem_limit`,
  `cpus`, `pids_limit` — `docker-compose.yml:33-47`) is real and independently
  verified by inspection, but it is a blast-radius *limiter*, not an
  access-control mechanism; it does not change the auth verdict above.

## Docker Model Runner

Backend confirmed running this session on Docker Desktop (macOS/arm64) via
`docker model status`: `llama.cpp latest-metal` backend, `Running`; `docker
model version` shows client `v1.2.4` and a reachable server once the daemon
was up.

**Default network binding and authentication posture (established
independently, not assumed).**

- Official documentation (`https://docs.docker.com/ai/model-runner/`,
  fetched this run), verbatim: *"The Model Runner API is not authenticated.
  Any client that can reach it, including other containers on the same
  Docker network, can pull, load, and run models, and send inference
  requests."* This directly confirms the kickoff baseline finding.
- The same page states the isolation boundary differs by platform, verbatim:
  *"On Linux, Docker Model Runner and its inference engines, such as
  Diffusers, run inside a container, which provides the isolation boundary.
  On macOS and Windows, the engines don't run inside a container, so Docker
  Model Runner runs them in a sandboxed environment (seatbelt/sandbox-exec
  and Job Objects respectively)."* This Desktop-vs-Engine difference is
  itself a finding, as flagged going into this run: DMR is not the same
  artifact on the two platforms.
- **Confirmed hands-on this run (Docker Desktop, macOS/arm64 — NOT the
  Linux/Docker Engine target platform, labeled accordingly)**:
  - `docker run --rm --network phase-r-baseline_default curlimages/curl:latest
    -sS http://model-runner.docker.internal/engines/llama.cpp/v1/models` from a
    sibling container on the llama-server's own Compose network returned
    HTTP 200 with a live model listing (including a pre-existing pulled
    model, `docker.io/ai/gemma4:latest`, unrelated to this task), no auth
    header sent.
  - The identical request from a container **not attached to that network at
    all** (plain `docker run --rm curlimages/curl:latest ...`, default
    bridge network) returned the same HTTP 200 result. On Docker Desktop, DMR
    is reachable via the Desktop-internal DNS proxy **regardless of which
    Docker network a container is on** — Docker-network segmentation, by
    itself, does not confine it on this platform.
- **Verdict**: default binding = effectively host-wide on Docker Desktop
  (confirmed hands-on: reachable independent of network membership); on
  Docker Engine the API is served by an actual container per the docs quote
  above, which is a materially different (and potentially more confinable)
  exposure surface, but this was **not independently confirmed hands-on this
  run** — no Linux/Docker Engine host was available — and is labeled
  documentation-only for that platform. Default authentication = **none**,
  confirmed by both documentation and hands-on testing.

See "DMR blast radius" below for the containment verdict this feeds into.

## Ollama in container

**Default network binding and authentication posture (established
independently, not assumed — this repo's earlier draft plan asserted Ollama
was "not unauthenticated-by-default in the same way" as DMR; that assertion
was struck during plan review and is treated here as unverified until
checked).**

- Ollama's own FAQ (`https://raw.githubusercontent.com/ollama/ollama/main/docs/faq.mdx`,
  fetched this run), verbatim: *"Ollama binds 127.0.0.1 port 11434 by
  default. Change the bind address with the `OLLAMA_HOST` environment
  variable."* The upstream binary default is localhost-only — the same
  posture as llama.cpp's own upstream default, and safer than either
  runtime's typical containerized deployment (see below).
- **The official container image does not use that default.** Fetched this
  run from `https://raw.githubusercontent.com/ollama/ollama/main/Dockerfile`
  (`ollama/ollama`, `main` branch), line 316:
  `ENV OLLAMA_HOST=0.0.0.0:11434`, with `ENTRYPOINT ["/bin/ollama"]` /
  `CMD ["serve"]` (lines 318-319). This is baked into the published
  `ollama/ollama` image, not something an operator opts into. It is also the
  only way the documented quick-start command in
  `https://raw.githubusercontent.com/ollama/ollama/main/docs/docker.mdx`
  (`docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama
  ollama/ollama`) can work at all: a process bound only to `127.0.0.1` inside
  a container cannot be reached through Docker's `-p` port publishing.
- Authentication: `docs/api.md` (fetched this run, ~1,900 lines, documents
  every REST endpoint — generate, chat, create/list/show/copy/delete model,
  pull/push, embeddings, running models) contains **zero** mentions of
  authentication, an API key, a bearer token, or any credential mechanism.
  `docs/faq.mdx` mentions only `OLLAMA_ORIGINS` (a CORS allow-list, not
  authentication). No authentication mechanism could be found in official
  Ollama documentation.
- A hands-on container test (running `ollama/ollama` locally and repeating
  the sibling-container reachability probe used for llama.cpp and DMR above)
  was attempted this run but could not be completed within the session — the
  ~2 GB image pull (`docker pull ollama/ollama:latest`) had not finished by
  the time this pass closed. The posture above is therefore
  **documentation-sourced (official FAQ + source Dockerfile), not
  independently confirmed by a running-container probe this run** — labeled
  accordingly, and distinct from the llama.cpp and DMR findings above, both
  of which were confirmed by a live running-container probe.
- **Verdict**: default binding (official container image) = `0.0.0.0` inside
  the container — the same expose-by-default pattern found for DMR and for
  this repository's own llama.cpp configuration, not a safer default; default
  authentication = **none found** in official documentation. Unlike the
  status quo, Ollama does not appear to expose an equivalent of `--api-key`
  in its documented API surface at all — the gap cannot be closed the same
  way.

## Per-criterion scoring table

Rows 1-8 are populated across TASK-0009's completed evidence passes. Labels
inside cells distinguish hands-on observations from documentation-only claims
and could-not-verify gaps; no performance number is inferred where no command
was run.

| # | Criterion | Status quo (llama.cpp) | Docker Model Runner | Ollama in container |
|---|---|---|---|---|
| 1 | Operator install footprint | Runtime itself: nothing beyond Docker+git. **As currently wired via `ai_server_generator`: Docker+git+Python 3.10+** (`README.md:19-27`) — a real, currently-true cost the minimal-requirements doctrine penalizes. See "Criteria 1, 2, 4 and 7" below. | Docker Desktop: nothing beyond Docker (toggle in Settings). **Docker Engine (Linux, primary target): additional host package `docker-model-plugin`** (`apt-get`/`dnf`, `docs.docker.com/manuals/ai/model-runner/get-started/`). | Nothing beyond Docker+git — server+CLI ship inside `ollama/ollama`; `docker run ... ollama/ollama` is the entire footprint (`docs/docker.mdx`). |
| 2 | Model acquisition / pull path (**weighted heavily**) | **No supported pull path.** Operator hand-sources a `.gguf` and copies it in (`docs/serving-baseline.md` step 4). No integrity check, no digest. | `docker model pull ai/<model>` or `hf.co/<repo>`; OCI-packaged, cached locally, offline after first pull; digest-pin architecturally plausible, not confirmed documented. | `docker exec ollama ollama pull <model>` / `POST /api/pull`; resumable pulls (documented); cached locally, offline after first pull; digest-pin not confirmed documented. |
| 3 | Access-control enforceability (LAN + bearer token) | **Partial today; enforceable only with changes.** Status quo has the project baseline LAN-safe refusal (`docs/lan-safe-runbook.md:5-8`) and localhost host-publish (`docker-compose.yml:9-10`, `templates/chat/docker-compose.yml.j2:6-7`), and llama.cpp supports `--api-key`, but this repo does not enable it; missing: generated reverse proxy/gateway, bearer-token wiring, LAN allowlist/firewall, token handling, and logs (`docs/lan-safe-runbook.md:25-45`). | **No as-is.** DMR API is unauthenticated by design and reachable by containers that can reach it; on Desktop this run showed reachability independent of Docker network membership. Missing: an enforceable choke point between all clients and DMR, token enforcement outside DMR, and a platform-specific way to prevent direct `model-runner.docker.internal` access; no DMR-native bearer token found. | **No as-is.** Official container binds `0.0.0.0` and no HTTP auth mechanism was found in official docs. Missing: reverse proxy/gateway bearer-token enforcement, LAN allowlist/firewall, and a way to ensure clients cannot bypass the proxy to the container API; no Ollama-native bearer token found. |
| 4 | Digest-pinnability / supply-chain auditability | **Yes, demonstrated**: image pinned by digest (`docker-compose.yml:6`), enumerated in `sbom.json`, re-pinnable via `scripts/resolve_image_digest.sh`. Model weights: no pull path to pin (criterion 2). Licensing: MIT runtime (compatible); model weights N/A (none shipped). | **No, not confirmed pinnable this run** by this project's tooling; runtime itself is Apache-2.0 (compatible) but delivered via Docker Desktop/Engine, outside our SBOM. Model artifacts: needs-notice per model (e.g. `ai/gemma3` carries Google's Gemma Terms of Use, confirmed this run). | **No, not confirmed pinnable this run**; runtime is MIT (compatible). Model library artifacts: needs-notice per model, same pattern as DMR (structural point confirmed; a specific example page could not be fetched successfully this run). |
| 5 | GPU/CPU portability across hardware tiers | **CPU yes; GPU path split.** macOS: CPU-only in this repo's normal Linux container on Docker Desktop (**measured-this-run**: `--list-devices` printed only `Available devices:`); Linux: CPU yes, GPU possible with a different llama.cpp build/backends and devices (CUDA/HIP/Vulkan documented upstream) but **not verified for this pinned image**. Windows out of scope. | **Strongest documented breadth.** macOS: Apple Silicon Metal backend reachable on Desktop (**measured-this-run**: `latest-metal`, MTL0 Apple M1 Pro logs). Linux: CPU, NVIDIA/CUDA, AMD/ROCm, and Vulkan backends documented for Docker Engine (**documentation-only**, not measured here). Windows out of scope. | **Good Linux container GPU story; macOS container GPU no.** macOS: Docker Desktop GPU acceleration unavailable for containers (**documentation-only**, Ollama FAQ); Linux: NVIDIA via `--gpus=all`, AMD/ROCm via `ollama/ollama:rocm`, and Vulkan via `/dev/dri` documented (**documentation-only**, not measured here). Windows out of scope. |
| 6 | Resource limits (`mem_limit`, `cpus`, `pids_limit`) | **Yes.** Enforced in Compose: `mem_limit`, `cpus`, and `pids_limit` are present in both the root compose (`docker-compose.yml:33-35`) and template (`templates/chat/docker-compose.yml.j2:33-35`); additional hardening appears around `user`, `no-new-privileges`, `cap_drop`, read-only rootfs, and tmpfs (`docker-compose.yml:36-49`, `templates/chat/docker-compose.yml.j2:36-49`). | **Partial.** Linux/Engine DMR runs inference engines inside a container per Docker docs, so container-level limits may be possible around that deployment, but no model-runner-specific `mem_limit`/`cpus`/`pids_limit` control was verified in this repo; macOS Desktop engines do not run inside a normal container, so Compose limits do not apply. | **Partial today; yes if templated as a project-owned container.** Ordinary Docker/Compose limits can apply to an Ollama container, but this repository has no Ollama compose template today; GPU/device exposure would need explicit limits and device grants. |
| 7 | Offline / air-gapped behaviour | **Works** fully offline once image+model are local; no runtime-time network dependency at all. | **Works once cached**, degrades (needs registry/HF reachability) on first pull; Engine install of `docker-model-plugin` is an extra one-time online dependency. | **Works once cached**, degrades on first pull; resumable pulls documented; no extra host package to fetch first. |
| 8 | Blast radius of default-exposure/authentication property | Config in this repo binds the container internally to `0.0.0.0` with no `--api-key` set anywhere; containment is host-port-publish only (`127.0.0.1`), not container/API auth; confirmed hands-on that a sibling container on the same Docker network reaches the full API unauthenticated. **MODERATE risk, and the only one of the three with a documented, unused fix available** (`--api-key`/`LLAMA_API_KEY`, upstream-supported, zero-effort to enable). | Unauthenticated by design (official docs + hands-on); on Docker Desktop, confirmed hands-on **not confinable by Docker-network segmentation at all** (reachable regardless of network membership); Linux/Engine containment is documentation-only, unconfirmed this run. **HIGH risk — see containment verdict below.** | Official container image binds `0.0.0.0` by default with no authentication mechanism found anywhere in official docs, and — unlike the status quo — no documented flag to add one. **HIGH risk, structurally worse than the status quo because there is no known fix to enable**, though not independently confirmed unconfinable by hands-on network testing this run (documentation-sourced only). |

## Criteria 1, 2, 3, 4, 5, 6, 7 and 8 — detailed findings

This section carries the prose justification for all eight rows of the scoring
table above. The decision and review sections below are deliberately separate
from the evidence findings.

### Criterion 1 — operator install footprint (weighted under the
minimal-requirements doctrine)

Per the Director's minimal-requirements doctrine (*"we should only function
as a package installer that adapts to each need, which is why our
requirements must be minimal and preferably already available in the Docker
images we use"*), this criterion assumes a **freshly formatted machine** and
credits an option only for what it needs beyond Docker and git — nothing
that merely happens to be installed on this development host is credited.

- **Status quo (llama.cpp), as the runtime itself**: **nothing** beyond
  Docker + git. The pinned `ghcr.io/ggml-org/llama.cpp:server` image contains
  the entire server binary; `docker compose up` against a hand-authored or
  already-generated `docker-compose.yml` needs no other host software.
- **Status quo, as currently wired in this repository via
  `ai_server_generator`** — a materially different, and more honest,
  statement of today's actual operator contract: the canonical path
  (`docs/serving-baseline.md` steps 1-3; `README.md`'s own "5-minute quick
  start") is `matrix` → `generate` → `validate`, all invoked as
  `python3 -m ai_server_generator ...`. `README.md:19-21` states the
  project's own prerequisites plainly: **"Python 3.10+", "Docker + Docker
  Compose"**, and a local `.gguf`; `README.md:25-27` additionally requires
  `python3 -m pip install -r requirements.txt` (pinned to `Jinja2==3.1.6`,
  `MarkupSafe==3.0.3` per `requirements.txt`) before `matrix`/`generate` can
  run at all. **This is a real, currently-true requirement beyond Docker and
  git — a fresh Linux install or a reset Mac does not ship Python 3.10+ or
  pip packages by default**, and this repository's own README names Python
  3.10+ as a hard prerequisite, not an optional convenience. This is flagged
  explicitly because it complicates any claim that the status quo already
  satisfies the minimal-requirements doctrine merely by virtue of being the
  incumbent: **as currently packaged, it does not** — only the *bare llama.cpp
  runtime itself*, decoupled from this repo's generator tooling, does.
- **Docker Model Runner**: on **Docker Desktop**, **nothing** beyond Docker
  itself — DMR ships inside Docker Desktop and is turned on via **Settings →
  AI → Enable Docker Model Runner** (`docs.docker.com/manuals/ai/model-runner/get-started/`,
  fetched this run); no separate package install. On **Docker Engine**
  (Linux — the primary supported platform), DMR is **not** bundled and must
  be installed as a **separate host package**: the same page states, verbatim,
  `sudo apt-get install docker-model-plugin` (Ubuntu/Debian) or
  `sudo dnf install docker-model-plugin` (RPM-based). **This is a real,
  documented requirement beyond Docker and git, specifically on the primary
  target platform** — it is a Docker-published package, not third-party
  software, but it is still an additional `sudo`-privileged install step a
  freshly formatted Linux host does not have until it is run.
- **Ollama in container**: **nothing** beyond Docker + git. The documented
  quick start (`docs/docker.mdx`, fetched this run) is a single command,
  `docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama
  ollama/ollama`; the server and CLI both ship inside the `ollama/ollama`
  image (model pulls can be issued via `docker exec ollama ollama pull
  <model>` or the container's own HTTP API), so no host-installed Ollama
  binary is required.

**No option here was credited for tooling that merely happens to be present
on this development host** (this Mac already has Python 3.14, Homebrew, and
a working `docker model` plugin from unrelated prior use — none of that was
assumed available, and the Python requirement above is named as a cost
specifically *because* a fresh machine will not have it).

### Criterion 2 — model acquisition / pull path (weighted heavily; the
largest practicality gap today, per the kickoff)

This criterion is weighted more heavily than the others in this document's
overall assessment because the kickoff (KICK-0002) identifies it as the
single largest practicality gap between the current product and a
"clone-and-run" experience for a non-sysadmin operator, and because it is
the criterion where the three options differ most starkly today.

- **Status quo**: **no supported pull path exists.** `docs/serving-baseline.md`
  step 4 requires the operator to manually run
  `cp models/ornith-9b.gguf generated/<preset-profile-access>/models/` —
  i.e. the operator must already possess a correctly named `.gguf` file
  somewhere on disk before this step, sourced by some means this repository
  does not provide, document, or verify. There is no `docker pull`-equivalent
  for the model weight itself; integrity is **not verifiable by this
  project** (no checksum, no digest, no provenance check is run against the
  hand-placed file); offline behavior is trivially "works" only because there
  is no network step to begin with — the operator did the network work
  themselves, outside this project's view. What the operator physically
  types, once a `.gguf` is already in hand: `cp <file>
  generated/<name>/models/` then `./scripts/start.sh` — but sourcing that
  file is the actual bottleneck this criterion is meant to score, and it is
  entirely unsolved today.
- **Docker Model Runner**: a real pull path exists —
  `docker model pull ai/smollm2` (Docker Hub) or `docker model pull
  hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF` (Hugging Face directly),
  confirmed from `docs.docker.com/manuals/ai/model-runner/get-started/`,
  fetched this run. Models are packaged as **OCI Artifacts**
  (`docs.docker.com/manuals/ai/model-runner/`, "Package GGUF and Safetensors
  files as OCI Artifacts") pulled from Docker Hub, any OCI-compliant
  registry, or Hugging Face, and are **cached locally** after first pull, so
  the runtime works offline once a model has been pulled once. Integrity:
  because the artifact is OCI-packaged it is architecturally
  content-addressable the same way container images are — but the
  documented CLI usage fetched this run (`docker model pull MODEL`, with an
  optional `:TAG`) does not show an explicit digest-pin example
  (`MODEL@sha256:...`) anywhere in the reference page fetched
  (`docs.docker.com/reference/cli/docker/model/pull/`). **Verdict: pull-by-name
  is real and simple; pull-by-digest is architecturally plausible but not
  confirmed by a documented command this run** — labeled accordingly rather
  than assumed. What the operator physically types (after DMR is enabled/
  installed per criterion 1): one line, `docker model pull ai/<model>`.
- **Ollama in container**: a real pull path exists via the container's own
  API/CLI — `docker exec ollama ollama pull llama3.2`, or `POST
  /api/pull` (`docs/api.md`, fetched this run: *"Download a model from the
  ollama library. Cancelled pulls are resumed from where they left off, and
  multiple calls will share the same download progress."*) — a materially
  **better resumability story** than DMR's documented behavior, which does
  not mention resumable pulls anywhere in the pages fetched this run.
  Integrity: Ollama's internal manifest/layer format is SHA256-digest
  addressed (confirmed this run — `docs/api.md` shows layer references such
  as `"using existing layer sha256:..."` and blob creation keyed by SHA256
  digest), so pull integrity is verifiable at the layer level, but — as with
  DMR — no top-level `ollama pull model@sha256:...` digest-pin command was
  found documented in the pages fetched this run. Offline: cached locally
  after first pull, same pattern as DMR. What the operator physically types:
  `docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama
  ollama/ollama` once, then `docker exec ollama ollama pull llama3.2`.
- **Weighting rationale, stated explicitly**: this criterion is weighted
  heavily because it is the one dimension on which the status quo is not
  merely worse but **categorically absent** — DMR and Ollama both give the
  operator a single, documented command that fetches a model by name with
  local caching and no manual file-hunting; the status quo gives the
  operator nothing but a copy instruction into a directory that assumes the
  hard part (finding and downloading a correctly formatted `.gguf`) already
  happened somewhere else. Any recommendation that keeps the status quo's
  pull path unchanged is choosing to leave the kickoff's largest named
  practicality gap open.

### Criterion 3 — access-control enforceability (LAN + bearer token)

This criterion asks whether the model API can be exposed to a trusted LAN only
through an enforcement point that applies a bearer token and source allowlist,
without letting callers bypass that enforcement point and hit the model socket
directly. The current in-repository security baseline is intentionally
localhost-only: `docs/lan-safe-runbook.md:5-8` states that `--access lan`,
`--auth bearer-token`, and `--lan-allowlist` are rejected by the generator,
and `docs/lan-safe-runbook.md:10-12` explains why — recording a security value
that is not enforced would be worse than refusing the workspace. The future
LAN bar is explicit but unimplemented: a reverse proxy must reject
authentication failures before traffic reaches the model container, firewall
rules must restrict sources, the bind must change only after auth+firewall
exist, tokens must live outside commits and rotate, and access logs must be
kept (`docs/lan-safe-runbook.md:25-45`).

- **Status quo (llama.cpp)**: **partial today; enforceable only with
  changes**. The host-published port is localhost-only in both the legacy root
  compose (`docker-compose.yml:9-10`) and generated template
  (`templates/chat/docker-compose.yml.j2:6-7`), which is a safe refusal for
  LAN but not LAN+token enforcement. The server process itself is currently
  bound inside the container to `0.0.0.0` (`docker-compose.yml:17-18`,
  `templates/chat/docker-compose.yml.j2:14-15`), and this run confirmed a
  sibling container on the same Docker network can reach it unauthenticated.
  What the option lacks for LAN+token enforcement today: generated reverse
  proxy/gateway wiring, mandatory bearer-token configuration, LAN source
  allowlist/firewall enforcement, secret storage/rotation handling, access
  logging, and a network topology where only the gateway shares the model
  network. The mitigating fact is that llama.cpp itself supports `--api-key` /
  `--api-key-file` (`LLAMA_API_KEY`), so the model process can be made to
  reject direct unauthenticated bypass attempts in addition to gateway
  enforcement; this repository simply does not enable it yet.
- **Docker Model Runner**: **no as-is**. Official Docker documentation says
  the Model Runner API is not authenticated and that any client that can reach
  it can pull, load, run, and send inference requests; this run confirmed that
  on Docker Desktop for macOS, `model-runner.docker.internal` was reachable
  from containers regardless of whether they shared the application Compose
  network. What DMR lacks for LAN+token enforcement today: DMR-native bearer
  token enforcement, a documented socket-only or gateway-only mode on Desktop,
  and a platform-specific control preventing containers or host clients from
  bypassing the Phase N gateway and calling DMR directly. On Linux/Engine,
  Docker documents DMR as container-based, which may permit stricter network
  confinement, but that was not measured on a Linux host this run and remains
  documentation-only.
- **Ollama in container**: **no as-is**. The official `ollama/ollama` image
  sets `OLLAMA_HOST=0.0.0.0:11434`, and no HTTP API authentication mechanism
  was found in official Ollama docs this run. What Ollama lacks for LAN+token
  enforcement today: an Ollama-native bearer-token switch equivalent to
  llama.cpp's `--api-key`, a generated reverse proxy/gateway in this
  repository, LAN source allowlist/firewall enforcement, token handling,
  access logging, and a topology that prevents direct container-network or
  host-port access to the Ollama API. It can be placed behind a proxy, but
  without a native token on the model API, bypass prevention depends entirely
  on Docker network design and host firewalling.

### Criterion 4 — digest-pinnability and supply-chain auditability

- **Status quo**: pin-able today, **demonstrated in this repository**.
  `docker-compose.yml:6` and `templates/chat/docker-compose.yml.j2` (image
  line) pin the serving image by digest
  (`ghcr.io/ggml-org/llama.cpp:server@sha256:4f02c...837d4`); `sbom.json`
  enumerates that exact image reference as a `pkg:oci/llama.cpp` component
  alongside the pinned Python dependencies, with the SBOM's own stated scope
  being "Pinned Python dependencies and the digest-pinned serving image.
  Transitive OS packages inside the container image are not enumerated" (an
  honest, self-declared limitation, not a gap this pass discovered);
  `scripts/resolve_image_digest.sh` lets an operator deliberately re-resolve
  and re-pin the digest via the registry's own content-digest header,
  without pulling anything, and `scripts/generate_sbom.py` regenerates
  `sbom.json` from the pinned values so the two cannot silently drift. Model
  weights have **no equivalent enumeration or pinning today**, but only
  because there is no pull path to enumerate (criterion 2) — there is
  nothing to pin because the operator sources the file entirely outside this
  project's tooling.
- **Docker Model Runner**: **no — not confirmed pinnable this run.** The
  runtime tooling itself (`docker/model-runner`, `docker/model-cli`) is
  Apache-2.0 and open source (confirmed via `api.github.com/repos/docker/model-runner`
  license field and a fetched `LICENSE` file), but we do not vendor or pin
  it — it is installed as part of Docker Desktop or the `docker-model-plugin`
  package (criterion 1), outside this project's SBOM entirely, the same way
  the Docker Engine binary itself is outside our SBOM. Pulled **model**
  artifacts are OCI-packaged (architecturally content-addressable, as noted
  under criterion 2), but no documented digest-pin CLI syntax was found this
  run, and this repository has no equivalent of `resolve_image_digest.sh` /
  `generate_sbom.py` for DMR-pulled models today. **Verdict: not currently
  pinnable or auditable by this project's existing supply-chain tooling; the
  underlying artifact format does not rule it out architecturally, but that
  is not the same as a working pin today.**
- **Ollama in container**: **no — not confirmed pinnable this run**, for the
  same reason. The runtime (`ollama/ollama`) is MIT-licensed and its
  internal layers are SHA256-addressed (criterion 2), but no documented
  top-level digest-pin pull command was found, and this repository has no
  SBOM/digest-resolution tooling for Ollama-pulled models today. Same
  verdict as DMR: architecturally plausible, not demonstrated.

#### Third-party licensing

The Director resolved ESC-0002 on 2026-07-25: this project is now licensed
**Apache-2.0** (previously private and unlicensed; see
`.pm-harness/escalations/resolved/ESC-0002.md`). The third-party notice
review the TASK-0007 audit required before distribution (finding LEG-001)
was explicitly **not** discharged by the licensing decision itself and was
carried forward to whichever phase closes the runtime decision — this one.
Note for the record: at the start of this pass, `pyproject.toml:10-15` still
carried the stale "Private project for personal use… carries no license"
comment and the `Private :: Do Not Upload` classifier from before ESC-0002
was decided, and no `LICENSE` file existed yet at the repository root. Both
of those consequences of ESC-0002 belong to **TASK-0011**, which is running
concurrently in this same working tree; by the time this pass finished, a
`LICENSE` file (Apache License 2.0) and a `license = { file = "LICENSE" }`
declaration in `pyproject.toml` had already landed from that concurrent
work, observed in-progress rather than authored by this pass. Named here so
the sequencing is on record: this task's Apache-2.0 compatibility verdicts
above do not depend on TASK-0011 landing first, and hold either way.

- **Status quo (llama.cpp)**: runtime license — **MIT**, confirmed this run
  by fetching `raw.githubusercontent.com/ggml-org/llama.cpp/master/LICENSE`
  ("MIT License, Copyright (c) 2023-2026 The ggml authors"). Image/model-
  artifact path — we ship the pinned `ghcr.io/ggml-org/llama.cpp:server`
  image (MIT-licensed binary; the image's transitive OS-level packages are
  explicitly not enumerated by `sbom.json`, and their individual licenses
  **could not be determined** this run without pulling and inspecting the
  image layer by layer, which was out of scope). We ship no model weights;
  the operator sources their own, so no weight-license decision is made on
  this project's behalf. **Verdict: compatible** (MIT is permissive and
  compatible with Apache-2.0 distribution) **for the runtime; not applicable
  for model weights** (none shipped or pulled by this project); base-image OS
  package licenses **could not be determined** this run.
- **Docker Model Runner**: runtime license — **Apache-2.0**, confirmed this
  run via `api.github.com/repos/docker/model-runner` (`license.spdx_id:
  "Apache-2.0"`) and a fetched `LICENSE` file from `docker/model-cli`
  (Apache License, Version 2.0). DMR itself, however, is delivered as a
  feature of **Docker Desktop** or the **Docker Engine `docker-model-plugin`
  package**, both distributed under Docker Inc.'s own terms (Docker Desktop
  under the Docker Subscription Service Agreement, which is free for
  personal/small-business/education use but requires a paid subscription for
  larger commercial use) — this project does not vendor or redistribute
  Docker Desktop or Docker Engine, the operator installs them separately
  under Docker's own terms, so this does not create a distribution-license
  conflict for this project, but it is a cost/eligibility question for some
  operators that the runtime's own Apache-2.0 license does not capture.
  Model artifacts pulled via `docker model pull` from the Docker Hub `ai/`
  namespace repackage third-party model weights under **their own upstream
  licenses**, independent of DMR's own license — confirmed this run:
  `ai/gemma3` (fetched via `hub.docker.com/v2/repositories/ai/gemma3`)
  repackages Google's Gemma weights, which are governed by Google's own
  Gemma Terms of Use, **not** a standard permissive open-source license (it
  imposes usage restrictions beyond MIT/Apache-2.0). **Verdict: compatible**
  for the DMR runtime tooling itself; **needs-notice, evaluated per model
  actually chosen** for any pulled model artifact — the Gemma example
  confirms this is not a hypothetical concern, and a specific default preset
  recommendation must not be made without checking that model's individual
  license.
- **Ollama in container**: runtime license — **MIT**, confirmed this run by
  fetching `raw.githubusercontent.com/ollama/ollama/main/LICENSE` ("MIT
  License, Copyright (c) Ollama"); the `ollama/ollama` container image is
  built from the same MIT-licensed repository (its `Dockerfile` was fetched
  from the same repo this run for the criterion-8 posture finding above).
  Model artifacts pulled from Ollama's own model library (`ollama.com/library`)
  carry their own upstream licenses the same way DMR's `ai/` namespace does —
  Ollama's library mirrors many of the same upstream model families (Llama
  Community License, Gemma Terms of Use, Apache-2.0 for some models, and
  others), so the same "each model has its own license, independent of the
  runtime" caution applies. This project did not fetch a specific Ollama
  library model page successfully this run to confirm one concrete example
  the way it did for DMR's `ai/gemma3` (attempted; page structure did not
  yield a usable license string in the time available this pass) — recorded
  as **could not determine a specific example this run**, though the
  structural point (per-model licensing, independent of the MIT-licensed
  runtime) is not in doubt given Ollama's own library composition is public
  knowledge and mirrors DMR's. **Verdict: compatible** for the Ollama runtime
  itself; **needs-notice, evaluated per model actually chosen** for any
  pulled model artifact, same as DMR.

### Criterion 5 — GPU/CPU portability across hardware tiers

Windows is explicitly out of scope for this decision per the Director decision
recorded in the 2026-07-26 plan amendment: supported targets are Linux
(primary) and reset Macs (secondary but genuine). No untested performance
number is inferred here. Criterion 5 is therefore split into six reachability
verdicts — three options times two platforms — and each verdict is labelled as
**measured-this-run**, **documentation-only**, or **could-not-verify**.

- **Status quo (llama.cpp), macOS**: **CPU-only for this repository's pinned
  Linux-container path — measured-this-run**. The command
  `docker run --rm --entrypoint /app/llama-server ghcr.io/ggml-org/llama.cpp:server@sha256:4f02c560799a1569be08b0183d52b94b0d4a6e4b88f52f20562d2334c73837d4 --list-devices`
  printed only `Available devices:` with no devices below it on this
  Darwin/arm64 Docker Desktop host. That does not prove llama.cpp cannot use
  Metal when built and run natively on macOS; upstream docs say Metal is
  enabled by default on macOS and makes computation run on the GPU. It does
  prove the status quo **as packaged here** — the pinned Linux container — did
  not expose a GPU device on this Mac.
- **Status quo (llama.cpp), Linux**: **CPU yes; GPU possible but not verified
  for this pinned image — documentation-only / could-not-verify for the exact
  artifact**. Upstream llama.cpp documents CPU, CUDA, HIP/ROCm, Vulkan, SYCL,
  OpenCL, and other backends, including a Docker Vulkan example using
  `/dev/dri` devices and Linux Vulkan packages. This repository's pinned
  `ghcr.io/ggml-org/llama.cpp:server` image was not verified this run as a
  CUDA/HIP/Vulkan-enabled image on Linux hardware, because no Linux/Docker
  Engine host with GPU was available.
- **Docker Model Runner, macOS**: **Metal acceleration reachable —
  measured-this-run**. `docker model status` reported `llama.cpp Running` with
  `latest-metal`, and `docker model logs` for the current Desktop backend
  recorded `device_info:` with `MTL0 : Apple M1 Pro`, `BLAS : Accelerate`, and
  `system_info: ... MTL : EMBED_LIBRARY = 1`. `docker model status --json`
  also reported `kind: Docker Desktop`, and Docker's official docs state that
  on macOS the engines do not run inside a container but in a sandboxed
  environment. This is the only option measured here that reached the Mac's
  Metal path while still being controlled through Docker Desktop.
- **Docker Model Runner, Linux**: **CPU, NVIDIA/CUDA, AMD/ROCm, and Vulkan
  documented — documentation-only**. Docker's DMR requirements page states
  that Linux Docker Engine supports CPU, NVIDIA (CUDA), AMD (ROCm), and Vulkan
  backends. It also states vLLM and Diffusers are Linux/NVIDIA-specific for
  their respective engines. No Linux/Engine host was available this run, so no
  DMR Linux backend was measured.
- **Ollama in container, macOS**: **container GPU acceleration unavailable —
  documentation-only**. Ollama's FAQ states: *"GPU acceleration is not
  available for Docker Desktop in macOS due to the lack of GPU passthrough and
  emulation."* Ollama's native macOS app supports Apple GPUs via Metal, but
  that is not the option being scored here; the option is Ollama in a normal
  Docker container.
- **Ollama in container, Linux**: **NVIDIA, AMD/ROCm, and Vulkan documented —
  documentation-only**. Ollama's Docker docs show CPU-only `docker run`,
  NVIDIA via `--gpus=all` after installing NVIDIA Container Toolkit, AMD via
  the `ollama/ollama:rocm` image with `/dev/kfd` and `/dev/dri`, and Vulkan
  bundled/enabled when the container can access GPU devices. Ollama's GPU docs
  separately list Linux NVIDIA support, AMD ROCm support, and Vulkan support.
  No Linux GPU host was available this run, so these are not measurements.

#### DMR Desktop host-side Metal probe (amendment 2)

**Verdict: host-side process reaching Metal — CONFIRMED for Docker Desktop on
this Darwin/arm64 host; normal Linux container Metal path — KILLED for this
pinned llama.cpp container on this host.** Literal commands and observations:
`uname -m` returned `arm64`; `sw_vers -productVersion` returned `26.5.2`;
`docker version --format '{{.Client.Version}} {{.Server.Version}}'` returned
`29.6.1 29.6.1`; `docker model version` returned client/server `v1.2.4` with
server engine `Docker Desktop`; `docker model status` returned `llama.cpp
Running` with `llama.cpp latest-metal`; `docker model status --json` returned
`"kind":"Docker Desktop"` and endpoint `http://model-runner.docker.internal/v1/`;
`docker ps --format '{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}'` listed only
the unrelated/generated llama.cpp container (`ghcr.io/ggml-org/llama.cpp:server`,
`ai-lab-llama-server-chat`) and no DMR model-runner container; `pgrep -afil
'com\.docker\.backend|docker-model|model-runner|llama\.cpp|llama-server|sandbox-exec'`
showed Docker Desktop backend processes (`/Applications/Docker.app/.../com.docker.backend`)
but no normal Docker container process for the DMR runner; `docker model logs`
showed the backend loading a model, `device_info` with `MTL0 : Apple M1 Pro`,
and `llama_server: server is listening on unix://<HOME>/Library/Containers/com.docker.docker/Data/inference-0.sock`.
Together with Docker's official statement that macOS engines do not run inside
a container and are sandboxed by Desktop, this confirms DMR's macOS inference
path is Desktop-managed and reaches Metal rather than running as a normal
Linux VM container.

The companion container probe was:
`docker run --rm --entrypoint /app/llama-server ghcr.io/ggml-org/llama.cpp:server@sha256:4f02c560799a1569be08b0183d52b94b0d4a6e4b88f52f20562d2334c73837d4 --list-devices`,
which printed only `Available devices:` and no GPU devices. For this repo's
normal pinned Linux-container runtime on macOS Docker Desktop, GPU acceleration
was therefore not reachable this run. If the DMR finding is used as a product
argument, it must be scoped to Docker Desktop on macOS: this GPU path is not
available to ordinary containerized runtimes on macOS unless Docker Desktop
adds GPU passthrough or the runtime is moved out of the container into a
host-side/native process.

#### Deferred measurement (criterion 5)

Each entry below is executable as a later, representative-hardware experiment
for a criterion-5 claim that was not fully settled on this host.

1. **Status quo (llama.cpp) — Linux integrated-GPU/Vulkan reachability**
   - **Commands:**
     ```bash
     docker run --rm --device /dev/dri/renderD128:/dev/dri/renderD128 \
       --entrypoint /app/llama-server \
       ghcr.io/ggml-org/llama.cpp:server@sha256:4f02c560799a1569be08b0183d52b94b0d4a6e4b88f52f20562d2334c73837d4 \
       --list-devices
     docker run --rm --device /dev/dri/renderD128:/dev/dri/renderD128 \
       -v "$PWD/generated/phase-r-baseline/probe-model:/models:ro" \
       --entrypoint /app/llama-server \
       ghcr.io/ggml-org/llama.cpp:server@sha256:4f02c560799a1569be08b0183d52b94b0d4a6e4b88f52f20562d2334c73837d4 \
       --model /models/stories260k-probe.gguf --host 127.0.0.1 --port 8000 \
       --n-gpu-layers 99 --metrics
     ```
   - **Metric:** whether `--list-devices` names a Vulkan/DRI GPU and whether
     server startup logs show tensors/offload on that device without falling
     back to CPU-only.
   - **Threshold:** pass if at least one GPU device is listed and the server
     reaches `/health` with GPU/offload log lines; fail if no device is listed
     or logs explicitly select CPU-only.
   - **Hardware:** Linux x86_64 or arm64, Docker Engine 29.x or current stable,
     integrated Intel/AMD GPU with Vulkan-capable Mesa stack, `/dev/dri`
     present, 16 GB RAM preferred (12 GB minimum), no discrete NVIDIA required.
   - **Criterion-5 claim settled:** whether the status quo pinned image can
     use Linux integrated-GPU/Vulkan acceleration as shipped, or whether a
     separate llama.cpp Vulkan image/build is required.

2. **Docker Model Runner — Linux Docker Engine backend reachability**
   - **Commands:**
     ```bash
     docker model version
     docker model status
     docker model pull ai/smollm2
     docker model run ai/smollm2 "Say hello in five words."
     docker model logs
     docker model ps
     ```
   - **Metric:** backend selected in `docker model status`/logs, device lines
     in `docker model logs`, and successful completion of a short generation.
   - **Threshold:** pass if DMR reports a Linux backend matching available
     hardware (CPU, CUDA, ROCm, or Vulkan) and completes one generation without
     backend fallback errors; fail if plugin cannot install/start or if logs
     show no supported backend for available GPU when one should be present.
   - **Hardware:** Fresh Linux host with Docker Engine 29.x or current stable,
     `docker-model-plugin` installed, 16 GB RAM preferred (12 GB minimum), and
     one of: NVIDIA GPU with Docker-supported driver/toolkit, AMD/Intel GPU
     with Vulkan/ROCm stack, or CPU-only host for CPU fallback.
   - **Criterion-5 claim settled:** whether DMR's documented Linux Engine CPU,
     CUDA, ROCm, and Vulkan support is operational on the target host class.

3. **Ollama in container — Linux container GPU reachability**
   - **Commands:**
     ```bash
     docker run -d --name ollama-test --gpus=all \
       -v ollama-test:/root/.ollama -p 127.0.0.1:11434:11434 ollama/ollama
     docker exec ollama-test ollama pull llama3.2
     docker exec ollama-test ollama run llama3.2 "Say hello in five words."
     docker exec ollama-test ollama ps
     docker rm -f ollama-test
     # For AMD/Vulkan hosts, replace the first command with:
     docker run -d --name ollama-test --device /dev/kfd --device /dev/dri \
       -v ollama-test:/root/.ollama -p 127.0.0.1:11434:11434 ollama/ollama:rocm
     ```
   - **Metric:** `ollama ps` `PROCESSOR` column (`100% GPU`, mixed CPU/GPU, or
     `100% CPU`) after a model is loaded, plus container startup/generation
     success.
   - **Threshold:** pass for GPU reachability if `ollama ps` reports any GPU
     fraction and the generation succeeds; CPU-only pass if `100% CPU` is
     expected on a CPU-only host; fail if GPU hardware is present and properly
     exposed but Ollama reports CPU-only or cannot load the model.
   - **Hardware:** Linux x86_64 or arm64, Docker Engine 29.x or current stable,
     16 GB RAM preferred (12 GB minimum), NVIDIA GPU with NVIDIA Container
     Toolkit for the `--gpus=all` path or AMD/Intel GPU with `/dev/dri`/ROCm or
     Vulkan support for the device path.
   - **Criterion-5 claim settled:** whether Ollama-in-container can use Linux
     Docker GPU acceleration on representative target hardware, and whether
     `ollama ps` provides a usable operator-visible CPU/GPU verdict.

### Criterion 6 — resource limits (`mem_limit`, `cpus`, `pids_limit`)

- **Status quo (llama.cpp)**: **yes**. The current root compose has explicit
  Docker resource limits: `mem_limit: ${MEM_LIMIT:-8g}`, `cpus:
  ${CPU_LIMIT:-6.0}`, and `pids_limit: 256` at `docker-compose.yml:33-35`.
  The generated chat template carries the same controls as templated values
  at `templates/chat/docker-compose.yml.j2:33-35`. Both files also include
  non-root execution and containment hardening adjacent to the limits:
  `user`, `security_opt: no-new-privileges:true`, `cap_drop: ALL`,
  `read_only: true`, and `/tmp` tmpfs at `docker-compose.yml:36-49` and
  `templates/chat/docker-compose.yml.j2:36-49`. These are not performance
  limits, but they reduce host-instability and blast-radius risk.
- **Docker Model Runner**: **partial**. On Linux/Engine, Docker's docs say DMR
  and its inference engines run inside a container, which suggests container
  resource limits may be possible in that deployment model, but this project
  has no DMR compose/service template and this run did not verify a
  model-runner-specific way to set `mem_limit`, `cpus`, or `pids_limit`.
  On macOS Docker Desktop — the only platform measured this run — engines do
  not run inside a normal container, so the project's Compose resource limits
  cannot be applied directly to the DMR inference engine. DMR therefore does
  not currently meet the status quo's resource-limit enforceability bar in
  this repository.
- **Ollama in container**: **yes in principle for a project-owned container;
  partial in this repository today**. Because the scored option is Ollama in a
  normal Docker container, Docker/Compose can apply `mem_limit`, `cpus`, and
  `pids_limit` just as it does for llama.cpp. However, this repository has no
  Ollama compose template today, so no current artifact enforces those values.
  If Ollama were selected, matching the status quo's resource bar would require
  adding an Ollama compose/template with explicit `mem_limit`, `cpus`,
  `pids_limit`, non-root/read-only/cap-drop choices where compatible, and
  explicit GPU device grants where acceleration is intended.

### Criterion 7 — offline / air-gapped behaviour

- **Status quo**: **works** fully offline once the pinned image and the
  operator-supplied `.gguf` are already local. There is no runtime-time
  network dependency at all — `docker compose up` against an already-pulled,
  digest-pinned image and a hand-placed model file needs no registry or
  daemon reachability beyond the local Docker daemon itself. The only
  network dependency in this option's entire lifecycle is the one-time image
  pull (or `resolve_image_digest.sh`'s deliberate re-pin) and however the
  operator originally obtained their `.gguf` — both are outside this
  project's runtime path once complete.
- **Docker Model Runner**: **works once cached, degrades on first use**.
  Per `docs.docker.com/manuals/ai/model-runner/`, fetched this run: "Models
  are pulled from Docker Hub, an OCI-compliant registry, or Hugging Face the
  first time you use them and are stored locally... After that, they're
  cached locally for faster access." So a model already pulled runs fully
  offline; a model not yet pulled requires registry/Hugging Face
  reachability at that moment. On Docker Engine specifically, the
  `docker-model-plugin` package install itself (criterion 1) is an
  additional one-time online dependency (`apt-get`/`dnf` package fetch) not
  shared by the status quo or Ollama, both of which need no extra host
  package beyond the container image itself.
- **Ollama in container**: **works once cached, degrades on first use** —
  the same pattern as DMR, and with a documented advantage on the "degrades"
  side: interrupted pulls resume rather than restart (`docs/api.md`,
  quoted under criterion 2). No extra host package is required beyond the
  `ollama/ollama` image itself (criterion 1), so Ollama's offline story has
  one fewer online dependency than DMR's on the Linux/Engine target
  specifically (no separate plugin package to fetch first).

## DMR blast radius

**Confirmation method: hands-on, this run**, on Docker Desktop for macOS
(arm64), Docker client `29.6.1`, `docker model` plugin `v1.2.4`. This is
**not** the Linux/Docker Engine target platform; findings are labeled
accordingly throughout.

Commands run, in order, this session:

1. `open -a Docker` then polled `docker info` until it succeeded (daemon was
   down at task start; came up within ~5s of launch).
2. `docker model status` → `Docker Model Runner is running` (`llama.cpp`
   backend, `Running`).
3. Generated and started a workspace (`generated/phase-r-baseline`,
   `./scripts/start.sh`), producing a running llama-server container attached
   to Docker network `phase-r-baseline_default`.
4. `docker run --rm --network phase-r-baseline_default curlimages/curl:latest
   -sS -m 5 http://model-runner.docker.internal/engines/llama.cpp/v1/models`
   → HTTP 200, JSON model list including a pre-existing pulled model
   (`docker.io/ai/gemma4:latest`, 7.52B params — cached on this machine from
   unrelated prior use, not pulled by this task), no `Authorization` header
   sent.
5. `docker run --rm curlimages/curl:latest -sS -m 5
   http://model-runner.docker.internal/engines/llama.cpp/v1/models` (default
   bridge network, **not** attached to the workspace's network at all) →
   identical HTTP 200 response.

Step 5 is the decisive result: on Docker Desktop, DMR's API is reachable via
the Desktop-internal DNS proxy **independent of Docker network membership**.
A container does not need to share a network with the model socket to reach
it.

Cross-checked against official documentation
(`https://docs.docker.com/ai/model-runner/`, fetched this run): the API is
unauthenticated by design (quoted above), and the isolation model differs by
platform — Linux/Docker Engine runs DMR "inside a container, which provides
the isolation boundary," while macOS/Windows Desktop runs it in a sandboxed,
non-containerized process. This is consistent with what was observed: on
this Desktop host, standard Docker-network-based containment strategies do
not apply because there is no real container network boundary being crossed
in the first place.

**Containment verdict**: of the four named options (dedicated network with
nothing else attached / no shared network with the model socket /
Unix-socket-only instead of TCP / outright rejection of DMR), the first two
were **directly falsified by hands-on evidence this run** — network
segmentation does not confine DMR on the only platform actually tested.
Unix-socket-only exposure was not found documented as a currently available
DMR configuration option in the fetched documentation (searched for `TCP`,
`socket`, `Unix socket`, `host-side` — no configuration toggle for
socket-only exposure was found; labeled "undocumented / could not verify" as
a mitigation, not ruled out, just not confirmed to exist). The Linux/Docker
Engine "runs inside a container" claim is documentation-only and was not
independently confirmed this run, so it cannot be relied on as an
already-verified mitigation. Given that the only platform this run could
actually test showed no effective containment, and the platform where
containment might work was not verified: **verdict — outright rejection of
DMR as an option**, on the evidence gathered this run. This verdict is
explicitly reviewable, not final: if a later pass obtains hands-on evidence
on a real Linux/Docker Engine host showing that Docker-network segmentation
(dedicated network, nothing else attached) genuinely confines DMR's
container-based deployment there, that would be new evidence sufficient to
revisit this verdict — but it has not been gathered yet, and the
recommendation in this document must not assume it will hold.

## Behind the Phase N gateway

**Status quo (llama.cpp):** The current localhost-only publish keeps the API off the LAN, but it is not yet a Phase N LAN gateway topology because the model container itself listens on `0.0.0.0` inside Docker and no token is configured; a sibling container already reached it unauthenticated this run. The model socket can be kept off every network the TLS-terminating gateway does not control only by generating a gateway container as the sole LAN-facing service, moving llama.cpp onto a private Docker network shared only with that gateway, and enabling llama.cpp's own `--api-key` / `LLAMA_API_KEY` so a direct network bypass still fails. Verdict: isolatable only if generated Phase N gateway, a private gateway-only model network, and llama.cpp `--api-key`/`LLAMA_API_KEY` wiring are added.

**Docker Model Runner:** On Docker Desktop for macOS, the API was reachable at `model-runner.docker.internal` from containers regardless of application-network membership, so the model-serving socket cannot be kept solely behind a TLS/bearer-token gateway using Docker network isolation. Linux/Engine may be different because Docker documents DMR engines as containerized there, but that remains documentation-only and no Desktop control was found to force socket-only or gateway-only exposure. Verdict: not isolatable without changes.

**Ollama in container:** A project-owned Ollama container can in principle sit behind a Phase N gateway because it is an ordinary Docker service, but the official image binds `0.0.0.0:11434` and no Ollama-native bearer token was found, so any host port publish or shared Docker network bypasses the gateway completely. The isolation bar is met only if the generated topology publishes the gateway, not Ollama; places Ollama on a private network shared only with the gateway; enforces the bearer token at the gateway; and adds host firewall/allowlist rules so the raw Ollama API is not reachable from LAN clients or unrelated containers. Verdict: isolatable only if an Ollama compose template removes host publish from the model container, places it on a private gateway-only network, and adds Phase N bearer-token reverse proxy and host firewall rules.

## Docker-mandatory vs no-Docker path

**Docker becomes mandatory** for the supported Phase R path. First, criterion
1 assumes a freshly formatted host with Docker and git, and both the current
llama.cpp Compose path and the two alternatives are evaluated as container
deployments; keeping a no-Docker Python serving path would add a separate
runtime and packaging contract rather than reduce the minimum host footprint.
Second, criteria 2 and 4 favor a container-oriented distribution boundary:
DMR and Ollama provide documented pull flows (criterion 2), while the current
status quo already has a digest-pinned image, SBOM, and digest-resolution
workflow (criterion 4). This does not mean Python disappears: the generator
still uses Python as an installer/configuration tool, but Python is not a
second model-serving runtime. A future implementation may revisit this if a
no-Docker path can meet the same pull, pinning, isolation, and resource gates.

## Recommendation

**Recommended: Status quo (llama.cpp), as the engineering recommendation
pending Director decision ceremony.** It is the only option with demonstrated
image digest pinning and repository SBOM integration (criterion 4), explicit
Compose resource limits and hardening (criterion 6), a fully offline runtime
once the image and model are local (criterion 7), and a documented native
`--api-key` mechanism that can close direct bypasses when the Phase N topology
is implemented (criteria 3 and 8); it also has no additional Docker Engine
plugin requirement (criterion 1), although its absent model pull path remains
the major criterion-2 defect and should be remedied before broad distribution.
The recommendation therefore optimizes for the security and audit bar already
present while explicitly accepting the criterion-2 gap as follow-up work, not
pretending that the status quo is complete.

Docker Model Runner is not chosen because criteria 3 and 8 remain unacceptable
after this run's hands-on Desktop test showed unauthenticated reachability
outside Docker-network segmentation, and its Linux containment was not measured.

Ollama in container is not chosen because criteria 3, 4, 6, and 8 remain
weaker than the status quo: its image binds broadly without documented native
API authentication, its model pinning is unverified, and this repository has
no hardened Ollama Compose template.

## Security review (security-engineer)

Handoff to `security-engineer`, routed through `engineering-manager`; this
worker does not contact the reviewer or transition TASK-0009. The DMR finding
is self-contained: confirmation was hands-on on Docker Desktop for macOS/arm64
using a sibling container on the Compose network and a second container on the
default bridge network, both calling
`http://model-runner.docker.internal/engines/llama.cpp/v1/models` without an
`Authorization` header and receiving HTTP 200. Docker's official
documentation also states that the Model Runner API is unauthenticated. The
containment verdict for the named options is **outright rejection of DMR as an
option** for this decision: Docker-network segmentation was falsified on the
tested Desktop platform, and Unix-socket-only exposure was not documented;
Linux/Engine container isolation remains documentation-only and unverified.

Gateway isolation posture to review:

- **Status quo (llama.cpp):** **isolatable only if** the generated Phase N
  gateway is the sole LAN-facing service, llama.cpp is on a private
  gateway-only network, and `--api-key`/`LLAMA_API_KEY` is enabled.
- **Docker Model Runner:** **not isolatable without changes** on the tested
  Desktop platform because direct API reachability bypasses Docker-network
  isolation; Linux/Engine behavior requires a fresh hands-on verification.
- **Ollama in container:** **isolatable only if** the model container has no
  host publish, shares only a private network with the gateway, and the
  gateway plus host firewall enforce bearer-token and source-allowlist rules.

The recommendation above is therefore an engineering recommendation only;
the security reviewer must decide whether the proposed llama.cpp changes meet
the Phase N bar, and whether the DMR macOS Metal benefit changes the risk
decision.

### Review outcome — 2026-07-25

1. **DMR evidence and scope:** sufficient and honestly scoped for this
   decision document. The unauthenticated API claim is supported both by the
   official documentation and by two hands-on macOS/arm64 Docker Desktop
   probes. The document correctly does not promote that observation to a
   Linux/Docker Engine result; Linux containment remains documentation-only
   and requires a fresh-host verification before it could change this
   decision.
2. **Recommendation:** defensible against the Phase N gateway requirement,
   but only as an engineering recommendation pending implementation of the
   stated gateway topology. llama.cpp is the only candidate here with a
   documented native API-key control plus the repository's existing digest,
   SBOM, resource-limit, and hardening controls. The current status quo is
   not itself Phase N-compliant; that distinction is stated correctly and
   must remain a release gate.
3. **Isolation conditions:** sufficient as stated when implemented together:
   the gateway is the sole published/LAN-facing service; llama.cpp is on a
   private network shared only with the gateway; `--api-key`/`LLAMA_API_KEY`
   is enabled; and host firewall/allowlist rules prevent raw service access.
   No single condition should be treated as sufficient by itself, and the
   implementation must test both an allowed gateway request and denied direct
   LAN/container paths.
4. **Required qualification/follow-up:** no correction is required to the
   Phase R claims. Before Phase N acceptance, record a fresh execution
   receipt proving the direct-bypass tests fail, token enforcement works, the
   model service has no host publish, and the gateway is the only intended
   LAN ingress. A Linux/Docker Engine DMR probe would be required only if DMR
   is reconsidered; it does not weaken this review of the current
   recommendation.
5. **DMR Metal exception:** the confirmed host-side Metal path is a security
   exception in the sense that it removes ordinary container-network
   isolation on Docker Desktop. It therefore reinforces, rather than changes,
   the current DMR rejection for this Phase R decision. Performance benefit
   does not compensate for the unauthenticated bypass surface.

Verdict: APPROVED

This is security approval of the documented Phase R recommendation and its
explicit conditions, not product approval or authorization to expose the
current status quo to the LAN.

## Delivery report

This report records the requested Gate commands after the research todos and
security review were completed. The task remains in `in_progress` until the
engineering manager moves it to review; all plan and documentation gates are
green.

| Command | Exit code | Result |
|---|---:|---|
| `docker --version` | 0 | Docker CLI available. |
| `python3 --version` | 0 | Python available. |
| `python3 -m pip --version` | 0 | pip available. |
| `test -f .pm-harness/HARNESS-SPEC.md` | 0 | Harness specification present. |
| `python3 .pm-harness/bin/harness.py validate` | 0 | Repository validation passed. |
| `python3 .pm-harness/bin/harness.py wiki check` | 0 | Wiki validation passed after this update. |
| `python3 .pm-harness/bin/harness.py changelog check --task TASK-0009` | 0 | TASK-0009 changelog entry present. |
| `python3 .pm-harness/bin/harness.py plan check TASK-0009` | 0 | All 25 approved plan todos are checked and evidence-backed. |

The gate results are the durable delivery record for the research document.
