from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


export_profile = load_module("export_profile", ROOT / "scripts" / "export_profile.py")
restore_profile = load_module("restore_profile", ROOT / "scripts" / "restore_profile.py")


class ProfileTests(unittest.TestCase):
    def test_export_copies_owned_source_and_references_external_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            codex = root / "codex"
            agents = root / "agents"
            owned = root / "owned-skill"
            owned.mkdir(parents=True)
            (owned / "SKILL.md").write_text("---\nname: owned\ndescription: test\n---\n", encoding="utf-8")
            (codex / "skills" / "external-local").mkdir(parents=True)
            (codex / "skills" / "external-local" / "SKILL.md").write_text("external", encoding="utf-8")
            (codex / "config.toml").parent.mkdir(parents=True, exist_ok=True)
            (codex / "config.toml").write_text(
                'model = "gpt-test"\napi_key = "must-not-export"\n'
                'environment = { OPAQUE = "must-not-export-either" }\n'
                '[mcp_servers.sample]\ncommand = "npx"\nargs = ["sample-mcp"]\n'
                'env = { SERVICE_TOKEN = "secret-value" }\n',
                encoding="utf-8",
            )
            output = root / "profile"
            result = export_profile.build_profile(SimpleNamespace(
                output=output,
                codex_home=codex,
                agents_home=agents,
                config=None,
                owned_skill=[f"owned={owned}"],
                owned_plugin=[],
                external_skill=["external|https://github.com/OWNER/skill|v1|skills/external|1.0"],
                external_plugin=[],
                force=False,
            ))
            self.assertEqual(2, result["skills"])
            self.assertTrue((output / "skills" / "owned" / "SKILL.md").is_file())
            self.assertFalse((output / "skills" / "external-local").exists())
            config_text = (output / "config" / "config.portable.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-test"', config_text)
            self.assertNotIn("must-not-export", config_text)
            self.assertNotIn("must-not-export-either", config_text)
            mcp = json.loads((output / "manifests" / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(["SERVICE_TOKEN"], mcp["servers"][0]["env_vars"])
            self.assertNotIn("secret-value", json.dumps(mcp))
            unresolved = json.loads((output / "manifests" / "unresolved.json").read_text(encoding="utf-8"))
            self.assertTrue(any(item["name"] == "external-local" for item in unresolved["items"]))
            profile_readme = (output / "README.md").read_text(encoding="utf-8")
            self.assertIn("<PROFILE_REPOSITORY_URL>", profile_readme)
            self.assertIn("GitHub authentication", profile_readme)
            self.assertIn("OAuth", profile_readme)
            self.assertIn("machine-local MCP", profile_readme)
            self.assertIn("Do not apply changes", profile_readme)

    def test_restore_merge_reports_conflict_and_preserves_equal_values(self):
        patch, conflicts = restore_profile.merge_patch(
            {"model": "same", "features": {"one": True}},
            {"model": "same", "features": {"one": True, "two": False}, "approval_policy": "never"},
        )
        self.assertEqual([], conflicts)
        self.assertEqual({"features": {"two": False}, "approval_policy": "never"}, patch)
        _, conflicts = restore_profile.merge_patch({"model": "old"}, {"model": "new"})
        self.assertEqual(["model"], conflicts)

    def test_restore_mcp_never_includes_secret_values(self):
        config = restore_profile.mcp_to_config({
            "servers": [{"name": "sample", "transport": "stdio", "command": "npx", "args": ["sample"], "env_vars": ["TOKEN"]}],
        })
        rendered = json.dumps(config)
        self.assertIn("TOKEN", rendered)
        self.assertNotIn("secret", rendered.casefold())

    def test_dry_run_previews_owned_skill_without_copying_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = root / "profile"
            source = profile / "skills" / "owned"
            destination_home = root / "codex"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: owned\ndescription: test\n---\n", encoding="utf-8")
            plan = []

            restore_profile.preview_owned_skills(
                profile,
                destination_home,
                [{"name": "owned", "kind": "owned", "path": "skills/owned"}],
                plan,
            )

            self.assertEqual(1, len(plan))
            self.assertIn("INSTALL owned Skill", plan[0])
            self.assertFalse((destination_home / "skills" / "owned").exists())


if __name__ == "__main__":
    unittest.main()
