#!/usr/bin/env python3
"""Audit a prospective public repository without echoing matched secret values."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python version gate
    tomllib = None


TEXT_EXTENSIONS = {
    "",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".gitignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonc",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}

FORBIDDEN_BASENAMES = {
    ".env",
    ".codex-global-state.json",
    "auth.json",
    "cookies.json",
    "credentials.json",
    "history.jsonl",
    "installation_id",
    "session_index.jsonl",
    "transcription-history.jsonl",
}

FORBIDDEN_DIRECTORY_NAMES = {
    ".sandbox",
    ".sandbox-bin",
    ".sandbox-secrets",
    "archived_sessions",
    "cache",
    "computer-use",
    "generated_images",
    "logs",
    "packages",
    "sessions",
    "sqlite",
}

FORBIDDEN_SUFFIXES = {
    ".db",
    ".exe",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
}

PLACEHOLDER_FRAGMENTS = {
    "change_me",
    "changeme",
    "example",
    "placeholder",
    "redacted",
    "replace_me",
    "your_",
    "${",
    "<",
}

PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("bearer-token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("windows-user-path", re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s\"']+")),
    ("mac-user-path", re.compile("/" + "Users/" + r"[^/\s\"']+")),
    ("linux-user-path", re.compile("/" + "home/" + r"[^/\s\"']+")),
    (
        "email-address",
        re.compile(r"\b[A-Z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    ),
]

SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|secret|cookie)\b\s*[:=]\s*[\"']?([^\s\"',}\]]+)"
)


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    line: int | None = None


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return not value or any(fragment in lowered for fragment in PLACEHOLDER_FRAGMENTS)


def local_identifiers() -> dict[str, str]:
    candidates = {
        "local-username": getpass.getuser(),
        "local-home-name": Path.home().name,
        "local-hostname": socket.gethostname(),
    }
    return {
        label: value
        for label, value in candidates.items()
        if value and len(value) >= 4 and value.lower() not in {"user", "home", "host", "localhost"}
    }


def safe_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def path_findings(path: Path, root: Path) -> list[Finding]:
    relative = safe_relative(path, root)
    lowered_parts = [part.lower() for part in Path(relative).parts]
    findings: list[Finding] = []
    if path.name.lower() in FORBIDDEN_BASENAMES:
        findings.append(Finding("forbidden-file", relative))
    if any(part in FORBIDDEN_DIRECTORY_NAMES for part in lowered_parts):
        findings.append(Finding("forbidden-directory", relative))
    lower_name = path.name.lower()
    if lower_name.endswith(tuple(FORBIDDEN_SUFFIXES)) or ".sqlite-" in lower_name:
        findings.append(Finding("forbidden-binary-or-state", relative))
    if path.is_file() and path.stat().st_size > 20 * 1024 * 1024:
        findings.append(Finding("oversized-file", relative))
    return findings


def scan_text(path: Path, root: Path, identifiers: dict[str, str]) -> list[Finding]:
    relative = safe_relative(path, root)
    try:
        raw = path.read_bytes()
    except OSError:
        return [Finding("unreadable-file", relative)]
    if b"\x00" in raw[:8192]:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [Finding("non-utf8-text", relative)]

    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for code, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(code, relative, number))
        match = SECRET_ASSIGNMENT.search(line)
        if match and not is_placeholder(match.group(2)):
            findings.append(Finding("literal-secret-assignment", relative, number))
        lowered_line = line.casefold()
        for label, value in identifiers.items():
            if value.casefold() in lowered_line:
                findings.append(Finding(label, relative, number))

    return findings


def inspect_toml(path: Path, root: Path) -> list[Finding]:
    if tomllib is None:
        return [Finding("python-3.11-required-for-toml", safe_relative(path, root))]
    try:
        with path.open("rb") as handle:
            tomllib.load(handle)
    except Exception:
        return [Finding("invalid-toml", safe_relative(path, root))]
    return []


def audit(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    identifiers = local_identifiers()
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink():
                findings.append(Finding("symlink-requires-review", safe_relative(path, root)))
                continue
            findings.extend(path_findings(path, root))
            if path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"Dockerfile", "Makefile"}:
                findings.extend(scan_text(path, root, identifiers))
            if path.suffix.lower() == ".toml":
                findings.extend(inspect_toml(path, root))
    return sorted(set(findings), key=lambda item: (item.path, item.line or 0, item.code))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Prospective repository root")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print("error: repository root is not a directory", file=sys.stderr)
        return 2
    findings = audit(root)
    if args.json:
        print(json.dumps({"ok": not findings, "findings": [asdict(item) for item in findings]}, indent=2))
    elif findings:
        for item in findings:
            location = f":{item.line}" if item.line is not None else ""
            print(f"{item.code}: {item.path}{location}")
        print(f"audit failed: {len(findings)} finding(s)")
    else:
        print("audit passed: no findings")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
