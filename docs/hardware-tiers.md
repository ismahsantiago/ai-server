---
tier_model_version: 1
owner: product
status: product-definition
supersedes: TASK-0008 provisional tier model
source: KICK-0002
---

# Hardware tiers

## Who this is for

"Entrepreneurs, home workers, and small dev teams reusing machines they would otherwise sell off." (KICK-0002, lines 80-82.)

"each machine will be different, each case is unique; we should only function as a package installer that adapts to each need, which is why our requirements must be minimal and preferably already available in the Docker images we use" (KICK-0002, lines 83-88.)

"the laptop I was going to sell now serves models to my home or office in one command" (KICK-0002, lines 89-92.)

Every tier definition must answer "what can my machine do" for a reader who does not know what a quantization or a KV cache is.

## Tiers

The tier set uses the corrected fit function in [Mapping](#mapping). Each band is a tier, including the honest no-fit outcome, so the taxonomy has six tiers.

### Start small

tier_id: `start-small`

tier_label: Start small

Mapped preset/profile/context: `smollm3-3b` / `medium-fast` / 2048.

What you can expect: Serve the catalog's smallest general-purpose option for a lightweight local assistant.

What you cannot do: Run any larger catalog option until the next fit boundary is reached.

### Code starter

tier_id: `code-starter`

tier_label: Code starter

Mapped preset/profile/context: `smollm3-3b`, `qwen3-coder-7b` / `medium-fast`, `medium` / 2048, 4096.

What you can expect: Add a coding-focused option alongside the smallest general-purpose option.

What you cannot do: Expect the agentic-code option or the larger reasoning option to fit yet.

### Everyday code

tier_id: `everyday-code`

tier_label: Everyday code

Mapped preset/profile/context: `smollm3-3b`, `qwen3-coder-7b`, `ornith-9b` / `medium-fast`, `medium`, `medium` / 2048, 4096, 4096.

What you can expect: Serve the catalog's agentic-code option as well as the smaller choices.

What you cannot do: Expect the larger reasoning option or the development option to fit yet.

### Deeper work

tier_id: `deeper-work`

tier_label: Deeper work

Mapped preset/profile/context: `smollm3-3b`, `qwen3-coder-7b`, `ornith-9b`, `phi-4-14b` / `medium-fast`, `medium`, `medium`, `good` / 2048, 4096, 4096, 6144.

What you can expect: Add the catalog's larger general-reasoning option for work that benefits from it.

What you cannot do: Expect the largest development option to fit yet.

### Full catalog

tier_id: `full-catalog`

tier_label: Full catalog

Mapped preset/profile/context: all committed presets / their committed default profiles / their committed default contexts.

What you can expect: Choose from every current catalog option, including the largest development option.

What you cannot do: Treat this as a promise of a particular speed, quality, or runtime result; those remain dependent on measured host facts and the runtime.

### Needs a smaller model

tier_id: `needs-smaller-model`

tier_label: Needs a smaller model

Mapped preset/profile/context: no committed preset / none / none.

What you can expect: Receive a clear result that this catalog has no fitting choice for the measured usable memory.

What you cannot do: Serve a current catalog preset from this machine without a catalog or host change.

The `tier_id` is the machine-readable key consumed by `doctor` and by any downstream Phase M filter, and is versioned by `tier_model_version`. The `tier_label` is display-only and may change without a version bump. A change to the set of `tier_id` values or to a tier's mapped presets forces a `tier_model_version` bump plus a CHANGELOG entry.

### The bottom band

Fact: Below the first boundary produced by the corrected fit sequence, no preset in the committed catalog fits.

Next: We have nothing for this machine today. A smaller committed preset or a new measured fit data change, routed through a future catalog task or TASK-0008 amendment, would create an option.

Wording discipline: Say that the current catalog has no fitting option while leaving the machine's value to its owner; do not turn a catalog limit into a judgement about the machine.

Never: "This machine is worthless for local AI."

bottom band is a tier because an explicit, stable no-fit outcome prevents a machine below the first boundary from being silently omitted.

## Mapping

The current provisional boundary sequence is obtained read-only with:

`python3 -c "from ai_server_generator.presets import ordered_presets; print(sorted({p.minimum_host_ram_gb for p in ordered_presets()}))"`

`[6.0, 9.5, 10.0, 14.0, 20.0]`

This produces six bands: one below the first boundary and one beginning at each boundary.

| alias | estimated_model_gb + kv_cache_gb_at_default_context + runtime_buffer_gb | minimum_host_ram_gb | difference |
| --- | ---: | ---: | ---: |
| ornith-9b | 7.5 | 10.0 | 2.5 |
| devstral-small-v25.07 | 17.5 | 20.0 | 2.5 |
| qwen3-coder-7b | 6.8 | 9.5 | 2.7 |
| smollm3-3b | 3.25 | 6.0 | 2.75 |
| phi-4-14b | 11.75 | 14.0 | 2.25 |

reserve applied twice: `minimum_host_ram_gb = footprint + 2.25..2.75`, then `budget = usable_memory - 2.5` is compared with that already-reserved minimum, so the host reserve is charged in both terms.

| preset | preset.default_context | profile ctx_size |
| --- | ---: | ---: |
| ornith-9b | 4096 | 4096 |
| devstral-small-v25.07 | 4096 | 4096 |
| qwen3-coder-7b | 4096 | 4096 |
| smollm3-3b | 2048 | 2048 |
| phi-4-14b | 6144 | 6144 |

The fields agree today. When they diverge, the operator-facing context claim uses `preset.default_context`, because it is the preset's explicit product contract. profile selection replaced: choosing the highest profile whose `mem_limit` fits can override that product contract even though the committed profile limits are `medium-fast` 6g, `medium` 8g, and `good` 10g; use each preset's committed `default_profile` instead.

### Band granularity

one tier per boundary; the named corrected-boundary function is `sorted({p.estimated_model_gb + p.kv_cache_gb_at_default_context + p.runtime_buffer_gb for p in ordered_presets()})`, which yields today's ordered band starts `[3.25, 6.8, 7.5, 11.75, 17.5]` plus the bottom band. The two adjacent provisional boundaries separated by half a gigabyte remain distinct; the corrected function decides their placement from committed data rather than rounding them into a marketing category. When a preset is added to or removed from `presets.py`, recompute this function and the tier set changes with its result, requiring the stated versioning rule.

## Verdict on the provisional model

ADJUSTED

The reserve audit in Mapping establishes a double charge; the one-tier-per-boundary rule keeps the result data-derived; and the profile/context ruling uses each preset's committed defaults rather than a separately selected profile. The provisional mapping must therefore be adjusted before it becomes authoritative.

### Specification for engineering

Target module: `ai_server_generator/tiering.py`.

Target function: `derive_tier(profile)` and the recommendation fit predicate it uses.

Inputs: measured usable memory (`memory.available_gb`, falling back only as the existing confidence contract permits), applicable `memory.cgroup_limit_gb`, and for each committed preset `estimated_model_gb`, `kv_cache_gb_at_default_context`, `runtime_buffer_gb`, `default_profile`, and `default_context`.

Replacement formula: `usable_budget = min(measured_available_or_permitted_total, cgroup_limit_if_applicable)`; a preset fits when `usable_budget >= p.estimated_model_gb + p.kv_cache_gb_at_default_context + p.runtime_buffer_gb`; tier boundaries are `sorted({that footprint for p in ordered_presets()})`, with no additional host-reserve subtraction.

Band list yielded today: bottom/no fit; 3.25; 6.8; 7.5; 11.75; 17.5.

Routing: TASK-0008 remains open. Product-manager must carry this specification to pm-orchestrator, which routes it to engineering-manager as a TASK-0008 amendment. This document does not apply the change.

### Operator impact

The considered alternative is the reserve-corrected mapping. 8 GB machine -> 0 presets double-counted vs 1 corrected (smollm3-3b); 10 GB -> 1 vs 3; 12 GB -> 2 vs 3 (+ornith-9b); 16 GB -> 3 vs 4 (+phi-4-14b). Thus an 8 GB, 12 GB, and 16 GB machine each lands in a different tier under the corrected mapping.

## Honesty posture

| claim class | permitted wording | forbidden wording | required visual separation in doctor |
| --- | --- | --- | --- |
| measured fact | `MEASURED: RAM observed as ...` | `This host will run ...` | Put raw observations in `MEASURED`. |
| derived recommendation | `DERIVED (recommendations): this preset fits the committed planning inputs` | `Verified to run on this machine` | Put fit results in `DERIVED (recommendations)` with their basis. |
| capability claim | `This catalog option is recommended subject to the displayed basis and runtime` | `Guaranteed capability` | Keep the claim after, and visibly separate from, both prior sections. |

`ai_server_generator/cli.py` documents that `_static_matrix_decision` never returns a passing `GO` because its inputs are static planning assumptions, and `ai_server_generator/presets.py` marks every preset `metadata_status: "planning-assumption-only"`. The same boundary governs `doctor`: doctor may emit `FIT` only when all required host inputs are measured, the basis is displayed, and the result remains labelled derived rather than a runtime guarantee.

ESC-0002 resolved distribution as Apache-2.0, replacing the former private, unlicensed posture. distribution moves the line: an operator we cannot speak to must see every recommendation labelled `DERIVED (recommendations)` with its planning-assumption-only basis, and every capability sentence must state that runtime execution is not verified.

## When we cannot measure

No case here is platform-specific; a macOS-specific reduced-confidence case is added only if TASK-0008 reports a measured detection gap, never by assumption. Reduced confidence never degrades to silence. Reduced confidence never degrades to a guess.

### RAM unknown

Says: `We could not measure usable memory, so no model recommendation is shown.`

Next: `Run doctor directly on the host and re-run it after memory measurement is available.`

### GPU unknown

Says: `We could not identify graphics acceleration, so this recommendation does not promise accelerated serving.`

Next: `Re-run doctor on the host and use the measured CPU and memory result until acceleration is identified.`

### Disk free space unknown

Says: `We could not measure free model storage, so confirm space before downloading a model.`

Next: `Check free space on the models drive, then re-run doctor.`

### Container observation scope

Says: `This run cannot confirm the physical host from inside its container, so host recommendations are reduced-confidence.`

Next: `Run doctor directly on the host, outside the container.`

### Serving runtime undetermined

Says: `The serving runtime is not selected yet, so memory-fit advice remains derived from the current planning data.`

Next: `Use the current recommendation as planning guidance and revisit it when TASK-0009 selects the runtime.`

empty runnable_presets replaced: an unknown RAM must surface the RAM-unknown sentence and next action rather than look like a measured no-fit outcome; this is the required product presentation for TASK-0008's data state.

## macOS

### Two independent questions

Detection richness and container acceleration are independent questions. TASK-0008 reports that macOS has richer probeable detail than previously assumed, pending its amended detection findings. TASK-0008 is verifying whether containerised serving reaches acceleration, while TASK-0009 evaluates whether a host-side runner is available. Neither fact is resolved today. Resolving one does not resolve the other.

### Branch A — containerised runtime only

Tier consequence: the tier expresses what measured CPU and memory can support when the container path is CPU-only, regardless of host Metal hardware.

Says: `Your Mac can still serve the choices shown for its measured CPU and memory; this container path does not use its graphics acceleration.`

Mapping delta: retain the corrected memory-fit mapping and do not add an acceleration-based recommendation.

### Branch B — a host-side runner is available

Tier consequence: the tier may include measured Metal acceleration in a runtime-specific recommendation once the runner establishes that basis.

Says: `Your Mac can use the choices shown from its measured memory, and this runner may use its graphics acceleration when the displayed basis confirms it.`

Mapping delta: add a runtime-specific acceleration basis only after the runner reports it; the corrected memory-fit mapping remains the common baseline.

### Selection rule

TASK-0008's reported verification selects the container-acceleration fact; TASK-0008's amended detection findings select the detection-richness fact; and TASK-0009's runner evaluation determines whether Branch B is available. Until those reports exist, neither branch is selected as the delivered runtime path.

## Interface contract for engineering

| required field | present in TASK-0008's plan? |
| --- | --- |
| `tier_id` | yes |
| `tier_label` | yes |
| `tier_model_version` | yes |
| `tier_model_status` | yes |
| `confidence` | yes |
| `undetermined_inputs` | yes |
| `basis` | yes |
