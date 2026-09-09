from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


inventory_codex = load_module("inventory_codex", ROOT / "scripts" / "inventory_codex.py")
audit_repository = load_module("audit_repository", ROOT / "scripts" / "audit_repository.py")


class InventoryTests(unittest.TestCase):
    def test_inventory_uses_logical_roots_and_excludes_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            codex_home = base / "private-codex-home"
            agents_home = base / "private-agents-home"
            (codex_home / "sessions").mkdir(parents=True)
            (codex_home / "sessions" / "session.jsonl").write_text("private", encoding="utf-8")
            (codex_home / "config.toml").write_text('model = "MODEL"\n', encoding="utf-8")
            (agents_home / "skills" / "sample").mkdir(parents=True)
            (agents_home / "skills" / "sample" / "SKILL.md").write_text(
                "---\nname: sample\ndescription: Sample workflow.\n---\n",
                encoding="utf-8",
            )

            payload = inventory_codex.build_inventory(codex_home, agents_home, [])
            rendered = json.dumps(payload)

            self.assertNotIn(str(base), rendered)
            self.assertIn("CODEX_HOME/config.toml", rendered)
            self.assertIn("AGENTS_HOME/skills", rendered)
            self.assertNotIn("session.jsonl", rendered)


class AuditTests(unittest.TestCase):
    def test_clean_placeholders_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config.toml").write_text(
                '[mcp_servers.sample]\nurl = "https://example.com/mcp"\n'
                'bearer_token_env_var = "EXAMPLE_TOKEN"\n',
                encoding="utf-8",
            )
            self.assertEqual([], audit_repository.audit(root))

    def test_forbidden_state_and_literal_secret_are_reported_without_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "auth.json").write_text("{}", encoding="utf-8")
            secret_value = "literal-value-that-must-not-be-echoed"
            assignment = "api_" + "key = \"" + secret_value + "\"\n"
            (root / "settings.toml").write_text(assignment, encoding="utf-8")

            findings = audit_repository.audit(root)
            codes = {item.code for item in findings}
            rendered = json.dumps([audit_repository.asdict(item) for item in findings])

            self.assertIn("forbidden-file", codes)
            self.assertIn("literal-secret-assignment", codes)
            self.assertNotIn(secret_value, rendered)


if __name__ == "__main__":
    unittest.main()

