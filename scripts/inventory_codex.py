#!/usr/bin/env python3
"""Create an anonymous, metadata-only inventory of portable Codex candidates."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable


SECRET_NAMES = {
    ".env",
    "auth.json",
    "credentials.json",
    "cookies.json",
    "api-key.txt",
    "access-token.txt",
}

VOLATILE_DIRS = {
    ".git",
    ".sandbox",
    ".sandbox-bin",
    ".sandbox-secrets",
    ".system",
    ".tmp",
    "archived_sessions",
    "browser",
    "cache",
    "computer-use",
    "generated_images",
    "logs",
    "node_repl",
    "packages",
    "process_manager",
    "sessions",
    "sqlite",
    "thread-writer-locks",
    "tmp",
}

VOLATILE_SUFFIXES = {
    ".db",
    ".log",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
}

LICENSE_NAMES = {
    "copying",
    "copying.md",
    "license",
    "license.md",
    "license.txt",
}


def logical_join(root_name: str, relative: Path) -> str:
    suffix = relative.as_posix()
    return root_name if suffix == "." else f"{root_name}/{suffix}"


def classify_name(path: Path) -> str:
    lower_name = path.name.lower()
    if lower_name in SECRET_NAMES:
        return "secret-or-private"
    if any(part.lower() in VOLATILE_DIRS for part in path.parts):
        return "generated-or-volatile"
    if lower_name.endswith(tuple(VOLATILE_SUFFIXES)) or ".sqlite-" in lower_name:
        return "generated-or-volatile"
    if any(word in lower_name for word in ("credential", "private-key", "access-token")):
        return "secret-or-private"
    return "candidate"


def summarize_tree(root: Path, logical_root: str) -> dict[str, object]:
    result: dict[str, object] = {
        "root": logical_root,
        "exists": root.exists(),
        "candidate_files": 0,
        "candidate_bytes": 0,
        "excluded_files": 0,
        "symlinks": 0,
        "licenses": [],
    }
    if not root.exists():
        return result

    if root.is_file():
        classification = classify_name(Path(root.name))
        if classification == "candidate":
            result["candidate_files"] = 1
            try:
                result["candidate_bytes"] = root.stat().st_size
            except OSError:
                pass
            if root.name.lower() in LICENSE_NAMES:
                result["licenses"] = [logical_root]
        else:
            result["excluded_files"] = 1
        return result

    licenses: list[str] = []
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_current = current_path.relative_to(root)

        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            child = current_path / dirname
            relative_child = relative_current / dirname
            if child.is_symlink():
                result["symlinks"] = int(result["symlinks"]) + 1
                continue
            if classify_name(relative_child) == "candidate":
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            child = current_path / filename
            relative_child = relative_current / filename
            classification = classify_name(relative_child)
            if child.is_symlink():
                result["symlinks"] = int(result["symlinks"]) + 1
                continue
            if classification != "candidate":
                result["excluded_files"] = int(result["excluded_files"]) + 1
                continue
            result["candidate_files"] = int(result["candidate_files"]) + 1
            try:
                result["candidate_bytes"] = int(result["candidate_bytes"]) + child.stat().st_size
            except OSError:
                pass
            if filename.lower() in LICENSE_NAMES:
                licenses.append(logical_join(logical_root, relative_child))

    result["licenses"] = licenses
    return result


def existing_children(root: Path, names: Iterable[str], logical_root: str) -> list[dict[str, object]]:
    summaries = []
    for name in names:
        child = root / name
        summaries.append(summarize_tree(child, f"{logical_root}/{name}"))
    return summaries


def build_inventory(codex_home: Path, agents_home: Path, plugin_sources: list[Path]) -> dict[str, object]:
    codex_candidates = existing_children(
        codex_home,
        ["AGENTS.md", "config.toml", "agents", "hooks", "rules", "skills"],
        "CODEX_HOME",
    )
    agent_candidates = existing_children(agents_home, ["skills"], "AGENTS_HOME")
    plugin_candidates = [
        summarize_tree(path, f"PLUGIN_SOURCE_{index}")
        for index, path in enumerate(plugin_sources, start=1)
    ]

    return {
        "schema_version": 1,
        "privacy": {
            "absolute_source_paths_included": False,
            "file_contents_read": False,
            "symlink_targets_followed": False,
        },
        "candidates": codex_candidates + agent_candidates + plugin_candidates,
        "excluded_categories": [
            "authentication-and-credentials",
            "sessions-and-history",
            "databases-and-logs",
            "caches-and-runtime-packages",
            "sandbox-and-browser-state",
            "device-and-installation-state",
            "project-trust-and-recent-paths",
        ],
        "notes": [
            "Candidate status does not establish authorship or redistribution rights.",
            "Inspect provenance before copying any skill or plugin source.",
            "Do not commit this inventory if candidate names are private.",
        ],
    }


def parse_args() -> argparse.Namespace:
    default_codex = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=default_codex)
    parser.add_argument("--agents-home", type=Path, default=Path.home() / ".agents")
    parser.add_argument(
        "--plugin-source",
        action="append",
        default=[],
        type=Path,
        help="User-authored plugin source root; repeat as needed.",
    )
    parser.add_argument("--output", type=Path, help="Write JSON to this non-repository path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_inventory(
        args.codex_home.expanduser(),
        args.agents_home.expanduser(),
        [path.expanduser() for path in args.plugin_source],
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

