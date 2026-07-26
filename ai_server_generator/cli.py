from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from .data import load_profiles, load_setups, ordered_profile_names, setup_listing_names
from .presets import ModelPreset, ordered_presets, resolve_preset


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
    validate.add_argument(
        "--tier",
        choices=["structure", "host", "runtime"],
        default="structure",
        help="Validation maturity: structure (default), host prerequisites/model, or live runtime.",
    )

    wizard = subparsers.add_parser(
        "wizard",
        help="Interactive localhost-only wizard: pick preset + profile, generate, validate, and optionally start/smoke.",
    )
    wizard.add_argument("--preset", default=None, help="Model preset alias (e.g. ornith-9b).")
    wizard.add_argument("--profile", default=None, help="Runtime profile (medium, medium-fast, good).")
    wizard.add_argument(
        "--out",
        default=None,
        help="Output directory (inside the repo), default generated/<preset>-<profile>-localhost.",
    )
    wizard.add_argument(
        "--overwrite",
        action="store_true",
        help="If the output directory exists, overwrite it using --force.",
    )
    wizard.add_argument(
        "--run",
        choices=["ask", "yes", "no"],
        default="ask",
        help="Whether to run the server after validate. Default ask.",
    )
    doctor = subparsers.add_parser("doctor", help="Inspect host capability without changing it.")
    doctor.add_argument("--format", choices=["text", "json"], default="text")
    doctor.add_argument("--out", default="artifacts/host-profile.json")
    doctor.add_argument("--no-write", action="store_true")
    doctor.add_argument("--models-path", default=None)
    return parser


def _read_line(prompt: str, unattended_hint: str) -> str:
    # Without a terminal there is nobody to answer, so surface the flag that
    # replaces the prompt instead of failing with an EOFError traceback after
    # the workspace has already been written.
    if not sys.stdin.isatty():
        raise ValueError(f"stdin is not a terminal; {unattended_hint}")
    try:
        return input(prompt)
    except EOFError as exc:
        raise ValueError(f"stdin closed before an answer; {unattended_hint}") from exc


def _prompt_yes_no(prompt: str, unattended_hint: str) -> bool:
    while True:
        raw = _read_line(prompt, unattended_hint).strip().lower()
        if raw in {"si", "s", "yes", "y"}:
            return True
        if raw in {"no", "n"}:
            return False
        print("Please answer SI/NO.")


def _prompt_choice_alias(
    title: str, alias_to_label: dict[str, str], preselected: str | None, flag: str
) -> str:
    if preselected:
        if preselected not in alias_to_label:
            raise ValueError(f"unknown {title} alias: {preselected}")
        return preselected

    aliases = list(alias_to_label.keys())
    hint = f"pass {flag} explicitly (one of: {', '.join(aliases)})"
    while True:
        print(title)
        for i, a in enumerate(aliases, start=1):
            print(f"  {i}) {a} — {alias_to_label[a]}")
        raw = _read_line("Type an alias or number: ", hint).strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(aliases):
                return aliases[idx]
        if raw in alias_to_label:
            return raw
        print("Invalid selection.")


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
        "model_contract": {
            "contract_version": preset.contract_version,
            "metadata_status": preset.metadata_status,
            "artifact_repository": preset.artifact_repository,
            "artifact_revision": preset.artifact_revision,
            "artifact_filename": preset.artifact_filename,
            "artifact_size_bytes": preset.artifact_size_bytes,
            "artifact_sha256": preset.artifact_sha256,
            "chat_template": preset.chat_template,
            "architecture": preset.architecture,
            "parameter_billions": preset.parameter_billions,
            "quantization_assumption": preset.quantization_assumption,
            "estimated_model_gb": preset.estimated_model_gb,
            "kv_cache_gb_at_default_context": preset.kv_cache_gb_at_default_context,
            "runtime_buffer_gb": preset.runtime_buffer_gb,
            "minimum_host_ram_gb": preset.minimum_host_ram_gb,
            "recommended_host_ram_gb": preset.recommended_host_ram_gb,
            "default_context": preset.default_context,
        } if preset else {
            "contract_version": 2,
            "metadata_status": "custom-artifact-unverified",
            "artifact_repository": None,
            "artifact_revision": None,
            "artifact_filename": Path(resolved_model_path).name,
            "artifact_size_bytes": None,
            "artifact_sha256": None,
            "chat_template": None,
            "architecture": "unknown",
            "parameter_billions": None,
            "quantization_assumption": "unknown",
            "estimated_model_gb": None,
            "kv_cache_gb_at_default_context": None,
            "runtime_buffer_gb": None,
            "minimum_host_ram_gb": None,
            "recommended_host_ram_gb": None,
            "default_context": None,
        },
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


def _static_matrix_decision(
    preset: ModelPreset | None, profile: dict[str, Any]
) -> tuple[str, str]:
    if preset is None:
        return (
            "WARN",
            "custom artifact metadata and host resources are not verified; generation is structural only",
        )
    profile_limit = float(str(profile["mem_limit"]).rstrip("gG"))
    estimated_runtime = (
        preset.estimated_model_gb
        + preset.kv_cache_gb_at_default_context
        + preset.runtime_buffer_gb
    )
    estimated_host = estimated_runtime + 2.5
    if estimated_runtime > profile_limit or estimated_host > 12.0:
        return (
            "NO-GO",
            f"planning estimate {estimated_runtime:.1f} GB runtime + 2.5 GB host reserve "
            f"exceeds profile {profile_limit:.1f} GB and/or 12 GB host assumption",
        )
    return (
        "WARN",
        f"planning estimate fits nominal limits ({estimated_runtime:.1f} GB runtime, "
        f"{estimated_host:.1f} GB host); actual GGUF and host are not verified",
    )


def _matrix_preview(args: argparse.Namespace) -> int:
    from .render import build_context
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
            model_contract=resolved["model_contract"],
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
    preset = resolve_preset(resolved["preset_alias"]) if resolved["preset_alias"] else None
    decision, reason = _static_matrix_decision(preset, load_profiles()[resolved["profile"]])
    print(f"Decision: {decision}")
    print(f"Reason: {reason}")
    print("Evidence: static planning assumptions only; no model, host, runtime, or quality check")
    warnings = _scenario_warnings(resolved["profile"], resolved["preset_alias"])
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        # Usage error, not a successful run: keep argparse's exit code so shell
        # callers and CI do not read a bare invocation as a passing command.
        parser.print_help(sys.stderr)
        return 2

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
            from .render import render_workspace
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
                model_contract=resolved["model_contract"],
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
            from .validator import validate_workspace
            errors = validate_workspace(args.generated_dir, tier=args.tier)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            labels = {
                "structure": "structure valid",
                "host": "host ready",
                "runtime": "runtime healthy",
            }
            print(f"{labels[args.tier]}: {args.generated_dir}")
            if args.tier == "structure":
                print("NOT VERIFIED: model existence/readability, Docker/Compose, host resources, runtime endpoint")
            elif args.tier == "host":
                print("NOT VERIFIED: runtime endpoint health or model response quality")
            return 0

        elif args.command == "doctor":
            from .doctor import run as run_doctor
            return run_doctor(output=args.out, fmt=args.format, no_write=args.no_write, models_path=args.models_path)

        elif args.command == "wizard":
            from .render import build_context, render_workspace, resolve_output_path
            from .validator import validate_workspace
            profiles = load_profiles()
            profile_aliases = ordered_profile_names()
            profile_to_label = {p: profiles[p].get("description", "") for p in profile_aliases}

            presets = ordered_presets()
            preset_to_label = {p.alias: f"{p.name} — {p.summary}" for p in presets}

            preset_alias = _prompt_choice_alias(
                "Select model preset", preset_to_label, args.preset, "--preset"
            )
            profile = _prompt_choice_alias(
                "Select runtime profile", profile_to_label, args.profile, "--profile"
            )

            access = "localhost"
            expected_model = Path(__file__).resolve().parents[1] / "models" / f"{preset_alias}.gguf"
            if not expected_model.is_file():
                print(
                    "ERROR: Missing model file for preset. "
                    f"Expected: {expected_model.as_posix()}\n"
                    "Please add the .gguf file manually into ./models/ and re-run the wizard."
                )
                return 1

            default_out = f"generated/{preset_alias}-{profile}-{access}"
            out_value = args.out or default_out

            # Resolve exactly as the renderer does, so the overwrite decision is
            # made about the directory that will actually be written. Anything
            # relative is interpreted against the project root, not the caller's
            # working directory.
            out_path = resolve_output_path(out_value)

            force = False
            if out_path.exists():
                if args.overwrite:
                    force = True
                else:
                    if not sys.stdin.isatty():
                        print(
                            "ERROR: Output directory already exists. "
                            "Re-run with --overwrite to replace it, or choose a different --out."
                        )
                        return 1
                    force = _prompt_yes_no(
                        "Output directory exists. Overwrite it? (SI/NO): ",
                        "re-run with --overwrite to replace it, "
                        "or choose a different --out",
                    )

            # 1) Matrix preview (resolved scenario)
            resolved = _resolve_generation_request(
                preset_alias=preset_alias,
                setup=None,
                profile=profile,
                access=access,
                model_path=None,
            )

            try:
                # Probe the scenario; build_context raises on an invalid one.
                build_context(
                    setup_name=resolved["setup"],
                    profile_name=resolved["profile"],
                    access=resolved["access"],
                    model_path=resolved["model_path"],
                    auth="none",
                    lan_allowlist="",
                    preset_alias=resolved["preset_alias"],
                    preset_name=resolved["preset_name"],
                    preset_summary=resolved["preset_summary"],
                    capability_tags=resolved["capability_tags"],
                    memory_guidance=resolved["memory_guidance"],
                    model_contract=resolved["model_contract"],
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
            print("auth: none")
            print("lan_allowlist: (none)")
            preset = resolve_preset(resolved["preset_alias"])
            decision, reason = _static_matrix_decision(preset, profiles[resolved["profile"]])
            print(f"Decision: {decision}")
            print(f"Reason: {reason}")
            print("Evidence: static planning assumptions only; no host/runtime/quality check")
            warnings = _scenario_warnings(resolved["profile"], resolved["preset_alias"])
            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print(f"- {warning}")

            # 2) Generate
            out_dir, files = render_workspace(
                setup_name=resolved["setup"],
                profile_name=resolved["profile"],
                access=resolved["access"],
                model_path=resolved["model_path"],
                out=out_value,
                force=force,
                dry_run=False,
                auth="none",
                lan_allowlist="",
                preset_alias=resolved["preset_alias"],
                preset_name=resolved["preset_name"],
                preset_summary=resolved["preset_summary"],
                capability_tags=resolved["capability_tags"],
                memory_guidance=resolved["memory_guidance"],
                model_contract=resolved["model_contract"],
                shorthand_mode=resolved["shorthand_mode"],
            )
            rel_out = out_dir.relative_to(Path(__file__).resolve().parents[1])
            print(f"Generated {len(files)} files into {rel_out.as_posix()}")

            # 3) Validate
            errors = validate_workspace(str(out_dir), tier="structure")
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"structure valid: {out_dir}")
            print("NOT VERIFIED: model host readiness and live runtime")

            # 4) Run?
            if args.run == "ask":
                if sys.stdin.isatty():
                    run_server = _prompt_yes_no(
                        "¿Deseas correr el servidor ahora? (SI/NO): ",
                        "pass --run yes or --run no",
                    )
                else:
                    # The workspace is already generated and valid; starting a
                    # container is the side effect nobody is present to approve.
                    print("stdin is not a terminal; not starting the server. Use --run yes to start it.")
                    run_server = False
            elif args.run == "yes":
                run_server = True
            else:
                run_server = False

            if not run_server:
                print("Server not started. Next steps:")
                print(f"- {out_dir}/scripts/start.sh")
                print(f"- {out_dir}/scripts/smoke.sh")
                print(f"- docker compose -f {out_dir}/docker-compose.yml ps")
                return 0

            # start + smoke
            start = subprocess.run(
                ["./scripts/start.sh"],
                cwd=str(out_dir),
                text=True,
                capture_output=True,
            )
            if start.returncode != 0:
                print("ERROR: start.sh failed.")
                if start.stdout:
                    print(start.stdout)
                if start.stderr:
                    print(start.stderr, file=sys.stderr)
                return start.returncode

            smoke = subprocess.run(
                ["./scripts/smoke.sh"],
                cwd=str(out_dir),
                text=True,
                capture_output=True,
            )
            if smoke.stdout:
                print(smoke.stdout)
            if smoke.stderr:
                print(smoke.stderr, file=sys.stderr)
            return smoke.returncode

        parser.print_help()
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
