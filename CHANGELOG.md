# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

Agents: see `.pm-harness/HARNESS-SPEC.md` §11 before editing this file. Every
unit of work that changes product behavior adds one bullet under
`[Unreleased]`, in the matching category, referencing its TASK id — before the
unit of work is considered done. Only `harness.py version bump` moves
`[Unreleased]` content into a dated release section; never hand-edit a
released `## [x.y.z]` section.

## [Unreleased]

### Added

- TASK-0003: Added the Python/Jinja2 `ai-server` generator CLI skeleton with profile/setup listing, dry-run generation, localhost chat workspace rendering, validation, and unsafe LAN rejection.
- TASK-0002: Added the generator-first roadmap defining clone → generate → launch workflow, configuration families, CLI UX, architecture, backlog, and security controls.
- TASK-0004: Added model preset catalog + aliases, `list models`, and `matrix` scenario preview with GO/NO-GO messaging.
- TASK-0005: Added human-first onboarding docs (`README.md`, `docs/human-guide.md`, `docs/README.md`) plus repository naming recommendations with a preferred choice for publication.
- TASK-0007: Added workspace backup, restore, and rollback scripts with SHA-256 verification, atomic replacement, and preservation of whatever they replace.
- TASK-0007: Added `sbom.json` (CycloneDX) covering pinned Python dependencies and the digest-pinned serving image, with `scripts/generate_sbom.py` and a CI staleness gate.
- TASK-0007: Added a committed golden fixture of generated output plus `scripts/update_golden_fixture.py`, so template changes cannot land without an explicit byte-for-byte diff.
- TASK-0007: Added `scripts/resolve_image_digest.sh` to resolve the serving image digest from the registry without pulling it.
- TASK-0006: Added a capability status table to `README.md` covering what is implemented, refused by design, and planned.
- TASK-0007: Added a CI functional sweep that generates, validates, and Compose-parses every preset in the catalog (not just one), plus a `compileall` byte-compile check, so a preset or template that breaks for any entry fails the pipeline.

### Changed

- TASK-0006: Clarified static matrix/validation boundaries, safe generated-workspace startup and overwrite guidance, current LAN enforcement limitations, and compiled the accepted product state into the LLM Wiki.
- TASK-0003: Changed Sprint 1 serving assets into reusable generator source material and ignored `generated/` outputs by default.
- TASK-0003: Hardened LAN generation checks to reject blank `--lan-allowlist` values even when `--auth bearer-token` is provided.
- TASK-0004: Changed generator flow to support `--preset` shorthand that expands into explicit setup/profile/access/model configuration and writes resolved details into generated manifest/runbook.
- TASK-0004: Changed generated workspace UX with concise helper scripts (`start`, `validate`, `smoke`) for abbreviated launch commands.
- TASK-0001: Changed Sprint 1 closure alignment so canonical operations follow `clone -> matrix -> generate -> validate -> start`, while root docker-compose/profile/script artifacts remain explicitly labeled compatibility/examples with generated equivalents referenced.

### Fixed

- TASK-0007: Fixed the serving image referencing `ghcr.io/ggerganov/llama.cpp`, a repository that no longer exists and returns 404, so no generated workspace could pull its image; the canonical `ghcr.io/ggml-org/llama.cpp` is now pinned by digest.
- TASK-0007: Fixed the CI shellcheck gate, which could never pass because the `CDPATH= cd` idiom trips SC1007 across every repository and generated script; replaced with the equivalent `CDPATH='' cd`.
- TASK-0007: Fixed the golden fixture's `.env` being swallowed by the `.gitignore` `.env` rule, which would have failed the drift gate on a clean checkout.
- TASK-0007: Fixed the wizard resolving a relative `--out` against the caller's working directory while the renderer resolved it against the project root, so the overwrite check inspected a different directory than the one written and surfaced `--force` guidance instead of `--overwrite`.
- TASK-0007: Fixed the wizard aborting with an `EOFError` traceback after generating a workspace when run without a terminal; preset/profile selection now requires the matching flag with a clear error, and `--run ask` without a TTY declines to start the server.
- TASK-0007: Fixed bare `ai-server` invocation reporting success; it now prints usage to stderr and exits 2.
- TASK-0006: Fixed README and LAN runbook claims that contradicted enforced behavior: LAN access, bearer-token auth, and `--lan-allowlist` are refused rather than opt-in; `matrix` reports WARN/NO-GO and never GO; the model is bind-mounted read-only from its host path instead of copied into the workspace.

### Deprecated

### Removed

### Security

- TASK-0006: Documented the localhost-only fail-closed posture in `README.md` and `docs/lan-safe-runbook.md`, replacing guidance that pointed operators toward a LAN exposure path the generator refuses to produce.
- TASK-0007: Pinned the serving container image by digest and made the validator reject any workspace whose image is not that exact reference, so a moved tag cannot change what runs.
- TASK-0007: Recorded that this is a private, personally-used project that is not distributed and carries no license; `pyproject.toml` declares `Private :: Do Not Upload` so an accidental publish fails.
