"""private_split.py — optional engine module `private-split` (CORE-SPEC §8.2).

Private-outer / public-inner layout: a private outer repository contains the
public inner repository as an ignored subdirectory; every AI/dev artifact
lives in the outer. Zero symlinks. Ported from pm-harness HARNESS-SPEC §8.1
and parametrized by the pack (root_dir, project state file, bridge marker).

Enabled per pack via specpack.json `engine_modules: ["private-split"]`.
Registers: the `private-split {init,migrate-from-personal,validate,status}`
subcommands and the declared-layout postcondition check in `validate`
(layout declared ⇒ split manifest present and the inner is a git repo).
"""
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

import harness_core as core

SPLIT_MANIFEST_NAME = "split.manifest.json"
LAYOUT_NAME = "private-outer-v1"

# Legacy personal-root layout (migration source only).
PERSONAL_CONFIG_NAME = "personal-config.json"
ISOLATED_PATHS = ["state", "memory", "ceremonies", "escalations",
                  "model-router.json", "executive-summary.md"]

DEFAULT_MOVE_DIRS_EXTRA = [".claude", ".opencode", ".cursor",
                           ".omo", ".slim", "docs", "audits", "notes"]
DEFAULT_MOVE_FILES = ["AGENTS.md", "CLAUDE.md"]
DEFAULT_MOVE_GLOBS = ["*.ai.md", "*.claude.md"]
DEFAULT_KEEP_IN_INNER_FILES = ["AGENTS.md"]
DEFAULT_NEVER_TOUCH = [
    ".git", "node_modules", "dist", "build", "target",
    "__pycache__", ".venv", "venv", ".idea", ".vscode",
]

BRIDGE_STUB = """{start}
## {name} (private-outer layout)

This project's AI/dev tooling lives one directory up, in the private
outer repository. Open your agent platform from the parent directory
(`../`) to activate the harness and its adapters. The runtime spec
is at `../{root_dir}/{spec_file}`.
{end}
"""

OUTER_GITIGNORE_HEADER = """# {name} — private outer repository
# The inner directory below is a separate public repository. Do not
# track it here; commit product-code changes in the inner repo instead.
"""


def root_dir():
    return core.CFG["root_dir"]


def project_json():
    return core.CFG["project_json"]


def bridge_markers():
    tag = f"{core.CFG['pack_id'].upper()}-HARNESS-BRIDGE"
    return f"<!-- {tag}:START -->", f"<!-- {tag}:END -->"


def personal_dir_name():
    return f"{root_dir()}-personal"


load_json = core.load_json
save_json = core.save_json
die = core.die


def personal_config_path(root):
    return os.path.join(root, PERSONAL_CONFIG_NAME)


def project_root_of(root):
    return os.path.dirname(root)


def resolve_personal_root(root, personal_root):
    """Return absolute personal root from user-supplied path (rel or abs)."""
    if os.path.isabs(personal_root):
        return os.path.normpath(personal_root)
    return os.path.normpath(os.path.join(project_root_of(root), personal_root))


def default_split_manifest(inner_dir):
    return {
        "$schema": "https://pm-harness.dev/schemas/split-manifest.v1.json",
        "version": 1,
        "layout": LAYOUT_NAME,
        "inner_dir": inner_dir,
        "move_to_outer": {
            "dirs": [root_dir()] + list(DEFAULT_MOVE_DIRS_EXTRA),
            "files": list(DEFAULT_MOVE_FILES),
            "globs": list(DEFAULT_MOVE_GLOBS),
        },
        "keep_in_inner": {
            "files": list(DEFAULT_KEEP_IN_INNER_FILES),
            "note": ("Bridge stub with harness bridge markers. "
                     "Not the original — the original was moved to the outer."),
        },
        "never_touch": list(DEFAULT_NEVER_TOUCH),
        "docs_policy": {
            "on_fresh_install": "create_in_outer",
            "on_migration": "keep_in_outer_ask_which_move_to_inner",
        },
    }


def validate_split_manifest(m):
    """Return a list of error strings; empty list means valid."""
    errs = []
    if not isinstance(m, dict):
        return ["manifest must be a JSON object"]
    if m.get("version") != 1:
        errs.append("version must be 1")
    if m.get("layout") != LAYOUT_NAME:
        errs.append(f"layout must be {LAYOUT_NAME!r}")
    inner = m.get("inner_dir")
    if (not isinstance(inner, str) or not inner
            or "/" in inner or "\\" in inner
            or inner in ("", ".", "..")):
        errs.append("inner_dir must be a non-empty simple directory name")
    move = m.get("move_to_outer")
    if not isinstance(move, dict):
        errs.append("move_to_outer must be an object")
    else:
        for key in ("dirs", "files", "globs"):
            v = move.get(key)
            if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
                errs.append(f"move_to_outer.{key} must be a list of strings")
    keep = m.get("keep_in_inner")
    if not isinstance(keep, dict):
        errs.append("keep_in_inner must be an object")
    elif not isinstance(keep.get("files"), list):
        errs.append("keep_in_inner.files must be a list")
    if not isinstance(m.get("never_touch"), list):
        errs.append("never_touch must be a list")
    policy = m.get("docs_policy")
    if not isinstance(policy, dict):
        errs.append("docs_policy must be an object")
    else:
        fi = policy.get("on_fresh_install")
        mi = policy.get("on_migration")
        if fi not in ("create_in_outer", "skip"):
            errs.append("docs_policy.on_fresh_install must be one of: create_in_outer, skip")
        if mi not in ("keep_in_outer_ask_which_move_to_inner",
                      "keep_in_outer", "move_all_to_inner"):
            errs.append("docs_policy.on_migration must be one of: "
                        "keep_in_outer_ask_which_move_to_inner, keep_in_outer, move_all_to_inner")
    return errs


class OpLog:
    """Append-only rollback log for filesystem operations.

    Each destructive op is recorded before execution. On failure, rollback()
    walks the log in reverse and undoes each op.
    """

    def __init__(self, path):
        self.path = path
        self.ops = []

    def record(self, kind, **payload):
        self.ops.append({"kind": kind, **payload})
        self._flush()

    def _flush(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.ops, f, indent=2)
        except OSError:
            # best-effort: rollback can still work in-memory
            pass

    def rollback(self):
        errors = []
        for op in reversed(self.ops):
            try:
                self._undo(op)
            except Exception as e:  # noqa: BLE001
                errors.append(f"undo {op.get('kind')} on {op.get('path') or op.get('dst')}: {e}")
        return errors

    def _undo(self, op):
        kind = op["kind"]
        if kind == "move":
            if os.path.exists(op["dst"]) and not os.path.exists(op["src"]):
                os.makedirs(os.path.dirname(op["src"]) or ".", exist_ok=True)
                os.rename(op["dst"], op["src"])
        elif kind == "mkdir":
            # only remove if we created it AND it is empty
            if os.path.isdir(op["path"]) and not os.listdir(op["path"]):
                os.rmdir(op["path"])
        elif kind == "write":
            if os.path.isfile(op["path"]):
                os.remove(op["path"])


def _iter_move_candidates(project_root, manifest):
    """Yield (source_path_relative_to_project, kind) for every path the
    manifest wants moved from inner to outer, in a deterministic order."""
    never = set(manifest.get("never_touch", []))
    seen = set()
    move = manifest["move_to_outer"]
    for d in move.get("dirs", []):
        if d in never or d in seen:
            continue
        p = os.path.join(project_root, d)
        if os.path.isdir(p) and not os.path.islink(p):
            seen.add(d)
            yield d, "dir"
    for f in move.get("files", []):
        if f in never or f in seen:
            continue
        p = os.path.join(project_root, f)
        if os.path.isfile(p):
            seen.add(f)
            yield f, "file"
    for pattern in move.get("globs", []):
        for p in sorted(glob.glob(os.path.join(project_root, pattern))):
            rel = os.path.relpath(p, project_root)
            if rel in never or rel in seen:
                continue
            if os.path.isfile(p):
                seen.add(rel)
                yield rel, "glob"


def _detect_layout(root):
    """Return one of: 'private-outer-v1', 'personal', 'fresh'."""
    pj = os.path.join(root, project_json())
    if os.path.isfile(pj):
        try:
            h = load_json(pj)
            if h.get("layout") == LAYOUT_NAME:
                return LAYOUT_NAME
        except Exception:  # noqa: BLE001
            pass
    if os.path.isfile(personal_config_path(root)):
        return "personal"
    return "fresh"


def _read_manifest_or_default(root, inner_dir):
    path = os.path.join(root, SPLIT_MANIFEST_NAME)
    if os.path.isfile(path):
        m = load_json(path)
        errs = validate_split_manifest(m)
        if errs:
            die("split.manifest.json is invalid: " + "; ".join(errs))
        return m, True
    return default_split_manifest(inner_dir), False


def _outer_gitignore_body(inner_dir):
    return (OUTER_GITIGNORE_HEADER.format(name=core.CFG["name"])
            + f"/{inner_dir}/\n\n"
            + "# Editors / OS\n.DS_Store\n.idea/\n.vscode/\n\n"
            + "# Python bytecode cache (the CLI is stdlib but produces .pyc)\n"
            + "__pycache__/\n*.py[cod]\n\n"
            + "# Secrets — never committed even in the private outer\n"
            + ".env\n.env.*\n*.pem\n*.key\n")


def _bridge_content():
    start, end = bridge_markers()
    return BRIDGE_STUB.format(start=start, end=end, name=core.CFG["name"],
                              root_dir=root_dir(),
                              spec_file=core.CFG["spec_file"])


def _plan_operations(project_root, outer_path, inner_name, manifest,
                     is_migration, docs_files_to_move_back=None):
    """Return a list of planned operations (dicts) without touching disk."""
    ops = []
    inner_final = os.path.join(outer_path, inner_name)
    ops.append({"kind": "mkdir", "path": outer_path,
                "desc": f"create outer directory {outer_path}"})
    ops.append({"kind": "move", "src": project_root, "dst": inner_final,
                "desc": f"move {project_root} → {inner_final}"})
    for rel, kind in _iter_move_candidates(project_root, manifest):
        src = os.path.join(inner_final, rel)
        dst = os.path.join(outer_path, rel)
        ops.append({"kind": "move", "src": src, "dst": dst,
                    "desc": f"move inner/{rel} → outer/{rel}"})
    if docs_files_to_move_back:
        for rel in docs_files_to_move_back:
            src = os.path.join(outer_path, "docs", rel)
            dst = os.path.join(inner_final, "docs", rel)
            ops.append({"kind": "move", "src": src, "dst": dst,
                        "desc": f"move outer/docs/{rel} → inner/docs/{rel} (product doc)"})
    fresh_docs_policy = manifest["docs_policy"]["on_fresh_install"]
    if not is_migration and fresh_docs_policy == "create_in_outer":
        outer_docs = os.path.join(outer_path, "docs")
        already_moves_docs = any(
            op["kind"] == "move" and os.path.basename(op["dst"]) == "docs"
            and op["dst"] == outer_docs for op in ops
        )
        if not already_moves_docs:
            ops.append({"kind": "mkdir", "path": outer_docs,
                        "desc": "create outer/docs/"})
    ops.append({"kind": "write", "path": os.path.join(outer_path, ".gitignore"),
                "desc": "write outer/.gitignore",
                "content": _outer_gitignore_body(inner_name)})
    ops.append({"kind": "write", "path": os.path.join(inner_final, "AGENTS.md"),
                "desc": "write inner/AGENTS.md bridge stub",
                "content": _bridge_content()})
    ops.append({"kind": "write",
                "path": os.path.join(outer_path, root_dir(), SPLIT_MANIFEST_NAME),
                "desc": f"write outer/{root_dir()}/{SPLIT_MANIFEST_NAME}",
                "content": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"})
    ops.append({"kind": "update-project-json",
                "path": os.path.join(outer_path, root_dir(), project_json()),
                "desc": f"annotate outer/{root_dir()}/{project_json()} with layout"})
    ops.append({"kind": "git-init", "path": outer_path,
                "desc": "git init in outer (best-effort)"})
    return ops


def _print_plan(ops):
    print("=" * 60)
    print(f"{core.CFG['name']} — private-outer split plan")
    print("=" * 60)
    for i, op in enumerate(ops, 1):
        print(f"  {i:2d}. {op['desc']}")
    print("=" * 60)


def _confirm(prompt):
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def _execute_plan(ops, oplog):
    """Execute planned ops in order. Any failure raises and triggers rollback."""
    for op in ops:
        kind = op["kind"]
        if kind == "mkdir":
            path = op["path"]
            if os.path.isdir(path):
                continue
            os.makedirs(path)
            oplog.record("mkdir", path=path)
        elif kind == "move":
            src, dst = op["src"], op["dst"]
            if not os.path.exists(src):
                continue
            if os.path.exists(dst):
                raise RuntimeError(f"destination exists: {dst}")
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            os.rename(src, dst)
            oplog.record("move", src=src, dst=dst)
        elif kind == "write":
            path = op["path"]
            if os.path.isfile(path):
                # Idempotent: never overwrite an existing file.
                continue
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write(op["content"])
            oplog.record("write", path=path)
        elif kind == "update-project-json":
            path = op["path"]
            if not os.path.isfile(path):
                continue
            data = load_json(path)
            data["layout"] = LAYOUT_NAME
            save_json(path, data)
        elif kind == "git-init":
            path = op["path"]
            git_dir = os.path.join(path, ".git")
            if os.path.isdir(git_dir):
                continue
            import subprocess
            try:
                r = subprocess.run(["git", "init", "--quiet", path],
                                   capture_output=True, timeout=15)
                if r.returncode != 0:
                    print(f"note: git init in {path} returned {r.returncode}: "
                          f"{r.stderr.decode('utf-8', 'replace')}", file=sys.stderr)
            except (FileNotFoundError, Exception) as e:  # noqa: BLE001
                print(f"note: could not git init {path}: {e} "
                      "(run `git init` manually)", file=sys.stderr)
        else:
            raise RuntimeError(f"unknown op kind: {kind}")


def _list_docs_files(docs_dir):
    """Return relative file paths under docs_dir, sorted, ignoring dot files."""
    out = []
    for base, dirs, files in os.walk(docs_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in sorted(files):
            if f.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(base, f), docs_dir)
            out.append(rel)
    return sorted(out)


def _interactive_docs_pick(project_root, assume_all_dev):
    """Return the list of files under docs/ that should be moved back to inner."""
    docs_dir = os.path.join(project_root, "docs")
    if not os.path.isdir(docs_dir):
        return []
    files = _list_docs_files(docs_dir)
    if not files:
        return []
    if assume_all_dev or not sys.stdin.isatty():
        print(f"note: docs/ has {len(files)} file(s); keeping all in outer "
              "(pass --interactive-docs to choose)", file=sys.stderr)
        return []
    print(f"\ndocs/ contains {len(files)} file(s). By default they all move "
          "to the private outer.")
    print("List product-doc paths (space or comma separated) to keep in inner/docs/.")
    print("Press Enter to keep everything in outer.")
    for i, f in enumerate(files, 1):
        print(f"  {i:3d}. {f}")
    try:
        ans = input("> ").strip()
    except EOFError:
        return []
    if not ans:
        return []
    tokens = [t.strip() for t in re.split(r"[,\s]+", ans) if t.strip()]
    picks = set()
    for tok in tokens:
        if tok.isdigit():
            idx = int(tok) - 1
            if 0 <= idx < len(files):
                picks.add(files[idx])
        elif tok in files:
            picks.add(tok)
    return sorted(picks)


def private_split_init(root, args):
    """Convert a public project into the private-outer / public-inner layout."""
    project_root = os.path.abspath(project_root_of(root))
    parent = os.path.dirname(project_root)
    inner_name = args.inner_name or os.path.basename(project_root)
    outer_name = args.outer_name or f"{inner_name}-ai-dev"
    outer_path = os.path.abspath(os.path.join(parent, outer_name))

    if not inner_name or "/" in inner_name or inner_name in ("", ".", ".."):
        die(f"invalid inner name: {inner_name!r}")
    if not outer_name or "/" in outer_name or outer_name in ("", ".", ".."):
        die(f"invalid outer name: {outer_name!r}")
    if os.path.abspath(outer_path) == project_root:
        die("outer and inner must differ")
    if outer_path.startswith(project_root + os.sep):
        die("outer must not live inside the project")

    layout = _detect_layout(root)
    if layout == LAYOUT_NAME:
        print(json.dumps({"layout": LAYOUT_NAME, "action": "no-op",
                          "reason": "already in private-outer-v1 layout"},
                         ensure_ascii=False))
        return
    if layout == "personal":
        die("this project uses the legacy personal-config.json layout; run "
            f"`{core.cli()} private-split migrate-from-personal` instead")

    if os.path.exists(outer_path):
        die(f"outer path already exists: {outer_path} (choose --outer-name or "
            "remove it)")

    manifest, from_disk = _read_manifest_or_default(root, inner_name)
    if from_disk and args.inner_name and manifest["inner_dir"] != args.inner_name:
        die(f"manifest.inner_dir={manifest['inner_dir']!r} conflicts with "
            f"--inner-name={args.inner_name!r}; edit the manifest or drop the flag")
    manifest["inner_dir"] = inner_name

    is_migration = os.path.isdir(os.path.join(project_root, "docs"))

    docs_to_move_back = []
    if is_migration and args.interactive_docs and not args.assume_all_dev_docs:
        docs_to_move_back = _interactive_docs_pick(
            project_root, assume_all_dev=False)

    manifest_path = os.path.join(root, SPLIT_MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        save_json(manifest_path, manifest)
        wrote_manifest_pre = True
    else:
        wrote_manifest_pre = False

    ops = _plan_operations(project_root, outer_path, inner_name, manifest,
                           is_migration=is_migration,
                           docs_files_to_move_back=docs_to_move_back)

    if args.dry_run:
        _print_plan(ops)
        print("(dry-run: no changes applied)")
        return

    if not args.yes:
        _print_plan(ops)
        if not _confirm("\nProceed? [y/N]: "):
            print("aborted")
            if wrote_manifest_pre:
                os.remove(manifest_path)
            return

    oplog_path = os.path.join(
        os.environ.get("TMPDIR", "/tmp"),
        f"harness-private-split-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log")
    oplog = OpLog(oplog_path)

    # chdir to a stable location BEFORE renaming the project directory,
    # otherwise our own CWD gets orphaned.
    original_cwd = os.getcwd()
    stable_cwd = parent
    try:
        os.chdir(stable_cwd)
    except OSError as e:
        die(f"cannot chdir to parent {stable_cwd}: {e}")

    try:
        _execute_plan(ops, oplog)
    except Exception as e:  # noqa: BLE001
        undo_errors = oplog.rollback()
        os.chdir(original_cwd if os.path.isdir(original_cwd) else stable_cwd)
        detail = str(e)
        if undo_errors:
            detail += " | rollback issues: " + "; ".join(undo_errors)
        die(f"private-split init failed: {detail} (oplog at {oplog_path})")

    new_inner = os.path.join(outer_path, inner_name)
    try:
        os.chdir(new_inner)
    except OSError:
        os.chdir(outer_path)

    print(json.dumps({
        "layout": LAYOUT_NAME,
        "outer_path": outer_path,
        "inner_path": new_inner,
        "manifest": os.path.join(outer_path, root_dir(), SPLIT_MANIFEST_NAME),
        "oplog": oplog_path,
        "ops_applied": len(oplog.ops),
        "next_step": (f"cd {outer_path} && git add -A && git commit -m 'initial'; "
                      "open your agent platform from the outer directory"),
    }, ensure_ascii=False))


def private_split_migrate_from_personal(root, args):
    """Convert a legacy personal-config.json install into the outer layout."""
    pcfg_path = personal_config_path(root)
    if not os.path.isfile(pcfg_path):
        if _detect_layout(root) == LAYOUT_NAME:
            print(json.dumps({"layout": LAYOUT_NAME, "action": "no-op",
                              "reason": "already in private-outer-v1 layout"},
                             ensure_ascii=False))
            return
        die("no personal-config.json found; nothing to migrate")

    pcfg = load_json(pcfg_path)
    personal_root_rel = pcfg.get("personal_root")
    if not personal_root_rel:
        die("personal-config.json is missing personal_root")
    personal_root = resolve_personal_root(root, personal_root_rel)
    personal_harness = os.path.join(personal_root, personal_dir_name())

    if not os.path.isdir(personal_harness):
        die(f"personal root not found at {personal_harness}")

    ops = []
    for name in ISOLATED_PATHS:
        link = os.path.join(root, name)
        target = os.path.join(personal_harness, name)
        if os.path.islink(link):
            if os.path.exists(target):
                ops.append({"kind": "unlink-and-rehydrate", "link": link,
                            "source": target,
                            "desc": f"replace symlink {link} with real content from {target}"})
            else:
                ops.append({"kind": "unlink-broken", "link": link,
                            "desc": f"remove broken symlink {link} "
                                    f"(target missing: {target})"})
        elif os.path.exists(link):
            ops.append({"kind": "note",
                        "desc": f"{link} is not a symlink; leaving as-is"})
    ops.append({"kind": "remove-personal-config",
                "path": pcfg_path,
                "desc": f"remove {pcfg_path}"})

    if args.dry_run:
        print("=" * 60)
        print(f"{core.CFG['name']} — migrate-from-personal (phase 1: rehydrate)")
        print("=" * 60)
        for i, op in enumerate(ops, 1):
            print(f"  {i:2d}. {op['desc']}")
        project_root = os.path.abspath(project_root_of(root))
        parent = os.path.dirname(project_root)
        inner_name = args.inner_name or os.path.basename(project_root)
        outer_name = args.outer_name or f"{inner_name}-ai-dev"
        outer_path = os.path.abspath(os.path.join(parent, outer_name))
        manifest, _ = _read_manifest_or_default(root, inner_name)
        manifest["inner_dir"] = inner_name
        is_migration = os.path.isdir(os.path.join(project_root, "docs"))
        phase2_ops = _plan_operations(
            project_root, outer_path, inner_name, manifest,
            is_migration=is_migration, docs_files_to_move_back=None)
        print()
        print("=" * 60)
        print(f"{core.CFG['name']} — migrate-from-personal (phase 2: private-split init)")
        print("=" * 60)
        for i, op in enumerate(phase2_ops, 1):
            print(f"  {i:2d}. {op['desc']}")
        print("(dry-run: no changes applied)")
        return

    if not args.yes:
        print("=" * 60)
        print(f"{core.CFG['name']} — migrate-from-personal (phase 1: rehydrate)")
        print("=" * 60)
        for i, op in enumerate(ops, 1):
            print(f"  {i:2d}. {op['desc']}")
        print("(after phase 1, phase 2 = private-split init runs)")
        if not _confirm("\nProceed with both phases? [y/N]: "):
            print("aborted")
            return

    for op in ops:
        kind = op["kind"]
        if kind == "unlink-and-rehydrate":
            link, source = op["link"], op["source"]
            if not os.path.exists(source):
                die(f"personal source missing: {source}")
            os.remove(link)
            os.rename(source, link)
        elif kind == "unlink-broken":
            link = op["link"]
            if os.path.islink(link):
                os.remove(link)
        elif kind == "remove-personal-config":
            if os.path.isfile(op["path"]):
                os.remove(op["path"])
        # 'note' ops are informational only.

    try:
        if os.path.isdir(personal_harness) and not os.listdir(personal_harness):
            os.rmdir(personal_harness)
    except OSError:
        pass
    try:
        if (os.path.isdir(personal_root) and
                set(os.listdir(personal_root)) <= {".gitignore", ".git"}):
            if ".git" not in os.listdir(personal_root):
                for f in os.listdir(personal_root):
                    os.remove(os.path.join(personal_root, f))
                os.rmdir(personal_root)
    except OSError:
        pass

    print("phase 1 complete; entering phase 2 (private-split init)…", file=sys.stderr)
    private_split_init(root, args)


def private_split_validate(root, args):
    """Read-only verification that the current layout matches the manifest."""
    project_root = project_root_of(root)
    manifest_path = os.path.join(root, SPLIT_MANIFEST_NAME)
    errors, warnings, info = [], [], []
    start, end = bridge_markers()

    if not os.path.isfile(manifest_path):
        errors.append({"check": "manifest-missing",
                       "detail": f"no {SPLIT_MANIFEST_NAME} in {root}"})
    else:
        try:
            m = load_json(manifest_path)
        except Exception as e:  # noqa: BLE001
            errors.append({"check": "manifest-parse", "detail": str(e)})
            m = None
        if m is not None:
            errs = validate_split_manifest(m)
            for e in errs:
                errors.append({"check": "manifest-schema", "detail": e})
            if not errs:
                outer_path = os.path.abspath(project_root)
                inner_path = os.path.join(outer_path, m["inner_dir"])
                if not os.path.isdir(inner_path):
                    errors.append({"check": "inner-missing",
                                   "detail": f"expected inner at {inner_path}"})
                else:
                    gi = os.path.join(outer_path, ".gitignore")
                    if not os.path.isfile(gi):
                        warnings.append({"check": "outer-gitignore",
                                         "detail": "no .gitignore in outer"})
                    else:
                        with open(gi) as f:
                            body = f.read()
                        if f"/{m['inner_dir']}/" not in body:
                            errors.append({"check": "outer-gitignore",
                                           "detail": f"missing '/{m['inner_dir']}/' entry"})
                    bridge = os.path.join(inner_path, "AGENTS.md")
                    if not os.path.isfile(bridge):
                        errors.append({"check": "bridge-missing",
                                       "detail": f"no AGENTS.md in {inner_path}"})
                    else:
                        with open(bridge) as f:
                            content = f.read()
                        if start not in content or end not in content:
                            errors.append({"check": "bridge-markers",
                                           "detail": "bridge stub lacks harness bridge markers"})
                    for d in m["move_to_outer"]["dirs"]:
                        in_outer = os.path.isdir(os.path.join(outer_path, d))
                        in_inner = os.path.isdir(os.path.join(inner_path, d))
                        if in_inner:
                            errors.append({"check": "artifact-in-inner",
                                           "detail": f"{d} exists in inner "
                                                     "(should be in outer)"})
                        elif not in_outer and d in (root_dir(),):
                            errors.append({"check": "artifact-missing",
                                           "detail": f"{d} missing from outer"})
                    for base in (outer_path, inner_path):
                        for entry in os.listdir(base):
                            p = os.path.join(base, entry)
                            if os.path.islink(p):
                                errors.append({"check": "no-symlinks",
                                               "detail": f"symlink at {p}"})
                    pj = os.path.join(root, project_json())
                    if os.path.isfile(pj):
                        try:
                            hjd = load_json(pj)
                            if hjd.get("layout") != LAYOUT_NAME:
                                warnings.append({"check": "project-layout-field",
                                                 "detail": f"{project_json()}.layout != "
                                                           + LAYOUT_NAME})
                        except Exception:  # noqa: BLE001
                            pass

    print(json.dumps({"errors": errors, "warnings": warnings, "info": info},
                     ensure_ascii=False, indent=2))
    sys.exit(1 if errors else 0)


def private_split_status(root, args):
    """Print current layout, paths, and manifest checksum."""
    project_root = project_root_of(root)
    manifest_path = os.path.join(root, SPLIT_MANIFEST_NAME)
    layout = _detect_layout(root)
    out = {
        "layout": layout,
        "harness_root": root,
        "project_root": project_root,
        "manifest_present": os.path.isfile(manifest_path),
    }
    if out["manifest_present"]:
        with open(manifest_path, "rb") as f:
            out["manifest_sha256"] = hashlib.sha256(f.read()).hexdigest()
        try:
            m = load_json(manifest_path)
            out["inner_dir"] = m.get("inner_dir")
            out["outer_path"] = os.path.abspath(project_root)
            out["inner_path"] = os.path.abspath(
                os.path.join(project_root, m.get("inner_dir", "")))
        except Exception as e:  # noqa: BLE001
            out["manifest_error"] = str(e)
    print(json.dumps(out, indent=2, ensure_ascii=False))


# ------------------------------------------------------ validate postcondition
def _split_postcondition(root, ctx):
    """Declared-layout postcondition (CORE-SPEC §8.2 / STD-ARN-01):
    private-outer-v1 means TWO repos — the inner must be a git repository."""
    errors, warnings = [], []
    project = ctx.get("project") or {}
    if project.get("layout") != LAYOUT_NAME:
        return errors, warnings
    sm = os.path.join(root, SPLIT_MANIFEST_NAME)
    inner = None
    if os.path.isfile(sm):
        try:
            inner = load_json(sm).get("inner_dir")
        except Exception as e:  # noqa: BLE001
            errors.append({"check": "split-manifest-parse",
                           "unit": SPLIT_MANIFEST_NAME, "detail": str(e)})
    else:
        errors.append({"check": "split-postcondition",
                       "unit": project_json(),
                       "detail": f"layout={LAYOUT_NAME} but no "
                                 f"{SPLIT_MANIFEST_NAME}"})
    if inner:
        inner_git = os.path.join(os.path.dirname(root), inner, ".git")
        if not os.path.exists(inner_git):
            errors.append({"check": "split-postcondition", "unit": inner,
                           "detail": f"inner repo '{inner}/' has no .git — "
                                     f"{LAYOUT_NAME} requires two repos "
                                     "(git init the inner)"})
    return errors, warnings


# ------------------------------------------------------------------ register
def _build_commands(sub):
    ps = sub.add_parser(
        "private-split",
        help="Private-outer / public-inner layout: outer contains inner "
             "(public) as ignored subdirectory.",
    ).add_subparsers(dest="sub", required=True)
    for name, fn, doc in (
        ("init", private_split_init,
         "Convert a public project into the private-outer layout (moves the "
         "project into a new outer sibling directory)."),
        ("migrate-from-personal", private_split_migrate_from_personal,
         "Convert a legacy personal-config.json install into the "
         "private-outer layout."),
        ("validate", private_split_validate,
         "Read-only: verify the current layout matches split.manifest.json."),
        ("status", private_split_status,
         "Print current layout, outer/inner paths, and manifest checksum."),
    ):
        p = ps.add_parser(name, help=doc)
        if name in ("init", "migrate-from-personal"):
            p.add_argument("--outer-name",
                           help="Name of the outer directory (default: <inner>-ai-dev).")
            p.add_argument("--inner-name",
                           help="Name of the inner directory (default: current project's basename).")
            p.add_argument("--dry-run", action="store_true",
                           help="Print the plan without touching disk.")
            p.add_argument("--yes", action="store_true",
                           help="Skip the confirmation prompt.")
            p.add_argument("--interactive-docs", action="store_true",
                           help="Prompt to choose which docs/ files stay in inner (migration only).")
            p.add_argument("--assume-all-dev-docs", action="store_true",
                           help="Assume all docs/ files are dev docs (default; opposite of --interactive-docs).")
        p.set_defaults(fn=fn)


def register(core_mod):
    core_mod.register_command(_build_commands)
    core_mod.register_validate_check(_split_postcondition)
