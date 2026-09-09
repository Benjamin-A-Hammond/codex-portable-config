# Codex Portable Config

[![CI](https://github.com/Benjamin-A-Hammond/codex-portable-config/actions/workflows/ci.yml/badge.svg)](https://github.com/Benjamin-A-Hammond/codex-portable-config/actions/workflows/ci.yml)

Export a sanitized Codex profile to Git, then restore its portable configuration on another machine.

This project is a Codex Skill plus deterministic Python helpers. It preserves stable, non-secret configuration, stores explicitly confirmed user-authored Skill and Plugin source, and records externally installed Skills, Plugins, and MCP servers as reinstall metadata. It is not a byte-for-byte backup of `CODEX_HOME`.

## What it restores

| Profile content | Stored in the profile | Restore behavior |
| --- | --- | --- |
| Portable Codex settings | Values in `config/config.portable.toml` | Merged without replacing the destination config |
| User-authored Skills | Complete source under `skills/` | Copied when the destination does not already exist |
| User-authored Plugins | Complete source under `plugins/` | Copied to an explicitly selected source destination; registration may still be required |
| External Skills | Name, source URL, revision, subpath, and version | Reinstalled through Codex's Skill installer |
| External Plugins | Identifier, source, and version | Reinstalled or connected through a supported Plugin mechanism |
| MCP servers | Non-secret definition and required environment-variable names | Safe values are merged; local commands and credentials are reported |
| Projects and removable-drive data | Not copied | Kept in their original repositories or storage locations |

Credentials, OAuth state, secret values, sessions, histories, databases, logs, caches, runtime packages, device state, project trust records, and private project files are intentionally excluded.

## Requirements

- Codex with local Skill support.
- Git, including authentication for any private profile repository.
- Python 3.11 or newer for the helper scripts.
- Access to the original Codex configuration when exporting.
- Access to the profile repository when restoring.

## Install this Skill

Paste this into Codex:

```text
Use $skill-installer to install the Skill from https://github.com/Benjamin-A-Hammond/codex-portable-config
```

Codex detects newly installed Skills automatically. Restart Codex if it does not appear. The official OpenAI documentation describes `$skill-installer` as the supported local workflow for installing curated Skills or Skills from other repositories.

## Create a portable profile

Paste this into Codex:

```text
Use $codex-portable-config to create a sanitized portable profile from my local Codex setup. Inventory first, ask me to classify any Skill or Plugin whose provenance is unclear, copy only source I explicitly confirm as user-authored, record external components by reinstall reference, run the privacy audit and restore dry-run, and do not publish anything until I approve the reviewed repository.
```

The Skill will classify each component, generate the profile repository, validate it, and report anything that cannot be reproduced safely.

For direct helper usage, provide explicit ownership and source metadata:

```text
python scripts/export_profile.py --codex-home <CODEX_HOME> --output <PROFILE_DIRECTORY> --owned-skill 'my-skill=<PATH_TO_OWNED_SKILL>' --external-skill 'external-skill|https://github.com/OWNER/REPOSITORY|main|skills/external-skill|1.0'
python scripts/doctor_profile.py <PROFILE_DIRECTORY>
python scripts/audit_repository.py <PROFILE_DIRECTORY>
```

Run the audit and inspect the complete Git diff before pushing a profile. A profile containing personal configuration or user-authored private source should normally use a private repository.

## Restore on a new machine

After installing Codex and this Skill, paste the following prompt and replace the placeholder:

```text
Use $codex-portable-config to restore my Codex setup from <PROFILE_REPOSITORY_URL>. Start with a dry-run and show me all configuration changes, owned-source copies, external Skill and Plugin reinstall actions, conflicts, and remaining manual requirements. Do not apply changes or install external components until I approve the dry-run. After approval, apply the portable configuration, restore user-authored source, reinstall resolved external Skills and Plugins through supported Codex mechanisms, run the doctor checks, and give me the final manual-completion checklist without displaying secret values.
```

For a private profile, sign in to GitHub or otherwise configure Git credentials before asking Codex to clone it.

The equivalent helper commands are:

```text
python scripts/restore_profile.py --profile-url <PROFILE_REPOSITORY_URL> --codex-home <CODEX_HOME>
python scripts/restore_profile.py --profile-url <PROFILE_REPOSITORY_URL> --codex-home <CODEX_HOME> --apply
```

You can also replace `--profile-url` with `--profile <LOCAL_PROFILE_DIRECTORY>`.

The standalone restore helper merges portable configuration and installs owned source. It deliberately reports external Skill and Plugin actions instead of silently performing third-party installations. In the agent-guided workflow, Codex reviews those actions with you and then uses the available Skill installer or Plugin mechanism after approval.

## Manual completion checklist

Every restore must finish by reporting which of these still require attention:

- GitHub authentication for a private profile or private dependency.
- API keys, tokens, passwords, and environment-variable values.
- OAuth sign-in and Plugin or connector authorization.
- Runtime dependencies such as Python, Node.js, `uv`, Docker, or package managers.
- Machine-local MCP executables, working directories, ports, and local data services.
- Removable-drive discovery, project paths, project registration, and trust decisions.
- A Codex restart when a newly installed Skill or changed config is not detected.

These steps cannot be made portable safely because they contain credentials, depend on the current machine, or require an interactive authorization decision.

## Update an existing machine

1. Pull the latest profile repository.
2. Run the restore helper without `--apply`.
3. Review conflicts and third-party install actions.
4. Apply only after the preview is acceptable.
5. Run `doctor_profile.py` and complete the reported manual items.

The updater never treats a local deletion as permission to delete content from the profile or destination.

## Rollback and conflict behavior

- Existing Skills, Plugins, and configuration-source paths are skipped instead of overwritten.
- A changed destination configuration value is reported as a conflict and stops the restore.
- Before appending compatible config values, the apply path writes a timestamped `config.toml.before-codex-portable-*` backup.
- Restore receipts and machine-local overrides stay outside version control.

## Safety model

- Never copy `CODEX_HOME` recursively.
- Copy source only when the user explicitly confirms ownership.
- Record externally sourced Skills and Plugins by reference, even when redistribution may be permitted.
- Parse MCP configuration structurally and retain environment-variable names rather than values.
- Exclude authentication data, volatile state, local databases, caches, runtimes, absolute machine paths, private project content, and identifying machine metadata.
- Treat public GitHub publication as a separate, reviewable action after validation.

The scanner is defense in depth, not a guarantee. Always inspect the generated repository and its Git history before publication.

## Repository layout

```text
SKILL.md                         Codex workflow and safety boundaries
scripts/inventory_codex.py      Anonymous discovery inventory
scripts/export_profile.py       Deterministic profile generator
scripts/restore_profile.py      Dry-run and apply implementation
scripts/doctor_profile.py       Reproducibility diagnostics
scripts/audit_repository.py     Secret and privacy scanner
references/                     Export and restore contracts
tests/                          Unit tests for key safety invariants
```

## Development

```text
python -m compileall -q scripts
python -m unittest discover -s tests -v
python scripts/audit_repository.py .
```

Validate the Skill with `quick_validate.py` from Codex's bundled `skill-creator` Skill.

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the validation and privacy requirements.

## Official documentation

- [Build Skills](https://learn.chatgpt.com/docs/build-skills)
- [Build Plugins](https://learn.chatgpt.com/docs/build-plugins)
- [Import from another agent](https://learn.chatgpt.com/docs/import)

Codex's built-in import flow targets supported third-party agents. This project provides a separate, auditable Git-based workflow for moving portable configuration between Codex installations.

## License

MIT. See [LICENSE](LICENSE).
