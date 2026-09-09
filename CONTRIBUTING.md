# Contributing

Contributions that improve portability, safety, deterministic restore behavior, documentation, or cross-platform support are welcome.

## Before opening a pull request

1. Keep the Skill focused on exporting and restoring portable Codex configuration.
2. Do not add credentials, private configuration, real user paths, hostnames, project names, or copied third-party Skill/Plugin source to fixtures or examples.
3. Preserve dry-run behavior and the approval boundary before apply or external installation.
4. Add or update tests for behavioral changes.
5. Run:

```text
python -m compileall -q scripts
python -m unittest discover -s tests -v
python scripts/audit_repository.py .
```

If Codex's bundled `skill-creator` is available, also run its `quick_validate.py` against the repository root.

## Security reports

Do not open a public issue for a suspected secret exposure or unsafe restore behavior. Follow [SECURITY.md](SECURITY.md).
