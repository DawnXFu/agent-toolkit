# Unified Handoff Implementation Plan

## Phase 1: Protocol and documentation

- Add requirements and design documents.
- Define schema version 1.0.
- Define quality modes, blocking rules, and storage behavior.

Acceptance: documents are internally consistent and preserve the existing `session-handoff` skill.

## Phase 2: Core library

- Implement configuration loading and project-root resolution.
- Implement scalar YAML frontmatter parsing/serialization.
- Implement Git and environment collection.
- Implement template generation.
- Implement validation, scoring, secret detection, and reference checks.
- Implement finalization and latest-copy updates.
- Implement staleness and legacy migration.

Acceptance: library functions operate without third-party packages on Python 3.9+.

## Phase 3: CLI and Agent Skill

- Implement `create`, `validate`, `check`, `list`, `staleness`, `resume`, `migrate`, and `init` commands.
- Add `SKILL.md` workflow instructions.
- Add adapter and protocol references.

Acceptance: each primary workflow is executable from the command line and understandable to compatible agents.

## Phase 4: Installation and documentation

- Add Bash and PowerShell installers.
- Add English and Chinese READMEs.
- Add example configuration and migration guidance.
- Add the skill to the repository skill index.

Acceptance: project- and user-scoped installation paths are documented for Claude Code, Codex, and OpenCode.

## Phase 5: Tests and CI

- Add standard-library unit and CLI tests.
- Add cross-platform GitHub Actions workflow.
- Run local tests and compile checks.

Acceptance: all local tests pass; CI configuration covers Python 3.9+ on Linux, Windows, and macOS.

## Phase 6: Review

- Inspect the branch diff.
- Create a Draft PR to the fork's `main` branch.
- Record completed phases, tests, limitations, and follow-up items.
- Do not merge automatically.
