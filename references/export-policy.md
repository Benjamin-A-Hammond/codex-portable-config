# Export policy

Use this policy to decide what may enter a portable Codex configuration repository. The goal is reproducibility, not a byte-for-byte backup.

## Export by value

Export files only when they are user-authored or redistribution is permitted:

- personal or repository skills, including their `SKILL.md`, scripts, references, assets, and UI metadata;
- custom plugin source trees with their manifests and license;
- user-authored `AGENTS.md`, rules, hooks, and agent definitions after removing local identifiers;
- non-secret configuration preferences that are stable across machines;
- MCP server definitions after structural sanitization;
- bootstrap, update, validation, and diagnostic scripts written for the portable repository.

## Export by reference

Record identifiers instead of copying installed code:

- public or marketplace plugin identifier and source;
- third-party skill repository URL, revision or release, subpath, and license;
- package-manager dependencies and version constraints;
- MCP packages such as npm, PyPI, container, or remote endpoint identifiers;
- required environment-variable names, never values.

Avoid pinning a local cache hash or app-version path as if it were a portable package version.

## Convert to local setup data

Move these values into a gitignored local override or an interactive bootstrap prompt:

- absolute executable and virtual-environment paths;
- home directories, usernames, drive letters, removable-volume paths, and project roots;
- local MCP working directories;
- optional runtime locations;
- organization-specific endpoints or headers that are not intended for public release.

Portable examples use placeholders such as `${CODEX_PORTABLE_ROOT}`, `${PROJECTS_ROOT}`, `OWNER`, `example.com`, and environment-variable names. Do not claim Codex expands a placeholder unless the generated bootstrap actually renders it.

## Always exclude

Exclude these paths and equivalent data regardless of filename casing:

- `auth.json`, credential stores, keyrings, cookies, OAuth state, `.env`, secret files, private keys, certificates with private material;
- `sessions`, `archived_sessions`, histories, memories, transcripts, queues, goals, thread indexes, and any `*.sqlite*` or database file;
- `logs`, `cache`, package caches, standalone packages, runtime downloads, sandboxes, temporary directories, browser/computer-use state, generated images, and media histories;
- installation IDs, device IDs, capability IDs, telemetry payloads, global UI state, project lists, recent paths, trust records, and notification state;
- `.git` directories nested inside copied sources;
- executable binaries and archives obtained from caches;
- user projects and their contents unless the user separately requests a project repository.

## MCP sanitization

Parse TOML; do not extract MCP tables with line-oriented regular expressions.

Safe examples include:

- `command = "npx"` with package arguments;
- a public remote `url`;
- `env_vars = ["SERVICE_TOKEN"]`;
- `bearer_token_env_var = "SERVICE_TOKEN"`;
- `env_http_headers` that maps header names to environment-variable names;
- timeouts, enablement, tool allow/deny lists, and approval modes.

Unsafe values include:

- literal values under `env`;
- static authorization headers;
- bearer tokens, API keys, passwords, cookies, and OAuth tokens;
- absolute `command` or `cwd` values;
- private hostnames, internal URLs, or organization identifiers.

Replace unsafe values with documented local requirements. Do not silently drop a value when doing so would make the restored server appear functional; mark that server as requiring local setup.

## Third-party licensing

Before copying a third-party skill or plugin, locate its license and verify redistribution is allowed. Preserve notices and required attribution. If no license is present, do not copy it; record the source for reinstall.

System and bundled Codex skills should be reinstalled with Codex, not vendored.

## Public-release gate

The public tree must pass all of the following:

- no scanner findings;
- no unknown provenance among copied skills/plugins;
- no unreviewed binaries;
- no personal or private names in filenames, content, commit messages, or repository description;
- no historical commit containing content that was later removed;
- a clean installation test in a temporary home;
- explicit selection of a compatible open-source license.
