import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / ".pm-harness" / "bin" / "harness_core.py"


class HarnessAgentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("task_harness_core", CORE_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load harness core")
        cls.core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.core)
        cls.core.configure(
            {
                "pack_id": "pm",
                "name": "PM Harness",
                "root_dir": ".pm-harness",
                "root_agent": "pm-orchestrator",
                "project_json": "harness.json",
                "spec_file": "HARNESS-SPEC.md",
                "cli_name": "harness.py",
            }
        )

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.harness = self.project / ".pm-harness"
        (self.harness / "adapters").mkdir(parents=True)
        (self.project / ".opencode" / "skills" / "pm").mkdir(parents=True)
        (self.project / ".opencode" / "skills" / "pm" / "SKILL.md").write_text(
            "installed", encoding="utf-8"
        )
        (self.harness / "harness.json").write_text(
            json.dumps(
                {
                    "roster": [
                        {
                            "manager": "engineering-manager",
                            "role": "engineering",
                            "agents": [
                                {
                                    "name": "worker",
                                    "role": "implementation",
                                    "active": True,
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (self.harness / "adapters" / "adapters.json").write_text(
            json.dumps(
                {
                    "platforms": {
                        "opencode": {
                            "files": [
                                {
                                    "dst": ".opencode/skills/pm/SKILL.md",
                                }
                            ],
                            "agents_dir": ".opencode/agents",
                            "agent_format": "opencode",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        self.args = type("Args", (), {"platform": "opencode"})()
        with contextlib.redirect_stdout(io.StringIO()):
            self.core.agents_materialize(str(self.harness), self.args)

    def tearDown(self):
        self.temporary.cleanup()

    def assert_check_fails(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(io.StringIO()):
                self.core.agents_check(str(self.harness), self.args)

    def test_check_rejects_empty_wrong_mode_tools_role_and_marker(self):
        agent = self.project / ".opencode" / "agents" / "worker.md"
        original = agent.read_text(encoding="utf-8")
        mutations = [
            "",
            original.replace("mode: subagent", "mode: primary"),
            original.replace("  task: false", "  task: true"),
            original.replace("implementation", "stale-role"),
            original.replace("PM-HARNESS:AGENT", "OTHER-HARNESS:AGENT"),
            original.replace("---\n", "", 1),
        ]
        for content in mutations:
            with self.subTest(content=content[:40]):
                agent.write_text(content, encoding="utf-8")
                self.assert_check_fails()
                agent.write_text(original, encoding="utf-8")

    def test_materialization_is_complete_and_leaves_no_temporary_file(self):
        agents_dir = self.project / ".opencode" / "agents"
        with contextlib.redirect_stdout(io.StringIO()):
            self.core.agents_materialize(str(self.harness), self.args)
            self.core.agents_check(str(self.harness), self.args)
        self.assertEqual(list(agents_dir.glob("*.tmp")), [])

    def test_check_rejects_stale_managed_agent(self):
        agents_dir = self.project / ".opencode" / "agents"
        source = agents_dir / "worker.md"
        (agents_dir / "retired.md").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.assert_check_fails()


if __name__ == "__main__":
    unittest.main()
