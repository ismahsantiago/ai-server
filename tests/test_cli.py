import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_server_generator.render import (
    SERVING_IMAGE,
    build_context,
    planned_files,
    render_workspace,
)


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class CliTests(unittest.TestCase):
    def run_cli(self, *args, check=False, env=None, cwd=None):
        result = subprocess.run(
            [PYTHON, "-m", "ai_server_generator", *args],
            cwd=str(cwd) if cwd else ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        if check and result.returncode != 0:
            self.fail(
                f"command failed: {' '.join(args)}\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def setUp(self):
        self.generated_root = ROOT / "generated"
        suffix = f"-{os.getpid()}"
        self.dry_run_out = self.generated_root / f"test-dry-run{suffix}"
        self.localhost_out = self.generated_root / f"test-chat-medium-localhost{suffix}"
        self.invalid_lan_out = self.generated_root / f"test-invalid-lan-no-auth{suffix}"
        self.ornith_out = self.generated_root / f"test-ornith-medium-localhost{suffix}"
        self.wizard_out = self.generated_root / f"test-wizard-ornith-medium-localhost{suffix}"
        self.wizard_overwrite_out = self.generated_root / f"test-wizard-overwrite-ornith-medium-localhost{suffix}"
        self.special_out = self.generated_root / f"test-special-input{suffix}"
        self.deterministic_a_out = self.generated_root / f"test-deterministic-a{suffix}"
        self.deterministic_b_out = self.generated_root / f"test-deterministic-b{suffix}"
        self.rollback_out = self.generated_root / f"test-render-rollback{suffix}"
        self.symlink_out = self.generated_root / f"test-output-link{suffix}"
        self.security_out = self.generated_root / f"test-security-mutations{suffix}"
        self.runtime_out = self.generated_root / f"test-runtime-contract{suffix}"
        self.all_outputs = [
            self.dry_run_out,
            self.localhost_out,
            self.invalid_lan_out,
            self.ornith_out,
            self.wizard_out,
            self.wizard_overwrite_out,
            self.special_out,
            self.deterministic_a_out,
            self.deterministic_b_out,
            self.rollback_out,
            self.symlink_out,
            self.security_out,
            self.runtime_out,
        ]
        for path in self.all_outputs:
            if path.is_symlink():
                path.unlink()
            else:
                shutil.rmtree(path, ignore_errors=True)
            for marker in ("backup", "staging", "replaced", "rolledback", "restore"):
                for sibling in path.parent.glob(f".{path.name}.{marker}-*"):
                    shutil.rmtree(sibling, ignore_errors=True)

        # Wizard preflight expects ./models/<preset>.gguf to exist.
        # We create a tiny dummy file for the preset(s) used in tests.
        self.models_dir = ROOT / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        (self.models_dir / "ornith-9b.gguf").write_text("dummy", encoding="utf-8")
        self.spaced_model = self.models_dir / "test model with spaces.gguf"
        self.spaced_model.write_text("tiny fixture", encoding="utf-8")

    def tearDown(self):
        for path in self.all_outputs:
            if path.is_symlink():
                path.unlink()
            else:
                shutil.rmtree(path, ignore_errors=True)
            for marker in ("backup", "staging", "replaced", "rolledback", "restore"):
                for sibling in path.parent.glob(f".{path.name}.{marker}-*"):
                    shutil.rmtree(sibling, ignore_errors=True)

        # Keep repo clean: remove dummy models added for tests.
        try:
            (self.models_dir / "ornith-9b.gguf").unlink(missing_ok=True)
            self.spaced_model.unlink(missing_ok=True)
        except Exception:
            pass

    def test_lists_profiles_and_setups(self):
        profiles = self.run_cli("list", "profiles", check=True)
        self.assertIn("medium-fast", profiles.stdout)
        self.assertIn("medium", profiles.stdout)
        self.assertIn("good", profiles.stdout)

        setups = self.run_cli("list", "setups", check=True)
        self.assertIn("chat-localhost-medium", setups.stdout)

        models = self.run_cli("list", "models", check=True)
        self.assertIn("ornith-9b", models.stdout)
        self.assertIn("phi-4-14b", models.stdout)
        self.assertIn("Ornith 1.0 (9B)", models.stdout)

    def test_matrix_preview_reports_go_for_localhost(self):
        result = self.run_cli(
            "matrix",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--access",
            "localhost",
            check=True,
        )
        self.assertIn("Decision: WARN", result.stdout)
        self.assertIn("static planning assumptions only", result.stdout)
        self.assertIn("ornith-9b", result.stdout)

    def test_matrix_preview_reports_no_go_for_unsafe_lan(self):
        result = self.run_cli(
            "matrix",
            "--preset",
            "devstral-small-v25.07",
            "--profile",
            "medium",
            "--access",
            "lan",
        )
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("NO-GO", combined)

    def test_generate_with_preset_populates_manifest_resolution(self):
        generate = self.run_cli(
            "generate",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--out",
            str(self.ornith_out.relative_to(ROOT)),
            "--force",
            check=True,
        )
        self.assertIn("Generated", generate.stdout)

        manifest = json.loads((self.ornith_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["preset_alias"], "ornith-9b")
        self.assertEqual(manifest["preset_name"], "Ornith 1.0 (9B)")
        self.assertEqual(manifest["resolved_setup"], "chat")
        self.assertEqual(manifest["resolved_profile"], "medium")
        self.assertEqual(manifest["resolved_access"], "localhost")
        self.assertEqual(manifest["host_model_path"], str((ROOT / "models/ornith-9b.gguf").resolve()))
        self.assertEqual(manifest["container_model_path"], "/models/model.gguf")
        self.assertEqual(manifest["model_contract"]["contract_version"], 1)

    def test_matrix_covers_all_presets_for_medium_and_medium_fast_localhost(self):
        aliases = [
            "ornith-9b",
            "devstral-small-v25.07",
            "qwen3-coder-7b",
            "smollm3-3b",
            "phi-4-14b",
        ]
        for alias in aliases:
            for profile in ["medium", "medium-fast"]:
                with self.subTest(alias=alias, profile=profile):
                    result = self.run_cli(
                        "matrix",
                        "--preset",
                        alias,
                        "--profile",
                        profile,
                        "--access",
                        "localhost",
                        check=True,
                    )
                    self.assertRegex(result.stdout, r"Decision: (WARN|NO-GO)")
                    self.assertNotIn("Decision: GO", result.stdout)
                    self.assertIn("no model, host, runtime, or quality check", result.stdout)

    def test_dry_run_reports_files_without_writing_output(self):
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            str(self.dry_run_out.relative_to(ROOT)),
            "--dry-run",
            check=True,
        )

        self.assertIn("DRY RUN", result.stdout)
        self.assertIn("docker-compose.yml", result.stdout)
        self.assertFalse(self.dry_run_out.exists())

    def test_generates_and_validates_chat_medium_localhost(self):
        generate = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            str(self.localhost_out.relative_to(ROOT)),
            "--force",
            check=True,
        )
        self.assertIn("Generated", generate.stdout)

        required = [
            "docker-compose.yml",
            ".env",
            "manifest.json",
            "README.md",
            "runbook.md",
            "scripts/start.sh",
            "scripts/validate.sh",
            "scripts/smoke.sh",
            "scripts/stop.sh",
            "scripts/start_serving.sh",
            "scripts/smoke_benchmark.sh",
            "scripts/validate_host.sh",
        ]
        for rel in required:
            self.assertTrue((self.localhost_out / rel).is_file(), rel)
        self.assertEqual(stat.S_IMODE((self.localhost_out / ".env").stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE((self.localhost_out / "manifest.json").stat().st_mode),
            0o644,
        )
        self.assertEqual(
            stat.S_IMODE((self.localhost_out / "scripts/start.sh").stat().st_mode),
            0o755,
        )

        manifest = json.loads((self.localhost_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["setup"], "chat")
        self.assertEqual(manifest["profile"], "medium")
        self.assertEqual(manifest["access"], "localhost")
        self.assertEqual(manifest["quick_commands"]["start"], "./scripts/start.sh")
        self.assertEqual(manifest["quick_commands"]["validate"], "./scripts/validate.sh")
        self.assertEqual(manifest["quick_commands"]["smoke"], "./scripts/smoke.sh")
        self.assertEqual(manifest["quick_commands"]["stop"], "./scripts/stop.sh")

        validation = self.run_cli("validate", str(self.localhost_out.relative_to(ROOT)), check=True)
        self.assertIn("structure valid", validation.stdout.lower())
        self.assertIn("NOT VERIFIED", validation.stdout)

    def test_wizard_generates_and_validates_localhost(self):
        result = self.run_cli(
            "wizard",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--out",
            str(self.wizard_out.relative_to(ROOT)),
            "--run",
            "no",
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        required = [
            "docker-compose.yml",
            ".env",
            "manifest.json",
            "README.md",
            "runbook.md",
            "scripts/start.sh",
            "scripts/validate.sh",
            "scripts/smoke.sh",
        ]
        for rel in required:
            self.assertTrue((self.wizard_out / rel).is_file(), rel)

    def test_bare_invocation_is_a_usage_error(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("usage:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_wizard_resolves_relative_out_against_project_root(self):
        relative_out = str(self.wizard_out.relative_to(ROOT))
        self.run_cli(
            "wizard",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--out",
            relative_out,
            "--run",
            "no",
            check=True,
        )
        self.assertTrue((self.wizard_out / "manifest.json").is_file())

        # From an unrelated working directory the same relative --out must still
        # name the workspace that was just generated, so the wizard reports its
        # own overwrite guidance instead of failing inside the renderer.
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        with tempfile.TemporaryDirectory() as elsewhere:
            result = self.run_cli(
                "wizard",
                "--preset",
                "ornith-9b",
                "--profile",
                "medium",
                "--out",
                relative_out,
                "--run",
                "no",
                cwd=elsewhere,
                env=env,
            )
        combined = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, msg=combined)
        self.assertIn("--overwrite", combined)
        self.assertNotIn("--force", combined)

    def test_wizard_without_terminal_does_not_crash_on_prompts(self):
        # The run prompt has no answerer, but the workspace is already valid,
        # so the wizard must decline to start the server and exit cleanly.
        result = subprocess.run(
            [
                PYTHON,
                "-m",
                "ai_server_generator",
                "wizard",
                "--preset",
                "ornith-9b",
                "--profile",
                "medium",
                "--out",
                str(self.wizard_out.relative_to(ROOT)),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, msg=combined)
        self.assertNotIn("Traceback", combined)
        self.assertNotIn("EOFError", combined)
        self.assertIn("not starting the server", combined)
        self.assertTrue((self.wizard_out / "manifest.json").is_file())

    def test_wizard_without_terminal_names_the_missing_flag(self):
        result = subprocess.run(
            [
                PYTHON,
                "-m",
                "ai_server_generator",
                "wizard",
                "--out",
                str(self.wizard_out.relative_to(ROOT)),
                "--run",
                "no",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, msg=combined)
        self.assertNotIn("Traceback", combined)
        self.assertIn("--preset", combined)
        self.assertFalse(self.wizard_out.exists())

    def test_wizard_fails_missing_model(self):
        out = self.generated_root / "test-wizard-missing-model"
        shutil.rmtree(out, ignore_errors=True)

        result = self.run_cli(
            "wizard",
            "--preset",
            "phi-4-14b",
            "--profile",
            "medium",
            "--out",
            str(out.relative_to(ROOT)),
            "--run",
            "no",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("Missing model file", combined)
        self.assertFalse(out.exists())

    def test_wizard_overwrite_requires_generated_ownership(self):
        self.wizard_overwrite_out.mkdir(parents=True, exist_ok=True)
        sentinel = self.wizard_overwrite_out / "operator-notes.txt"
        sentinel.write_text("do not overwrite", encoding="utf-8")

        # Without --overwrite it should fail (non-interactive).
        result = self.run_cli(
            "wizard",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--out",
            str(self.wizard_overwrite_out.relative_to(ROOT)),
            "--run",
            "no",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

        # --overwrite is also fail-closed for an unrecognized user directory.
        result2 = self.run_cli(
            "wizard",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--out",
            str(self.wizard_overwrite_out.relative_to(ROOT)),
            "--run",
            "no",
            "--overwrite",
            check=False,
        )
        self.assertNotEqual(result2.returncode, 0)
        self.assertIn("unrecognized directory", result2.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not overwrite")

        # A workspace generated by this tool can be replaced explicitly.
        shutil.rmtree(self.wizard_overwrite_out)
        first = self.run_cli(
            "wizard",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--out",
            str(self.wizard_overwrite_out.relative_to(ROOT)),
            "--run",
            "no",
            check=True,
        )
        self.assertIn("Generated", first.stdout)
        # The v1 manifest is the explicit safe legacy recognition rule.
        (self.wizard_overwrite_out / ".ai-server-generated.json").unlink()
        result3 = self.run_cli(
            "wizard",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--out",
            str(self.wizard_overwrite_out.relative_to(ROOT)),
            "--run",
            "no",
            "--overwrite",
            check=False,
        )
        self.assertEqual(result3.returncode, 0, msg=result3.stdout + result3.stderr)
        self.assertTrue((self.wizard_overwrite_out / "docker-compose.yml").is_file())

    def test_rejects_outputs_outside_generated_root_and_generated_root_itself(self):
        unsafe_outputs = [
            ".",
            "..",
            "generated",
            "docs/test-output",
            "models/test-output",
            "scripts/test-output",
            "audits/test-output",
            ".git/test-output",
            str(ROOT.parent / "outside-ai-server"),
        ]
        for output in unsafe_outputs:
            with self.subTest(output=output):
                result = self.run_cli(
                    "generate",
                    "--setup",
                    "chat",
                    "--profile",
                    "medium",
                    "--access",
                    "localhost",
                    "--model-path",
                    "./models/placeholder.gguf",
                    "--out",
                    output,
                    "--force",
                    "--dry-run",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("strict descendant of generated", result.stderr)

    def test_rejects_output_path_that_traverses_symlink(self):
        self.symlink_out.symlink_to(ROOT / "docs", target_is_directory=True)
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            f"{self.symlink_out.relative_to(ROOT)}/child",
            "--force",
            "--dry-run",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not traverse a symlink", result.stderr)

    def test_force_replacement_keeps_recoverable_sibling_backup(self):
        relative = str(self.rollback_out.relative_to(ROOT))
        self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            relative,
            check=True,
        )
        refusal = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium-fast",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            relative,
        )
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("use --force", refusal.stderr)
        self.assertEqual(
            json.loads((self.rollback_out / "manifest.json").read_text(encoding="utf-8"))[
                "profile"
            ],
            "medium",
        )
        (self.rollback_out / "operator-note.txt").write_text("previous version", encoding="utf-8")

        self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium-fast",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            relative,
            "--force",
            check=True,
        )

        backups = list(self.rollback_out.parent.glob(f".{self.rollback_out.name}.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            (backups[0] / "operator-note.txt").read_text(encoding="utf-8"),
            "previous version",
        )
        self.assertFalse((self.rollback_out / "operator-note.txt").exists())

    def test_force_rejects_tampered_ownership_marker(self):
        relative = str(self.special_out.relative_to(ROOT))
        self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            relative,
            check=True,
        )
        marker_path = self.special_out / ".ai-server-generated.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["generation_fingerprint"] = "0" * 64
        marker_path.write_text(json.dumps(marker), encoding="utf-8")

        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium-fast",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            relative,
            "--force",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized directory", result.stderr)
        self.assertEqual(
            json.loads(marker_path.read_text(encoding="utf-8"))["generation_fingerprint"],
            "0" * 64,
        )

    def test_render_validation_failure_preserves_prior_output_and_cleans_staging(self):
        kwargs = {
            "setup_name": "chat",
            "profile_name": "medium",
            "access": "localhost",
            "model_path": "./models/placeholder.gguf",
            "out": str(self.rollback_out.relative_to(ROOT)),
            "force": False,
            "dry_run": False,
        }
        render_workspace(**kwargs)
        before = {
            path.relative_to(self.rollback_out): path.read_bytes()
            for path in self.rollback_out.rglob("*")
            if path.is_file()
        }

        with mock.patch(
            "ai_server_generator.render._render_to_staging",
            side_effect=RuntimeError("injected render failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected render failure"):
                render_workspace(**{**kwargs, "force": True})
        after_render_failure = {
            path.relative_to(self.rollback_out): path.read_bytes()
            for path in self.rollback_out.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after_render_failure, before)

        with mock.patch(
            "ai_server_generator.validator.validate_workspace",
            return_value=["injected validation failure"],
        ):
            with self.assertRaisesRegex(ValueError, "injected validation failure"):
                render_workspace(**{**kwargs, "force": True})

        after = {
            path.relative_to(self.rollback_out): path.read_bytes()
            for path in self.rollback_out.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertEqual(
            list(self.rollback_out.parent.glob(f".{self.rollback_out.name}.staging-*")),
            [],
        )
        self.assertEqual(
            list(self.rollback_out.parent.glob(f".{self.rollback_out.name}.backup-*")),
            [],
        )

    def test_serializes_special_characters_without_config_injection(self):
        model_path = "./models/model \"quote' : # ${COMPOSE_VALUE} ü.gguf"
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            model_path,
            "--out",
            str(self.special_out.relative_to(ROOT)),
            check=True,
        )
        self.assertEqual(result.returncode, 0)
        manifest = json.loads((self.special_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(Path(manifest["host_model_path"]).is_absolute())
        self.assertIn("${COMPOSE_VALUE}", manifest["host_model_path"])
        self.assertEqual(manifest["model_path"], manifest["host_model_path"])
        self.assertEqual(manifest["container_model_path"], "/models/model.gguf")

        compose = (self.special_out / "docker-compose.yml").read_text(encoding="utf-8")
        expected_yaml_scalar = json.dumps(
            manifest["host_model_path"].replace("$", "$$"),
            ensure_ascii=False,
        )
        self.assertIn(f"        source: {expected_yaml_scalar}\n", compose)
        self.assertIn("        target: /models/model.gguf\n", compose)
        self.assertNotIn("\n    privileged:", compose)

        dotenv = (self.special_out / ".env").read_text(encoding="utf-8")
        self.assertIn("MODEL_PATH='", dotenv)
        self.assertIn("MODEL_HOST_PATH='", dotenv)
        self.assertIn("${COMPOSE_VALUE}", dotenv)
        self.assertIn("\\'", dotenv)

    def test_rejects_control_characters_and_invalid_cidr_before_render(self):
        bad_model = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/safe.gguf\n    privileged: true",
            "--out",
            str(self.special_out.relative_to(ROOT)),
        )
        self.assertNotEqual(bad_model.returncode, 0)
        self.assertIn("control characters", bad_model.stderr)
        self.assertFalse(self.special_out.exists())

        bad_cidr = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "lan",
            "--auth",
            "bearer-token",
            "--lan-allowlist",
            "192.168.1.0/24\nAPI_BEARER_TOKEN=attacker",
            "--out",
            str(self.special_out.relative_to(ROOT)),
        )
        self.assertNotEqual(bad_cidr.returncode, 0)
        self.assertIn("control characters", bad_cidr.stderr)
        self.assertFalse(self.special_out.exists())

        for bad_path in ("./models/nul\x00.gguf", "./models/carriage\rreturn.gguf"):
            with self.subTest(bad_path=repr(bad_path)):
                with self.assertRaisesRegex(ValueError, "control characters"):
                    build_context(
                        setup_name="chat",
                        profile_name="medium",
                        access="localhost",
                        model_path=bad_path,
                        auth="none",
                        lan_allowlist="",
                    )

    def test_generation_is_byte_deterministic(self):
        common = [
            "generate",
            "--preset",
            "ornith-9b",
            "--profile",
            "medium",
            "--access",
            "localhost",
        ]
        self.run_cli(
            *common,
            "--out",
            str(self.deterministic_a_out.relative_to(ROOT)),
            check=True,
        )
        self.run_cli(
            *common,
            "--out",
            str(self.deterministic_b_out.relative_to(ROOT)),
            check=True,
        )

        first = {
            path.relative_to(self.deterministic_a_out): path.read_bytes()
            for path in self.deterministic_a_out.rglob("*")
            if path.is_file()
        }
        second = {
            path.relative_to(self.deterministic_b_out): path.read_bytes()
            for path in self.deterministic_b_out.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first, second)
        manifest = json.loads(first[Path("manifest.json")])
        self.assertNotIn("generated_at", manifest)
        self.assertRegex(manifest["generation_fingerprint"], r"^[0-9a-f]{64}$")

    def test_rejects_lan_generation_without_auth_and_allowlist(self):
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "lan",
            "--out",
            str(self.invalid_lan_out.relative_to(ROOT)),
            "--dry-run",
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("LAN generation requires", combined)
        self.assertFalse(self.invalid_lan_out.exists())

    def test_rejects_lan_generation_with_blank_allowlist(self):
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "lan",
            "--auth",
            "bearer-token",
            "--lan-allowlist",
            "   ",
            "--out",
            str(self.invalid_lan_out.relative_to(ROOT)),
            "--dry-run",
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("LAN generation requires", combined)
        self.assertFalse(self.invalid_lan_out.exists())

    def test_rejects_lan_even_with_auth_and_allowlist_until_gateway_is_enforced(self):
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "lan",
            "--auth",
            "bearer-token",
            "--lan-allowlist",
            "192.168.1.0/24",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            str(self.invalid_lan_out.relative_to(ROOT)),
            "--dry-run",
        )

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("LAN generation requires an authenticated TLS gateway", combined)
        self.assertIn("mechanically enforced client allowlisting", combined)
        self.assertFalse(self.invalid_lan_out.exists())

    def _generate_security_fixture(self):
        shutil.rmtree(self.security_out, ignore_errors=True)
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            "./models/placeholder.gguf",
            "--out",
            str(self.security_out.relative_to(ROOT)),
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def _generate_runtime_fixture(self):
        shutil.rmtree(self.runtime_out, ignore_errors=True)
        result = self.run_cli(
            "generate",
            "--setup",
            "chat",
            "--profile",
            "medium",
            "--access",
            "localhost",
            "--model-path",
            str(self.spaced_model),
            "--out",
            str(self.runtime_out.relative_to(ROOT)),
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def _fake_runtime_env(self, fake_bin: Path, *, health="ok", response="ok"):
        docker = fake_bin / "docker"
        docker.write_text(
            """#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >>"${FAKE_DOCKER_LOG}"
if [ "${1:-}" = "info" ]; then
  [ "${FAKE_DAEMON:-ok}" = "ok" ]
  exit
fi
if [ "${1:-}" = "stats" ]; then
  printf '128MiB / 8GiB\\n'
  exit 0
fi
case "$*" in
  "compose version") printf 'Docker Compose fake\\n'; exit 0 ;;
  *" config --format json")
    python3 - <<'PY'
import json
import os
print(json.dumps({"services": {"llama-server": {
  "image": os.environ["FAKE_SERVING_IMAGE"],
  "ports": [{"host_ip": "127.0.0.1", "published": "8000", "target": 8000}],
  "user": "65532:65532",
  "privileged": False,
  "cap_drop": ["ALL"],
  "security_opt": ["no-new-privileges:true"],
  "read_only": True,
  "tmpfs": ["/tmp:size=256m"],
  "pids_limit": 256,
  "cpus": 6.0,
  "mem_limit": 8589934592,
  "volumes": [{"type": "bind", "source": os.environ["FAKE_MODEL_PATH"],
               "target": "/models/model.gguf", "read_only": True}],
  "command": ["--model", "/models/model.gguf"]
}}}))
PY
    exit 0 ;;
  *" ps -q llama-server") printf 'fake-container\\n'; exit 0 ;;
  *) exit 0 ;;
esac
""",
            encoding="utf-8",
        )
        curl = fake_bin / "curl"
        curl.write_text(
            """#!/usr/bin/env bash
set -eu
case "$*" in
  *"/health"*)
    [ "${FAKE_HEALTH:-ok}" = "ok" ]
    exit ;;
esac
out=""
previous=""
for argument in "$@"; do
  if [ "$previous" = "--output" ]; then out="$argument"; fi
  previous="$argument"
done
[ -n "$out" ] || exit 2
case "${FAKE_RESPONSE:-ok}" in
  ok) printf '{"choices":[{"message":{"content":"OK"}}]}' >"$out"
      printf '200 0.010 0.020' ;;
  malformed) printf '{"unexpected":true}' >"$out"
      printf '200 0.010 0.020' ;;
  status) printf '{"error":"failed"}' >"$out"
      printf '503 0.010 0.020' ;;
  transport) exit 7 ;;
esac
""",
            encoding="utf-8",
        )
        docker.chmod(0o755)
        curl.chmod(0o755)
        log = fake_bin / "docker.log"
        return {
            **dict(os.environ),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": str(log),
            "FAKE_MODEL_PATH": str(self.spaced_model.resolve()),
            "FAKE_SERVING_IMAGE": SERVING_IMAGE,
            "FAKE_HEALTH": health,
            "FAKE_RESPONSE": response,
        }, log

    def test_model_contract_and_validation_tiers_are_explicit(self):
        self._generate_runtime_fixture()
        manifest = json.loads((self.runtime_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["host_model_path"], str(self.spaced_model.resolve()))
        self.assertEqual(manifest["container_model_path"], "/models/model.gguf")
        compose = (self.runtime_out / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn(f"source: {json.dumps(str(self.spaced_model.resolve()))}", compose)
        self.assertIn("target: /models/model.gguf", compose)
        self.assertNotIn(self.spaced_model.read_text(encoding="utf-8"), compose)

        structure = self.run_cli(
            "validate", str(self.runtime_out.relative_to(ROOT)), "--tier", "structure"
        )
        self.assertEqual(structure.returncode, 0, structure.stderr)
        self.assertIn("structure valid", structure.stdout)
        self.assertIn("NOT VERIFIED", structure.stdout)

        with tempfile.TemporaryDirectory() as temporary:
            fake_bin = Path(temporary)
            env, _ = self._fake_runtime_env(fake_bin)
            host = self.run_cli(
                "validate",
                str(self.runtime_out.relative_to(ROOT)),
                "--tier",
                "host",
                env=env,
            )
            self.assertEqual(host.returncode, 0, host.stderr)
            self.assertIn("host ready", host.stdout)
            self.assertIn("runtime endpoint", host.stdout)

            runtime_ok = self.run_cli(
                "validate",
                str(self.runtime_out.relative_to(ROOT)),
                "--tier",
                "runtime",
                env=env,
            )
            self.assertEqual(runtime_ok.returncode, 0, runtime_ok.stderr)
            self.assertIn("runtime healthy", runtime_ok.stdout)

            env["FAKE_DAEMON"] = "down"
            runtime = self.run_cli(
                "validate",
                str(self.runtime_out.relative_to(ROOT)),
                "--tier",
                "runtime",
                env=env,
            )
            self.assertNotEqual(runtime.returncode, 0)
            self.assertIn("runtime not verified: Docker daemon unavailable", runtime.stderr)

    def test_host_tier_rejects_invalid_model_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake_bin = Path(temporary)
            env, _ = self._fake_runtime_env(fake_bin)
            unreadable = self.models_dir / f"runtime-unreadable-{os.getpid()}.gguf"
            wrong_extension = self.models_dir / f"runtime-model-{os.getpid()}.bin"
            missing = self.models_dir / f"runtime-missing-{os.getpid()}.gguf"
            unreadable.write_text("fixture", encoding="utf-8")
            wrong_extension.write_text("fixture", encoding="utf-8")
            unreadable.chmod(0)
            cases = [
                (missing, "does not exist"),
                (self.models_dir, "regular file"),
                (unreadable, "not readable"),
                (wrong_extension, "extension must be .gguf"),
            ]
            try:
                for model_path, expected in cases:
                    with self.subTest(model_path=model_path):
                        shutil.rmtree(self.runtime_out, ignore_errors=True)
                        generated = self.run_cli(
                            "generate",
                            "--setup",
                            "chat",
                            "--profile",
                            "medium",
                            "--access",
                            "localhost",
                            "--model-path",
                            str(model_path),
                            "--out",
                            str(self.runtime_out.relative_to(ROOT)),
                        )
                        self.assertEqual(generated.returncode, 0, generated.stderr)
                        env["FAKE_MODEL_PATH"] = str(model_path.resolve())
                        host = self.run_cli(
                            "validate",
                            str(self.runtime_out.relative_to(ROOT)),
                            "--tier",
                            "host",
                            env=env,
                        )
                        self.assertNotEqual(host.returncode, 0)
                        self.assertIn(expected, host.stderr)
            finally:
                unreadable.chmod(0o644)
                unreadable.unlink(missing_ok=True)
                wrong_extension.unlink(missing_ok=True)

    def test_generated_lifecycle_scripts_are_cwd_independent_bounded_and_stop(self):
        self._generate_runtime_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            unrelated = Path(temporary) / "unrelated"
            fake_bin = Path(temporary) / "bin"
            unrelated.mkdir()
            fake_bin.mkdir()
            env, log = self._fake_runtime_env(fake_bin)

            success = subprocess.run(
                [str(self.runtime_out / "scripts/start.sh")],
                cwd=unrelated,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertIn("Runtime healthy", success.stdout)

            env["FAKE_HEALTH"] = "down"
            env["AI_SERVER_READINESS_TIMEOUT_SECONDS"] = "1"
            env["AI_SERVER_READINESS_INTERVAL_SECONDS"] = "1"
            timeout = subprocess.run(
                [str(self.runtime_out / "scripts/start.sh")],
                cwd=ROOT,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(timeout.returncode, 0)
            self.assertIn("readiness timed out", timeout.stderr)
            self.assertIn("logs --tail 80 llama-server", log.read_text(encoding="utf-8"))

            stopped = subprocess.run(
                [str(self.runtime_out / "scripts/stop.sh")],
                cwd=unrelated,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            self.assertIn("down --timeout 30", log.read_text(encoding="utf-8"))

    def test_smoke_is_strict_and_emits_only_numeric_or_not_measured_evidence(self):
        self._generate_runtime_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            fake_bin = Path(temporary)
            env, _ = self._fake_runtime_env(fake_bin)
            smoke = subprocess.run(
                [str(self.runtime_out / "scripts/smoke.sh")],
                cwd=Path(temporary),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(smoke.returncode, 0, smoke.stderr)
            report_path = Path(smoke.stdout.strip().split("evidence: ", 1)[1])
            report = report_path.read_text(encoding="utf-8")
            self.assertRegex(report, r"TTFB p50 ms \| [0-9]+\.[0-9]+")
            self.assertRegex(report, r"Container memory MB \| [0-9]+\.[0-9]+")
            self.assertIn("Tokens per second | NOT_MEASURED", report)
            self.assertNotIn("placeholder", report.lower())

            env["FAKE_RESPONSE"] = "malformed"
            malformed = subprocess.run(
                [str(self.runtime_out / "scripts/smoke.sh")],
                cwd=ROOT,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(malformed.returncode, 0)
            self.assertIn("valid chat-completion JSON", malformed.stderr)

            env["FAKE_RESPONSE"] = "status"
            bad_status = subprocess.run(
                [str(self.runtime_out / "scripts/smoke.sh")],
                cwd=ROOT,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(bad_status.returncode, 0)
            self.assertIn("Expected HTTP 200", bad_status.stderr)

    def test_validator_rejects_secret_file_mode_and_placeholder_tokens(self):
        self._generate_security_fixture()
        env_path = self.security_out / ".env"

        env_path.chmod(0o644)
        mode_result = self.run_cli("validate", str(self.security_out.relative_to(ROOT)))
        self.assertNotEqual(mode_result.returncode, 0)
        self.assertIn(".env must have mode 0600", mode_result.stderr)

        env_path.chmod(0o600)
        with env_path.open("a", encoding="utf-8") as handle:
            handle.write("API_BEARER_TOKEN='change-me-strong-token'\n")
        token_result = self.run_cli("validate", str(self.security_out.relative_to(ROOT)))
        self.assertNotEqual(token_result.returncode, 0)
        self.assertIn("blank, weak, or placeholder bearer token", token_result.stderr)
        self.assertNotIn("change-me-strong-token", token_result.stderr)

    def test_validator_rejects_missing_or_inert_security_posture(self):
        self._generate_security_fixture()
        manifest_path = self.security_out / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("security_posture")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        missing = self.run_cli("validate", str(self.security_out.relative_to(ROOT)))
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("manifest missing key: security_posture", missing.stderr)

        self._generate_security_fixture()
        env_path = self.security_out / ".env"
        with env_path.open("a", encoding="utf-8") as handle:
            handle.write("LAN_ALLOWLIST='192.168.1.0/24'\n")
        inert = self.run_cli("validate", str(self.security_out.relative_to(ROOT)))
        self.assertNotEqual(inert.returncode, 0)
        self.assertIn("must not contain an inert LAN allowlist", inert.stderr)

    def _run_script(self, name, *args, check=True):
        result = subprocess.run(
            [str(ROOT / "scripts" / name), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"{name} failed: {result.stdout}\n{result.stderr}")
        return result

    def test_backup_restore_and_rollback_round_trip(self):
        self.run_cli(
            "generate",
            "--preset",
            "ornith-9b",
            "--out",
            str(self.ornith_out.relative_to(ROOT)),
            check=True,
        )
        with tempfile.TemporaryDirectory() as backup_root:
            self._run_script("backup_workspace.sh", str(self.ornith_out), backup_root)
            archives = list(Path(backup_root).glob("*.tar.gz"))
            self.assertEqual(len(archives), 1)
            archive = archives[0]
            self.assertTrue(archive.with_suffix(".gz.sha256").is_file())

            # A damaged workspace is fully recovered from the archive.
            (self.ornith_out / "README.md").write_text("corrupted", encoding="utf-8")
            self._run_script("restore_workspace.sh", str(archive), str(self.ornith_out))
            self.assertNotEqual(
                (self.ornith_out / "README.md").read_text(encoding="utf-8"), "corrupted"
            )
            self.run_cli("validate", str(self.ornith_out.relative_to(ROOT)), check=True)

            # A tampered archive must never reach the target directory.
            with archive.open("ab") as handle:
                handle.write(b"garbage")
            failed = self._run_script(
                "restore_workspace.sh", str(archive), str(self.ornith_out), check=False
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Checksum verification failed", failed.stderr)

        # --force regeneration leaves a recoverable copy that rollback restores.
        self.run_cli(
            "generate",
            "--preset",
            "smollm3-3b",
            "--out",
            str(self.ornith_out.relative_to(ROOT)),
            "--force",
            check=True,
        )
        replaced = json.loads((self.ornith_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(replaced["preset_alias"], "smollm3-3b")

        self._run_script("rollback_workspace.sh", str(self.ornith_out))
        restored = json.loads((self.ornith_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(restored["preset_alias"], "ornith-9b")
        self.run_cli("validate", str(self.ornith_out.relative_to(ROOT)), check=True)

    def test_generated_output_matches_golden_fixture(self):
        result = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "update_golden_fixture.py"), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        fixture = ROOT / "tests" / "golden" / "chat-ornith-medium-localhost"
        tracked = {
            path.relative_to(fixture).as_posix()
            for path in fixture.rglob("*")
            if path.is_file()
        }
        self.assertEqual(tracked, set(planned_files()))

    def test_sbom_is_current_and_pins_every_dependency(self):
        result = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "generate_sbom.py"), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        sbom = json.loads((ROOT / "sbom.json").read_text(encoding="utf-8"))
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        containers = [c for c in sbom["components"] if c["type"] == "container"]
        self.assertEqual(len(containers), 1)
        self.assertEqual(
            containers[0]["hashes"][0]["content"],
            SERVING_IMAGE.split("@sha256:", 1)[1],
        )
        for component in sbom["components"]:
            self.assertTrue(component.get("version"), component)

    def test_serving_image_is_pinned_by_digest(self):
        self.assertIn("@sha256:", SERVING_IMAGE)
        # The dead ggerganov repository must not come back by copy-paste.
        self.assertNotIn("ggerganov", SERVING_IMAGE)

        self.run_cli(
            "generate",
            "--preset",
            "ornith-9b",
            "--out",
            str(self.ornith_out.relative_to(ROOT)),
            check=True,
        )
        compose = (self.ornith_out / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn(f"    image: {SERVING_IMAGE}", compose)

        manifest = json.loads((self.ornith_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["serving_image"], SERVING_IMAGE)

        root_compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("@sha256:", root_compose)
        self.assertNotIn("ggerganov", root_compose)

    def test_validator_rejects_unpinned_manifest_image(self):
        self._generate_security_fixture()
        manifest_path = self.security_out / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["serving_image"] = "ghcr.io/ggml-org/llama.cpp:server"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        result = self.run_cli("validate", str(self.security_out.relative_to(ROOT)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("serving_image must match the pinned serving image", result.stderr)

    def test_validator_rejects_one_compose_security_mutation_at_a_time(self):
        mutations = [
            (
                '      - "127.0.0.1:8000:8000"',
                '      - "0.0.0.0:8000:8000"',
                "must bind explicitly to 127.0.0.1",
            ),
            (
                '    user: "65532:65532"',
                '    user: "0:0"',
                "must declare a non-root user and group",
            ),
            (
                "    cap_drop:\n      - ALL\n",
                "",
                "must drop ALL capabilities",
            ),
            (
                "    pids_limit: 256\n",
                "",
                "must set a positive PID limit",
            ),
            (
                "    mem_limit: 8g\n",
                "",
                "must set a positive mem_limit resource limit",
            ),
            (
                "        read_only: true",
                "        read_only: false",
                "must not have writable host bind mounts",
            ),
            (
                "\n    read_only: true\n",
                "\n    read_only: false\n",
                "root filesystem must be read-only",
            ),
            (
                "    security_opt:\n      - no-new-privileges:true\n",
                "",
                "must set no-new-privileges:true",
            ),
            (
                '      - "/models/model.gguf"',
                '      - "/models/different.gguf"',
                "model path must match manifest",
            ),
            (
                f"    image: {SERVING_IMAGE}",
                "    image: ghcr.io/ggml-org/llama.cpp:server",
                "Compose image must be the digest-pinned serving image",
            ),
        ]
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                self._generate_security_fixture()
                compose_path = self.security_out / "docker-compose.yml"
                compose = compose_path.read_text(encoding="utf-8")
                self.assertIn(old, compose)
                compose_path.write_text(compose.replace(old, new, 1), encoding="utf-8")

                result = self.run_cli("validate", str(self.security_out.relative_to(ROOT)))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
