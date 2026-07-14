# Legacy Migration Guide

Legacy source directory:

```text
.claude/handoffs/*.md
```

Discover old and new files:

```bash
python scripts/unified_handoff.py list --include-legacy
```

Copy legacy files:

```bash
python scripts/unified_handoff.py migrate
```

Migration rules:

- Source files are never modified or deleted.
- Copies are written to `.agent-context/handoffs/legacy-<name>.md`.
- Missing frontmatter is added using schema 1.0.
- Migrated copies use `status: legacy`.
- Legacy copies are not automatically promoted to `HANDOFF.md` because they have not passed the new validator.
- Re-running migration skips existing targets.
