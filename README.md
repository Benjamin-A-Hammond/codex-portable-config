# Codex Portable Config

An open-source Codex skill for creating a sanitized, portable Git repository from an existing local Codex setup.

It exports reproducible source configuration rather than copying `CODEX_HOME`. User-authored skills, custom plugin sources, safe MCP definitions, and installation metadata can be included. Credentials, sessions, databases, logs, caches, runtime packages, device state, private project data, and personal identifiers are excluded.

## Install

Ask Codex to install this skill from its GitHub repository, or copy this repository into a supported user skill location. Replace `OWNER` with the repository owner:

```text
$skill-installer install https://github.com/OWNER/codex-portable-config
```

Restart Codex if the skill is not discovered immediately.

## Use

Invoke the skill with a request such as:

```text
$codex-portable-config create a portable repository from my local Codex setup.
```

The skill first inventories the installation without copying content, classifies provenance and licensing, builds a clean repository, and runs a privacy audit before any GitHub publication.

## Safety model

- No recursive `CODEX_HOME` copy.
- No secrets, OAuth state, authentication files, sessions, histories, SQLite databases, logs, caches, runtime packages, sandbox state, project trust records, or device identifiers.
- No local usernames, home paths, hostnames, private project names, or machine-specific executable paths in the published tree.
- Third-party skills and plugins are referenced for reinstall unless redistribution is clearly permitted.
- Public release is a distinct, reviewable action after validation.

The scanner is defense in depth, not a guarantee. Review the complete repository and staged diff before publishing.

## Development

The scripts require Python 3.11 or newer and use only the standard library.

```text
python scripts/inventory_codex.py --help
python scripts/audit_repository.py .
python -m unittest discover -s tests -v
```

Validate the skill with the `quick_validate.py` script distributed with Codex's `skill-creator` skill.

## License

MIT. See [LICENSE](LICENSE).

