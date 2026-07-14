# Unified Handoff Design

## 1. Design Goals

The system standardizes the handoff artifact rather than vendor session storage. A validated Markdown document is the source of truth, while agent-specific behavior remains at the edges through adapter guidance.

Design priorities:

1. Portability across agents and operating systems
2. Deterministic metadata collection
3. Explicit epistemic status and evidence
4. Safe failure behavior
5. Low installation friction
6. Compatibility with the open Agent Skills format
7. Maintainable, independently testable Python modules

## 2. System Architecture

```text
Agent invocation
      │
      ▼
SKILL.md workflow
      │
      ├── create ────────► draft Markdown
      │                       │
      │                       ▼
      ├── validate/check ─► quality + security report
      │                       │
      │              pass + --finalize
      │                       ▼
      │                 validated archive
      │                       │
      │                       └── copy ► HANDOFF.md
      │
      ├── list
      ├── staleness
      ├── resume ─────────► target-specific prompt
      └── migrate ────────► copied legacy handoffs
```

Repository components:

- `scripts/unified_handoff.py`: command-line interface and exit-code policy
- `scripts/handoff_lib/`: reusable domain package
- `scripts/handoff_lib/__init__.py`: stable public compatibility boundary
- `SKILL.md`: agent workflow and invocation rules
- `references/`: protocol, template, adapters, and checklists
- `tests/`: standard-library `unittest` suite

### 2.1 Package boundaries

The `handoff_lib` package is organized by responsibility:

| Module | Responsibility |
|---|---|
| `constants.py` | Protocol constants, defaults, section policy, built-in secret patterns |
| `models.py` | Shared dataclasses for commands, resolved paths, and validation results |
| `system.py` | Time, subprocess, deep-merge, and atomic-write primitives |
| `markdown.py` | Scalar frontmatter parsing, rendering, section extraction, slug handling |
| `git.py` | Git-root resolution, remote sanitization, branch and working-tree metadata |
| `config.py` | Configuration validation, project-root resolution, storage paths |
| `environment.py` | Tool detection, test-command inference, adapter text, scaffold formatting |
| `drafts.py` | Draft discovery, predecessor linking, and handoff scaffold generation |
| `security.py` | Placeholder checks, secret scanning, and file-reference verification |
| `validation.py` | Quality scoring, finalization, latest-copy updates, and listing |
| `staleness.py` | Age/Git/reference comparison and resume recommendations |
| `migration.py` | Legacy Claude handoff migration and handoff argument lookup |

Modules use explicit relative imports. There is no execution-order coupling, dynamic `exec`, generated source concatenation, or hidden shared namespace.

### 2.2 Dependency direction

Low-level modules do not import workflow modules:

```text
constants / models
        │
        ▼
system / markdown
        │
        ├── git
        ├── config
        ├── environment
        └── security
                │
                ▼
      drafts / validation / staleness / migration
                │
                ▼
             __init__.py
                │
                ▼
        unified_handoff.py
```

The dependency graph is intentionally acyclic. Workflow modules compose lower-level services; the public package initializer only re-exports symbols.

### 2.3 Public API compatibility

Existing callers continue to use:

```python
from handoff_lib import create_draft, validate_handoff, resume_prompt
```

`handoff_lib/__init__.py` defines an explicit `__all__` list and re-exports the historical public surface. Internal module paths may evolve without forcing CLI or consumer changes.

Architecture tests enforce that:

- `handoff_lib` resolves to a package
- every domain module imports independently
- the CLI-required public symbols remain exported
- `scripts/handoff_lib.py` does not return
- `scripts/handoff_lib_parts/` does not return
- no `exec(compile(...))` loader is introduced

## 3. Project and Storage Resolution

Resolution order:

1. Explicit `--project-root`
2. Nearest ancestor containing `.agent-context/config.json`
3. Git worktree root
4. Current working directory

This allows a monorepo package to own its own handoff context by placing `.agent-context/config.json` in that package. Otherwise, the repository root owns the handoff history.

Resolved paths:

```text
project_root / storage_dir / handoffs_subdir
project_root / storage_dir / latest_file
project_root / storage_dir / config.json
```

All filesystem operations use `pathlib.Path`. External commands receive argument arrays rather than shell strings.

## 4. State Model

Handoff status values:

- `draft`: scaffold or failed validation
- `validated`: passed validation and finalized
- `legacy`: migrated from the old Claude-specific directory

State transitions:

```text
create ─► draft
           │
           ├── validation failure ─► draft
           └── validation pass + finalize ─► validated

legacy source ─► migrate ─► legacy copy
```

A validated file is immutable by convention. Continued work creates a new draft with `continues_from` pointing to the prior archive filename.

## 5. Protocol Schema

YAML frontmatter is intentionally limited to scalar values. This permits a small standard-library parser without importing PyYAML. JSON-style quoted strings are valid YAML scalars and are used when serializing.

Required metadata keys:

- `schema_version`
- `handoff_id`
- `created_at`
- `updated_at`
- `source_agent`
- `target_agent`
- `mode`
- `language`
- `status`
- `repository`
- `working_directory`
- `branch`
- `head_commit`
- `quality_score`
- `continues_from`

Section identifiers remain English and stable. Section bodies may be written in any language.

## 6. Git Collection

`collect_git_info()` runs bounded Git commands with timeouts. Failures return partial metadata instead of aborting.

Collected commands include:

```text
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git log --oneline -5
git diff --name-only
git diff --name-only --cached
git ls-files --others --exclude-standard
git remote get-url origin
git diff --name-only <base>...HEAD
```

The remote URL sanitizer removes HTTP user information. No full diff is generated.

## 7. Environment and Command Inference

Environment collection is descriptive, not executable. Draft creation records detected tools and candidate commands but does not run them.

Inference sources:

- `package.json` scripts and lockfiles
- `pyproject.toml`, `pytest.ini`, `tox.ini`, and `tests/`
- `Makefile` targets
- explicit configuration

Configured commands take precedence. Inferred commands are labeled so the next agent can verify them before execution.

## 8. Validation Pipeline

Validation stages:

1. Parse frontmatter and sections.
2. Check protocol metadata.
3. Check blocking sections.
4. Detect unresolved placeholders.
5. Evaluate mode-specific recommended sections.
6. Scan for secrets.
7. Verify local file references.
8. Check epistemic labels and next-step actionability.
9. Calculate score and verdict.

### 8.1 Blocking rules

Finalization is blocked when:

- Secrets are detected.
- Objective is absent, too short, a placeholder, or `N/A`.
- Current State is absent, too short, a placeholder, or `N/A`.
- Immediate Next Steps is absent, too short, a placeholder, `N/A`, or lacks an ordered/task-list item.

### 8.2 Scoring

The score starts at 100. Typical deductions include:

- Blocking section problem: 25 each
- Secret finding: 30 total plus blocking verdict
- Placeholder: 2 each, capped
- Missing or incomplete recommended section: mode-weighted deduction
- Broken file reference: 2 each, capped
- Missing epistemic classification: deduction in standard/full modes
- Non-actionable next step: blocking deduction

Thresholds come from configuration and default to 70/80/85.

### 8.3 Safe finalization

`validate --finalize` performs:

1. Validation
2. Frontmatter update (`status`, `quality_score`, `updated_at`)
3. Atomic write of the finalized archive
4. Removal of the corresponding draft
5. Atomic physical copy to `HANDOFF.md`

If validation fails, the draft is updated with its score and remains a draft. `HANDOFF.md` is untouched.

## 9. Security and Reference Verification

Built-in secret patterns cover common credential classes. Findings contain only type and line number; matched values are never returned.

Custom patterns come from `custom_secret_patterns`. Invalid custom regular expressions produce warnings rather than crashes.

The validator extracts likely repository-relative paths from Markdown tables, inline code spans, and `path/to/file.ext:line` references. URLs, command options, paths outside the project root, and malformed candidates are excluded. Missing references are warnings and score deductions, not blocking errors.

## 10. Staleness Model

The preferred baseline is `head_commit` from frontmatter. Git-aware checks include:

- Current branch differs from recorded branch
- Number of commits since recorded HEAD
- Files changed since recorded HEAD
- Referenced files removed
- Current working tree differs

Time age is a secondary factor. If the recorded commit no longer exists, the report marks the baseline unavailable and falls back to age and file checks.

Levels:

- `FRESH`
- `SLIGHTLY_STALE`
- `STALE`
- `VERY_STALE`
- `UNKNOWN` for insufficient non-Git data

Thresholds are configurable.

## 11. Agent Adapters and Installation

The core artifact stays agent-neutral. Adapters define only invocation and resumption guidance.

- Claude Code uses `.claude/skills/` and `/unified-handoff`.
- Codex uses `.agents/skills/` and explicit `$unified-handoff` or skill selection.
- OpenCode uses `.agents/skills/`, `.opencode/skills/`, or Claude-compatible locations and its native skill tool.
- Generic tools read `SKILL.md` and run the bundled Python CLI.

Bash and PowerShell installers support project/user scope, agent selection, copy installation, and optional linking. Both installers detect source-equals-destination and avoid deleting an installed copy when re-run from that copy.

## 12. Legacy Compatibility

`list --include-legacy` reads `.claude/handoffs/*.md` without modifying them.

`migrate`:

1. Reads each legacy file.
2. Derives a timestamp from the filename or filesystem metadata.
3. Prepends schema 1.0 frontmatter with `status: legacy` when absent.
4. Copies to `.agent-context/handoffs/legacy-<name>`.
5. Leaves the source file untouched.

Legacy files are not automatically promoted to `HANDOFF.md` because they have not passed the new validator.

## 13. Error Handling

CLI commands return:

- `0`: success or ready
- `1`: validation failure or stale state requiring review
- `2`: argument, configuration, or missing-resource error

Human output is concise. `--json` emits structured results for automation.

## 14. Test Design

Tests use `tempfile.TemporaryDirectory` and isolated repositories when Git is available. No network is required.

Coverage includes:

- Package architecture and independent module imports
- Public API compatibility
- Configuration and project-root resolution
- Frontmatter round trip
- Draft creation in Git and non-Git directories
- Validation scoring and blocking rules
- Secret detection with line-safe reports
- Finalization and latest-copy behavior
- Legacy migration
- Staleness comparison
- Unicode and spaced paths
- CLI smoke tests
- Bash and PowerShell installer smoke tests

CI compiles and tests Python 3.9 through 3.13 across Ubuntu, Windows, and macOS.

## 15. Compatibility and Constraints

- Python 3.9+
- Standard library only
- UTF-8 files
- No daemon or background service
- No vendor session database access
- No automatic execution of inferred test commands
- No full diff embedding
- No environment variable values
