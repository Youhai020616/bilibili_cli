# Release Checklist

Before cutting a release:

1. Run `python -m pytest -q`.
2. Smoke-test `bili --help` and `bili --version`.
3. Confirm `bili search`, `bili video info`, `bili comments`, `bili danmaku`, and `bili download` still work.
4. Confirm write commands still default to dry-run.
5. Confirm `docs/commands.md`, `docs/api.md`, `docs/schema.md`, `docs/troubleshooting.md`, and `SKILL.md` are current.
6. Bump version in `pyproject.toml` and `src/bili_cli/__init__.py`.
7. Update `RELEASE_NOTES.md`.
8. Commit, tag, and push.
9. Publish GitHub release artifacts if shipping externally.
