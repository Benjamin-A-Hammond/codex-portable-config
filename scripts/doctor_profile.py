#!/usr/bin/env python3
"""Check a generated profile without reading or printing secret values."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tomllib
from pathlib import Path


def check(profile: Path) -> list[str]:
    findings: list[str] = []
    required = [
        profile / "config" / "config.portable.toml",
        profile / "manifests" / "skills.json",
        profile / "manifests" / "plugins.json",
        profile / "manifests" / "mcp.json",
        profile / "manifests" / "unresolved.json",
    ]
    for path in required:
        if not path.is_file():
            findings.append(f"missing: {path.relative_to(profile).as_posix()}")
    config_path = profile / "config" / "config.portable.toml"
    if config_path.is_file():
        try:
            with config_path.open("rb") as handle:
                tomllib.load(handle)
        except Exception:
            findings.append("invalid TOML: config/config.portable.toml")

    loaded: dict[str, dict] = {}
    for name in ("skills", "plugins", "mcp", "unresolved"):
        path = profile / "manifests" / f"{name}.json"
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError
            loaded[name] = value
        except (OSError, ValueError, json.JSONDecodeError):
            findings.append(f"invalid JSON: manifests/{name}.json")

    for entry in loaded.get("skills", {}).get("skills", []):
        if entry.get("kind") == "owned" and not (profile / str(entry.get("path", ""))).is_dir():
            findings.append(f"missing owned Skill source: {entry.get('name', 'unnamed')}")
        if entry.get("kind") == "external" and not entry.get("source"):
            findings.append(f"external Skill has no source: {entry.get('name', 'unnamed')}")
    for entry in loaded.get("plugins", {}).get("plugins", []):
        if entry.get("kind") == "owned" and not (profile / str(entry.get("path", ""))).is_dir():
            findings.append(f"missing owned Plugin source: {entry.get('id', 'unnamed')}")
        if entry.get("kind") == "external" and not entry.get("source"):
            findings.append(f"external Plugin has no source: {entry.get('id', 'unnamed')}")
    for entry in loaded.get("mcp", {}).get("servers", []):
        if entry.get("transport") == "stdio" and entry.get("command") and shutil.which(str(entry["command"])) is None:
            findings.append(f"MCP executable not found: {entry.get('name', 'unnamed')}")
        if entry.get("env_vars"):
            missing = [name for name in entry["env_vars"] if not os.environ.get(str(name))]
            if missing:
                findings.append(f"MCP environment setup required: {entry.get('name', 'unnamed')} ({', '.join(sorted(missing))})")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    findings = check(args.profile.expanduser().resolve())
    if findings:
        for item in findings:
            print(item)
        return 1
    print("doctor passed: profile structure is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
