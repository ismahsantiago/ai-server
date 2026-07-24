import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class CliTests(unittest.TestCase):
    def run_cli(self, *args, check=False):
        result = subprocess.run(
            [PYTHON, "-m", "ai_server_generator", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"command failed: {' '.join(args)}\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def setUp(self):
        self.generated_root = ROOT / "generated"
        self.dry_run_out = self.generated_root / "test-dry-run"
        self.localhost_out = self.generated_root / "test-chat-medium-localhost"
        self.invalid_lan_out = self.generated_root / "test-invalid-lan-no-auth"
        self.ornith_out = self.generated_root / "test-ornith-medium-localhost"
        self.wizard_out = self.generated_root / "test-wizard-ornith-medium-localhost"
        self.wizard_overwrite_out = self.generated_root / "test-wizard-overwrite-ornith-medium-localhost"
        self.all_outputs = [
            self.dry_run_out,
            self.localhost_out,
            self.invalid_lan_out,
            self.ornith_out,
            self.wizard_out,
            self.wizard_overwrite_out,
        ]
        for path in self.all_outputs:
            shutil.rmtree(path, ignore_errors=True)

        # Wizard preflight expects ./models/<preset>.gguf to exist.
        # We create a tiny dummy file for the preset(s) used in tests.
        self.models_dir = ROOT / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        (self.models_dir / "ornith-9b.gguf").write_text("dummy", encoding="utf-8")

    def tearDown(self):
        for path in self.all_outputs:
            shutil.rmtree(path, ignore_errors=True)

        # Keep repo clean: remove dummy models added for tests.
        try:
            (self.models_dir / "ornith-9b.gguf").unlink(missing_ok=True)
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
        self.assertIn("GO", result.stdout)
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
                    self.assertIn("Decision: GO", result.stdout)

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
            "scripts/start_serving.sh",
            "scripts/smoke_benchmark.sh",
            "scripts/validate_host.sh",
        ]
        for rel in required:
            self.assertTrue((self.localhost_out / rel).is_file(), rel)

        manifest = json.loads((self.localhost_out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["setup"], "chat")
        self.assertEqual(manifest["profile"], "medium")
        self.assertEqual(manifest["access"], "localhost")
        self.assertEqual(manifest["quick_commands"]["start"], "./scripts/start.sh")
        self.assertEqual(manifest["quick_commands"]["validate"], "./scripts/validate.sh")
        self.assertEqual(manifest["quick_commands"]["smoke"], "./scripts/smoke.sh")

        validation = self.run_cli("validate", str(self.localhost_out.relative_to(ROOT)), check=True)
        self.assertIn("valid", validation.stdout.lower())

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

    def test_wizard_overwrite_when_dir_exists(self):
        self.wizard_overwrite_out.mkdir(parents=True, exist_ok=True)

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

        # With --overwrite it should succeed.
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
        self.assertEqual(result2.returncode, 0, msg=result2.stdout + result2.stderr)
        self.assertTrue((self.wizard_overwrite_out / "docker-compose.yml").is_file())

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


if __name__ == "__main__":
    unittest.main()
