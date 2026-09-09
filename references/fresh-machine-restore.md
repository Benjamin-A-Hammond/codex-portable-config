# Fresh-machine restore

Use this procedure when restoring a generated profile on a new or reinstalled machine.

## User-facing prompt

Offer this copy-ready prompt, with the profile URL substituted:

```text
Use $codex-portable-config to restore my Codex setup from <PROFILE_REPOSITORY_URL>. Start with a dry-run and show me all configuration changes, owned-source copies, external Skill and Plugin reinstall actions, conflicts, and remaining manual requirements. Do not apply changes or install external components until I approve the dry-run. After approval, apply the portable configuration, restore user-authored source, reinstall resolved external Skills and Plugins through supported Codex mechanisms, run the doctor checks, and give me the final manual-completion checklist without displaying secret values.
```

## Agent procedure

1. Confirm Codex, Git, and Python 3.11 or newer are available. Confirm Git can read a private profile before cloning it.
2. Run `scripts/restore_profile.py` with `--profile-url` or `--profile`, without `--apply`.
3. Show the configuration merge, owned-source destinations, external reinstall actions, conflicts, and unresolved entries. Do not collapse manual requirements into a generic warning.
4. Stop for approval before `--apply` or any external Skill/Plugin installation.
5. After approval, run the apply path. It may merge compatible configuration and copy explicitly owned source; it must not overwrite existing component directories.
6. Use the available system Skill installer for resolved external Skill references. Use the supported Plugin mechanism for external Plugins. Do not turn a source URL into an invented installation command when the mechanism is unavailable.
7. Run `scripts/doctor_profile.py` against the checked-out profile and validate installed owned Skills when a validator is available.
8. Report completed work separately from the manual checklist.

## Required manual checklist

State which of the following apply:

- GitHub authentication for private repositories or dependencies;
- API keys, tokens, passwords, and environment-variable values;
- OAuth sign-in and Plugin or connector authorization;
- Python, Node.js, `uv`, Docker, or other runtime/package dependencies;
- local MCP executables, working directories, ports, and data services;
- removable-drive detection, project paths, project registration, and trust decisions;
- Codex restart when newly installed Skills or changed configuration are not detected.

Never read or print secret values merely to prove that they are configured. Report only whether the required variable name is present.

## Stop conditions

Stop without applying when:

- the profile has unresolved provenance entries;
- the privacy audit reports a finding;
- destination configuration conflicts with a managed value;
- an owned-source path is missing from the profile;
- the profile repository cannot be authenticated;
- the requested Plugin installation mechanism is unavailable;
- applying would overwrite an existing Skill, Plugin, or configuration-source directory.
