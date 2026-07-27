<!-- COMPILED SPEC — do not edit by hand.
     engine 2.1.0 + pm-pack 2.6.0
     Sections 0-12/E/V are CORE-SPEC (engine); the domain sections
     and guardrails below come from the pm SpecPack.
     Regenerate with harness-engine/engine/installer/generate.py -->

# CORE-SPEC v0 (engine 2.0.0-draft) — Normative contracts of the Harness Engine

This document is the generic half of the **source of truth** for every
workflow of a harness installed from a SpecPack. At install time the
generator compiles `CORE-SPEC + the pack's DOMAIN-SPEC + the pack's
guardrails` into ONE normative document per project; agents keep reading a
single file, exactly as today.

Every manager/agent SKILL.md is subordinate to these contracts. If a skill
contradicts the compiled spec, the spec wins and the skill must be proposed
as a patch (§6).


## 0. Conventions and placeholders

The engine text is written in English. Every user-facing string is rendered
through the pack's locale at compile/run time. Placeholders resolved from
`specpack.json` (§E and `specpack-schema.json`):

| Placeholder | lex pack | pm pack |
|---|---|---|
| `.pm-harness` | `.lex-harness` | `.pm-harness` |
| `.pm-harness/bin/harness.py` | `.pm-harness/bin/lex.py` | `.pm-harness/bin/harness.py` |
| `pm-orchestrator` | `coordinador-general` | `pm-orchestrator` |
| `Director` | Director | Director |
| `harness.json` | `case.json` | `harness.json` |
| `PM-HARNESS` | `LEX-HARNESS` | `PM-HARNESS` |
| `executive-summary.md` | `resumen-ejecutivo.md` | `executive-summary.md` |

The installed CLI binary is a ~10-line shim:
`import harness_core, <pack>_ext; harness_core.main(pack=<pack>_ext)`.

**Language contract**: engine code, CORE-SPEC, and machine-oriented artifacts
are English; the language of generated human-facing artifacts (plans,
ceremonies, memory notes, wiki pages, escalations) is the pack's `language`.
Agents reply to the Director in the Director's language.

**Enforcement**: the CLI at `.pm-harness/bin/harness.py` implements these contracts in code.
Agents MUST prefer the CLI over hand-editing JSON; hand edits are only
acceptable where no CLI command exists, and are still validated.

---

## 1. State machine (units of work)

Applies to every unit of work: task, agent session, ceremony, artifact, and
every pack-declared kind.

### 1.1 States and allowed transitions

```
untouched → touched → dirty → started → in_progress ⇄ blocked
                                   ↓
                             in_review → changes_requested ⇄ in_progress
                                   ↓
                               approved → closed
```

| From | To (allowed) |
|---|---|
| `untouched` | `touched`, `cancelled` |
| `touched` | `dirty`, `stale`, `cancelled` |
| `dirty` | `started`, `stale`, `cancelled` |
| `started` | `in_progress`, `stale`, `cancelled` |
| `in_progress` | `blocked`, `in_review`, `stale`, `cancelled` |
| `blocked` | `in_progress`, `stale`, `cancelled` |
| `in_review` | `changes_requested`, `approved`, `cancelled` |
| `changes_requested` | `in_progress`, `cancelled` |
| `approved` | `closed`, `cancelled` |
| `closed` | `reopened` |
| `reopened` | `in_progress` |
| `stale` | `in_progress` (resumable), `cancelled` |
| `cancelled` | — (terminal) |

Rules:
- **Any transition not listed is invalid and must be rejected explicitly**,
  recording the rejected attempt in the history with `rejected: true`
  (`state transition` does this automatically).
- Direct `closed → in_progress` is forbidden: it must go through `reopened`.
- `stale` is resumable; `cancelled` is terminal.
- Timeout: a unit sitting in `in_progress` with no transition for **48h** is
  a `stale` candidate (flagged by the validator, confirmed by its owner or
  manager).
- **Pack gate hooks (§E.2)**: a pack may register additional checks on
  specific transitions for specific kinds (e.g. lex: `in_review → approved`
  for `kind: escrito` requires a current validation verdict whose hash
  matches the artifact). `state transition` runs every registered hook and
  rejects on failure, with the same `rejected: true` record.

### 1.2 Per-unit manifest — `state/{id}.json`

```json
{
  "id": "TASK-0001",
  "title": "...",
  "kind": "task",
  "owner": "{manager}/{agent}",
  "created_by": "pm-orchestrator",
  "status": "in_progress",
  "depends_on": ["TASK-0000"],
  "artifact_paths": ["..."],
  "artifact_checksum": "sha256:...",
  "history": [
    { "ts": "...", "agent": "...", "from": null, "to": "untouched", "reason": "created" }
  ]
}
```

- `history` is **append-only**: an existing entry is never edited or deleted.
- `id` is prefixed by kind. Core kinds: `TASK-` (task), `CER-` (ceremony),
  `ESC-` (escalation), `ART-` (artifact). Packs add kinds/prefixes via
  `unit_kinds` (§E.4). **`state new` validates the prefix against the kind**
  using the merged core+pack table.
- `artifact_checksum`: sha256 of the last touched artifact (`state checksum
  <id> <file>`); `null` if not applicable.
- `status` MUST always equal the `to` of the last non-rejected history entry.
- Resumability: any session/model can pick a unit back up by reading its
  manifest; the history carries the minimal context of why it is where it is.

---

## 2. Self-managed per-agent memory

### 2.1 Memory note — `memory/{agent}/{id}.md`

```markdown
---
id: mem-{agent}-0003
type: decision            # decision | feedback | project-fact | user-preference
scope: /{project}/{team}/{agent}   # hierarchical path; ".../private" suffix makes it private
created: 2026-07-02
ttl_days: null            # optional; null = no expiry
importance: 4             # 1-5
tags: [..]
signature: "a1b2c3d4"     # first 8 hex of sha256 of the normalized body (lowercased, trimmed)
supersedes: mem-...-0001  # optional: id of the note this one replaces
---

(body)
```

Write rules:
- **Only the owning agent** writes, deprecates, or replaces notes in its own
  store. The pm-orchestrator may **read** other agents' memory to resolve
  conflicts, but never writes into another agent's store.
- Notes scoped `.../private` never leave their owning agent unless the owner
  itself promotes them (rewriting with a broader scope via `supersedes`).
- `signature` prevents duplicates: computed before writing; if a live note
  with the same signature exists, the write is refused (`memory add`
  enforces this).
- `supersedes` resolves contradictions without losing history: the old note
  is NOT deleted; it becomes dead (excluded from recall) but stays readable.

### 2.2 Index — `memory/{agent}/MEMORY.md`

One line per live note: `| id | type | scope | importance | created | tags |
summary ≤ 100 chars |`. **Compaction**: when the index exceeds 30 live
entries, the owning agent compacts it (groups importance 1-2, expired, or
redundant notes into a summary note with multiple `supersedes`) and
regenerates the index. The CLI warns when the threshold is crossed.

### 2.3 Recall with a composite score

For a query with keywords `K` on date `today`:

```
score(note) = 0.5 * (importance / 5)
            + 0.3 * recency          # recency = max(0, 1 - days_since_created/90)
            + 0.2 * relevance        # relevance = |tags ∪ title_words ∩ K| / |K|
```

Dead notes (superseded) and expired ones (`created + ttl_days < today`) are
excluded from recall. Suggested inclusion threshold: `score ≥ 0.35`, top-5.
Run it with `.pm-harness/bin/harness.py memory recall <agent> --keywords k1,k2`.

**Future compatibility**: the `relevance` term is the single plug-in point
for a vector backend: replacing keyword-match with cosine similarity must not
touch the frontmatter or the rest of the formula.

---

## 3. Model routing

Two independent layers plus a separate reactive fallback. Goal: assign the
cheapest model that can do the job, per task, per delegation, at every
nesting level of the orchestration.

### 3.0 Dynamic model catalog

`model-router.json → available_models` holds the model ids actually
available in the current session/platform. The root agent syncs it at
session start (and whenever the platform's model list changes):
`.pm-harness/bin/harness.py models set "<comma-separated ids>"`.

All resolutions fuzzy-match against this catalog.

**Model inventory (capability/cost-aware routing).** `.pm-harness/bin/harness.py models scan
<inventory.json>` stores a `model-orchestrator-scan-v1` inventory
(capabilities, cost profiles, limits) under `state/model-inventory.json`
(TTL 24h). The root agent runs it at session start next to `models set`
when an inventory is available. The inventory only ADDS information:
routing without one (or with a stale one) behaves exactly as before —
it is never a prerequisite. The local
`adapters/adapters.json → platforms.<platform>.models` block declares each
platform's shape: `id_format` (`"model"` or `"provider/model"`; entries are
stored verbatim in the platform's own format), `effort_levels` (the
reasoning-effort ladder, or `null` when the platform has no effort concept),
and `discovery` (how to enumerate models; if enumeration is impossible,
register at minimum the current session model).

### 3.1 Prompt obligation (layer 1 — classification)

Before ANY delegation, the delegator (pm-orchestrator or manager) must emit
this literal block in its reasoning/record of the task:

```
Category: <trivial|routine|complex|strategic|creative|research> — <one-line reason>
Skill(s): [<existing skills to use, or "none applicable">] — <one-line reason>
```

Without this block the delegation is invalid (the receiver must reject and
return it). This is a prompt-engineering obligation, not a code classifier.

**Canonical category ids** are the six English tokens above — in code, in
manifests, in plan frontmatter, always. The pack's locale supplies display
labels and the pack's `categories` table supplies domain examples and
reasons (e.g. lex: `complex` = expert-evidence analysis, long-brief
validation; pm: `complex` = multi-module refactor). Packs may not add or
remove categories.

### 3.2 Category→model resolution (layer 2 — deterministic)

Source: the project-local `model-router.json`, executed by
`.pm-harness/bin/harness.py route <category> --task <id>`. Resolution order (first match wins):

1. Director override (`director_overrides[category]`)
2. User config override (`user_overrides[category]`)
3. Category default (`categories[category].preferred`, fuzzy-matched against
   `available_models` — case-insensitive substring over the model id)
4. Fallback chain (`categories[category].fallbacks`, in order)
5. System default (`system_default`)

Every resolution appends a record to `provenance_log` with `ts, task_id,
category, requested, resolved, chain_tried, source, effort, effort_source,
provider`. `source` ∈ `director-override | user-override | category-default
| fallback | system-default`.

**Capability floor (hard rule).** A category may declare
`min_capability` (e.g. `{"reasoning": "high"}` — shipped by default for
`complex`, `strategic` and `creative`). When a fresh inventory is present
and the resolved model is known to sit below the floor, the resolution
SKIPS it for the next candidate in the chain and records the skip in
`chain_tried` (`<model> (below-floor: reasoning=low<high)`). Models absent
from the inventory pass. This turns "never delegate high-stakes analysis
to a low-capability model" from advice into mechanics. Every resolution
record also carries `estimated_cost_tier`
(`free|low|medium|high`, from the inventory's cost profile; null when
unknown) — the base of cost observability.

**Effort (second routing dimension).** Each category also resolves a
reasoning-effort level, with the same precedence; an override may be a plain
alias string (model only) or an object `{"model": <alias>, "effort":
<level>}`. `route --platform <name>` clamps the effort to that platform's
`effort_levels` from the local adapters.json (`null` → effort omitted).
Model and effort are resolved together, per task, never pinned to an agent
(§7.1).

### 3.3 Reactive fallback (separate)

Only fires on a **real** session/model error (timeout, model unavailable,
provider error). Retry with the next model in the same category's chain and
log to `provenance_log` with `source: "fallback"` and the original error in
`chain_tried`. It never participates in normal task assignment.

---

## 4. Escalation and authority limits

Hierarchy: Director (human) ← pm-orchestrator ← Managers ← Agents.

### 4.1 Authority limits

| Level | Decides alone | Escalates upward when |
|---|---|---|
| Agent | How to implement its task within the given scope | Requirement ambiguity, conflict with another task, blocked after **2 documented attempts** |
| Manager | Priority and assignment within its team; domain technical decisions | Cross-team conflict, scope change, high risk (irreversible actions, cost, confidentiality/security), 2 agent escalations for the same cause |
| pm-orchestrator | Tactical scope, cross-team trade-offs, roster sizing (§4.3), ceremonies, priorities | ONLY Director-level decisions: strategic direction, budget, changes to this spec, self-improvement patches, creating/removing area managers, and every pack-declared always-escalate rule |

- The **pm-orchestrator is the only filter** to the Director. No manager
  or agent writes into `escalations/pending/` directly: they escalate to
  their superior, and only the pm-orchestrator decides whether something
  becomes a Director escalation.
- "Autonomy" never means "nobody to ask": every level keeps
  `teams/{manager}/plan.md` active and escalates against it, not against a
  void.
- **Pack always-escalate rules**: the pack's `guardrails` may declare
  detections that ALWAYS reach the Director regardless of level (e.g.
  lex: LFPIORPI vulnerable-activity fit, conflict of interest). These are
  injected into the compiled spec and are not autonomous decisions of any
  agent.

### 4.2 Escalation format — `escalations/pending/{ESC-id}.md`

Frontmatter: `id, created, task_ref, channel (session | audio | email),
blocking`. Body sections: **Context** (2-4 lines), **Options** (each with
one-line cost/benefit), **pm-orchestrator recommendation**.

Channels (only content is generated; nothing is actually sent): `session`
(direct question in the active chat), `audio` (script ≤90 spoken seconds),
`email` (executive summary ready to copy). When resolved, the escalation
moves to `escalations/resolved/` with the decision appended, and its
`state/ESC-*.json` manifest transitions to `closed`.

### 4.3 Continuous roster self-management

The pm-orchestrator manages its team **through the whole lifecycle**, not
only at kickoff:

- **Decides alone** (no escalation): activating/deactivating agents inside
  an already-approved manager according to real load (roster `active`
  flag), reassigning tasks between agents of the same role, adjusting
  priorities. Each adjustment is recorded via `.pm-harness/bin/harness.py roster toggle
  <manager> <agent> --active <true|false> --reason "..."` — which appends to
  the `harness.json` changelog automatically. Autonomy never means
  opacity.
- **Escalates to the Director** (approval required): creating or
  removing a whole manager (changes what areas the org covers), changing the
  escalation model, or any adjustment that changes who holds review
  authority over a gated artifact.
- Criterion: **does it change the shape of the team (managers/areas) or only
  its sizing (agents inside an approved area)?** The former escalates; the
  latter is self-management.
- After any roster change, re-materialize platform agents (§7.1) — members
  with `active: false` are not materialized and their pointer files are
  removed.

---

## 5. Ceremonies

Triggered by the Director in natural language, or through the platform
command surface installed with the adapter — commands carry no domain logic
and only route the request to the root agent. Every ceremony produces
`ceremonies/{YYYY-MM-DD}-{type}.md` and a `state/CER-*.json` manifest.

**Core ceremony set** (every pack ships them, under pack-localized names):

| Ceremony | Inputs | Output |
|---|---|---|
| `kickoff` | Domain analysis + Director's brief + source docs | Feedback session record: proposed plan, per-area draft specs, Director feedback, approval (§5.1) |
| `status` (standup / estado-del-caso) | `teams/*/plan.md` + active manifests, read-only (+ pack inputs, e.g. running deadlines) | Per-manager report: done / in progress / blocked / next |
| `decision` (mesa-de-estrategia) | Only the relevant members convened; structured debate (position → evidence → rebuttal → close) | Memory note `type: decision` + minutes |
| `closure` (showcase / cierre-de-etapa) | Artifacts `closed` since the last closure (+ pack transitions) | Executive summary compiled by the pm-orchestrator; reads `version current` to decide whether a release is due (§11) |
| `review` (retro / revision-de-expediente) | At least one improvement proposal per manager | Feeds self-improvement (§6); minutes with proposals and status |

Packs add domain ceremonies via `ceremonies` (§E.3), each declaring its
template and mandatory sections; the enforcement (record + `CER-*` manifest
+ executive-summary refresh) is core and identical for all.

`executive-summary.md` (root of `.pm-harness/`) is regenerated on demand or at
the close of any ceremony; it must be reusable across the 3 channels of
§4.2, with these fixed sections: *One-line status / Facts / Pending for the
Director / Next*.

### 5.1 Kickoff gate and autonomy modes (code-enforced)

The pm-orchestrator **never decides an initiative alone by default**. Before
any TASK is created for a new initiative, it runs a `kickoff` feedback
session with the Director: present the analysis, a proposed plan, and
draft specs per applicable area; collect feedback; iterate until approval.

- `harness.json.autonomy` ∈ `guided` (default) | `autonomous`. Only the
  Director changes it (`autonomy set <mode> --by director`, or
  `kickoff approve --grant-autonomy`).
- In `guided` mode, `state new` **refuses to create TASK units** until a
  kickoff is approved (`kickoff new` → `kickoff approve <id> --by
  director`). Enforced in code, not by prompt discipline.
- `autonomous` mode is legitimate but must be **explicitly granted**; the
  grant is recorded in the changelog. Giving the orchestrator a prompt plus
  documents is NOT a grant of autonomy.
- **Approval requires the Director's verbatim feedback**: `kickoff
  approve` refuses while the ceremony's Director-feedback section is empty
  (even "no observations" must be recorded); `--feedback "..."` records it
  at approval time. Enforced in code.
- Non-TASK kinds (CER-, ESC-, ART-, and pack kinds unless the pack declares
  otherwise) are never blocked by the gate.
- The kickoff gate never overrides a pack's human-approval guardrails (e.g.
  lex §15.1: nothing is filed with an authority without the responsible
  lawyer's sign-off, autonomy or not).

---

## 6. Self-improvement and skill auto-selection/creation

### 6.1 Self-improvement

Pipeline: feedback (reviews/retros, repeated Director corrections,
observable failures) → classify (`role | prompt | workflow |
team-structure`) → concrete patch proposal (diff over the affected SKILL.md)
→ **Director approval** → apply → record in the `harness.json`
changelog.

Auto-trigger (without the Director asking) when: the same feedback
appears **2+ times**; an agent fails in an observable pattern (same gate
broken 2+ times); the Director manually bypasses the normal flow.

### 6.2 Skill auto-selection/creation

Before delegating, every manager reviews the installed skills (`.pm-harness/bin/harness.py
skills list`) and declares the result in the §3.1 prompt obligation. A new
skill is only proposed when no equivalent exists. A task pattern solved
manually **2+ times** triggers a "convert to skill" proposal, which requires
≥1 happy-path and ≥1 error-path QA scenario before approval. Packs may
declare additional 2+ formalization triggers (e.g. lex: an informal template
used 2+ times triggers the template-definition ceremony).

---

## 7. Hierarchical delegation

- Delegation by **recursive tool-calling**: each manager is the only one
  that executes directly at its level. To delegate: identify the matching
  declared role (match by role, not by proper name), build an ad-hoc task
  (with the §3.1 block + the receiver's SKILL.md content + the
  `task-handoff` skill injected into the subagent prompt) and collect the
  result.
- A manager **never** also appears as a worker at its own level (prevents
  delegation loops).
- Every delegation references a state manifest (§1.2) and updates its
  transitions on delivery.
- Nested orchestrations re-run §3.1 + §3.2 at their own level: model choice
  is re-derived per subtask, never inherited blindly.

### 7.1 Platform-native agent materialization

The roster must be **visible and invocable on the host platform**, not only
described in `.pm-harness/teams/`. The installer ships each platform a
local plugin surface (commands, agents, activation skill) including a
**statically installed root agent file** so the orchestrator is invocable
immediately after install. Whenever the roster is generated or changed, the
root agent materializes one **pointer agent file** per active roster member
into the platform's native agents directory, taken from the LOCAL
`.pm-harness/adapters/adapters.json → platforms.<platform>.agents_dir`
(skip platforms where it is `null`). Never resolve this from global config
(§8).

Rules:

- Pointer files contain **no domain logic**. The single source of truth
  stays `.pm-harness/teams/.../SKILL.md`; the pointer's body instructs the
  platform to read and adopt that file and to obey the compiled SPEC.
- Every pointer file starts its body with the marker
  `<!-- PM-HARNESS:AGENT -->`. The root agent may regenerate/delete files
  carrying that marker on roster changes; it must never overwrite an agent
  file in `agents_dir` that lacks the marker (user-owned).
- Pointer files use the platform's native agent frontmatter, selected by
  `adapters.json → platforms.<platform>.agent_format` (`claude-code`: name +
  description + comma-separated tools, namespaced `<plugin>:{member-id}`;
  `opencode`: description + mode + boolean tools map — root agent `mode:
  primary`, everyone else `mode: subagent`). Descriptions declare **both
  selection boundaries**: when to delegate AND when not (`Not for: ...`,
  from the roster's optional `not_for`). Workers get no subagent-spawning
  tool. Pointers never pin a `model`: model choice always flows through §3
  at delegation time.
- Members with `active: false` (§4.3) are not materialized; their
  marker-bearing pointer files are removed.
- Materialization is idempotent and additive; it never touches files outside
  `agents_dir`. CLI: `agents materialize [--platform <name>]` and `agents
  check` (non-zero exit when any active roster member lacks its pointer).
- Plugin command files (installed by the installer, not by materialization)
  carry no domain logic and only route to the root agent with the
  Director's arguments.

### 7.2 Context passing (stateless subagents)

Every subagent invocation is **independent and stateless**: it inherits no
conversation context and shares no memory with the delegator or with sibling
agents. Consequences, all normative:

- The delegator includes **everything** the receiver needs inside the
  delegation prompt: the receiver's SKILL.md content, the ad-hoc task, and
  the facts block below.
- Every delegation prompt **starts** with a structured **FACTS block**,
  copied verbatim, never summarized, surviving any later compaction:

  ```
  FACTS (do not summarize, do not drop):
  task_id: TASK-...
  category: <§3.1 category> — <reason>
  model: <resolved id> (provenance: <source>)
  plan: <path to the approved §12 plan>
  gates: <exact commands the result must pass>
  constraints: <hard limits: paths, prohibitions, deadlines, confidentiality>
  artifacts: <exact paths to read/write>
  ```

  Transactional facts (ids, numbers, exact paths, exit codes) live here
  because summarization destroys them; key information goes first because
  long-input attention favors the beginning.
- **Attention-dilution rule**: when one delegation would require analyzing
  more than ~7 discrete items, split it into one pass per item (or small
  batch) plus one final cross-item integration pass.
- **Result trimming**: the delegator distills subagent output before passing
  it upward, but transactional facts and provenance are preserved verbatim.

---

## 8. Local isolation (non-negotiable)

- All harness state lives under `<project>/.pm-harness/` by default; pack
  `layout` may add sibling domain directories (e.g. lex `expediente/`) that
  are equally project-local.
- No project state ever propagates to another project or to global config.
- The installer never reads or writes project state; it only scaffolds
  missing skeleton files, never overwrites, and fails explicitly.
- Global config never overrides local config: overrides flow Director >
  user > default, and all of them live INSIDE the local `model-router.json`.
- **Pack isolation exceptions** must be declared in the pack, explicit,
  Director-triggered, and path-whitelisted (e.g. lex template-library
  export/import writes only under `plantillas/`). State, memory, evidence,
  and caches are never shareable between projects under any mechanism.

### 8.1 Update Mode (engine function)

Opt-in refresh of logic/skeleton files to the installed engine+pack
versions. Normative properties:

- Refreshes **engine files and pack files separately** (an engine-only
  bugfix reaches every pack's installs with one engine release).
- Never touches project state: `harness.json`, `model-router.json`,
  state/, memory/, wiki INDEX, standards GATES/IMPROVEMENT, `CHANGELOG.md`,
  or any pack `layout` domain directory.
- Automatic prior backup under `.pm-harness/.backups/<timestamp>/`.
- Version tracking in `.pm-harness/HARNESS-VERSION`, stamped with BOTH
  versions (e.g. `engine 2.0.0 / lex-pack 1.2.0`); each pack declares its
  compatible engine range (`engine_version_required`, SemVer).

### 8.2 Optional engine modules

Generic capabilities that not every pack needs ship as engine modules a pack
enables by flag. v0 modules: `private-split` (the `private-outer-v1`
public-repo layout with its manifest, validation, and mechanically verified
two-repo postcondition — enabled by the pm pack). A module's contracts bind
only packs that enable it.

---

## 9. Documentation: the LLM Wiki

Project knowledge is maintained as an **LLM Wiki** under
`.pm-harness/wiki/`, in three layers:

1. **Sources** — the project's raw documents. Immutable from the wiki's
   point of view; always cited, never edited.
2. **Wiki** — `wiki/pages/*.md`: compiled, cross-referenced pages (entities,
   concepts, decisions, contradiction flags). Agents answer
   project-knowledge questions **from the wiki first**, opening sources only
   to verify or fill gaps. Synthesis happens once, incrementally.
3. **Schema** — `wiki/WIKI-SCHEMA.md`: the maintenance contract (page
   frontmatter, `[[link]]` rules, contradiction handling). Normative;
   changes require Director approval.

Duties:

- Ingesting a new/changed source updates the affected pages and
  `wiki/INDEX.md` in the same unit of work (the `llm-wiki` skill is the
  procedure).
- A TASK that changes documented behavior/state cannot close before the wiki
  is updated and `wiki check` is clean.
- Contradictions between sources are NEVER resolved silently: they are
  recorded side by side and escalated.
- `wiki check` is the hard gate (schema/index/frontmatter breaks are
  errors); unresolved `[[links]]` are warnings — a visible backlog, never
  silently deleted. `validate` surfaces wiki problems as warnings.
- The wiki inherits the project's confidentiality (§8): it never leaves the
  project.

## 10. Standards system and quality gates

`.pm-harness/standards/` holds the project's quality rules, born from real
findings so no finding of the same type happens twice:

- `README.md` — loading protocol: agents read `GATES.md` always, then ONLY
  the rule documents matching the task's dimensions. Rule format: stable ID
  `STD-XXX-nn`, imperative statement, mechanical verification, origin.
  Budget ~20 rules per document — retire before adding.
- `GATES.md` — Gate 0 (task start), Gate 1 (before integrating: `validate`,
  `plan check`, `wiki check` when docs were touched, `changelog check` when
  behavior changed, **plus every pack-registered gate command** — e.g. lex
  `evidence verify`, `escrito gate` — plus the stack/domain checklist),
  Gate 2 (release).
- `IMPROVEMENT.md` — the APR protocol: every uncovered defect produces an
  APR entry with exactly one destination (`new rule | harden gate | clarify
  | retire | log only`) in the same change that fixes it.

Normative rules:

- Managers fill the stack/domain-specific Gate 1 commands during roster
  generation and keep them current; delegated tasks carry the gates in their
  FACTS block (§7.2).
- **Security/risk is a first-class area**: every roster includes explicit
  ownership of the pack's risk dimension (security engineering for pm;
  ethics/compliance review for lex). Risk-relevant changes require that
  area's review at Gate 1; the pack's non-negotiable gates are never dropped,
  whatever the roster size.
- Audit runs feed `IMPROVEMENT.md`; repeated findings of a covered type
  mandate a `harden gate` APR (§6.1 triggers apply).
- Pack domain gates are part of Gate 1; this system organizes them, it never
  substitutes or weakens them.

## 11. Changelog, delivery discipline, and semantic versioning

Two distinct "changelog" concepts coexist: the `changelog` array inside
`harness.json` is a machine-oriented, append-only **audit trail** of
harness-level events (autonomy grants, kickoff approvals, roster toggles,
skill patches, releases); `CHANGELOG.md` at the **project root** (sibling of
`.pm-harness/`, never overwritten once created) is the human-and-agent
release history in [Keep a Changelog](https://keepachangelog.com) format.
Every unit of work that changes observable behavior/documented state adds
one bullet under `## [Unreleased]` (category `Added / Changed / Fixed /
Deprecated / Removed / Security`), referencing its TASK id, before that unit
is considered done.

Every PR (or, on solo/local work, every integration into the trunk) is
documented with the seeded `.github/pull_request_template.md`: summary,
why/context, change type, risk and risk type, how it was tested, evidence,
and a checklist (CHANGELOG updated, tests added/updated, `validate` clean,
docs/wiki updated when behavior changed). An unfilled template section is
treated the same as a missing one.

Versioning is **SemVer** (`vMAJOR.MINOR.PATCH`, local git tags at the
project root), bumped manually by the agent driving the closure ceremony
(§5), never automatically: any breaking change → major; any new capability →
minor; otherwise → patch.

Duties:

- `changelog check [--task <id>]` is the hard gate: fails if `CHANGELOG.md`
  is missing, has no `[Unreleased]` section, the section is empty, or (with
  `--task`) no entry references that task id.
- `version bump {major|minor|patch}` moves `[Unreleased]` into a dated
  section, resets the skeleton, records the release in the
  `harness.json` changelog array, and creates a local annotated tag. It
  never pushes: publishing anything is a Director-confirmed action
  outside the CLI's scope (§8).
- `version current` reports the latest tag and pending `[Unreleased]`
  entries; the closure ceremony reads it to decide whether a release is due.
- The `changelog-release` skill is the end-to-end procedure (classify →
  write entry → confirm validation evidence per the pack's gates → fill the
  PR template → bump at integration time).
- `validate` does not hard-fail on a missing/incomplete `CHANGELOG.md`
  (soft-warning posture, like the wiki); `changelog check` is the dedicated
  hard gate at Gate 1.
- Released sections are never hand-edited.

## 12. Hierarchical planning contract

No TASK is executed from an improvised mental model: execution follows an
**approved, written plan**, proportional to the task's §3.1 category,
reviewed by the level immediately above the executor. The plan gate is the
execution mirror of the escalation ladder (§4.1) and generalizes the kickoff
gate (§5.1) down the hierarchy.

### 12.1 The plan artifact — `plans/{TASK-id}.plan.md`

One plan file per TASK unit (only `kind: task` units are planned). The TASK
manifest carries `"plan_ref": "plans/{TASK-id}.plan.md"`. Frontmatter:
`task_ref, category, status (draft | approved), created, created_by,
approved_by, approved_at`. Body sections: **Objective** (one verifiable
paragraph) / **Todos** (each a verifiable step with its acceptance
criterion) / **Gates** (the exact Gate 1 commands) / **Risks** (irreversible
steps — and pack-critical risks such as procedural deadlines — flagged
explicitly) / **Open questions** / **Amendments** (append-only).

- Frontmatter and todo checkboxes are machine-read by the CLI; everything
  else is prose for the approver.
- A plan with zero todos is not a plan: `plan check` fails on it.

### 12.2 Plan-before-execute gate (code-enforced)

Each level plans its own work; its **immediate superior** approves,
mirroring §4.1. The superior is derived from the manifest's `owner`:
`{manager}/{agent}` → `{manager}`; `{manager}` → `pm-orchestrator`;
`pm-orchestrator` → `director`. The Director may approve any plan at any
level.

- `state transition <TASK-id> in_progress` **refuses `started →
  in_progress`** while the TASK has no approved plan, recording the rejected
  attempt with `rejected: true`. Only TASK units are gated.
- `plan approve <TASK-id> --by <approver>` refuses any approver other than
  the owner's superior or the Director. Self-approval is structurally
  impossible for `complex`-and-up categories.

### 12.3 Proportionality by §3.1 category

| Category | Plan weight | Approval |
|---|---|---|
| `trivial`, `routine` | **Lightweight**: objective + todos (+ gates). May be written by the delegator in the delegation itself. | Auto-approved by the delegator: `plan new <id> --category trivial --by <superior> --approve` (the CLI only accepts `--approve` for these two categories, and only from the owner's superior). |
| `complex`, `strategic`, `creative`, `research` | **Full**: every §12.1 section filled, risks and open questions included. | Explicit review by the superior using the `plan-review` skill (12.5), then `plan approve <id> --by <superior>`. |

### 12.4 Execution adherence and amendments

- The plan is the execution contract: the executor works the todos and
  checks them off as their acceptance criteria are met.
- `plan check <TASK-id>` is the adherence gate: it fails when the plan is
  missing, unapproved, has zero todos, or has unchecked todos. The CLI
  **refuses `in_progress → in_review`** while todos remain unchecked. (The
  in-review refusal applies to TASKs that have a plan file; a legacy TASK
  already past the `started` gate surfaces as a `validate` warning instead
  of being stranded.)
- **Deviations never rewrite the plan.** `plan amend <TASK-id> --reason ...
  --by <executor> --approved-by <approver>` appends under `## Amendments`
  (append-only) and may add new todos (`--add-todo`, repeatable). The CLI
  refuses an `--approved-by` that is not the plan's original approver (or
  the Director). Dropping a todo is an amendment that says so — the
  checkbox is marked done with a reference to the amendment, never deleted.
- A scope change that exceeds the approver's own authority is not an
  amendment but an escalation (§4).

### 12.5 The `plan-review` skill

Plan review is a **skill, not a roster role**: the approver runs
`skills/plan-review/` before approving any full-weight plan. Dedicated
planner/critic agents are explicitly rejected (they would break the
single-filter invariant §4.1). Checklist: objective verifiability, todo
completeness and atomicity, acceptance-criteria testability, gap/ambiguity
hunting, scope-creep detection, risk and rollback coverage (including
pack-critical risks), and open-questions triage. Verdict: `approve | revise`
with concrete findings; `revise` returns the plan to its author, it never
rewrites the plan in place.

Duties:

- Managers require an approved plan before delegating execution: the FACTS
  block (§7.2) carries the plan path, and the §3.1 category in the manifest,
  the delegation block, and the plan frontmatter must agree.
- `validate` surfaces plan problems as **warnings**; the hard gates are the
  two code-enforced transitions plus `plan check` at Gate 1.

---

## E. Extension points (closed list — the only ones)

A SpecPack customizes the engine EXCLUSIVELY through these five mechanisms.

1. **CLI subcommands** — `harness_core.register_command(name, fn)`. The
   installed binary is a shim: `harness_core.main(pack=<pack>_ext)`. Pack
   commands share the core's `find_root`/`die`/json helpers; they never
   redefine core commands.
2. **Gate hooks** — `harness_core.register_gate(transition, kind, check_fn)`
   attaches pack checks to state-machine transitions (§1.1), and
   `harness_core.register_validate_check(fn)` adds pack checks to
   `validate`. Core runs all registered hooks; a failing hook rejects with
   `rejected: true`.
3. **Ceremony declarations** — the pack declares each domain ceremony's
   name, template, and mandatory sections; enforcement (record + `CER-*`
   manifest + executive-summary refresh) is core (§5).
4. **Kinds and prefixes** — the pack's `unit_kinds` table extends the core
   kinds (TASK/CER/ESC/ART); prefix↔kind validation is core (§1.2).
5. **Locale** — every user-facing string is resolved from the pack's
   `locale/<lang>.json`; engine code contains no user-facing literals.

**Hard rule**: a pack never patches the engine — no monkey-patching, no
copying core functions, no shadowing core commands. If a pack needs
something the hooks don't provide, that is an engine change (new engine
version), never a pack workaround.

## V. Versioning

The engine follows its own SemVer. Each pack declares
`engine_version_required` (SemVer range). The generated installer stamps
both into `HARNESS-VERSION`. A compiled SPEC records the engine version, the
pack id and the pack version in its header. Changes to this CORE-SPEC follow
§11 discipline in the `harness-engine` repo and require Director
approval when they alter normative behavior.

---

# PM DOMAIN-SPEC — product specialization of the PM Harness

This document holds the product-domain sections of the PM Harness. It is
compiled after the engine CORE-SPEC (sections 1-12, generic) into the
installed HARNESS-SPEC.md. References §1-§12 point at the compiled core.

## 13. Product specialization

- **Reference roster areas**: Product / Engineering / Design / Security (and
  any other rostered area). Security ownership is never dropped, whatever
  the roster size (§10): a security manager, or a security-engineer role
  under engineering in small rosters — see the merge rules in the root
  agent's SKILL.
- **Kickoff per-area draft specs** (§5.1) cover Product, Engineering,
  Design, Security, and any other rostered area.
- **`private-outer-v1` layout**: this pack enables the engine module
  `private-split` (§8.2). When the project has a public source repository,
  the owner may keep the entire harness — and every other AI/dev artifact —
  out of it by converting the project into the private-outer / public-inner
  layout: the outer (`<project>-ai-dev/`) holds `.pm-harness/`, platform
  adapters, and dev docs; the public inner lives as an ignored
  subdirectory; both are independent git repositories; the split is
  declared in `.pm-harness/split.manifest.json` (schema
  `schemas/split-manifest.v1.json`); the layout is symlink-free by design;
  the postcondition (two repos) is mechanically verified by `validate`.
  Conversion/validation/status: `harness.py private-split
  {init,migrate-from-personal,validate,status}`, orchestrated interactively
  by the `pm-harness-private-split` skill.
- **PR discipline** (§11): every PR is documented with the seeded
  `.github/pull_request_template.md` (shipped in `github/`); an unfilled
  template section is treated the same as a missing one.

---

## Guardrails (PM pack)

1. **Security is a first-class area** (§10): security-relevant changes
   require that area's review at Gate 1; the dependency-audit gate is never
   dropped, whatever the roster size.
2. **Nothing is published without the Director**: pushing commits/tags,
   releasing, or any outward-facing action is a Director-confirmed step
   outside the CLI's scope (§8/§11).
3. **The harness never crosses project boundaries** (§8): in the
   private-outer layout, outer and inner together form ONE project; harness
   state in the outer never propagates elsewhere.
