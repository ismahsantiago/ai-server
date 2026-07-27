## Active

- TASK-0009 — Phase R: runtime decision (status-quo llama.cpp image vs Docker Model Runner vs Ollama-in-container) for a reused-laptop LAN server. Status: `closed`. Category `research`, model `session-current-model` (effort medium, source `system-default`) after session catalog sync to `sakana/fugu`. Governed by KICK-0002. All 25 plan todos, gates, checksum, and the blocking security review completed; `security-engineer` recorded `Verdict: APPROVED` with Phase N conditions.
- TASK-0011 — Apply Apache-2.0 licensing decision (ESC-0002). Status: `closed`. Gate 1 passed with `HARNESS_PLAN_TASK=TASK-0011 bash scripts/ci.sh`; manifest transitioned `in_progress → in_review → approved → closed`, and LICENSE checksum recorded.
- TASK-0008 — Phase H: host inspection (`doctor`), hardware tiering for heterogeneous reused machines. Status: `started`. Category `complex`, model `claude-opus-5` (effort high, source `category-default`). Governed by KICK-0002. Full plan drafting delegated to `ml-systems-engineer`; the plan is reviewed by engineering-manager with the `plan-review` skill and approved by `pm-orchestrator`.
- TASK-0007 — Fresh audit + bounded remediation. Status remains `in_progress`
  while independent whole-change security review and final gates are pending.
  The append-only remediation ledger now reconciles all 25 findings: local
  remedies have focused evidence and external/runtime/platform/legal items
  have explicit owners and fail-closed reasons. The independent whole-change
  security rereview is `APPROVED` after `SR7-FINAL-001`; all 13 plan todos are
  complete and the task is ready for manager-owned state transitions.

## Next

- TASK-0009 is closed; its Phase R recommendation and security conditions are the input for any separately approved Phase N implementation task.
- TASK-0009: closed after security review and final gate run. Carry the Phase N gateway, private-network, API-key, firewall, and direct-bypass test conditions into the next implementation phase.
- TASK-0008: on `plan approve`, transition `started → in_progress` and delegate implementation to `ml-systems-engineer` with the FACTS block + `task-handoff`.
- TASK-0008: route the security-area review (todo 25) to `security-engineer` **as soon as todos 1-12 are green**, not at the end of the list. A redaction objection on `gpu.name`/`cpu.model` would invalidate the byte-exact schema fixture (todo 7), so late review means a re-run.
- Escalate the hardware-tier definitions and the tier → preset/profile/context mapping to `pm-orchestrator` for `product-manager` ownership; engineering ships the tier model as `provisional` until product ratifies it.
- TASK-0007: route the now-green plan through engineering-manager-owned state
  transitions. Do not infer live Linux/model, LAN, Codex-adapter,
  distribution, or legal readiness from static evidence.

## Blocked

- TASK-0009 closure evidence: `.pm-harness/plans/TASK-0009.plan.md` is approved, `plan check TASK-0009` exits 0, the recorded security verdict is `APPROVED`, and the manifest follows `in_progress → in_review → approved → closed`. Phase N LAN implementation remains explicitly out of scope for this task.
- TASK-0008 plan gate: `.pm-harness/plans/TASK-0008.plan.md` is drafted (**28 todos**, 8 gates, 12 risks, plus normative `## Platform capability matrix` and `## Software readiness gap registry` sections), reviewed by engineering-manager with `plan-review` across **three** rounds → verdict **approve**. **Waiting on `pm-orchestrator` to run `plan approve TASK-0008 --by pm-orchestrator`** before `started → in_progress`. `plan check TASK-0008` exits 1 with `plan-not-approved (status=draft)` and `28 unchecked of 28` — the correct pre-approval state. `## Amendments` is deliberately empty: the plan was never approved, so Director-constraint round 3 landed as a draft revision, not an amendment (§12.4).
- **ESCALATED to pm-orchestrator — macOS host path has no usable interpreter.** Measured: on a *freshly reset* Mac `/usr/bin/python3` is a CLT-installer stub, and even once CLT is installed it is **Python 3.9.6**, below this repo's own `requires-python = ">=3.10"` (`pyproject.toml:9`). Combined with the verified fact that a container on a Mac cannot observe the physical machine (three-level memory), macOS is blocked on both paths: the container view is structurally blind and the host view has no interpreter. Owner is Phase I packaging (`ml-platform-engineer`), not TASK-0008. Options: a POSIX-`sh` host shim (viable — `sysctl`/`vm_stat`/`sw_vers` are all shell), a packaged launcher, or accepting a documented one-time CLT prerequisite.
- `scripts/ci.sh` is **red on any developer checkout today**, independently of this task: line 117 pins `plan check TASK-0007`, which exits 1 (`13 unchecked of 13`), and `set -euo pipefail` fails the script. TASK-0008 todo 17 fixes it (derive ids from manifests in `in_review`/`closed` + `HARNESS_PLAN_TASK` override) and todo 24 files it as APR-001 `harden gate`.
- Tier semantics (how many tiers, their names, and the tier → recommended preset/profile mapping) are product-owned per KICK-0002. Engineering will not invent them: `doctor` ships a mechanically derived, explicitly provisional mapping and an open question routed through `pm-orchestrator`.

## Standing constraints (all TASK-0008 work)

- Phase R (runtime adoption) is NOT in scope: `doctor` reports which backends are *available*, never which one we adopt.
- No new runtime dependency. `requirements.txt` stays `Jinja2` + `MarkupSafe`; probes are stdlib-only.
- Graceful degradation is the primary engineering risk: no probe failure may fail the run.
- Golden fixture `tests/golden/chat-ornith-medium-localhost/` is not regenerated by this task.

## Known constraints on TASK-0009 evidence (recorded by engineering-manager, 2026-07-25, before delegation)

- Development host is **macOS / arm64 (Apple Silicon)** with Docker Desktop, and the Docker daemon was **not running** at task start. The target is a **Linux Docker Engine x86 consumer laptop with an integrated GPU**. Any hands-on measurement taken here is indicative only and must be labelled as such in the deliverable.
- `models/` contains no `.gguf` (only `README.md`), and every report in `logs/benchmarks/` is a **placeholder** (`HTTP status: not-tested`, `Model path: /models/placeholder.gguf`). There is therefore **no real llama.cpp performance baseline to compare against**: the "benchmark against the existing baseline" deliverable must either establish a first real baseline or declare the gap explicitly. Fabricated numbers are a task failure.
- The `docker model` CLI plugin v1.2.4 is present on this host; DMR behaviour observed through Docker Desktop is **not** evidence about DMR on plain Docker Engine.
