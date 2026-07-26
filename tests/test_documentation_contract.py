import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_human_guide_matches_localhost_operator_contract(self):
        guide = (ROOT / "docs" / "human-guide.md").read_text(encoding="utf-8")

        self.assertIn("It never reports `GO`", guide)
        self.assertIn("LAN status: planned and blocked", guide)
        self.assertIn("Both `matrix` and\n`generate` refuse `--access lan`", guide)
        self.assertNotIn("--access lan --auth", guide)
        self.assertNotIn("cp models/", guide)
        self.assertIn('"$WORKSPACE/scripts/start.sh"', guide)
        self.assertIn('"$WORKSPACE/scripts/smoke.sh"', guide)
        self.assertIn('"$WORKSPACE/scripts/stop.sh"', guide)

    def test_readme_distinguishes_cli_subcommands_from_generated_scripts(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "there are no\n`ai_server_generator start`, `smoke`, or `stop` subcommands",
            readme,
        )
        self.assertIn("generated/<workspace>/scripts/start.sh", readme)
        self.assertIn('MODEL="$PWD/models/<approved-model>.gguf"', readme)
        self.assertIn('--models-path "$PWD/models"', readme)
        self.assertNotIn("/srv/ai-server/models", readme)
        self.assertNotIn("ssh -L", readme)
        self.assertNotIn("git checkout db93bbc", readme)
        self.assertNotIn("Validado antes del commit", readme)
        self.assertIn("Do not use `--access lan`", readme)

    def test_generated_readme_exposes_reproducibility_and_model_mount_contract(self):
        template = (ROOT / "templates" / "chat" / "README.md.j2").read_text(
            encoding="utf-8"
        )

        self.assertIn("{{ serving_image }}", template)
        self.assertIn("{{ generation_fingerprint }}", template)
        self.assertIn("{{ host_model_path }}", template)
        self.assertIn("{{ container_model_path }}", template)
        self.assertIn("Do not copy the model into this workspace", template)


if __name__ == "__main__":
    unittest.main()
