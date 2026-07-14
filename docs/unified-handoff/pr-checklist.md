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

## Architecture

- [x] Replace the dynamic `exec`-based implementation loader with a conventional Python package.
- [x] Separate configuration, Markdown, Git, environment, draft, validation, security, staleness, and migration concerns.
- [x] Preserve the existing `from handoff_lib import ...` public API through explicit re-exports.
- [x] Add regression tests that reject `handoff_lib.py`, `handoff_lib_parts/`, and `exec(compile(...))` loaders.

## Verification

- [x] Add standard-library unit and CLI tests.
- [x] Add Python compile checks.
- [x] Add Ubuntu, Windows, and macOS CI coverage for Python 3.9 through 3.13.
- [x] Add Bash and PowerShell installer smoke tests.
- [x] Remove bootstrap payloads and write-enabled delivery workflows.
- [ ] Confirm all pull-request checks pass after the package refactor.

## Review notes

The implementation now lives in `scripts/handoff_lib/` as ordinary Python modules. `scripts/handoff_lib/__init__.py` is the compatibility boundary for the CLI and external imports. Domain modules use explicit relative imports, can be tested independently, and no longer depend on shared execution order or repository transport limits.
