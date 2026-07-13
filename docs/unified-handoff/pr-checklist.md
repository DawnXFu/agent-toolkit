# Unified Handoff PR Checklist

## Scope

- [x] Add `skills/unified-handoff/` without modifying the existing `session-handoff` skill.
- [x] Preserve a vendor-neutral Markdown handoff as the source of truth.
- [x] Support Claude Code, Codex, OpenCode, and generic Agent Skills-compatible tools.
- [x] Support Git and non-Git directories.

## Protocol and safety

- [x] Use schema version 1.0 YAML frontmatter.
- [x] Separate verified facts, agent inferences, and unverified assumptions.
- [x] Capture decisions, failed attempts, evidence, user constraints, corrections, and next steps.
- [x] Block finalization on secret findings or incomplete critical sections.
- [x] Keep failed documents as drafts and never overwrite `HANDOFF.md`.

## Workflows

- [x] Implement `init`, `create`, `validate`, `check`, `list`, `staleness`, `resume`, and `migrate`.
- [x] Add legacy `.claude/handoffs/` read and copy migration support.
- [x] Add English and Chinese documentation.
- [x] Add Bash and PowerShell installers.
- [x] Add repository skill index entry.

## Verification

- [x] Add standard-library unit and CLI tests.
- [x] Add Python compile checks.
- [x] Add Ubuntu, Windows, and macOS CI coverage for Python 3.9 through 3.13.
- [x] Remove bootstrap payloads and write-enabled delivery workflows.
- [ ] Confirm all pull-request checks pass.

## Review notes

The implementation uses a small `handoff_lib.py` facade that loads ordered implementation parts. This keeps the public import stable while allowing the files to remain transportable through conservative repository connectors. A future maintenance refactor may replace the ordered parts with conventional package modules without changing the public CLI or protocol.
