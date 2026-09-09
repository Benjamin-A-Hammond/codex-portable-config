# Portable repository contract

The generated repository is an auditable source of truth from which a local Codex configuration can be reconstructed. It is not a live `CODEX_HOME` and must not contain volatile Codex state.

## Recommended layout

```text
codex-portable-config/
|-- README.md
|-- LICENSE
|-- .gitignore
|-- config/
|   |-- config.portable.toml
|   `-- local.example.toml
|-- skills/
|   `-- <user-authored-skill>/
|-- plugins/
|   `-- <user-authored-plugin>/
|-- manifests/
|   |-- third-party-skills.json
|   |-- plugins.json
|   |-- mcp-requirements.json
|   `-- provenance.json
|-- scripts/
|   |-- bootstrap.ps1
|   |-- bootstrap.sh
|   |-- update.ps1
|   |-- update.sh
|   `-- doctor.py
`-- local/
    `-- README.md
```

The `local/` directory is gitignored except for its README. It holds rendered configuration or per-machine values when needed.

## Bootstrap contract

Every bootstrap implementation must support a read-only or dry-run mode and must:

1. resolve the current home and effective Codex locations at runtime;
2. inventory planned source and destination paths;
3. refuse to copy credentials or volatile state;
4. back up each user-owned file before modifying it;
5. merge only repository-managed configuration sections;
6. install user-authored skills without deleting unrelated local skills;
7. install or register custom plugin sources through supported Codex mechanisms;
8. report third-party plugins and skills that require reinstall;
9. report environment variables and OAuth connections that require local action;
10. validate the installed files and produce a machine-local receipt.

The receipt must not contain secret values or absolute project paths and must remain outside Git.

## Configuration ownership

Mark generated sections with stable comments or maintain a separate structural manifest so updates can distinguish repository-managed values from user-local values. Do not treat the full destination `config.toml` as repository-owned.

When TOML merging cannot preserve an unknown construct safely, stop and present a proposed manual merge rather than rewriting the file.

## Plugin handling

Custom plugin sources may be committed when provenance and licensing are clear. Installed marketplace plugins should normally appear in `manifests/plugins.json` with fields such as:

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

`config/config.portable.toml` may contain directly usable definitions only when they have no secret or machine-local values. Servers requiring local values belong in `manifests/mcp-requirements.json`, and the bootstrap renders their final tables after collecting those values locally.

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
- installation, dry-run, update, rollback, and doctor commands;
- secret and OAuth setup boundaries;
- provenance and licensing policy;
- known platform-specific components.

Examples must use placeholders and public sample domains. Do not personalize the repository from the source machine.
