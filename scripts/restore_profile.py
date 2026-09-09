#!/usr/bin/env python3
"""Preview or apply a generated Codex profile without overwriting local state."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from export_profile import render_toml
except ImportError:  # pragma: no cover
    from scripts.export_profile import render_toml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    if tomllib is None:
        raise RuntimeError("Python 3.11 or newer is required for TOML restore")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def merge_patch(existing: Any, desired: Any, path: tuple[str, ...] = ()) -> tuple[Any, list[str]]:
    """Return values missing from existing and a list of true conflicts."""
    if isinstance(desired, dict):
        if existing is None:
            return desired, []
        if not isinstance(existing, dict):
            return None, [".".join(path)]
        patch: dict[str, Any] = {}
        conflicts: list[str] = []
        for key, value in desired.items():
            if key not in existing:
                patch[key] = value
                continue
            child_patch, child_conflicts = merge_patch(existing[key], value, path + (str(key),))
            conflicts.extend(child_conflicts)
            if child_patch not in (None, {}, []):
                patch[key] = child_patch
        return patch, conflicts
    if existing == desired:
        return None, []
    return None, [".".join(path)]


def mcp_to_config(manifest: dict[str, Any]) -> dict[str, Any]:
    servers: dict[str, Any] = {}
    for entry in manifest.get("servers", []):
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        server: dict[str, Any] = {}
        if entry.get("transport") == "remote" and entry.get("source"):
            server["url"] = entry["source"]
        elif entry.get("transport") == "stdio":
            if entry.get("command"):
                server["command"] = entry["command"]
            if entry.get("args"):
                server["args"] = entry["args"]
        if isinstance(entry.get("config"), dict):
            server.update(entry["config"])
        # Do not write secret values. The manifest remains the source of truth for names.
        if entry.get("env_vars"):
            server["env_vars"] = entry["env_vars"]
        servers[str(entry["name"])] = server
    return {"mcp_servers": servers} if servers else {}


def external_actions(skills: dict[str, Any], plugins: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for entry in skills.get("skills", []):
        if entry.get("kind") == "external" and entry.get("source"):
            source = str(entry["source"])
            actions.append(f"skill-installer install {source}")
    for entry in plugins.get("plugins", []):
        if entry.get("kind") == "external":
            label = entry.get("id", "unnamed-plugin")
            source = entry.get("source") or "<missing-source>"
            actions.append(f"install or connect Plugin {label} from {source} using the supported Plugin mechanism")
    return actions


def prepare_profile(args: argparse.Namespace) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if args.profile:
        return args.profile.expanduser().resolve(), None
    if not args.profile_url:
        raise ValueError("provide --profile PATH or --profile-url URL")
    temporary = tempfile.TemporaryDirectory(prefix="codex-profile-")
    target = Path(temporary.name) / "profile"
    command = ["git", "clone", "--depth", "1", args.profile_url, str(target)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        temporary.cleanup()
        raise RuntimeError(completed.stderr.strip() or "git clone failed")
    return target, temporary


def apply_owned_skills(profile: Path, codex_home: Path, entries: list[dict[str, Any]], plan: list[str]) -> None:
    destination_root = codex_home / "skills"
    destination_root.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if entry.get("kind") != "owned" or not entry.get("path"):
            continue
        source = profile / str(entry["path"])
        destination = destination_root / str(entry["name"])
        if destination.exists():
            plan.append(f"SKIP existing Skill: {destination}")
            continue
        shutil.copytree(source, destination)
        plan.append(f"INSTALLED owned Skill: {destination}")


def apply_owned_plugins(profile: Path, destination_root: Path | None, entries: list[dict[str, Any]], plan: list[str]) -> None:
    owned = [entry for entry in entries if entry.get("kind") == "owned" and entry.get("path")]
    if not owned:
        return
    if destination_root is None:
        plan.append("MANUAL: provide --plugin-dest to install owned Plugin source")
        return
    destination_root.mkdir(parents=True, exist_ok=True)
    for entry in owned:
        source = profile / str(entry["path"])
        destination = destination_root / str(entry["id"])
        if destination.exists():
            plan.append(f"SKIP existing Plugin: {destination}")
            continue
        shutil.copytree(source, destination)
        plan.append(f"INSTALLED owned Plugin source: {destination}")


def apply_config_sources(profile: Path, codex_home: Path, plan: list[str]) -> None:
    config_root = profile / "config"
    for relative in ("AGENTS.md", "rules", "agents", "hooks"):
        source = config_root / relative
        destination = codex_home / relative
        if not source.exists():
            continue
        if destination.exists():
            plan.append(f"SKIP existing config source: {destination}")
            continue
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        plan.append(f"INSTALLED config source: {destination}")


def main() -> int:
    args = parse_args()
    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        profile, temporary = prepare_profile(args)
        skills = read_json(profile / "manifests" / "skills.json")
        plugins = read_json(profile / "manifests" / "plugins.json")
        mcp = read_json(profile / "manifests" / "mcp.json")
        unresolved = read_json(profile / "manifests" / "unresolved.json")
        desired = read_toml(profile / "config" / "config.portable.toml")
        mcp_config = mcp_to_config(mcp)
        desired = {**desired, **mcp_config}
        codex_home = args.codex_home.expanduser().resolve()
        destination_config = codex_home / "config.toml"
        existing = read_toml(destination_config)
        patch, conflicts = merge_patch(existing, desired)
        actions = external_actions(skills, plugins)
        plan: list[str] = []
        if conflicts:
            plan.extend(f"CONFLICT config key: {item}" for item in conflicts)
        elif patch:
            plan.append(f"MERGE config values into {destination_config}")
        for item in unresolved.get("items", []):
            plan.append(f"UNRESOLVED {item.get('kind', 'item')}: {item.get('name', 'unnamed')} ({item.get('reason', 'review required')})")
        plan.extend(f"MANUAL: {item}" for item in actions)
        if not args.apply:
            print(json.dumps({"mode": "dry-run", "profile": str(profile), "plan": plan, "conflicts": conflicts}, indent=2, ensure_ascii=False))
            return 1 if conflicts or unresolved.get("items") else 0
        if conflicts:
            print("error: restore stopped because destination configuration conflicts with the profile", file=sys.stderr)
            for item in conflicts:
                print(f"  {item}", file=sys.stderr)
            return 3
        if unresolved.get("items") and not args.allow_unresolved:
            print("error: unresolved Skill/Plugin sources remain; use --allow-unresolved only after review", file=sys.stderr)
            return 3

        if patch:
            destination_config.parent.mkdir(parents=True, exist_ok=True)
            if destination_config.exists():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                backup = destination_config.with_name(f"config.toml.before-codex-portable-{stamp}")
                shutil.copy2(destination_config, backup)
                plan.append(f"BACKUP {backup}")
            with destination_config.open("a", encoding="utf-8", newline="\n") as handle:
                if destination_config.stat().st_size:
                    handle.write("\n")
                handle.write(render_toml(patch))
        apply_owned_skills(profile, codex_home, skills.get("skills", []), plan)
        apply_owned_plugins(profile, args.plugin_dest.expanduser().resolve() if args.plugin_dest else None, plugins.get("plugins", []), plan)
        apply_config_sources(profile, codex_home, plan)
        print(json.dumps({"mode": "apply", "profile": str(profile), "plan": plan, "manual_actions": actions}, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            temporary.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--profile", type=Path)
    source.add_argument("--profile-url")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--plugin-dest", type=Path, help="Destination for explicitly owned Plugin source")
    parser.add_argument("--apply", action="store_true", help="Apply after the dry-run plan has been reviewed")
    parser.add_argument("--allow-unresolved", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
