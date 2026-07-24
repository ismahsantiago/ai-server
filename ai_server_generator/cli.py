from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .data import load_profiles, load_setups, ordered_profile_names, setup_listing_names
from .presets import ordered_presets, resolve_preset
from .render import build_context, planned_files, render_workspace
from .validator import validate_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-server",
        description="Generate and validate local ai-server workspaces.",
    )
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List generator metadata.")
    list_parser.add_argument("kind", choices=["profiles", "setups", "models"])

    generate = subparsers.add_parser("generate", help="Generate a workspace from templates.")
    generate.add_argument("--preset")
    generate.add_argument("--setup")
    generate.add_argument("--profile")
    generate.add_argument("--access", choices=["localhost", "lan"])
    generate.add_argument("--model-path")
    generate.add_argument("--out", required=True)
    generate.add_argument("--dry-run", action="store_true")
    generate.add_argument("--force", action="store_true")
    generate.add_argument("--auth", default="none", choices=["none", "bearer-token"])
    generate.add_argument("--lan-allowlist", default="")

    matrix = subparsers.add_parser("matrix", help="Preview a preset/profile/access scenario.")
    matrix.add_argument("--preset")
    matrix.add_argument("--setup")
    matrix.add_argument("--profile")
    matrix.add_argument("--access", choices=["localhost", "lan"])
    matrix.add_argument("--model-path")
    matrix.add_argument("--auth", default="none", choices=["none", "bearer-token"])
    matrix.add_argument("--lan-allowlist", default="")

    validate = subparsers.add_parser("validate", help="Validate a generated workspace.")
    validate.add_argument("generated_dir")
    return parser


def _list_profiles() -> int:
    profiles = load_profiles()
    for name in ordered_profile_names():
        profile = profiles[name]
        print(f"{name}\t{profile.get('description', '')}")
    return 0


def _list_setups() -> int:
    setups = load_setups()
    printed: set[str] = set()
    for name in setup_listing_names():
        if name in printed:
            continue
        printed.add(name)
        if name in setups:
            description = setups[name].get("description", "")
        else:
            description = "Generated setup shortcut"
        print(f"{name}\t{description}")
    return 0


def _list_models() -> int:
    for preset in ordered_presets():
        tags = ",".join(preset.capability_tags)
        print(f"{preset.alias}\t{preset.name}\t{preset.summary}\t{tags}")
    return 0


def _resolve_generation_request(
    *,
    preset_alias: str | None,
    setup: str | None,
    profile: str | None,
    access: str | None,
    model_path: str | None,
) -> dict[str, Any]:
    preset = resolve_preset(preset_alias) if preset_alias else None

    resolved_setup = setup or (preset.default_setup if preset else "chat")
    resolved_profile = profile or (preset.default_profile if preset else "medium")
    resolved_access = access or (preset.default_access if preset else "localhost")
    resolved_model_path = model_path or (preset.default_model_path if preset else "./models/placeholder.gguf")

    preset_details = {
        "preset_alias": preset.alias if preset else "",
        "preset_name": preset.name if preset else "",
        "preset_summary": preset.summary if preset else "",
        "capability_tags": ", ".join(preset.capability_tags) if preset else "custom",
        "memory_guidance": preset.memory_guidance if preset else "Custom model path; verify host memory before launch.",
        "shorthand_mode": bool(preset),
    }

    return {
        "setup": resolved_setup,
        "profile": resolved_profile,
        "access": resolved_access,
        "model_path": resolved_model_path,
        **preset_details,
    }


def _scenario_warnings(profile: str, preset_alias: str) -> list[str]:
    warnings: list[str] = []
    if profile == "good":
        warnings.append("good profile increases memory pressure; confirm headroom on 12 GB hosts.")
    if preset_alias == "phi-4-14b":
        warnings.append("Phi-4 (14B) generation is supported, but runtime fit depends on quantization and host load.")
    return warnings


def _matrix_preview(args: argparse.Namespace) -> int:
    resolved = _resolve_generation_request(
        preset_alias=args.preset,
        setup=args.setup,
        profile=args.profile,
        access=args.access,
        model_path=args.model_path,
    )

    try:
        build_context(
            setup_name=resolved["setup"],
            profile_name=resolved["profile"],
            access=resolved["access"],
            model_path=resolved["model_path"],
            auth=args.auth,
            lan_allowlist=args.lan_allowlist,
            preset_alias=resolved["preset_alias"],
            preset_name=resolved["preset_name"],
            preset_summary=resolved["preset_summary"],
            capability_tags=resolved["capability_tags"],
            memory_guidance=resolved["memory_guidance"],
            shorthand_mode=resolved["shorthand_mode"],
        )
    except ValueError as exc:
        print("Decision: NO-GO")
        print(f"Reason: {exc}")
        return 1

    print("Scenario matrix preview")
    print(f"preset: {resolved['preset_alias'] or 'custom'}")
    print(f"setup/profile/access: {resolved['setup']} / {resolved['profile']} / {resolved['access']}")
    print(f"model_path: {resolved['model_path']}")
    print(f"auth: {args.auth}")
    print(f"lan_allowlist: {args.lan_allowlist or '(none)'}")
    print("Decision: GO")
    warnings = _scenario_warnings(resolved["profile"], resolved["preset_alias"])
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            if args.kind == "profiles":
                return _list_profiles()
            if args.kind == "setups":
                return _list_setups()
            if args.kind == "models":
                return _list_models()
        elif args.command == "matrix":
            return _matrix_preview(args)
        elif args.command == "generate":
            resolved = _resolve_generation_request(
                preset_alias=args.preset,
                setup=args.setup,
                profile=args.profile,
                access=args.access,
                model_path=args.model_path,
            )
            out_path, files = render_workspace(
                setup_name=resolved["setup"],
                profile_name=resolved["profile"],
                access=resolved["access"],
                model_path=resolved["model_path"],
                out=args.out,
                force=args.force,
                dry_run=args.dry_run,
                auth=args.auth,
                lan_allowlist=args.lan_allowlist,
                preset_alias=resolved["preset_alias"],
                preset_name=resolved["preset_name"],
                preset_summary=resolved["preset_summary"],
                capability_tags=resolved["capability_tags"],
                memory_guidance=resolved["memory_guidance"],
                shorthand_mode=resolved["shorthand_mode"],
            )
            rel = out_path.relative_to(Path(__file__).resolve().parents[1])
            if args.dry_run:
                print(f"DRY RUN: would generate {len(files)} files into {rel}")
                for item in files:
                    print(f"- {item}")
            else:
                print(f"Generated {len(files)} files into {rel}")
            return 0
        elif args.command == "validate":
            errors = validate_workspace(args.generated_dir)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"valid: {args.generated_dir}")
            return 0
        parser.print_help()
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
