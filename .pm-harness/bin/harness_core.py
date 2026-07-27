#!/usr/bin/env python3
"""harness_core.py — Harness Engine core CLI library (CORE-SPEC.md).

Python 3.8+, stdlib only. Every command operates on the nearest harness root
directory upward from the current directory (override with --root).

This module is not a binary: an installed harness ships a ~10-line shim that
imports it together with the pack's extension module and calls
`harness_core.main(pack=<pack module>)`. A SpecPack customizes the engine
EXCLUSIVELY through the closed extension points of CORE-SPEC §E:

  configure(cfg_dict)                    pack identity/paths/kinds/locale
  register_command(builder)              builder(subparsers) adds subcommands
  register_gate(fn, kind=None, to=None)  fn(root, manifest, to) -> err | None
  register_validate_check(fn)            fn(root, ctx) -> (errors, warnings)
  register_validate_counter(fn)          fn(root, ctx) -> {label: count}

A pack module provides `PACK` (the configure dict) and `register(core)`
(imperative registrations). Packs never monkey-patch the engine.

Exit codes: 0 = ok, 1 = contract violation / error (detail to stderr).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ENGINE_VERSION = "2.1.0"

# --------------------------------------------------------- pack configuration
DEFAULTS = {
    "pack_id": "core",              # derives the pointer-file marker
    "name": "Harness Engine",
    "root_dir": ".harness",         # harness state directory name
    "root_agent": "orchestrator",
    "director": "director",
    "project_json": "project.json", # project state file inside root_dir
    "spec_file": "SPEC.md",         # compiled spec filename inside root_dir
    "cli_name": "harness.py",       # installed shim name (for messages)
    "kinds": {},                    # extra kind -> {prefix, kickoff_gated, planned}
    "messages": {},                 # locale overrides over MESSAGES keys
}
CFG = dict(DEFAULTS)

_COMMANDS = []          # [builder(subparsers)]
_GATES = []             # [(kind|None, to|None, fn(root, manifest, to) -> err|None)]
_VALIDATE_CHECKS = []   # [fn(root, ctx) -> (errors, warnings) | None]
_VALIDATE_COUNTERS = [] # [fn(root, ctx) -> {label: count}]


def configure(cfg):
    CFG.update(cfg or {})


def register_command(builder):
    _COMMANDS.append(builder)


def register_gate(fn, kind=None, to=None):
    _GATES.append((kind, to, fn))


def register_validate_check(fn):
    _VALIDATE_CHECKS.append(fn)


def register_validate_counter(fn):
    _VALIDATE_COUNTERS.append(fn)


def _reset_registries():
    """Test hook: forget pack registrations and configuration."""
    del _COMMANDS[:], _GATES[:], _VALIDATE_CHECKS[:], _VALIDATE_COUNTERS[:]
    CFG.clear()
    CFG.update(DEFAULTS)


def cli():
    return CFG["cli_name"]


# --------------------------------------------------------------- state tables
ALLOWED = {
    "untouched": {"touched", "cancelled"},
    "touched": {"dirty", "stale", "cancelled"},
    "dirty": {"started", "stale", "cancelled"},
    "started": {"in_progress", "stale", "cancelled"},
    "in_progress": {"blocked", "in_review", "stale", "cancelled"},
    "blocked": {"in_progress", "stale", "cancelled"},
    "in_review": {"changes_requested", "approved", "cancelled"},
    "changes_requested": {"in_progress", "cancelled"},
    "approved": {"closed", "cancelled"},
    "closed": {"reopened"},
    "reopened": {"in_progress"},
    "stale": {"in_progress", "cancelled"},
    "cancelled": set(),
}
CORE_KINDS = {
    "task": {"prefix": "TASK", "kickoff_gated": True, "planned": True},
    "ceremony": {"prefix": "CER"},
    "escalation": {"prefix": "ESC"},
    "artifact": {"prefix": "ART"},
}
STUCK_HOURS = 48
RECALL_THRESHOLD = 0.35
INDEX_COMPACT_AT = 30
PLAN_CATEGORIES = ("trivial", "routine", "complex", "strategic", "creative",
                   "research")
LIGHTWEIGHT_CATEGORIES = {"trivial", "routine"}
UNRELEASED_CATEGORIES = ["Added", "Changed", "Fixed", "Deprecated", "Removed",
                         "Security"]
SEMVER_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TOOL_NAMES = ["bash", "read", "write", "edit", "glob", "grep"]

DEFAULT_ROUTER = {
    "schema_version": 3,
    "resolution_order": ["director_overrides", "user_overrides",
                         "category_default_fuzzy", "fallback_chain",
                         "system_default"],
    "categories": {
        "trivial": {"preferred": "fast-cheap", "fallbacks": ["balanced"],
                    "reason": "renames, one-liners, formatting, status reads",
                    "effort": "low"},
        "routine": {"preferred": "balanced",
                    "fallbacks": ["fast-cheap", "frontier"],
                    "reason": "well-specified work with known patterns",
                    "effort": "medium"},
        "complex": {"preferred": "frontier", "fallbacks": ["balanced"],
                    "reason": "multi-artifact changes, tricky logic",
                    "effort": "high",
                    "min_capability": {"reasoning": "high"}},
        "strategic": {"preferred": "frontier", "fallbacks": ["balanced"],
                      "reason": "direction, trade-offs, risk",
                      "effort": "high",
                      "min_capability": {"reasoning": "high"}},
        "creative": {"preferred": "frontier", "fallbacks": ["balanced"],
                     "reason": "naming, drafting, novel design",
                     "effort": "medium",
                     "min_capability": {"reasoning": "high"}},
        "research": {"preferred": "balanced",
                     "fallbacks": ["frontier", "fast-cheap"],
                     "reason": "lookup, comparison, source synthesis",
                     "effort": "medium"},
    },
    "alias_resolution": {
        "_instruction": "Fuzzy-match: resolve an alias to the first model in available_models whose id contains (case-insensitive) any hint, in hint order.",
        "fast-cheap": ["haiku", "mini", "flash", "lite"],
        "balanced": ["sonnet", "gpt-5", "pro", "medium"],
        "frontier": ["opus", "ultra", "o1", "max", "fable"],
    },
    "available_models": [],
    "director_overrides": {},
    "user_overrides": {},
    "system_default": "session-current-model",
    "provenance_log": [],
    "effort_ladder": ["low", "medium", "high", "max"],
}


def kinds_table():
    t = dict(CORE_KINDS)
    for k, spec in (CFG.get("kinds") or {}).items():
        spec = dict(spec) if isinstance(spec, dict) else {"prefix": spec}
        # specpack.json declares prefixes with the trailing dash ("WID-");
        # internally prefixes are stored bare ("WID").
        spec["prefix"] = spec["prefix"].rstrip("-")
        t[k] = spec
    return t


def kind_prefixes():
    return {k: v["prefix"] for k, v in kinds_table().items()}


# ------------------------------------------------------------ message catalog
# Every user-facing string a pack may localize lives here; the pack's locale
# (CFG["messages"]) overrides by key (CORE-SPEC §E.5).
MESSAGES = {
    "kickoff_template": """# Kickoff — {id}: {initiative}

- **Date**: {date}
- **Created by**: {by}
- **Status**: pending Director approval

## Initiative
{initiative}

## Proposed plan
<!-- Root agent: analysis, phases, milestones. Filled during the session. -->

## Per-area specifications (draft, one subsection per applicable area)

## Director feedback
<!-- Verbatim session notes; every point answered or incorporated. -->

## Approval
<!-- Set by `{cli} kickoff approve {id} --by director`. -->
""",
    "plan_template": """---
task_ref: {id}
category: {category}
status: {status}
created: {date}
created_by: {by}
approved_by: {approved_by}
approved_at: {approved_at}
---

## Objective
{objective}

## Todos
{todos}

## Gates
<!-- Exact Gate 1 commands (standards/GATES.md) this task must pass. -->

## Risks
<!-- What could go wrong; flag irreversible steps explicitly. -->

## Open questions
<!-- Unknowns that may become an escalation (SPEC §4) or an amendment. -->

## Amendments
<!-- Append-only. Never edit or delete an existing entry. -->
""",
    "plan_objective_placeholder": "<!-- the outcome, in verifiable terms -->",
    "plan_todo_placeholder":
        "- [ ] <!-- verifiable step (AC: how to prove it is done) -->",
    "agent_body": (
        "<!-- {marker} generated by {root_agent}; "
        "safe to regenerate on roster changes -->\n\n"
        "Read `{root_dir}/teams/{path}/SKILL.md` and adopt that role "
        "verbatim. You are governed by `{root_dir}/{spec_file}`; use\n"
        "`python3 {root_dir}/bin/{cli}` for every state transition, memory "
        "write, and model resolution. All your state stays under "
        "`{root_dir}/` of this project and never leaves it (SPEC §8).\n"),
    "governed_by": " Governed by {root_dir}/{spec_file}.",
    "root_agent_desc": (
        "Root agent of this project's {name} (reports to the Director). "
        "Delegate to it when: any project work, delegation, ceremony or "
        "escalation triage. Not for: executing domain work directly — it "
        "always delegates to the manager whose declared role matches."),
    "manager_desc": (
        "{role} manager of this project's {name} (reports to {root_agent}). "
        "Delegate to it when: {when}."),
    "worker_desc": (
        "{role} of this project's {name} (worker — reports to {manager}). "
        "Delegate to it when: {when}."),
    "delegate_when_default": "work matches its declared role {role!r}",
    "manager_not_for": "executing worker tasks itself, or work owned by another team",
    "worker_not_for": "work outside its declared role, or anything requiring delegation to others",
    "kickoff_feedback_heading": "## Director feedback",
    "kickoff_feedback_required": (
        "kickoff {id} has no Director feedback recorded (SPEC §5.1): the "
        "'{heading}' section of {ceremony} is empty. Record the Director's "
        "verbatim observations there (or 'no observations'), or pass them "
        "now: `{cli} kickoff approve {id} --by director --feedback \"...\"`."),
    "kickoff_gate_blocked": (
        "kickoff gate (SPEC §5.1): no approved kickoff and autonomy is "
        "'guided'. Hold the kickoff feedback session with the Director "
        "first, then `{cli} kickoff new --initiative '<title>'` and, once "
        "the plan/specs are approved, `{cli} kickoff approve <id> --by "
        "director`. Alternatively the Director may grant full autonomy: "
        "`{cli} autonomy set autonomous --by director`."),
    "plan_gate_started": (
        "plan gate (SPEC §12.2): {id} has no approved plan — started → "
        "in_progress rejected. Write it (`{cli} plan new {id} --category "
        "<c> --by <author>`), get the owner's superior to approve it "
        "(`{cli} plan approve {id} --by {superior}`) and retry."),
    "plan_gate_review_unapproved": (
        "plan gate (SPEC §12.4): the plan of {id} is not approved — "
        "in_review rejected."),
    "plan_gate_review_todos": (
        "plan gate (SPEC §12.4): the plan of {id} has {n} unchecked "
        "todo(s) — in_review rejected. Finish them or record the deviation "
        "with `{cli} plan amend {id} ...`."),
}


def msg(key, **kw):
    return (CFG.get("messages") or {}).get(key, MESSAGES[key]).format(**kw)


# ------------------------------------------------------------------ utilities
def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_utc():
    return datetime.now(timezone.utc).date()


def find_root(explicit):
    rd = CFG["root_dir"]
    if explicit:
        p = os.path.abspath(explicit)
        if os.path.basename(p) != rd:
            p = os.path.join(p, rd)
        if os.path.isdir(p):
            return p
        die(f"no {rd} at {p}")
    d = os.getcwd()
    while True:
        cand = os.path.join(d, rd)
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            die(f"no {rd}/ found upward from cwd (use --root)")
        d = parent


def die(msg_, code=1):
    # Structured error contract: machine-parseable, so a calling agent can
    # branch instead of reading free text.
    print(json.dumps({"error": msg_, "exit_code": code}, ensure_ascii=False),
          file=sys.stderr)
    sys.exit(code)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path(root, task_id):
    return os.path.join(root, "state", f"{task_id}.json")


def project_path(root):
    return os.path.join(root, CFG["project_json"])


def next_seq(existing_ids, prefix):
    seqs = [int(m.group(1)) for i in existing_ids
            for m in [re.match(re.escape(prefix) + r"-(\d+)$", i)] if m]
    return max(seqs or [0]) + 1


# ------------------------------------------------------ kickoff / autonomy §5.1
def kickoff_gate(root, kind):
    """CORE-SPEC §5.1: no kickoff-gated unit is created before the Director
    approves the kickoff, unless full autonomy was explicitly granted."""
    if not kinds_table().get(kind, {}).get("kickoff_gated"):
        return
    try:
        c = load_json(project_path(root))
    except Exception:
        return
    if c.get("autonomy", "guided") == "autonomous":
        return
    if any(k.get("status") == "approved" for k in c.get("kickoffs", [])):
        return
    die(msg("kickoff_gate_blocked", cli=cli()))


def kickoff_new(root, args):
    cp = project_path(root)
    c = load_json(cp)
    kicks = c.setdefault("kickoffs", [])
    kid = "KICK-%04d" % (len(kicks) + 1)
    date = now_iso()[:10]
    cer = os.path.join(root, "ceremonies", f"{date}-kickoff-{kid}.md")
    os.makedirs(os.path.dirname(cer), exist_ok=True)
    if not os.path.exists(cer):
        with open(cer, "w") as f:
            f.write(msg("kickoff_template", id=kid, initiative=args.initiative,
                        date=date, by=args.by, cli=cli()))
    kicks.append({"id": kid, "initiative": args.initiative,
                  "created": now_iso(), "created_by": args.by,
                  "status": "pending", "approved_by": None,
                  "approved_at": None,
                  "ceremony": os.path.relpath(cer, root)})
    save_json(cp, c)
    print(f"{kid} created (pending Director approval) — record the feedback "
          f"session in {cer}")


def _feedback_section(text, heading):
    """Return the substantive content of the Director-feedback section
    (comments and blank lines stripped); None when the heading is absent."""
    m = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text,
                  re.M | re.S)
    if not m:
        return None
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    return body.strip()


def kickoff_feedback_gate(root, args, k):
    """WS9.1 (SPEC §5.1): approval requires the Director's verbatim feedback
    recorded in the kickoff ceremony — even if it is 'no observations'."""
    cer = os.path.join(root, k.get("ceremony") or "")
    heading = msg("kickoff_feedback_heading")
    if not k.get("ceremony") or not os.path.isfile(cer):
        die(f"kickoff ceremony record not found: {k.get('ceremony')!r} — "
            "cannot approve without the feedback session record (SPEC §5.1)")
    text = open(cer).read()
    fb = getattr(args, "feedback", None)
    if fb:
        if heading not in text:
            text = text.rstrip() + f"\n\n{heading}\n"
        m = re.search(rf"^{re.escape(heading)}\s*$", text, re.M)
        insert_at = m.end()
        entry = f"\n\n- {now_iso()[:10]} — director: {fb}"
        text = text[:insert_at] + entry + text[insert_at:]
        with open(cer, "w") as f:
            f.write(text)
    if not _feedback_section(text, heading):
        die(msg("kickoff_feedback_required", id=k["id"], heading=heading,
                ceremony=k.get("ceremony"), cli=cli()))


def kickoff_approve(root, args):
    if args.by.strip().lower() != "director":
        die("only the Director approves a kickoff (--by director)")
    cp = project_path(root)
    c = load_json(cp)
    for k in c.get("kickoffs", []):
        if k["id"] == args.id:
            if k["status"] == "approved":
                die(f"{args.id} is already approved")
            kickoff_feedback_gate(root, args, k)
            k["status"] = "approved"
            k["approved_by"] = "director"
            k["approved_at"] = now_iso()
            c.setdefault("changelog", []).append(
                {"ts": now_iso(), "actor": "director",
                 "change": f"kickoff {args.id} approved: {k['initiative']}",
                 "approved_by": "director"})
            if getattr(args, "grant_autonomy", False):
                c["autonomy"] = "autonomous"
                c["changelog"].append(
                    {"ts": now_iso(), "actor": "director",
                     "change": "autonomy set to autonomous",
                     "approved_by": "director"})
            save_json(cp, c)
            print(f"{args.id} approved"
                  + (" (full autonomy granted)"
                     if getattr(args, "grant_autonomy", False) else ""))
            return
    die(f"kickoff {args.id} not found")


def kickoff_status(root, args):
    c = load_json(project_path(root))
    print(json.dumps({"autonomy": c.get("autonomy", "guided"),
                      "kickoffs": c.get("kickoffs", [])},
                     indent=2, ensure_ascii=False))


def autonomy_set(root, args):
    if args.by.strip().lower() != "director":
        die("only the Director changes the autonomy mode (--by director)")
    cp = project_path(root)
    c = load_json(cp)
    c["autonomy"] = args.mode
    c.setdefault("changelog", []).append(
        {"ts": now_iso(), "actor": "director",
         "change": f"autonomy set to {args.mode}", "approved_by": "director"})
    save_json(cp, c)
    print(f"autonomy = {args.mode}")


def stamp(root, args):
    """Fill null install metadata (idempotent; never overwrites)."""
    cp = project_path(root)
    c = load_json(cp)
    changed = []
    if not c.get("installed_at"):
        c["installed_at"] = now_iso()
        changed.append("installed_at")
    for e in c.get("changelog", []):
        if not e.get("ts"):
            e["ts"] = now_iso()
            changed.append("changelog.ts")
    if changed:
        save_json(cp, c)
    print("stamped: " + (", ".join(changed) if changed else "nothing to fill"))


# ------------------------------------------------------------- planning §12
def plan_file(root, task_id):
    return os.path.join(root, "plans", f"{task_id}.plan.md")


def superior_of(owner):
    """CORE-SPEC §12.2: {manager}/{agent} → {manager}; {manager} →
    root agent; root agent → director."""
    if "/" in owner:
        return owner.split("/", 1)[0]
    if owner == CFG["root_agent"]:
        return "director"
    return CFG["root_agent"]


def parse_plan(path):
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None, text
    fm = dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M))
    return fm, m.group(2)


def plan_todo_counts(body):
    """(checked, unchecked) inside the '## Todos' section only."""
    m = re.search(r"^## Todos\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    sec = m.group(1) if m else ""
    return (len(re.findall(r"^\s*- \[[xX]\]", sec, re.M)),
            len(re.findall(r"^\s*- \[ \]", sec, re.M)))


def _plan_approver_ok(by, owner):
    by = by.strip().lower()
    return by == "director" or by == superior_of(owner).lower()


def plan_gate(root, m, to):
    """CORE-SPEC §12.2/§12.4: hard gates on planned-kind transitions;
    None if it passes."""
    if not kinds_table().get(m.get("kind"), {}).get("planned"):
        return None
    pp = plan_file(root, m["id"])
    fm = parse_plan(pp)[0] if os.path.isfile(pp) else None
    if m["status"] == "started" and to == "in_progress":
        if not fm or fm.get("status", "").strip() != "approved":
            return msg("plan_gate_started", id=m["id"], cli=cli(),
                       superior=superior_of(m["owner"]))
    if to == "in_review" and os.path.isfile(pp):
        fm, body = parse_plan(pp)
        if not fm or fm.get("status", "").strip() != "approved":
            return msg("plan_gate_review_unapproved", id=m["id"])
        checked, unchecked = plan_todo_counts(body)
        if unchecked:
            return msg("plan_gate_review_todos", id=m["id"], n=unchecked,
                       cli=cli())
    return None


def plan_new(root, args):
    mp = manifest_path(root, args.id)
    if not os.path.exists(mp):
        die(f"{args.id} does not exist — create the TASK manifest first "
            f"(`{cli()} state new`)")
    m = load_json(mp)
    if not kinds_table().get(m.get("kind"), {}).get("planned"):
        die(f"{args.id} is kind '{m.get('kind')}' — only planned kinds get "
            "plans (CORE-SPEC §12.1)")
    pp = plan_file(root, args.id)
    if os.path.exists(pp):
        die(f"plan already exists: {os.path.relpath(pp, root)} — deviations "
            "go through `plan amend`, never a rewrite (§12.4)")
    if args.category not in PLAN_CATEGORIES:
        die(f"unknown category '{args.category}' "
            f"(one of: {', '.join(PLAN_CATEGORIES)})")
    approved = getattr(args, "approve", False)
    if approved:
        if args.category not in LIGHTWEIGHT_CATEGORIES:
            die(f"--approve is only valid for "
                f"{'/'.join(sorted(LIGHTWEIGHT_CATEGORIES))} plans (§12.3); "
                f"'{args.category}' requires plan-review + explicit "
                "`plan approve` by the owner's superior")
        if not _plan_approver_ok(args.by, m["owner"]):
            die(f"--approve requires --by to be the owner's superior "
                f"('{superior_of(m['owner'])}') or 'director' (§12.2/§12.3)")
    todos = "\n".join(f"- [ ] {t}" for t in (args.todo or [])) or \
        msg("plan_todo_placeholder")
    ts = now_iso()
    os.makedirs(os.path.dirname(pp), exist_ok=True)
    with open(pp, "w") as f:
        f.write(msg("plan_template",
                    id=args.id, category=args.category,
                    status="approved" if approved else "draft", date=ts[:10],
                    by=args.by, approved_by=args.by if approved else "null",
                    approved_at=ts if approved else "null",
                    objective=args.objective or msg("plan_objective_placeholder"),
                    todos=todos))
    m["plan_ref"] = os.path.relpath(pp, root)
    save_json(mp, m)
    print(f"{os.path.relpath(pp, root)} created "
          + (f"(approved by {args.by} — lightweight {args.category})"
             if approved else "(draft — pending approval by "
             f"{superior_of(m['owner'])})"))


def plan_approve(root, args):
    pp = plan_file(root, args.id)
    if not os.path.isfile(pp):
        die(f"no plan for {args.id} (`{cli()} plan new` first)")
    mp = manifest_path(root, args.id)
    if not os.path.exists(mp):
        die(f"manifest of {args.id} not found")
    m = load_json(mp)
    fm, _ = parse_plan(pp)
    if fm is None:
        die(f"{os.path.relpath(pp, root)} has no frontmatter")
    if fm.get("status", "").strip() == "approved":
        die(f"the plan of {args.id} is already approved "
            f"(by {fm.get('approved_by')})")
    if not _plan_approver_ok(args.by, m["owner"]):
        die(f"only the owner's superior ('{superior_of(m['owner'])}') or the "
            f"Director approve this plan (§12.2); got --by '{args.by}'")
    text = open(pp).read()
    text = re.sub(r"^status:.*$", "status: approved", text,
                  count=1, flags=re.M)
    text = re.sub(r"^approved_by:.*$", f"approved_by: {args.by}", text,
                  count=1, flags=re.M)
    text = re.sub(r"^approved_at:.*$", f"approved_at: {now_iso()}", text,
                  count=1, flags=re.M)
    with open(pp, "w") as f:
        f.write(text)
    print(f"plan of {args.id} approved by {args.by}")


def plan_check(root, args):
    pp = plan_file(root, args.id)
    errors = []
    if not os.path.isfile(pp):
        errors.append({"check": "plan-missing", "unit": args.id,
                       "detail": f"missing {os.path.relpath(pp, root)}"})
    else:
        fm, body = parse_plan(pp)
        if fm is None:
            errors.append({"check": "plan-frontmatter", "unit": args.id,
                           "detail": "no --- delimited frontmatter"})
        elif fm.get("status", "").strip() != "approved":
            errors.append({"check": "plan-not-approved", "unit": args.id,
                           "detail": f"status={fm.get('status', '?')}"})
        checked, unchecked = plan_todo_counts(body)
        if checked + unchecked == 0:
            errors.append({"check": "plan-no-todos", "unit": args.id,
                           "detail": "a plan with zero todos is not a plan "
                                     "(§12.1)"})
        elif unchecked:
            errors.append({"check": "plan-unchecked-todos", "unit": args.id,
                           "detail": f"{unchecked} unchecked of "
                                     f"{checked + unchecked}"})
    print(json.dumps({"errors": errors, "warnings": []},
                     indent=2, ensure_ascii=False))
    sys.exit(1 if errors else 0)


def plan_amend(root, args):
    pp = plan_file(root, args.id)
    if not os.path.isfile(pp):
        die(f"no plan for {args.id} — nothing to amend")
    fm, _ = parse_plan(pp)
    if fm is None or fm.get("status", "").strip() != "approved":
        die(f"the plan of {args.id} is not approved — amendments record "
            "deviations from an APPROVED plan; edit the draft directly "
            "(§12.4)")
    orig = fm.get("approved_by", "").strip()
    got = args.approved_by.strip().lower()
    if got != "director" and got != orig.lower():
        die(f"amendments are approved by the plan's original approver "
            f"('{orig}') or the Director (§12.4); got '{args.approved_by}'")
    text = open(pp).read()
    if "## Amendments" not in text:
        text = text.rstrip() + "\n\n## Amendments\n"
    entry = (f"- {now_iso()} — by {args.by}, approved by "
             f"{args.approved_by}: {args.reason}\n")
    text = text.rstrip() + "\n" if not text.endswith("\n") else text
    text += entry
    if args.add_todo:
        n = len(re.findall(r"^- \d{4}-", text, re.M))
        new = "".join(f"- [ ] {t} (amendment {n})\n" for t in args.add_todo)
        m = re.search(r"^## Todos\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        if not m:
            die("the plan has no '## Todos' section to add todos to")
        text = (text[:m.end(1)].rstrip("\n") + "\n" + new + "\n"
                + text[m.end(1):])
    with open(pp, "w") as f:
        f.write(text)
    print(f"plan of {args.id} amended by {args.by} "
          f"(approved by {args.approved_by}"
          + (f", +{len(args.add_todo)} todo(s))" if args.add_todo else ")"))


# -------------------------------------------------------------------- wiki §9
def wiki_scan(root):
    """LLM Wiki checks (CORE-SPEC §9). Returns (errors, warnings)."""
    errors, warnings = [], []
    wdir = os.path.join(root, "wiki")
    idx_path = os.path.join(wdir, "INDEX.md")
    idx_body = ""
    if os.path.isfile(idx_path):
        idx_body = open(idx_path).read()
    else:
        errors.append({"check": "wiki-index-missing", "unit": "wiki/INDEX.md",
                       "detail": "no INDEX.md"})
    if not os.path.isfile(os.path.join(wdir, "WIKI-SCHEMA.md")):
        errors.append({"check": "wiki-schema-missing",
                       "unit": "wiki/WIKI-SCHEMA.md", "detail": "no schema"})
    pages = sorted(glob.glob(os.path.join(wdir, "pages", "*.md")))
    names = {os.path.splitext(os.path.basename(p))[0] for p in pages}
    project_root = os.path.dirname(root)
    for p in pages:
        base = os.path.basename(p)
        fm, body = parse_note(p)
        if not fm:
            errors.append({"check": "wiki-frontmatter", "unit": base,
                           "detail": "no --- frontmatter"})
            continue
        miss = [k for k in ("title", "kind", "updated") if k not in fm]
        if miss:
            errors.append({"check": "wiki-frontmatter", "unit": base,
                           "detail": "missing: " + ",".join(miss)})
        if "sources" not in open(p).read().split("---", 2)[1]:
            errors.append({"check": "wiki-frontmatter", "unit": base,
                           "detail": "missing: sources"})
        if base not in idx_body:
            errors.append({"check": "wiki-index-coverage", "unit": base,
                           "detail": "page not listed in INDEX.md"})
        for link in set(re.findall(r"\[\[([^\]|#]+)\]\]", body)):
            if link.strip() not in names:
                warnings.append({"check": "wiki-unresolved-link", "unit": base,
                                 "detail": f"[[{link.strip()}]] has no page yet"})
        for src in re.findall(r"^\s*-\s+(\S+)\s*$",
                              open(p).read().split("---", 2)[1], re.M):
            if not os.path.exists(os.path.join(project_root, src)):
                warnings.append({"check": "wiki-source-missing", "unit": base,
                                 "detail": src})
    return errors, warnings


def wiki_check(root, args):
    if not os.path.isdir(os.path.join(root, "wiki")):
        die(f"no wiki/ under {CFG['root_dir']} (the installer seeds it)")
    errors, warnings = wiki_scan(root)
    print(json.dumps({"errors": errors, "warnings": warnings},
                     indent=2, ensure_ascii=False))
    sys.exit(1 if errors else 0)


# ----------------------------------------------- changelog & versioning §11
def changelog_path(root):
    """CORE-SPEC §11: CHANGELOG.md lives at the project root, sibling of the
    harness dir, never inside it."""
    return os.path.join(os.path.dirname(root), "CHANGELOG.md")


def _unreleased_span(text):
    """(start, end, body) of the `## [Unreleased]` section, up to the next
    `## [` heading or EOF. None if absent."""
    m = re.search(r"^## \[Unreleased\]\s*$", text, re.M)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"^## \[", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    return start, end, text[start:end]


def changelog_check(root, args):
    path = changelog_path(root)
    errors, warnings = [], []
    if not os.path.isfile(path):
        errors.append({"check": "changelog-missing", "unit": "CHANGELOG.md",
                       "detail": "no CHANGELOG.md at the project root"})
    else:
        span = _unreleased_span(open(path).read())
        if span is None:
            errors.append({"check": "changelog-no-unreleased",
                           "unit": "CHANGELOG.md",
                           "detail": "no '## [Unreleased]' section"})
        else:
            bullets = re.findall(r"^- .+$", span[2], re.M)
            if not bullets:
                errors.append({"check": "changelog-empty-unreleased",
                               "unit": "CHANGELOG.md",
                               "detail": "Unreleased has no entries"})
            elif args.task and not any(args.task in b for b in bullets):
                errors.append({"check": "changelog-task-not-referenced",
                               "unit": "CHANGELOG.md",
                               "detail": f"no Unreleased entry mentions {args.task}"})
    print(json.dumps({"errors": errors, "warnings": warnings},
                     indent=2, ensure_ascii=False))
    sys.exit(1 if errors else 0)


def _latest_semver_tag(project_root):
    try:
        out = subprocess.run(
            ["git", "-C", project_root, "tag", "-l", "v*.*.*"],
            capture_output=True, text=True, check=True).stdout.split()
    except Exception:
        return None
    versions = [(tuple(int(x) for x in m.groups()), t)
                for t in out for m in [SEMVER_TAG_RE.match(t)] if m]
    return max(versions)[1] if versions else None


def version_current(root, args):
    project_root = os.path.dirname(root)
    tag = _latest_semver_tag(project_root) or "v0.0.0"
    path = changelog_path(root)
    span = _unreleased_span(open(path).read()) if os.path.isfile(path) else None
    pending = len(re.findall(r"^- .+$", span[2], re.M)) if span else 0
    print(json.dumps({"latest_tag": tag, "pending_unreleased_entries": pending},
                     ensure_ascii=False))


def version_bump(root, args):
    project_root = os.path.dirname(root)
    path = changelog_path(root)
    if not os.path.isfile(path):
        die("no CHANGELOG.md at the project root — nothing to release")
    text = open(path).read()
    span = _unreleased_span(text)
    if span is None:
        die("CHANGELOG.md has no '## [Unreleased]' section")
    start, end, body = span
    if not re.findall(r"^- .+$", body, re.M):
        die("no Unreleased changes to release — nothing to bump")

    last = _latest_semver_tag(project_root) or "v0.0.0"
    major, minor, patch = (int(x) for x in SEMVER_TAG_RE.match(last).groups())
    if args.part == "major":
        major, minor, patch = major + 1, 0, 0
    elif args.part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new_version = f"v{major}.{minor}.{patch}"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Git tag FIRST: it is the operation most likely to fail (no HEAD, tag
    # exists, git missing). Files are only mutated once the tag stands, so a
    # failed bump never leaves CHANGELOG.md or the project state half-done.
    try:
        subprocess.run(
            ["git", "-C", project_root, "tag", "-a", new_version,
             "-m", args.notes or f"Release {new_version}"],
            check=True, capture_output=True, text=True)
    except FileNotFoundError:
        die("git is not on the PATH")
    except subprocess.CalledProcessError as e:
        die(f"git tag failed: {e.stderr.strip()}")

    fresh_unreleased = "\n" + "".join(f"### {c}\n\n" for c in UNRELEASED_CATEGORIES)
    released_section = f"## [{new_version[1:]}] - {date}\n{body.rstrip()}\n\n"
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text[:start] + fresh_unreleased + released_section + text[end:])
    os.replace(tmp, path)

    cp = project_path(root)
    c = load_json(cp)
    c.setdefault("changelog", []).append({
        "ts": now_iso(), "actor": args.by,
        "change": f"released {new_version}", "approved_by": args.by,
    })
    save_json(cp, c)

    print(f"version bumped: {last} -> {new_version} "
          f"(local tag created, not pushed)")


# ---------------------------------------------------------------- state cmds
def state_new(root, args):
    kickoff_gate(root, args.kind)
    prefixes = kind_prefixes()
    kind_pref = prefixes.get(args.kind)
    if not kind_pref:
        die(f"unknown kind '{args.kind}' (valid: {sorted(prefixes)})")
    if not re.match(re.escape(kind_pref) + r"-\d+$", args.id):
        die(f"id '{args.id}' does not match kind '{args.kind}' "
            f"(expected {kind_pref}-NNNN, CORE-SPEC §1.2)")
    p = manifest_path(root, args.id)
    if os.path.exists(p):
        die(f"{args.id} already exists")
    m = {
        "id": args.id,
        "title": args.title,
        "kind": args.kind,
        "owner": args.owner,
        "created_by": args.created_by,
        "status": "untouched",
        "depends_on": [d for d in (args.depends_on or "").split(",") if d],
        "artifact_paths": [a for a in (args.artifacts or "").split(",") if a],
        "artifact_checksum": None,
        "history": [{"ts": now_iso(), "agent": args.created_by, "from": None,
                     "to": "untouched", "reason": "created"}],
    }
    os.makedirs(os.path.dirname(p), exist_ok=True)
    save_json(p, m)
    print(f"{args.id} created (untouched)")


def state_transition(root, args):
    p = manifest_path(root, args.id)
    if not os.path.exists(p):
        die(f"{args.id} not found")
    m = load_json(p)
    cur = m["status"]
    entry = {"ts": now_iso(), "agent": args.agent, "from": cur, "to": args.to,
             "reason": args.reason}
    if args.to not in ALLOWED.get(cur, set()):
        entry["rejected"] = True
        m["history"].append(entry)
        save_json(p, m)
        die(f"invalid transition {cur} → {args.to} for {args.id} "
            f"(allowed: {sorted(ALLOWED.get(cur, set())) or 'none — terminal'}); "
            "rejected attempt recorded in the history")
    # Pack gate hooks (CORE-SPEC §E.2), then the core plan gate (§12).
    for g_kind, g_to, g_fn in _GATES:
        if g_kind is not None and m.get("kind") != g_kind:
            continue
        if g_to is not None and args.to != g_to:
            continue
        gate_err = g_fn(root, m, args.to)
        if gate_err:
            entry["rejected"] = True
            entry["reason"] = f"[gate] {gate_err} | {args.reason}"
            m["history"].append(entry)
            save_json(p, m)
            die(f"gate blocks {args.to} for {args.id}: {gate_err}")
    blocked = plan_gate(root, m, args.to)
    if blocked:
        entry["rejected"] = True
        m["history"].append(entry)
        save_json(p, m)
        die(blocked + " Rejected attempt recorded in the history.")
    m["history"].append(entry)
    m["status"] = args.to
    save_json(p, m)
    print(f"{args.id}: {cur} → {args.to}")


def state_checksum(root, args):
    p = manifest_path(root, args.id)
    if not os.path.exists(p):
        die(f"{args.id} not found")
    if not os.path.isfile(args.file):
        die(f"artifact not found: {args.file}")
    digest = sha256_file(args.file)
    m = load_json(p)
    m["artifact_checksum"] = f"sha256:{digest}"
    rel = os.path.relpath(args.file, os.path.dirname(root))
    if rel not in m.get("artifact_paths", []):
        m.setdefault("artifact_paths", []).append(rel)
    save_json(p, m)
    print(f"{args.id}: artifact_checksum = sha256:{digest[:12]}…")


# ------------------------------------------------------------------ memory §2
def parse_note(path):
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None, text
    fm = dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M))
    return fm, m.group(2).strip()


def signature_of(body):
    norm = body.strip().lower()
    return hashlib.sha256(norm.encode()).hexdigest()[:8]


def store_notes(store_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(store_dir, "*.md"))):
        if os.path.basename(p) in ("MEMORY.md", "README.md"):
            continue
        fm, body = parse_note(p)
        if fm:
            out.append((p, fm, body))
    return out


def live_note_ids(notes):
    dead = {fm.get("supersedes") for _, fm, _ in notes if fm.get("supersedes")}
    return [fm["id"] for _, fm, _ in notes if fm["id"] not in dead], dead


def memory_add(root, args):
    store = os.path.join(root, "memory", args.agent)
    os.makedirs(store, exist_ok=True)
    body = args.body if args.body else sys.stdin.read()
    body = body.strip()
    if not body:
        die("empty note body")
    sig = signature_of(body)
    notes = store_notes(store)
    live, dead = live_note_ids(notes)
    for _, fm, _ in notes:
        if fm["id"] in live and fm.get("signature", "").strip('"') == sig:
            die(f"duplicate: live note {fm['id']} already has signature {sig}")
    if args.supersedes and args.supersedes not in {fm["id"] for _, fm, _ in notes}:
        die(f"supersedes points to a missing note: {args.supersedes}")
    seq = 1 + max([int(m.group(1)) for _, fm, _ in notes
                   for m in [re.search(r"(\d+)$", fm["id"])] if m] or [0])
    nid = f"mem-{args.agent}-{seq:04d}"
    tags = [t for t in (args.tags or "").split(",") if t]
    lines = ["---", f"id: {nid}", f"type: {args.type}", f"scope: {args.scope}",
             f"created: {today_utc().isoformat()}",
             f"ttl_days: {args.ttl_days if args.ttl_days is not None else 'null'}",
             f"importance: {args.importance}", f"tags: [{', '.join(tags)}]",
             f'signature: "{sig}"']
    if args.supersedes:
        lines.append(f"supersedes: {args.supersedes}")
    lines += ["---", "", body, ""]
    path = os.path.join(store, f"{nid}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    rebuild_index(store)
    print(f"{nid} written (signature {sig})"
          + (f", supersedes {args.supersedes}" if args.supersedes else ""))


def rebuild_index(store):
    notes = store_notes(store)
    live, dead = live_note_ids(notes)
    rows = ["| id | type | scope | importance | created | tags | summary |",
            "|---|---|---|---|---|---|---|"]
    for _, fm, body in notes:
        if fm["id"] in dead:
            continue
        summary = re.sub(r"\s+", " ", body)[:100]
        rows.append(f"| {fm['id']} | {fm.get('type','')} | {fm.get('scope','')} "
                    f"| {fm.get('importance','')} | {fm.get('created','')} "
                    f"| {fm.get('tags','').strip('[]')} | {summary} |")
    with open(os.path.join(store, "MEMORY.md"), "w") as f:
        f.write("\n".join(rows) + "\n")
    if len(rows) - 2 > INDEX_COMPACT_AT:
        print(f"note: the index has {len(rows)-2} live entries (> {INDEX_COMPACT_AT}); "
              "the owner must compact per CORE-SPEC §2.2", file=sys.stderr)


def memory_recall(root, args):
    store = os.path.join(root, "memory", args.agent)
    if not os.path.isdir(store):
        die(f"no memory store for {args.agent}")
    today = (datetime.strptime(args.today, "%Y-%m-%d").date()
             if args.today else today_utc())
    kws = {k.strip().lower() for k in args.keywords.split(",") if k.strip()}
    notes = store_notes(store)
    _, dead = live_note_ids(notes)
    scored = []
    for _, fm, body in notes:
        if fm["id"] in dead:
            continue
        created = datetime.strptime(fm["created"], "%Y-%m-%d").date()
        ttl = fm.get("ttl_days", "null")
        if ttl not in ("null", "", None) and created + timedelta(days=int(ttl)) < today:
            continue
        imp = int(fm["importance"])
        days = (today - created).days
        recency = max(0.0, 1 - days / 90)
        words = set(re.findall(r"\w+", fm.get("tags", "").lower())) | \
            set(re.findall(r"\w+", body.split("\n")[0].lower()))
        rel = len(words & kws) / len(kws) if kws else 0.0
        score = 0.5 * imp / 5 + 0.3 * recency + 0.2 * rel
        scored.append((score, fm["id"], imp, recency, rel, body[:80]))
    scored.sort(reverse=True)
    for s, nid, imp, recency, rel, snippet in scored[:5]:
        mark = "INCLUDE" if s >= RECALL_THRESHOLD else "below-threshold"
        print(f"{s:.3f}  {nid}  (imp={imp} rec={recency:.2f} rel={rel:.2f}) "
              f"[{mark}]  {snippet}")
    if not scored:
        print("(no live notes)")


# ------------------------------------------------------------------ routing §3
def router_path(root):
    return os.path.join(root, "model-router.json")


def ensure_router(root):
    """Create a default model-router.json if it is missing."""
    p = router_path(root)
    if os.path.isfile(p):
        return p
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    save_json(p, DEFAULT_ROUTER)
    return p


def models_set(root, args):
    r = load_json(ensure_router(root))
    r["available_models"] = [m.strip() for m in args.models.split(",") if m.strip()]
    save_json(router_path(root), r)
    print(f"available_models = {r['available_models']}")


def models_list(root, args):
    r = load_json(ensure_router(root))
    for m in r.get("available_models", []):
        print(m)
    if not r.get("available_models"):
        print("(empty — run `models set` with the session's model ids)",
              file=sys.stderr)


# ---- model inventory (WS1: capability/cost-aware routing, SPEC §3.0)
INVENTORY_SCHEMA = "model-orchestrator-scan-v1"
INVENTORY_TTL_HOURS = 24
CAPABILITY_LADDER = ["low", "medium", "high", "very_high"]


def inventory_path(root):
    return os.path.join(root, "state", "model-inventory.json")


def models_scan(root, args):
    """Store a model-orchestrator inventory (capabilities, costs, limits) as
    the routing knowledge base. The inventory only ADDS information: routing
    without one behaves exactly as before."""
    if not os.path.isfile(args.inventory):
        die(f"inventory file not found: {args.inventory}")
    inv = load_json(args.inventory)
    if inv.get("schema") != INVENTORY_SCHEMA:
        die(f"unsupported inventory schema {inv.get('schema')!r} "
            f"(expected {INVENTORY_SCHEMA})")
    models = inv.get("models") or []
    if not models:
        die("inventory has no models")
    out = {"schema": INVENTORY_SCHEMA, "scanned_at": now_iso(),
           "generated_at": inv.get("generated_at"),
           "models": models}
    os.makedirs(os.path.join(root, "state"), exist_ok=True)
    save_json(inventory_path(root), out)
    print(f"model inventory stored: {len(models)} models "
          f"(TTL {INVENTORY_TTL_HOURS}h) → state/model-inventory.json")


def load_inventory(root):
    """Return {model_id: entry} when a fresh inventory exists, else {}."""
    p = inventory_path(root)
    if not os.path.isfile(p):
        return {}
    try:
        inv = load_json(p)
        scanned = datetime.fromisoformat(
            inv["scanned_at"].replace("Z", "+00:00"))
    except Exception:
        return {}
    age = datetime.now(timezone.utc) - scanned
    if age > timedelta(hours=INVENTORY_TTL_HOURS):
        return {}
    return {m["id"]: m for m in inv.get("models", []) if m.get("id")}


def _inventory_entry(model_id, inventory):
    if model_id in inventory:
        return inventory[model_id]
    # catalog ids may be stored in the platform's own format; match by
    # case-insensitive substring in either direction
    mid = model_id.lower()
    for k, v in inventory.items():
        kl = k.lower()
        if mid in kl or kl in mid or kl.split("/")[-1] == mid.split("/")[-1]:
            return v
    return None


def meets_capability_floor(model_id, floor, inventory):
    """Hard floor rule (SPEC §3.2): a resolved model below the category's
    min_capability is skipped for the next in the chain. Unknown models
    (not in the inventory) pass — the inventory only adds information."""
    if not floor or not inventory:
        return True, None
    entry = _inventory_entry(model_id, inventory)
    if entry is None:
        return True, None
    caps = entry.get("capabilities", {})
    for dim, minimum in floor.items():
        have = caps.get(dim)
        if have is None:
            continue
        if isinstance(minimum, bool) or isinstance(have, bool):
            if bool(minimum) and not bool(have):
                return False, f"{dim}={have}<{minimum}"
            continue
        try:
            hi = CAPABILITY_LADDER.index(str(have))
            mi = CAPABILITY_LADDER.index(str(minimum))
        except ValueError:
            continue
        if hi < mi:
            return False, f"{dim}={have}<{minimum}"
    return True, None


def estimated_cost_tier(model_id, inventory):
    """Coarse cost tier from the inventory's cost_profile (per 1M input):
    free (0) | low (<1) | medium (<5) | high (>=5); None when unknown."""
    entry = _inventory_entry(model_id, inventory) if inventory else None
    if not entry:
        return None
    per_in = (entry.get("cost_profile") or {}).get("per_1m_input")
    if per_in is None:
        return None
    if per_in == 0:
        return "free"
    if per_in < 1:
        return "low"
    if per_in < 5:
        return "medium"
    return "high"


def fuzzy(alias, hints, available):
    for hint in hints.get(alias, []):
        for m in available:
            if hint.lower() in m.lower():
                return m
    return None


def route(root, args):
    r = load_json(router_path(root))
    cat = args.category
    if cat not in r["categories"]:
        die(f"unknown category '{cat}' (valid: {sorted(r['categories'])})")
    available = r.get("available_models", [])
    hints = r.get("alias_resolution", {})
    chain_tried, resolved, source = [], None, None
    effort, effort_source = None, None
    inventory = load_inventory(root)
    floor = r["categories"][cat].get("min_capability")

    def passes_floor(m):
        """Hard rule (WS1): a candidate below the category's capability
        floor is skipped for the next in the chain, and the skip is
        recorded in chain_tried."""
        ok, why = meets_capability_floor(m, floor, inventory)
        if not ok:
            chain_tried.append(f"{m} (below-floor: {why})")
        return ok

    for layer, table in (("director-override", r.get("director_overrides", {})),
                         ("user-override", r.get("user_overrides", {}))):
        if cat in table:
            entry = table[cat]
            # CORE-SPEC §3.2: an override is an alias, or an object
            # {"model": alias, "effort": level} that also pins the effort.
            alias = entry.get("model", "") if isinstance(entry, dict) else entry
            if isinstance(entry, dict) and entry.get("effort"):
                effort, effort_source = entry["effort"], layer
            chain_tried.append(alias)
            m = fuzzy(alias, hints, available) or (alias if alias in available else None)
            if m and passes_floor(m):
                resolved, source = m, layer
                break
            # Unresolvable override: follow the §3.2 chain instead of
            # emitting a raw alias as if it were a model id.
    if not resolved:
        alias = r["categories"][cat]["preferred"]
        chain_tried.append(alias)
        m = fuzzy(alias, hints, available)
        if m and passes_floor(m):
            resolved, source = m, "category-default"
    if not resolved:
        for alias in r["categories"][cat]["fallbacks"]:
            chain_tried.append(alias)
            m = fuzzy(alias, hints, available)
            if m and passes_floor(m):
                resolved, source = m, "fallback"
                break
    if not resolved:
        resolved, source = r["system_default"], "system-default"

    if effort is None:
        effort = r["categories"][cat].get("effort", "medium")
        effort_source = "category-default"
    if args.platform:
        # Clamp to the platform's effort ladder (CORE-SPEC §3.2); null means
        # the platform has no effort concept.
        adapters = load_json(os.path.join(root, "adapters", "adapters.json"))
        plat = adapters["platforms"].get(args.platform)
        if plat is None:
            die(f"unknown platform '{args.platform}' "
                f"(valid: {sorted(adapters['platforms'])})")
        levels = (plat.get("models") or {}).get("effort_levels")
        if levels is None:
            effort, effort_source = None, "platform-no-effort-concept"
        elif effort not in levels:
            ladder = r.get("effort_ladder", ["low", "medium", "high", "max"])
            pos = ladder.index(effort) if effort in ladder else len(ladder) - 1
            supported = [l for l in ladder if l in levels]
            effort = ([l for l in supported if ladder.index(l) <= pos] or supported)[-1]
            effort_source += "+platform-clamped"

    record = {"ts": now_iso(), "task_id": args.task or None, "category": cat,
              "requested": chain_tried[0], "resolved": resolved,
              "provider": resolved.split("/", 1)[0] if "/" in resolved else None,
              "effort": effort, "effort_source": effort_source,
              "chain_tried": chain_tried, "source": source,
              "estimated_cost_tier": estimated_cost_tier(resolved, inventory)}
    if not args.no_log:
        r.setdefault("provenance_log", []).append(record)
        save_json(router_path(root), r)
    print(json.dumps(record, ensure_ascii=False))


# ------------------------------------------------------------------- skills
def skills_list(root, args):
    project_root = os.path.dirname(root)
    home = os.path.expanduser("~")
    catalogs = [
        (f"project:{CFG['root_dir']}", os.path.join(root, "skills")),
        ("project:.opencode", os.path.join(project_root, ".opencode", "skills")),
        ("project:.claude", os.path.join(project_root, ".claude", "skills")),
        ("global:opencode", os.path.join(
            os.environ.get("OPENCODE_CONFIG_DIR",
                           os.path.join(home, ".config", "opencode")), "skills")),
        ("global:claude", os.path.join(home, ".claude", "skills")),
    ]
    found = 0
    for label, base in catalogs:
        for p in sorted(glob.glob(os.path.join(base, "*", "SKILL.md"))):
            fm, _ = parse_note(p)
            name = (fm or {}).get("name", os.path.basename(os.path.dirname(p)))
            desc = (fm or {}).get("description", "").strip('"')[:90]
            print(f"[{label}] {name} — {desc}")
            found += 1
    if not found:
        print("(no skills found)")


# ------------------------------------------------------------------ roster §4.3
def _team_agents(team):
    # Canonical key is "agents"; "agentes" accepted for pre-engine installs.
    return team.get("agents", team.get("agentes", []))


def _agent_active(ag):
    # Canonical key is "active"; "activo" accepted for pre-engine installs.
    return ag.get("active", ag.get("activo", True))


def roster_show(root, args):
    c = load_json(project_path(root))
    print(json.dumps(c.get("roster", []), indent=2, ensure_ascii=False))


def roster_toggle(root, args):
    if args.active not in ("true", "false"):
        die("--active must be true or false")
    active = args.active == "true"
    c = load_json(project_path(root))
    for team in c.get("roster", []):
        if team["manager"] != args.manager:
            continue
        for ag in _team_agents(team):
            if ag["name"] == args.agent:
                if _agent_active(ag) == active:
                    die(f"{args.agent} is already active={args.active}")
                key = "activo" if "activo" in ag else "active"
                ag[key] = active
                c.setdefault("changelog", []).append({
                    "ts": now_iso(), "actor": args.actor,
                    "change": (f"roster: {args.manager}/{args.agent} → "
                               f"active={args.active} — {args.reason}"),
                    "approved_by": None,
                })
                save_json(project_path(root), c)
                print(f"{args.manager}/{args.agent}: active={args.active} "
                      "(recorded in changelog; re-run `agents materialize`)")
                return
        die(f"agent '{args.agent}' does not exist under {args.manager}")
    die(f"manager '{args.manager}' does not exist in the roster")


# ----------------------------------------------- platform agents §7.1
def agent_marker():
    return f"<!-- {CFG['pack_id'].upper()}-HARNESS:AGENT"


def roster_members(root):
    """Flatten the roster into pointer-agent specs (CORE-SPEC §7.1).

    Excludes agents with active: false (self-management §4.3)."""
    c = load_json(project_path(root))
    roster = c.get("roster") or []
    if not roster:
        die(f"the {CFG['project_json']} roster is empty — generate the "
            "roster first (Phase B)")
    governed = msg("governed_by", root_dir=CFG["root_dir"],
                   spec_file=CFG["spec_file"])

    def not_for(entry, default):
        return f" Not for: {entry.get('not_for', default)}."

    members = [{
        "id": CFG["root_agent"], "path": CFG["root_agent"], "delegates": True,
        "desc": msg("root_agent_desc", name=CFG["name"]) + governed,
    }]
    for team in roster:
        m = team["manager"]
        when = team.get("delegate_when",
                        msg("delegate_when_default", role=team["role"]))
        members.append({
            "id": m, "path": m, "delegates": True,
            "desc": (msg("manager_desc", role=team["role"], name=CFG["name"],
                         root_agent=CFG["root_agent"], when=when)
                     + not_for(team, msg("manager_not_for")) + governed),
        })
        for ag in _team_agents(team):
            if not _agent_active(ag):
                continue
            when = ag.get("delegate_when",
                          msg("delegate_when_default", role=ag["role"]))
            members.append({
                "id": ag["name"], "path": f"{m}/agents/{ag['name']}",
                "delegates": False,
                "desc": (msg("worker_desc", role=ag["role"], name=CFG["name"],
                             manager=m, when=when)
                         + not_for(ag, msg("worker_not_for")) + governed),
            })
    return members


def agent_file_content(member, fmt):
    desc = member["desc"].replace('"', "'")
    body = msg("agent_body", marker=agent_marker().lstrip("<!- "),
               root_agent=CFG["root_agent"], root_dir=CFG["root_dir"],
               spec_file=CFG["spec_file"], cli=cli(), path=member["path"])
    if fmt == "claude-code":
        tools = ", ".join(t.capitalize() for t in TOOL_NAMES)
        if member["delegates"]:
            tools += ", Task"
        fm = (f"---\nname: {member['id']}\ndescription: \"{desc}\"\n"
              f"tools: {tools}\n---\n")
    elif fmt == "opencode":
        # CORE-SPEC §7.1: the root agent is Tab-selectable (primary); the
        # rest are @-mentionable subagents.
        mode = "primary" if member["id"] == CFG["root_agent"] else "subagent"
        lines = [f"  {t}: true" for t in TOOL_NAMES]
        lines.append(f"  task: {'true' if member['delegates'] else 'false'}")
        fm = (f"---\ndescription: \"{desc}\"\nmode: {mode}\ntools:\n"
              + "\n".join(lines) + "\n---\n")
    else:
        die(f"unknown agent_format {fmt!r}")
    return fm + body


def selected_platforms(root, only):
    project = os.path.dirname(root)
    adapters = load_json(os.path.join(root, "adapters", "adapters.json"))
    out = []
    for name, cfg in adapters["platforms"].items():
        if only and name != only:
            continue
        if not cfg.get("agents_dir"):
            continue
        # The first `files` entry (plugin manifest / activation skill) marks
        # the adapter as installed.
        marker_dst = cfg["files"][0]["dst"]
        installed = os.path.isfile(os.path.join(project, marker_dst))
        if only or installed:
            out.append((name, cfg))
    if only and not out:
        die(f"platform {only!r} unknown or has agents_dir: null")
    return project, out


def agents_materialize(root, args):
    project, platforms = selected_platforms(root, args.platform)
    members = roster_members(root)
    ids = {m["id"] for m in members}
    marker = agent_marker()
    for name, cfg in platforms:
        agents_dir = os.path.join(project, cfg["agents_dir"])
        os.makedirs(agents_dir, exist_ok=True)
        written, skipped, removed = [], [], []
        for m in members:
            dst = os.path.join(agents_dir, f"{m['id']}.md")
            if os.path.isfile(dst):
                with open(dst, encoding="utf-8") as f:
                    current = f.read()
                if marker not in current:
                    skipped.append(m["id"] + " (user-owned, no marker)")
                    continue
            content = agent_file_content(m, cfg.get("agent_format"))
            fd, temporary = tempfile.mkstemp(
                dir=agents_dir, prefix=f".{m['id']}.", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, dst)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)
            written.append(m["id"])
        for fn in sorted(os.listdir(agents_dir)):
            if not fn.endswith(".md") or fn[:-3] in ids:
                continue
            p = os.path.join(agents_dir, fn)
            if marker in open(p).read():
                os.remove(p)
                removed.append(fn)
        print(json.dumps({"platform": name, "agents_dir": cfg["agents_dir"],
                          "format": cfg.get("agent_format"), "written": written,
                          "skipped": skipped, "removed_stale": removed},
                         ensure_ascii=False))


def agents_check(root, args):
    project, platforms = selected_platforms(root, args.platform)
    members = roster_members(root)
    ok = True
    for name, cfg in platforms:
        agents_dir = os.path.join(project, cfg["agents_dir"])
        missing, invalid = [], []
        for member in members:
            path = os.path.join(agents_dir, f"{member['id']}.md")
            if not os.path.isfile(path):
                missing.append(member["id"])
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    actual = f.read()
            except (OSError, UnicodeError) as exc:
                invalid.append({"id": member["id"], "reason": str(exc)})
                continue
            expected = agent_file_content(member, cfg.get("agent_format"))
            if actual != expected:
                invalid.append({
                    "id": member["id"],
                    "reason": "content differs from the current roster/adapter contract",
                })
        stale = []
        expected_ids = {member["id"] for member in members}
        if os.path.isdir(agents_dir):
            for filename in sorted(os.listdir(agents_dir)):
                if not filename.endswith(".md") or filename[:-3] in expected_ids:
                    continue
                path = os.path.join(agents_dir, filename)
                try:
                    with open(path, encoding="utf-8") as f:
                        managed = agent_marker() in f.read()
                except (OSError, UnicodeError):
                    managed = False
                if managed:
                    stale.append(filename)
        if missing or invalid or stale:
            ok = False
        print(json.dumps({"platform": name, "missing": missing,
                          "invalid": invalid, "stale": stale},
                         ensure_ascii=False))
    if not ok:
        sys.exit(1)


# ----------------------------------------------------------------- validate
def validate(root, args):
    errors, warnings, info = [], [], []
    manifests = sorted(glob.glob(os.path.join(root, "state", "*.json")))
    roster_ids = {CFG["root_agent"], "director"}
    project = {}
    try:
        c = load_json(project_path(root))
        project = c
        for t in c.get("roster", []):
            roster_ids.add(t["manager"])
            for a in _team_agents(t):
                roster_ids.add(a["name"])
                roster_ids.add(f'{t["manager"]}/{a["name"]}')
    except Exception as e:
        errors.append({"check": "project-json", "unit": CFG["project_json"],
                       "detail": str(e)})

    # --- state manifests (§1)
    prefixes = kind_prefixes()
    ids, deps, statuses = set(), {}, {}
    now = datetime.now(timezone.utc)
    for mp in manifests:
        unit = os.path.basename(mp)
        try:
            d = load_json(mp)
        except Exception as e:
            errors.append({"check": "json-parse", "unit": unit, "detail": str(e)})
            continue
        missing = [k for k in ("id", "kind", "owner", "status", "history") if k not in d]
        if missing:
            errors.append({"check": "missing-fields", "unit": unit,
                           "detail": ",".join(missing)})
            continue
        pref = prefixes.get(d["kind"])
        if pref and not d["id"].startswith(pref + "-"):
            errors.append({"check": "kind-prefix", "unit": d["id"],
                           "detail": f'kind={d["kind"]} expects prefix {pref}-'})
        ids.add(d["id"])
        deps[d["id"]] = d.get("depends_on", [])
        statuses[d["id"]] = (d["kind"], d["status"])
        hist = [e for e in d["history"] if not e.get("rejected")]
        if hist and d["status"] != hist[-1]["to"]:
            errors.append({"check": "status-mismatch", "unit": d["id"],
                           "detail": f'status={d["status"]} vs last to={hist[-1]["to"]}'})
        prev_ts = None
        for i, e in enumerate(hist):
            if i == 0:
                if e["from"] is not None or e["to"] != "untouched":
                    errors.append({"check": "invalid-transition", "unit": d["id"],
                                   "detail": f'first entry {e["from"]} → {e["to"]}'})
            elif e["from"] != hist[i - 1]["to"] or e["to"] not in ALLOWED.get(e["from"], set()):
                errors.append({"check": "invalid-transition", "unit": d["id"],
                               "detail": f'{e["from"]} → {e["to"]}'})
            ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
            if prev_ts and ts < prev_ts:
                errors.append({"check": "history-not-append-only", "unit": d["id"],
                               "detail": f"ts decreases at index {i}"})
            prev_ts = ts
        if d["owner"] not in roster_ids:
            errors.append({"check": "orphan-owner", "unit": d["id"], "detail": d["owner"]})
        if d["status"] == "in_progress" and prev_ts and now - prev_ts > timedelta(hours=STUCK_HOURS):
            warnings.append({"check": "stuck-in-progress", "unit": d["id"],
                             "detail": f'no transition since {hist[-1]["ts"]}'})
        if d["status"] == "stale":
            info.append({"check": "stale-resumable", "unit": d["id"]})
        # Planning contract (§12) — soft here; the transition gates and
        # `plan check` are the hard enforcement.
        if kinds_table().get(d["kind"], {}).get("planned"):
            pp = plan_file(root, d["id"])
            executing = d["status"] in ("in_progress", "blocked", "in_review",
                                        "changes_requested", "approved")
            if not os.path.isfile(pp):
                if d.get("plan_ref"):
                    errors.append({"check": "plan-ref-dangling", "unit": d["id"],
                                   "detail": d["plan_ref"]})
                elif executing:
                    warnings.append({"check": "plan-missing", "unit": d["id"],
                                     "detail": f"status={d['status']} without "
                                               "plans/*.plan.md (§12)"})
            else:
                pfm, _ = parse_plan(pp)
                if pfm is None:
                    warnings.append({"check": "plan-frontmatter",
                                     "unit": d["id"],
                                     "detail": "plan has no frontmatter"})
                elif executing and pfm.get("status", "").strip() != "approved":
                    warnings.append({"check": "plan-not-approved",
                                     "unit": d["id"],
                                     "detail": f"executing with plan status="
                                               f"{pfm.get('status', '?')}"})
    for uid, ds in deps.items():
        for dep in ds:
            if dep not in ids:
                errors.append({"check": "orphan-dependency", "unit": uid, "detail": dep})
    color = {u: 0 for u in deps}

    def dfs(u, path):
        color[u] = 1
        for v in deps.get(u, []):
            if color.get(v) == 1:
                errors.append({"check": "dependency-cycle", "unit": u,
                               "detail": " → ".join(path + [v])})
            elif color.get(v) == 0:
                dfs(v, path + [v])
        color[u] = 2
    for u in list(deps):
        if color[u] == 0:
            dfs(u, [u])

    # --- memory (§2)
    note_count = 0
    for store in sorted(glob.glob(os.path.join(root, "memory", "*"))):
        if not os.path.isdir(store):
            continue
        notes = store_notes(store)
        note_count += len(notes)
        all_ids = {fm["id"] for _, fm, _ in notes}
        _, dead = live_note_ids(notes)
        live_sigs = {}
        for p, fm, _ in notes:
            miss = [k for k in ("id", "type", "scope", "importance", "signature") if k not in fm]
            if miss:
                errors.append({"check": "memory-frontmatter",
                               "unit": os.path.relpath(p, root),
                               "detail": "missing: " + ",".join(miss)})
                continue
            s = fm.get("supersedes")
            if s and s not in all_ids:
                errors.append({"check": "supersedes-missing", "unit": fm["id"], "detail": s})
            if fm["id"] in dead:
                continue
            sig = fm["signature"].strip('"')
            if sig in live_sigs:
                errors.append({"check": "duplicate-signature", "unit": fm["id"],
                               "detail": f"same as {live_sigs[sig]}"})
            live_sigs[sig] = fm["id"]

    # --- install metadata and kickoff (§5.1)
    if project:
        if not project.get("installed_at") or any(not e.get("ts")
                                                  for e in project.get("changelog", [])):
            warnings.append({"check": "install-metadata",
                             "unit": CFG["project_json"],
                             "detail": "null installed_at / changelog ts — "
                                       f"run `{cli()} stamp`"})
        gated_prefixes = tuple(v["prefix"] + "-" for v in kinds_table().values()
                               if v.get("kickoff_gated"))
        has_gated = any(os.path.basename(mp).startswith(gated_prefixes)
                        for mp in manifests) if gated_prefixes else False
        kick_ok = any(k.get("status") == "approved"
                      for k in project.get("kickoffs", []))
        if (has_gated and not kick_ok
                and project.get("autonomy", "guided") == "guided"):
            warnings.append({"check": "kickoff-missing",
                             "unit": CFG["project_json"],
                             "detail": "kickoff-gated manifests exist with no "
                                       "approved kickoff and autonomy=guided"})

    # --- wiki (§9) — soft here; `wiki check` is the hard gate
    if os.path.isdir(os.path.join(root, "wiki")):
        werr, wwarn = wiki_scan(root)
        errors.extend(werr)
        warnings.extend(wwarn)

    # --- parseable config
    for cfg_file in ("model-router.json", os.path.join("adapters", "adapters.json")):
        p = os.path.join(root, cfg_file)
        if os.path.isfile(p):
            try:
                load_json(p)
            except Exception as e:
                errors.append({"check": "json-parse", "unit": cfg_file, "detail": str(e)})

    # --- pack-registered checks (CORE-SPEC §E.2)
    ctx = {"project": project, "manifests": manifests, "ids": ids,
           "statuses": statuses, "roster_ids": roster_ids}
    for fn in _VALIDATE_CHECKS:
        res = fn(root, ctx)
        if res:
            perr, pwarn = res
            errors.extend(perr)
            warnings.extend(pwarn)

    counters = {"manifests": len(manifests), "memory_notes": note_count}
    for fn in _VALIDATE_COUNTERS:
        counters.update(fn(root, ctx) or {})
    print("checked: { " + ", ".join(f"{k}: {v}" for k, v in counters.items())
          + " }")
    for name, lst in (("errors", errors), ("warnings", warnings), ("info", info)):
        if not lst:
            print(f"{name}: []")
        else:
            print(f"{name}:")
            for e in lst:
                print(f"  - {json.dumps(e, ensure_ascii=False)}")
    sys.exit(1 if errors else 0)


# ---------------------------------------------------------------------- main
def build_parser():
    ap = argparse.ArgumentParser(
        prog=cli(), description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root",
                    help=f"path to {CFG['root_dir']} (default: search upward)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("state").add_subparsers(dest="sub", required=True)
    p = st.add_parser("new")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--kind", default="task", choices=sorted(kind_prefixes()))
    p.add_argument("--created-by", default=CFG["root_agent"])
    p.add_argument("--depends-on")
    p.add_argument("--artifacts")
    p.set_defaults(fn=state_new)
    p = st.add_parser("transition")
    p.add_argument("id")
    p.add_argument("to")
    p.add_argument("--agent", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(fn=state_transition)
    p = st.add_parser("checksum")
    p.add_argument("id")
    p.add_argument("file")
    p.set_defaults(fn=state_checksum)

    me = sub.add_parser("memory").add_subparsers(dest="sub", required=True)
    p = me.add_parser("add")
    p.add_argument("agent")
    p.add_argument("--type", required=True,
                   choices=["decision", "feedback", "project-fact", "user-preference"])
    p.add_argument("--scope", required=True)
    p.add_argument("--importance", required=True, type=int, choices=range(1, 6))
    p.add_argument("--tags")
    p.add_argument("--ttl-days", type=int)
    p.add_argument("--supersedes")
    p.add_argument("--body")
    p.set_defaults(fn=memory_add)
    p = me.add_parser("recall")
    p.add_argument("agent")
    p.add_argument("--keywords", required=True)
    p.add_argument("--today")
    p.set_defaults(fn=memory_recall)

    mo = sub.add_parser("models").add_subparsers(dest="sub", required=True)
    p = mo.add_parser("set")
    p.add_argument("models")
    p.set_defaults(fn=models_set)
    p = mo.add_parser("list")
    p.set_defaults(fn=models_list)
    p = mo.add_parser("scan", help="Store a model-orchestrator inventory "
                      "(capabilities/costs/limits) for capability-aware "
                      "routing (SPEC §3.0).")
    p.add_argument("inventory", help="path to a model-orchestrator-scan-v1 JSON")
    p.set_defaults(fn=models_scan)

    p = sub.add_parser("route")
    p.add_argument("category")
    p.add_argument("--task")
    p.add_argument("--platform",
                   help="clamp the effort to the platform's effort_levels")
    p.add_argument("--no-log", action="store_true")
    p.set_defaults(fn=route)

    sk = sub.add_parser("skills").add_subparsers(dest="sub", required=True)
    p = sk.add_parser("list")
    p.set_defaults(fn=skills_list)

    ro = sub.add_parser("roster").add_subparsers(dest="sub", required=True)
    p = ro.add_parser("show")
    p.set_defaults(fn=roster_show)
    p = ro.add_parser("toggle")
    p.add_argument("manager")
    p.add_argument("agent")
    p.add_argument("--active", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", default=CFG["root_agent"])
    p.set_defaults(fn=roster_toggle)

    ag = sub.add_parser("agents").add_subparsers(dest="sub", required=True)
    p = ag.add_parser("materialize")
    p.add_argument("--platform")
    p.set_defaults(fn=agents_materialize)
    p = ag.add_parser("check")
    p.add_argument("--platform")
    p.set_defaults(fn=agents_check)

    ko = sub.add_parser(
        "kickoff",
        help="Kickoff gate (CORE-SPEC §5.1): Director feedback session "
             "before any gated unit is created.",
    ).add_subparsers(dest="sub", required=True)
    p = ko.add_parser("new")
    p.add_argument("--initiative", required=True)
    p.add_argument("--by", default=CFG["root_agent"])
    p.set_defaults(fn=kickoff_new)
    p = ko.add_parser("approve")
    p.add_argument("id")
    p.add_argument("--by", required=True)
    p.add_argument("--grant-autonomy", action="store_true",
                   help="also grant full autonomy (autonomy=autonomous)")
    p.add_argument("--feedback",
                   help="record the Director's verbatim feedback in the "
                        "ceremony before approving (required non-empty, "
                        "SPEC §5.1)")
    p.set_defaults(fn=kickoff_approve)
    p = ko.add_parser("status")
    p.set_defaults(fn=kickoff_status)

    au = sub.add_parser("autonomy").add_subparsers(dest="sub", required=True)
    p = au.add_parser("set")
    p.add_argument("mode", choices=["guided", "autonomous"])
    p.add_argument("--by", required=True)
    p.set_defaults(fn=autonomy_set)

    pl = sub.add_parser(
        "plan",
        help="Hierarchical planning contract (CORE-SPEC §12): "
             "plan-before-execute gate, adherence, append-only amendments.",
    ).add_subparsers(dest="sub", required=True)
    p = pl.add_parser("new", help="Create plans/{TASK-id}.plan.md and set "
                                  "plan_ref on the manifest.")
    p.add_argument("id")
    p.add_argument("--category", required=True, choices=PLAN_CATEGORIES)
    p.add_argument("--by", required=True)
    p.add_argument("--objective")
    p.add_argument("--todo", action="append",
                   help="Repeatable: a '- [ ]' todo line (include its AC).")
    p.add_argument("--approve", action="store_true",
                   help="trivial/routine only: create pre-approved by the "
                        "owner's superior (--by must be that superior).")
    p.set_defaults(fn=plan_new)
    p = pl.add_parser("approve")
    p.add_argument("id")
    p.add_argument("--by", required=True)
    p.set_defaults(fn=plan_approve)
    p = pl.add_parser("check", help="Adherence gate: approved plan and "
                                    "todos complete.")
    p.add_argument("id")
    p.set_defaults(fn=plan_check)
    p = pl.add_parser("amend", help="Record a deviation on an approved plan "
                                    "(append-only).")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--approved-by", required=True)
    p.add_argument("--add-todo", action="append",
                   help="Repeatable: new todo the deviation introduces.")
    p.set_defaults(fn=plan_amend)

    wi = sub.add_parser("wiki").add_subparsers(dest="sub", required=True)
    p = wi.add_parser("check")
    p.set_defaults(fn=wiki_check)

    ch = sub.add_parser("changelog").add_subparsers(dest="sub", required=True)
    p = ch.add_parser("check",
                      help="Gate §11: CHANGELOG.md with a non-empty "
                           "Unreleased section (mentioning --task if given).")
    p.add_argument("--task")
    p.set_defaults(fn=changelog_check)

    ve = sub.add_parser("version").add_subparsers(dest="sub", required=True)
    p = ve.add_parser("current",
                      help="Latest SemVer tag and pending Unreleased entries.")
    p.set_defaults(fn=version_current)
    p = ve.add_parser("bump",
                      help="Release Unreleased as a new SemVer version "
                           "(local git tag + dated section).")
    p.add_argument("part", choices=["major", "minor", "patch"])
    p.add_argument("--notes")
    p.add_argument("--by", default=CFG["root_agent"])
    p.set_defaults(fn=version_bump)

    p = sub.add_parser("stamp",
                       help=f"Fill null installed_at / changelog.ts in "
                            f"{CFG['project_json']} (idempotent).")
    p.set_defaults(fn=stamp)

    p = sub.add_parser("validate")
    p.set_defaults(fn=validate)

    # Pack subcommands (CORE-SPEC §E.1)
    for builder in _COMMANDS:
        builder(sub)
    return ap


def main(pack=None, argv=None):
    if pack is not None:
        configure(getattr(pack, "PACK", None) or {})
        register = getattr(pack, "register", None)
        if register:
            register(sys.modules[__name__])
    ap = build_parser()
    args = ap.parse_args(argv)
    root = find_root(args.root)
    args.fn(root, args)


if __name__ == "__main__":
    main()
