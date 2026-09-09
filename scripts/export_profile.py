#!/usr/bin/env python3
"""Export a data-first Codex profile with explicit ownership boundaries."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any


SECRET_KEY = re.compile(r"(?i)(?:secret|token|password|passwd|api[_-]?key|private[_-]?key|cookie|credential|authorization)")
MACHINE_KEY = re.compile(r"(?i)^(?:cwd|working[_-]?directory|executable|binary|home|path|root|socket)$")
ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|/|\\\\)")
VOLATILE_NAMES = {".git", ".sandbox", ".sandbox-bin", "cache", "logs", "packages", "sessions", "sqlite"}
BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def parse_pipe_spec(raw: str, fields: list[str]) -> dict[str, Any]:
    parts = raw.split("|")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"expected {'|'.join(fields[:2])}[|...], got {raw!r}")
    result: dict[str, Any] = {fields[index]: parts[index] if index < len(parts) and parts[index] else None for index in range(len(fields))}
    return result


def parse_owned(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise ValueError(f"expected NAME=PATH, got {raw!r}")
    name, source = raw.split("=", 1)
    if not name or not source:
        raise ValueError(f"expected NAME=PATH, got {raw!r}")
    return name, Path(source).expanduser().resolve()


def is_secret_key(key: str) -> bool:
    return bool(SECRET_KEY.search(key))


def sanitize_value(value: Any, path: tuple[str, ...], warnings: list[str]) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if key_text == "mcp_servers":
                continue
            if key_text in {"projects", "marketplaces"} or key_text.casefold() == "perpath":
                warnings.append(f"excluded machine-local state: {'.'.join(path + (key_text,))}")
                continue
            if key_text.casefold() in {"env", "environment", "headers", "http_headers"}:
                warnings.append(f"excluded environment/header values: {'.'.join(path + (key_text,))}")
                continue
            if is_secret_key(key_text):
                warnings.append(f"excluded secret-like setting: {'.'.join(path + (key_text,))}")
                continue
            if MACHINE_KEY.match(key_text):
                warnings.append(f"excluded machine-local setting: {'.'.join(path + (key_text,))}")
                continue
            clean[key_text] = sanitize_value(child, path + (key_text,), warnings)
        return clean
    if isinstance(value, list):
        return [sanitize_value(child, path, warnings) for child in value]
    if isinstance(value, str) and ABSOLUTE_PATH.match(value):
        warnings.append(f"excluded absolute path value: {'.'.join(path)}")
        return "${LOCAL_PATH}"
    return value


def safe_mcp_args(args: Any, warnings: list[str], server: str) -> list[Any]:
    if not isinstance(args, list):
        return []
    result: list[Any] = []
    for index, value in enumerate(args):
        if isinstance(value, str) and (ABSOLUTE_PATH.match(value) or is_secret_key(value)):
            warnings.append(f"MCP {server}: excluded local or secret argument at index {index}")
            continue
        result.append(value)
    return result


def extract_mcp(config: dict[str, Any], warnings: list[str]) -> list[dict[str, Any]]:
    raw_servers = config.get("mcp_servers", {})
    if not isinstance(raw_servers, dict):
        return []
    result: list[dict[str, Any]] = []
    for name, raw in sorted(raw_servers.items()):
        if not isinstance(raw, dict):
            warnings.append(f"MCP {name}: ignored non-table definition")
            continue
        server: dict[str, Any] = {"name": name, "schema_version": 1}
        if isinstance(raw.get("url"), str):
            server["transport"] = "remote"
            server["source"] = raw["url"]
        elif isinstance(raw.get("command"), str):
            server["transport"] = "stdio"
            command = raw["command"]
            if ABSOLUTE_PATH.match(command):
                warnings.append(f"MCP {name}: command is machine-local")
                server["command"] = None
            else:
                server["command"] = command
            server["args"] = safe_mcp_args(raw.get("args", []), warnings, name)
            if command in {"npx", "npm", "uvx", "pipx", "docker"} and server.get("args"):
                server["package_or_image"] = server["args"][0]
        else:
            server["transport"] = "unknown"
            warnings.append(f"MCP {name}: no url or command found")

        env = raw.get("env")
        if isinstance(env, dict):
            server["env_vars"] = sorted(str(key) for key in env)
        header_env = raw.get("env_http_headers")
        if isinstance(header_env, dict):
            server["header_names"] = sorted(str(key) for key in header_env)
            server["header_env_vars"] = sorted(str(value) for value in header_env.values() if isinstance(value, str) and value.isidentifier())
        if isinstance(raw.get("bearer_token_env_var"), str):
            server["env_vars"] = sorted(set(server.get("env_vars", [])) | {raw["bearer_token_env_var"]})

        safe_config: dict[str, Any] = {}
        for key, value in raw.items():
            if key in {"url", "command", "args", "env", "env_http_headers", "bearer_token_env_var", "cwd"}:
                continue
            if is_secret_key(key) or key == "cwd":
                continue
            safe_config[key] = sanitize_value(value, ("mcp_servers", name, key), warnings)
        if safe_config:
            server["config"] = safe_config
        server["requires_local_setup"] = bool(server.get("env_vars") or server.get("command") is None)
        result.append(server)
    return result


def toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def toml_key(value: str) -> str:
    return value if BARE_KEY.fullmatch(value) else json.dumps(value, ensure_ascii=False)


def render_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []

    def emit_table(table: dict[str, Any], prefix: tuple[str, ...] = ()) -> None:
        scalars = [(key, value) for key, value in table.items() if not isinstance(value, dict) and not (isinstance(value, list) and any(isinstance(item, dict) for item in value))]
        nested = [(key, value) for key, value in table.items() if isinstance(value, dict)]
        arrays = [(key, value) for key, value in table.items() if isinstance(value, list) and any(isinstance(item, dict) for item in value)]
        for key, value in scalars:
            lines.append(f"{toml_key(str(key))} = {toml_scalar(value) if not isinstance(value, list) else json.dumps(value, ensure_ascii=False)}")
        for key, value in nested:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"[{'.'.join(toml_key(str(part)) for part in prefix + (key,))}]")
            emit_table(value, prefix + (key,))
        for key, value in arrays:
            for item in value:
                if not isinstance(item, dict):
                    raise ValueError(f"unsupported TOML array value at {'.'.join(prefix + (key,))}")
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(f"[[{'.'.join(toml_key(str(part)) for part in prefix + (key,))}]]")
                emit_table(item, prefix + (key,))

    emit_table(data)
    return "\n".join(lines).rstrip() + "\n"


def copy_owned(source: Path, destination: Path) -> None:
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return
    if not source.is_dir():
        raise ValueError(f"owned source is not a file or directory: {source}")
    ignored = shutil.ignore_patterns(*VOLATILE_NAMES, "*.sqlite", "*.db", "*.log", "auth.json", ".env")
    shutil.copytree(source, destination, dirs_exist_ok=False, ignore=ignored)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def build_profile(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise ValueError(f"output is not empty; use --force only for an explicitly selected profile: {output}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "config").mkdir(exist_ok=True)
    config_path = args.config.expanduser().resolve() if args.config else args.codex_home.expanduser().resolve() / "config.toml"
    warnings: list[str] = []
    config: dict[str, Any] = {}
    if config_path.is_file():
        with config_path.open("rb") as handle:
            loaded = tomllib.load(handle)
        if isinstance(loaded, dict):
            config = loaded
    else:
        warnings.append("config.toml was not found; exported profile has no portable user parameters")

    mcp = extract_mcp(config, warnings)
    portable = sanitize_value(config, (), warnings)
    portable.pop("mcp_servers", None)

    for relative in ("AGENTS.md", "rules", "agents", "hooks"):
        source = args.codex_home.expanduser().resolve() / relative
        if source.exists():
            copy_owned(source, output / "config" / relative)

    skills: list[dict[str, Any]] = []
    plugins: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    owned_skill_names: set[str] = set()
    for raw in args.owned_skill:
        name, source = parse_owned(raw)
        destination = output / "skills" / name
        copy_owned(source, destination)
        owned_skill_names.add(name)
        skills.append({"name": name, "kind": "owned", "path": f"skills/{name}", "source_status": "copied"})
    for raw in args.external_skill:
        entry = parse_pipe_spec(raw, ["name", "source", "ref", "subpath", "version"])
        entry.update({"kind": "external", "install_mode": "skill-installer", "source_status": "resolved"})
        skills.append(entry)

    for root_name, root in (("CODEX_HOME/skills", args.codex_home.expanduser() / "skills"), ("AGENTS_HOME/skills", args.agents_home.expanduser() / "skills")):
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.name == ".system" or ".partial" in child.name:
                continue
            if child.is_dir() and child.name not in owned_skill_names and not any(item.get("name") == child.name for item in skills):
                unresolved.append({"kind": "skill", "name": child.name, "discovered_at": root_name, "reason": "source URL and provenance were not supplied"})

    for raw in args.owned_plugin:
        name, source = parse_owned(raw)
        destination = output / "plugins" / name
        copy_owned(source, destination)
        plugins.append({"id": name, "kind": "owned", "path": f"plugins/{name}", "source_status": "copied"})
    for raw in args.external_plugin:
        entry = parse_pipe_spec(raw, ["id", "source", "version", "ref"])
        entry.update({"kind": "external", "install_mode": "reinstall", "source_status": "resolved"})
        plugins.append(entry)

    (output / "manifests").mkdir(exist_ok=True)
    (output / "local").mkdir(exist_ok=True)
    (output / ".gitignore").write_text("local/*\n!local/README.md\n*.receipt.json\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# Codex portable profile\n\n"
        "This profile stores portable, non-secret Codex configuration. Explicitly confirmed user-owned Skill and Plugin source may be included; external components are recorded in manifests for reinstall.\n\n"
        "## Restore\n\n"
        "Install the public `codex-portable-config` Skill, run its restore helper in dry-run mode, review the plan, and then apply it. API keys, OAuth sign-in, runtimes, and unresolved sources remain manual setup.\n\n"
        "## Files\n\n"
        "- `config/`: stable non-secret configuration and user instructions.\n"
        "- `skills/` and `plugins/`: explicitly owned source only.\n"
        "- `manifests/`: external Skill, Plugin, and MCP reinstall metadata.\n"
        "- `local/`: machine-local notes and receipts; do not commit secrets.\n",
        encoding="utf-8",
    )
    (output / "config" / "config.portable.toml").write_text(render_toml(portable), encoding="utf-8")
    (output / "local" / "README.md").write_text("Machine-local overrides, receipts, and secret setup stay here and must not be committed.\n", encoding="utf-8")
    write_json(output / "manifests" / "skills.json", {"schema_version": 1, "skills": sorted(skills, key=lambda item: item["name"])})
    write_json(output / "manifests" / "plugins.json", {"schema_version": 1, "plugins": sorted(plugins, key=lambda item: item["id"])})
    write_json(output / "manifests" / "mcp.json", {"schema_version": 1, "servers": mcp})
    write_json(output / "manifests" / "unresolved.json", {"schema_version": 1, "items": unresolved, "warnings": warnings})
    return {"output": str(output), "skills": len(skills), "plugins": len(plugins), "mcp_servers": len(mcp), "unresolved": len(unresolved), "warnings": warnings}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--agents-home", type=Path, default=Path.home() / ".agents")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--owned-skill", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--owned-plugin", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--external-skill", action="append", default=[], metavar="NAME|SOURCE|REF|SUBPATH|VERSION")
    parser.add_argument("--external-plugin", action="append", default=[], metavar="ID|SOURCE|VERSION|REF")
    parser.add_argument("--force", action="store_true", help="Allow writing into a selected non-empty output directory")
    return parser.parse_args()


def main() -> int:
    try:
        result = build_profile(parse_args())
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
