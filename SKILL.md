---
name: codex-portable-config
description: Build or refresh a sanitized, portable Git repository from a local Codex setup, covering user-authored skills, custom plugin sources, MCP definitions, and reproducible bootstrap metadata. Use for Codex configuration backup, migration, portability, or GitHub publication; do not use to copy sessions, credentials, caches, or an entire CODEX_HOME.
---

# Codex Portable Config

Create a reviewable source repository that can reproduce the portable parts of a Codex setup on another machine. Treat the local installation as sensitive input, not as content that is safe to copy wholesale.

## Non-negotiable boundaries

- Never copy `CODEX_HOME` recursively.
- Never export credentials, OAuth state, API keys, cookies, environment values, private keys, authentication files, local databases, sessions, histories, logs, caches, runtime packages, sandboxes, browser state, generated media, installation identifiers, device identifiers, or project trust state.
- Never put a local username, home directory, hostname, email address, drive letter, project name, organization name, repository remote, or other identifying value into generated examples or documentation. Use neutral placeholders.
- Do not copy installed third-party skill or plugin code merely because it is present locally. Record its public source, package identifier, version, and license when known. Copy code only when the user owns it or its license permits redistribution.
- Treat public GitHub publication as a separate external mutation. Complete the local export and privacy audit first, show the audit result and repository diff, then obtain authorization if public release was not already explicitly requested.
- Keep secrets local. Portable MCP configuration may name environment variables but must not contain their values.

Read [references/export-policy.md](references/export-policy.md) before selecting local files. Read [references/repository-contract.md](references/repository-contract.md) when creating bootstrap scripts or the target repository layout.

## Workflow

### 1. Establish scope without collecting content

Resolve the effective `CODEX_HOME`, the user skill roots, and any user-supplied custom plugin source directories. Prefer documented environment/configuration locations over guessed paths.

Run `scripts/inventory_codex.py` to create an anonymous inventory outside the target repository. The inventory must use logical roots such as `CODEX_HOME/` and `AGENTS_HOME/`; do not include absolute source paths.

Do not open excluded files to decide whether they are useful. Their category is enough to exclude them.

### 2. Classify provenance

Classify every candidate as one of:

- `user-authored`: eligible for export;
- `third-party-redistributable`: export only with license and attribution;
- `third-party-reference`: record installation metadata, not code;
- `machine-local`: convert to a placeholder or local setup requirement;
- `secret-or-private`: exclude;
- `generated-or-volatile`: exclude.

When provenance is unclear, default to `third-party-reference` and do not copy the code.

### 3. Build a clean target, never an unfiltered snapshot

Create the target in a new or explicitly selected directory. Default the repository name to `codex-portable-config`, but accept a different user choice.

Generate the structure defined in the repository contract. Important behavior:

- Copy eligible skills as complete skill directories.
- Copy custom plugin source directories, not installed plugin caches.
- Record marketplace or third-party plugins in a manifest for reinstall.
- Extract MCP definitions structurally from TOML. Preserve server names and non-secret behavior, replace machine paths with setup variables, and replace secret values with environment-variable names.
- Generate both PowerShell and POSIX bootstrap paths when the exported components are cross-platform. If a component is platform-specific, declare that explicitly instead of pretending portability.
- Merge managed sections into an existing destination config; never replace an entire local `config.toml`, authentication store, or trust database.
- Keep generated working copies and machine-local overrides out of Git.

### 4. Validate the target

Before any commit or publication:

1. Parse every generated TOML, JSON, YAML, and plugin manifest with an appropriate parser or official validator.
2. Validate each exported skill with the available skill validator.
3. Validate each custom plugin with the available plugin validator.
4. Run relevant bootstrap scripts in dry-run mode against a temporary home.
5. Run `scripts/audit_repository.py <target>`. It must return success with zero findings.
6. Inspect `git diff --cached` or the complete pre-commit file list.
7. Confirm the repository contains no personal identifiers, secrets, private project names, absolute local paths, or unlicensed copied code.

Do not weaken the scanner or add broad ignore rules merely to make it pass. Replace the unsafe content or keep it local.

### 5. Initialize and publish

Initialize Git only after validation. Use a generic repository description and a recognized open-source license selected by the user; when unspecified, ask before choosing a license because licensing changes redistribution rights.

Prefer creating the GitHub repository from the reviewed local tree. Do not publish through a personal account inferred from unrelated local configuration. Resolve the intended GitHub owner and visibility from the user's explicit request or authenticated GitHub context.

If GitHub authentication or repository-creation tooling is unavailable, leave a complete, validated local repository and report the exact remaining publish command without claiming publication.

### 6. Report reproducibility gaps

Distinguish what was exported from what still requires per-machine action, especially:

- Codex and Git installation;
- runtime dependencies such as Node, Python, `uv`, or Docker;
- API keys and environment variables;
- OAuth and plugin connections;
- platform-specific MCP executables;
- removable-drive discovery or project registration.

The repository is complete only when these gaps are documented and its dry-run bootstrap explains them without exposing local values.

