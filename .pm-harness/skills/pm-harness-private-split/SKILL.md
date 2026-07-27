---
name: pm-harness-private-split
description: "Converts an installed PM Harness project into the private-outer / public-inner layout. The private outer repo contains the public project as an ignored subdirectory, keeping .pm-harness/, .claude/, .opencode/, docs/, audits/ and other AI/dev artifacts in the private outer. Guides the Director through detect → dry-run → confirm → execute → validate. Triggers: 'split my project into public and private', 'move the harness to a private outer repo', 'private-outer layout', 'pm harness private split'."
allowed-tools:
  - "bash"
  - "read"
  - "write"
  - "glob"
---

# pm-harness-private-split — inverted-layout orchestrator

You are the interactive orchestrator for the private-outer / public-inner
split. You **never touch the filesystem directly** — every mutation goes
through the CLI at `.pm-harness/bin/harness.py private-split ...`. Your
job is to detect state, present a clear plan, get confirmation, execute,
and audit.

Contracts:

- Design and invariants: `docs/plans/private-outer-split.md`.
- Manifest schema: `.pm-harness/schemas/split-manifest.v1.json` (bundled with
  the installer templates at `templates/v1/schemas/split-manifest.v1.json`).
- Enforcement CLI: `.pm-harness/bin/harness.py private-split
  {init,migrate-from-personal,validate,status}`.

## Absolute prohibitions

- **NEVER** move, rename, or delete files yourself — always call the CLI.
- **NEVER** proceed to execute without the Director's explicit confirmation
  (dry-run first, then `--yes`).
- **NEVER** create symlinks. The layout is symlink-free by design.
- **NEVER** touch the inner's `.git/` or product source directories other
  than through the manifest-controlled bridge stub.

## Triggers

- "split my project into public and private"
- "move the harness to a private outer repository"
- "private-outer layout"
- "instala el arnés en modo privado / con outer privado"
- "pm harness private split"

## Inputs

1. `target_root`: the current project directory (default `.`).
2. `outer_name` (optional): name of the outer directory
   (default `<target_root basename>-ai-dev`).
3. `inner_name` (optional): name of the inner (default = current basename).
4. `interactive_docs` (optional flag): whether to prompt file-by-file to
   decide which items under `docs/` belong to the inner (product docs) vs.
   the outer (dev docs). Off by default; when off, `docs/` moves entirely
   to the outer.

## Step 1 — Detect current layout

Call:

```bash
python3 .pm-harness/bin/harness.py private-split status
```

The output includes a `layout` field. Branch:

- `"private-outer-v1"` → already migrated. Print the status block and stop.
- `"personal"` → the project uses the legacy `personal-config.json` layout.
  You **must** use `migrate-from-personal`, not `init`. Continue to Step 2
  with that flag.
- `"fresh"` → the project is a fresh public repo with the harness
  installed. Use `init`. Continue to Step 2.
- Anything else → report and stop; ask the Director.

## Step 2 — Dry-run preview

Run the appropriate CLI with `--dry-run`:

- Fresh: `python3 .pm-harness/bin/harness.py private-split init --dry-run`
- Legacy: `python3 .pm-harness/bin/harness.py private-split migrate-from-personal --dry-run`

Optional flags to pass through:

- `--outer-name <name>` — override the default outer name.
- `--inner-name <name>` — override the default inner name (rare).
- `--interactive-docs` — enable the docs/ file-by-file picker during
  execute. It only fires when the project has an existing `docs/`.

Present the plan to the Director verbatim. Do not summarize away the
operation list.

## Step 3 — Get explicit confirmation

Ask the Director: "Proceed with the plan above? (yes / no)". Do NOT invent
consent. If they say no, stop.

## Step 4 — Execute

Re-run the same command WITHOUT `--dry-run`, adding `--yes`:

- Fresh: `python3 .pm-harness/bin/harness.py private-split init --yes [extra flags]`
- Legacy: `python3 .pm-harness/bin/harness.py private-split migrate-from-personal --yes [extra flags]`

The CLI:

1. Writes an op-log to `$TMPDIR/pm-harness-private-split-<ts>.log` before
   any mutation.
2. Chdir's to the parent, renames the project into `<outer>/<inner>/`,
   then moves artifacts per manifest.
3. Writes `<outer>/.gitignore`, `<outer>/.pm-harness/split.manifest.json`,
   `<outer>/<inner>/AGENTS.md` (bridge stub), stamps
   `<outer>/.pm-harness/harness.json.layout`.
4. `git init`s the outer (best-effort).
5. On any failure, rolls back and exits non-zero — the CLI does **not**
   leave a half-migrated state without a clear error message pointing at
   the op-log.

Report the CLI's JSON summary block verbatim.

## Step 5 — Post-migration audit

From inside the outer directory:

```bash
python3 .pm-harness/bin/harness.py private-split validate
```

Success = exit 0 with `errors: []`. If any error appears, surface it to
the Director and stop; do not attempt to "fix" it yourself.

Then run the end-to-end audit script (if available in the source repo of
the harness generator):

```bash
python3 scripts/test-private-split.py
```

This is a self-contained scenario runner that materializes fresh fake
projects in temp dirs and verifies every invariant. It is **not** required
for user projects but is a strong signal in the source repo.

## Step 6 — Tell the Director what changed

Emit a final block with:

- The outer path and inner path.
- The location of the manifest and the op-log.
- Two next-step commands they should run themselves:

```bash
cd <outer>
git add -A && git commit -m "PM Harness private-outer split (initial)"
# push to a private remote
git remote add origin <private-remote>
git push -u origin main
```

Remind them: from now on they should open OpenCode / Claude Code at the
outer root, not the inner.

## QA Scenarios

### Happy path — fresh public project

**Input**: `.pm-harness/` installed, no `personal-config.json`.
**Expected**: `status` reports `fresh`; dry-run plan lists ~10 ops;
confirmation prompt; execute renames project into outer/inner and moves
artifacts; validate exits 0. Final report includes outer, inner, manifest,
op-log paths.
**Verify**: from the outer, `test -f .pm-harness/split.manifest.json &&
test -d <inner> && grep -q PM-HARNESS-BRIDGE <inner>/AGENTS.md && echo OK`.
**Evidence**: CLI JSON summary + validate report block.

### Happy path — legacy personal-config install

**Input**: `.pm-harness/personal-config.json` present, `state/`, `memory/`,
`model-router.json`, `executive-summary.md` are symlinks into
`<personal_root>/.pm-harness-personal/`.
**Expected**: `status` reports `personal`; `migrate-from-personal` runs
phase 1 (undo symlinks, delete personal-config.json) then phase 2
(private-split init). Final layout is `private-outer-v1` with no symlinks.
**Verify**: `for f in state memory model-router.json executive-summary.md; do
test -e "<outer>/.pm-harness/$f" && ! test -L "<outer>/.pm-harness/$f"; done`.
**Evidence**: CLI JSON summary + validate report block.

### Idempotence

**Input**: run the skill a second time on an already-migrated outer.
**Expected**: `status` reports `private-outer-v1`; the skill stops in
Step 1 without proposing any ops.
**Verify**: no filesystem mtime changes; no CLI mutations.
**Evidence**: `status` block in the reply.

### Error path — outer collision

**Input**: fresh project, but `../<inner>-ai-dev/` already exists.
**Expected**: dry-run succeeds; execute fails immediately with
`already exists` and non-zero exit; the project is untouched.
**Verify**: `test -d <original-project>/src` still holds.
**Evidence**: CLI error block quoted in the reply.

### Error path — mid-flight failure

**Input**: fresh project, but the parent directory becomes read-only after
the outer is created (simulated by chmod or an intentional test failure).
**Expected**: rollback triggered by the CLI. The outer is removed (empty
dirs undone), the project artifacts return to their pre-move locations,
CLI exits non-zero with a message pointing at the op-log for forensics.
**Verify**: `diff -r <project> <backup-before-run>` reports no changes
(except a possibly-created `.pm-harness/split.manifest.json`, which is
retained across retries by design).
**Evidence**: op-log path + validate on the un-moved project.
