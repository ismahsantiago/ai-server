# TASK-0007 — Product and operator-experience dimension

## Scope and decision

This is an independent, read-only product and operator-experience pass for
todo 5. It used the approved plan, the fresh inventory, current audit
standards, current source, templates, documentation, tests, and existing
generated workspaces. No prior audit report was opened. No source, plan, state,
or existing generated workspace was modified.

The current product is terminal-only: the executable surfaces are the Python
CLI and generated shell helpers (`ai_server_generator/cli.py:15-77`,
`templates/chat/scripts/start.sh.j2:1-5`). There is no web, desktop, or other
graphical surface in the current product map. A separate UI/design dimension
does not apply to this run. The applicable design surface is CLI, terminal
workflow, documentation, and generated runbook usability.

## Traced workflow

The intended path is discoverable as `matrix → generate → validate →
scripts/start.sh`, with `smoke.sh` and `stop.sh` after startup. The CLI
implements `matrix`, `generate`, and `validate` as subcommands
(`ai_server_generator/cli.py:22-52`); startup is a generated helper rather
than a CLI subcommand (`templates/chat/scripts/start.sh.j2:1-5`). The guided
wizard combines selection, generation, structural validation, and optional
start/smoke (`ai_server_generator/cli.py:372-551`).

The important current state transitions are:

1. `matrix` prints a static `WARN`/`NO-GO` decision and explicitly states that
   no model, host, runtime, or quality check was performed
   (`ai_server_generator/cli.py:281-291`).
2. `generate --dry-run` reports the 13 planned files and does not create the
   destination.
3. `validate` has separate `structure`, `host`, and `runtime` tiers and emits
   the omitted checks for reduced tiers (`ai_server_generator/cli.py:354-370`).
4. Generated startup validates the host, starts Compose, polls `/health`, and
   reports logs on timeout (`templates/chat/scripts/start_serving.sh.j2:34-55`).

## Findings

### UX7-001 — High — Materialized workspaces can describe a different runtime than the canonical generator

**Evidence.** The current generator pins the serving image to
`ghcr.io/ggml-org/llama.cpp:server@sha256:...`
(`ai_server_generator/render.py:44-55`) and the canonical Compose template uses
that context plus `restart: "no"` and a single read-only model bind
(`templates/chat/docker-compose.yml.j2:3-7`, `templates/chat/docker-compose.yml.j2:28-32`).
The existing generated workspace `generated/ornith-medium-localhost/` instead
declares `ghcr.io/ggerganov/llama.cpp:server` and `restart: unless-stopped`
(`generated/ornith-medium-localhost/docker-compose.yml:2-8`). Its generated
README repeats the old image (`generated/ornith-medium-localhost/README.md:5-11`).

**Impact.** An operator following a visible generated workspace can run a
different image, restart policy, and security/runtime contract from the one
currently validated by the generator. This can produce avoidable startup
failures, stale security assumptions, and misleading incident diagnosis. The
problem is particularly difficult to recover from because the workspace looks
like a normal generated canonical output.

**Recommendation.** Establish and mechanically enforce one ownership/version
policy for existing generated workspaces: either regenerate them into a
controlled migration path or mark them explicitly as legacy/non-canonical.
Add a drift check comparing materialized manifests/templates with the current
generator contract, and make the generated README report the exact image
digest and generation contract.

### UX7-002 — High — Human LAN instructions contradict the fail-closed product contract

**Evidence.** The current CLI refuses LAN generation and returns `NO-GO` even
when bearer-token and CIDR flags are supplied
(`ai_server_generator/cli.py:276-279`; observed command exit `1`). The current
generated runbook correctly says LAN is disabled and must not be treated as a
manual exception (`templates/chat/runbook.md.j2:16-21`). However, the human
guide labels LAN usage as opt-in, provides executable `matrix`, `generate`, and
`validate` commands, and then says the generator records the allowlist
(`docs/human-guide.md:98-110`). The commands are not executable under the
current contract, and the statement that the allowlist is recorded is false
for the current implementation.

**Impact.** Operators can waste time following a dead path or infer that a
manual firewall/auth step makes LAN exposure acceptable, despite the product
intentionally refusing to materialize it. The contradiction weakens the
fail-closed safety message and makes escalation to the future gateway phase
less clear.

**Recommendation.** Replace the section with a planned/blocked capability
notice that shows the observed refusal and links to the future gateway
acceptance criteria. Keep executable examples limited to localhost until the
gateway, authentication, allowlist enforcement, and bypass tests exist.

### UX7-003 — Medium — Model-location instructions are inconsistent across onboarding surfaces

**Evidence.** The canonical README says the generated Compose binds the model
from its absolute host path and therefore requires no copy into the workspace
(`README.md:57-66`). The generator resolves the host model path from the
project root and writes it into the generated context
(`ai_server_generator/cli.py:156-170`; `ai_server_generator/render.py:159-163`).
The wizard also checks for `models/<preset>.gguf` in the repository
(`ai_server_generator/cli.py:387-394`). In contrast, the human guide instructs
the operator to create a generated `models/` directory and copy the model into
it (`docs/human-guide.md:80-88`). The current Compose template binds the exact
resolved host file, not a generated workspace directory
(`templates/chat/docker-compose.yml.j2:28-32`).

**Impact.** An operator can copy a large model unnecessarily, believe the
copy is required when it is not, or copy it to a location that the generated
manifest does not use. This creates wasted disk usage and a confusing
`validate --tier host` failure when the source path differs.

**Recommendation.** Choose one canonical model-location contract and expose it
identically in CLI output, README, human guide, runbook, manifest, and Compose.
The contract should show the resolved host path, container path, whether a copy
is required, and the exact command to validate that path before startup.

### UX7-004 — Medium — The primary workflow documentation names a non-existent `start` CLI command

**Evidence.** The README describes the canonical sequence as `matrix`,
`generate`, `validate`, `start`, `smoke`, and `stop`
(`README.md:82-90`), but the CLI parser exposes only `list`, `generate`,
`matrix`, `validate`, and `wizard` (`ai_server_generator/cli.py:20-57`). The
actual start/stop/smoke actions are generated shell helpers
(`templates/chat/scripts/start.sh.j2:1-5`,
`templates/chat/scripts/stop.sh.j2:1-14`,
`templates/chat/scripts/smoke.sh.j2:1-5`).

**Impact.** A new operator using the documented nouns may try
`python3 -m ai_server_generator start` and receive an argparse error, then
have to infer that `start` means a generated script. This is a recoverable
failure, but it breaks the advertised clone-to-start path at the point where
the operator expects a stable command contract.

**Recommendation.** Use the exact command names in the workflow documentation,
for example `./scripts/start.sh`, `./scripts/smoke.sh`, and
`./scripts/stop.sh`, or add an actual CLI command. Add a documented command
reference generated from `--help` so future workflow names cannot drift.

## Non-findings and positive controls

- No separate graphical UI or visual interaction surface exists in the current
  repository; no UI design finding is invented for this terminal product.
- Missing subcommand handling is explicit: bare CLI invocation returned exit
  `2` with help text (`ai_server_generator/cli.py:300-308`; observed exit `2`).
- The matrix output is honest about static evidence and does not claim runtime
  readiness (`ai_server_generator/cli.py:288-291`; observed localhost command
  exit `0` with `WARN`).
- LAN generation is fail-closed: the supplied authenticated-CIDR scenario
  returned `NO-GO`, exit `1`, and no output was generated.
- `generate --dry-run` returned exit `0`, listed 13 files, and did not create
  `generated/task0007-ux-dry-run`.
- Non-interactive wizard invocation names the missing `--preset` flag and did
  not write output (`ai_server_generator/cli.py:102-123`; observed exit `1`).
- `validate` reports a missing generated directory directly and returned exit
  `1`; it does not present a false success state.
- Generated helper scripts resolve paths from `BASH_SOURCE[0]`, so their basic
  caller-location contract is clear (`templates/chat/scripts/*.j2`, for
  example `start_serving.sh.j2:6-8`).

## Commands and exit codes

| Command/check | Exit | Evidence |
|---|---:|---|
| `python3 -m ai_server_generator` | 2 | Help plus usage error |
| `python3 -m ai_server_generator --help` | 0 | CLI surface listed |
| Localhost `matrix` scenario | 0 | `WARN`, static-only evidence |
| LAN `matrix` with auth/CIDR | 1 | `NO-GO`, gateway/allowlist refusal |
| Localhost `generate --dry-run` | 0 | 13 files listed, no destination written |
| Non-interactive `wizard` without preset | 1 | Explicit `--preset` recovery hint |
| `validate generated/does-not-exist` | 1 | Explicit missing-directory error |
| `python3 .pm-harness/bin/harness.py validate` | 0 | 13 manifests, no errors/warnings |
| `git diff --check` | 0 | No whitespace errors |
| `python3 .pm-harness/bin/harness.py plan check TASK-0007` | 1 | Expected: 9 unchecked todos remain; this audit did not modify the plan |

## Audit result

`INCOMPLETE — findings recorded`.

Findings: 4 total — 2 high, 2 medium, 0 low. The product is operationally
understandable as a terminal-first localhost generator, but documentation and
materialized-workspace drift currently prevent a single reliable operator
journey from clone through runtime start. No remediation was performed in this
dimension.
