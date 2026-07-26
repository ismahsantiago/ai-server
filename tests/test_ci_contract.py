import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class CICheckContractTests(unittest.TestCase):
    def test_ci_installs_the_exported_lock_with_hash_enforcement(self) -> None:
        root = Path(__file__).parents[1]
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        lock = (root / "requirements.lock").read_text(encoding="utf-8")

        self.assertIn(
            "pip install --require-hashes --requirement requirements.lock",
            workflow,
        )
        self.assertIn("cache-dependency-path: requirements.lock", workflow)
        logical_lines = lock.replace("\\\n", " ").splitlines()
        requirements = [
            line for line in logical_lines if line and not line.lstrip().startswith("#")
        ]
        self.assertGreater(len(requirements), 2)
        for requirement in requirements:
            with self.subTest(requirement=requirement.split()[0]):
                self.assertIn("==", requirement)
                self.assertIn("--hash=sha256:", requirement)

    def test_audit_checksum_is_opt_in_and_current_run_scoped(self) -> None:
        script = (Path(__file__).parents[1] / "scripts" / "ci.sh").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("audit_opencode_default_gpt-5_24-07-2026", script)
        self.assertIn('AUDIT_EVIDENCE_MANIFEST', script)
        self.assertIn("validate_audit_manifest.py", script)
        self.assertIn('AUDIT_DIR:-', script)
        self.assertIn('AUDIT_EVIDENCE_MANIFEST:-', script)

    def run_manifest_validator(self, audit_dir: Path, manifest: Path | None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["AUDIT_DIR"] = str(audit_dir)
        if manifest is None:
            environment.pop("AUDIT_EVIDENCE_MANIFEST", None)
        else:
            environment["AUDIT_EVIDENCE_MANIFEST"] = str(manifest)
        return subprocess.run(
            ["python3", "scripts/validate_audit_manifest.py"],
            cwd=Path(__file__).parents[1],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_partial_audit_opt_in_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_manifest_validator(Path(temporary), None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be set together", result.stderr)

    def test_manifest_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit_dir = Path(temporary) / "audit"
            audit_dir.mkdir()
            manifest = audit_dir / "evidence-manifest.sha256"
            manifest.write_text("0" * 64 + "  ../outside.txt\n", encoding="utf-8")
            result = self.run_manifest_validator(audit_dir, manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes AUDIT_DIR", result.stderr)

    def test_manifest_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            audit_dir = root / "audit"
            audit_dir.mkdir()
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            link = audit_dir / "linked.txt"
            link.symlink_to(outside)
            digest = hashlib.sha256(outside.read_bytes()).hexdigest()
            manifest = audit_dir / "evidence-manifest.sha256"
            manifest.write_text(f"{digest}  linked.txt\n", encoding="utf-8")
            result = self.run_manifest_validator(audit_dir, manifest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes AUDIT_DIR", result.stderr)

    def test_harness_guard_and_current_task_override_remain(self) -> None:
        script = (Path(__file__).parents[1] / "scripts" / "ci.sh").read_text(
            encoding="utf-8"
        )

        harness_start = script.index("if [ -f .pm-harness/bin/harness.py ]; then")
        harness_end = script.index("else\n  echo \"PM Harness not present", harness_start)
        harness_block = script[harness_start:harness_end]
        self.assertIn('HARNESS_PLAN_TASK:-', harness_block)
        self.assertIn(".pm-harness/bin/harness.py validate", harness_block)
        self.assertNotRegex(harness_block, r"TASK-[0-9]")
        self.assertIn("Path('.pm-harness/state').glob('TASK-*.json')", harness_block)
        self.assertIn("'in_review', 'approved', 'closed'", harness_block)
        self.assertIn("['python3', '.pm-harness/bin/harness.py'", harness_block)

    def test_doctor_smoke_checks_are_non_writing_and_pre_harness(self) -> None:
        script = (Path(__file__).parents[1] / "scripts" / "ci.sh").read_text(
            encoding="utf-8"
        )

        text_smoke = "python3 -m ai_server_generator doctor --no-write"
        json_smoke = f"{text_smoke} --format json >/dev/null"
        self.assertEqual(script.count(text_smoke), 2)
        self.assertIn(json_smoke, script)
        self.assertLess(
            script.index(text_smoke),
            script.index("if [ -f .pm-harness/bin/harness.py ]; then"),
        )

    def test_generated_fixture_model_stays_under_the_owned_models_root(self) -> None:
        script = (Path(__file__).parents[1] / "scripts" / "ci.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn('mktemp -d "${PROJECT_ROOT}/models/.ci-fixture.XXXXXX"', script)
        self.assertIn('MODEL_FIXTURE="${MODEL_FIXTURE_DIR}/fixture.gguf"', script)
        self.assertNotIn('MODEL_FIXTURE="${WORK_DIR}/fixture.gguf"', script)
        self.assertIn('rm -rf -- "${WORK_DIR}" "${MODEL_FIXTURE_DIR}"', script)
