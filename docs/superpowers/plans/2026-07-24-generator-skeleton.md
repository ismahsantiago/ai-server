# Sprint 2 Generator Skeleton Implementation Plan

Task: TASK-0003

## Objective

Build a generator-first Python/Jinja2 CLI skeleton for ai-server that can list supported profiles and setups, render the first `chat` + `medium` + `localhost` generated workspace, validate generated output, and reject unsafe LAN generation without both bearer-token auth and a LAN allowlist.

## Responsibilities and tasks

1. **Engineering manager integration**
   - Keep scope limited to the approved MVP: chat-localhost-medium plus skeleton commands.
   - Maintain harness state via `python3 .pm-harness/bin/harness.py` only.
   - Update the plan checkboxes only after all acceptance criteria are complete.

2. **UX/dev CLI path**
   - Add `python3 -m ai_server_generator --help` and console script metadata `ai-server = ai_server_generator.cli:main`.
   - Implement subcommands: `list profiles`, `list setups`, `generate`, and `validate`.
   - Keep command output concise and script-friendly.

3. **ML platform generation path**
   - Add JSON profile/setup/manifest metadata.
   - Add Jinja2 templates for `docker-compose.yml`, `.env`, `manifest.json`, `README.md`, `runbook.md`, and scripts.
   - Ensure dry-run reports planned files without writing output.
   - Ensure force generation can overwrite generated output inside the project and refuses unsafe output paths.

4. **Security path**
   - Keep localhost as the default access mode.
   - Reject LAN generation unless `--auth bearer-token` and `--lan-allowlist` are both supplied.
   - Record auth/access metadata in generated manifests without requiring Docker daemon during tests.

5. **Validation path**
   - Validate generated directories by checking manifest consistency and required files.
   - Do not require Docker daemon for test validation.
   - Add stdlib `unittest` coverage for listing, dry-run no-write, localhost generation/validation, and unsafe LAN rejection.

## TDD sequence

1. Write CLI behavior tests first in `tests/test_cli.py`.
2. Verify tests fail because `ai_server_generator` is missing.
3. Implement the minimal package, metadata loaders, renderer, templates, and validators required to pass.
4. Re-run tests and required gate commands.
5. Update `CHANGELOG.md`, generated sample output, and plan checkboxes after verification.

## Acceptance criteria

- `python3 -m unittest` passes.
- All task gates in `.pm-harness/plans/TASK-0003.plan.md` pass, including the required non-zero unsafe LAN dry-run command.
- `generated/chat-medium-localhost` contains the generated chat-localhost-medium workspace.
- `CHANGELOG.md` has an Unreleased entry referencing TASK-0003.
