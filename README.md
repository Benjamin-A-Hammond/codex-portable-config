# Codex Portable Config

An open-source Codex skill for exporting and restoring a sanitized, portable Codex profile.

It preserves stable non-secret configuration by value, copies only explicitly confirmed user-authored Skill and Plugin source, and records externally installed Skills, Plugins, and MCP servers as reinstall metadata. Credentials, OAuth state, sessions, databases, logs, caches, runtime packages, device state, private project data, and personal identifiers are excluded.

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

The skill first inventories the installation without copying content, asks for ownership/source metadata where needed, builds a data-first profile, and runs a privacy audit before any GitHub publication.

## Export a profile

The deterministic helper accepts explicit ownership declarations. External sources are recorded by reference only:

```text
python scripts/export_profile.py --codex-home <CODEX_HOME> --output <PROFILE> \
  --owned-skill my-skill=<PATH_TO_OWNED_SKILL> \
  --external-skill external-skill|https://github.com/OWNER/REPOSITORY|main|skills/external-skill|1.0
```

Run `scripts/doctor_profile.py <PROFILE>` and `scripts/audit_repository.py <PROFILE>` before committing.

## Restore on a new machine

Install Codex and this Skill, then preview the profile before applying it:

```text
python scripts/restore_profile.py --profile <PROFILE> --codex-home <CODEX_HOME>
python scripts/restore_profile.py --profile <PROFILE> --codex-home <CODEX_HOME> --apply
```

The restore process backs up and merges compatible configuration, installs owned Skills, and reports external Skill/Plugin installation actions. API keys, OAuth login, runtimes, and unresolved sources remain manual steps.

## Safety model

- No recursive `CODEX_HOME` copy.
- External Skill, Plugin, and MCP source code is never copied; only install metadata is stored.
- Explicitly confirmed user-authored Skill and Plugin source may be copied into the profile.
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
