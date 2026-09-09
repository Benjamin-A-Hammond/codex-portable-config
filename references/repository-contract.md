# Portable repository contract

The generated profile is an auditable source of truth from which a local Codex configuration can be reconstructed. It is not a live `CODEX_HOME` and must not contain volatile Codex state or externally installed source trees.

## Recommended layout

```text
codex-portable-config/
|-- README.md
|-- LICENSE
|-- .gitignore
|-- config/
|   `-- config.portable.toml
|-- skills/
|   `-- <user-authored-skill>/
|-- plugins/
|   `-- <user-authored-plugin>/
|-- manifests/
|   |-- skills.json
|   |-- plugins.json
|   |-- mcp.json
|   `-- unresolved.json
`-- local/
    `-- README.md
```

The `local/` directory is gitignored except for its README. It holds rendered configuration or per-machine values when needed.

## Restore contract

Every restore implementation must support a read-only or dry-run mode and must:

1. resolve the current home and effective Codex locations at runtime;
2. inventory planned source and destination paths;
3. refuse to copy credentials or volatile state;
4. back up each user-owned file before modifying it;
5. merge only repository-managed configuration sections;
6. install user-authored skills without deleting unrelated local skills;
7. install or register user-authored Plugin sources through supported Codex mechanisms;
8. report external Plugins and Skills that require reinstall from their manifests;
9. report environment variables, OAuth connections, and runtime packages that require local action;
10. validate the installed files and produce a machine-local receipt.

The receipt must not contain secret values or absolute project paths and must remain outside Git.

## Configuration ownership

`config/config.portable.toml` is the profile-owned source. The restore script compares it structurally with the destination and appends only missing values after a backup. Do not treat the full destination `config.toml` as repository-owned.

When TOML merging cannot preserve an unknown construct safely, stop and present a proposed manual merge rather than rewriting the file.

## Plugin handling

User-authored plugin sources may be committed after explicit ownership confirmation. Externally installed plugins must appear in `manifests/plugins.json` with fields such as:

```json
{
  "schema_version": 1,
  "plugins": [
    {
      "id": "plugin-name@marketplace-name",
      "source": "https://github.com/OWNER/REPOSITORY",
      "version": "VERSION_OR_REVISION",
      "install_mode": "reinstall"
    }
  ]
}
```

Do not invent missing versions or repository URLs. Use `null` plus a setup warning when metadata is unavailable.

## MCP handling

`manifests/mcp.json` is the canonical portable MCP description. It contains server names, transport, package or endpoint identifiers, non-secret arguments, and required environment-variable names. The restore process renders MCP tables into the destination config after collecting local values. `config/config.portable.toml` contains other stable non-secret user parameters.

The doctor must distinguish:

- definition present;
- executable/package available;
- required environment-variable name present, without reading or printing its value;
- OAuth login still required;
- connectivity verified or not tested.

## Update behavior

An update must be pull-then-preview-then-apply. It must not propagate local deletions into the repository automatically and must stop on merge conflicts or destination drift that affects managed sections.

## Documentation requirements

The generated README must describe:

- what is portable and what is intentionally excluded;
- supported platforms;
- fresh-machine prerequisites;
- a copy-ready agent prompt for dry-run, approval, apply, external reinstall, and doctor checks;
- installation, remote/local dry-run, update, rollback, and doctor commands;
- GitHub authentication, secret values, OAuth, runtime, local MCP, removable-drive/project, and restart boundaries;
- provenance and licensing policy;
- known platform-specific components.

Examples must use placeholders and public sample domains. Do not personalize the repository from the source machine.
