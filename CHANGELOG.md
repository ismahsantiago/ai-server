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

### Changed

- TASK-0003: Changed Sprint 1 serving assets into reusable generator source material and ignored `generated/` outputs by default.
- TASK-0003: Hardened LAN generation checks to reject blank `--lan-allowlist` values even when `--auth bearer-token` is provided.
- TASK-0004: Changed generator flow to support `--preset` shorthand that expands into explicit setup/profile/access/model configuration and writes resolved details into generated manifest/runbook.
- TASK-0004: Changed generated workspace UX with concise helper scripts (`start`, `validate`, `smoke`) for abbreviated launch commands.
- TASK-0001: Changed Sprint 1 closure alignment so canonical operations follow `clone -> matrix -> generate -> validate -> start`, while root docker-compose/profile/script artifacts remain explicitly labeled compatibility/examples with generated equivalents referenced.

### Fixed

### Deprecated

### Removed

### Security
