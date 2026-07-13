# Unified Handoff Requirements

## 1. Purpose

Create a cross-agent session handoff skill that produces consistent, high-quality, resumable Markdown context for Claude Code, Codex CLI, OpenCode, Kilo Code, and other Agent Skills-compatible tools.

The new skill MUST coexist with the upstream `session-handoff` skill and MUST NOT modify or remove it in v1.

## 2. Product Scope

### In scope

- A new skill named `unified-handoff`.
- CREATE, RESUME, LIST, CHECK, and MIGRATE workflows.
- Compact, standard, and full handoff modes.
- Target-agent-aware resume instructions while keeping one neutral core document.
- Git-aware operation with graceful degradation outside Git repositories.
- Cross-platform support for WSL/Linux, Windows PowerShell, macOS, Chinese paths, spaces, worktrees, and monorepos.
- Python 3.9+ implementation using only the standard library.
- Markdown output with YAML frontmatter.
- Validation, quality scoring, secret scanning, staleness checking, and legacy migration.

### Out of scope for v1

- A database, vector store, or persistent memory service.
- Automatic reading of proprietary session databases.
- Mandatory OpenCode plugin integration.
- Automatic merge into the fork's default branch.
- Full transcript export.

## 3. Supported Agents

The skill MUST support:

1. Claude Code
2. Codex CLI
3. OpenCode
4. Kilo Code, where Agent Skills compatibility permits
5. Generic Agent Skills-compatible tools

Agent-specific behavior MUST be limited to resume instructions and adapter documentation. The handoff schema MUST remain agent-neutral.

## 4. User Workflows

### 4.1 Create

The user or agent can request:

```text
/handoff
/handoff compact
/handoff standard
/handoff full
/handoff --target codex
/handoff --target opencode "Next session should fix login timeout"
```

The workflow MUST:

1. Collect project and Git metadata.
2. Generate a prefilled handoff scaffold.
3. Require the agent to fill semantic sections from current context.
4. Validate the completed document.
5. Save a timestamped archive.
6. Update `.agent-context/HANDOFF.md` only after successful validation.

Agents MAY proactively suggest creating a handoff after substantial work, but MUST NOT generate one silently.

### 4.2 Resume

The resume workflow MUST:

1. Locate the latest or requested handoff.
2. Check staleness.
3. Read the complete current handoff.
4. Read predecessor handoffs only when required.
5. Verify repository, branch, assumptions, blockers, and critical files.
6. Begin with `Immediate Next Steps` item 1.

### 4.3 List

The list workflow MUST show:

- Handoff ID
- Created time
- Title
- Mode
- Source agent
- Target agent
- Validation status
- Quality score
- Staleness summary when available

### 4.4 Check

The check workflow MUST validate an existing handoff without modifying it.

### 4.5 Migrate

The migration workflow MUST discover legacy `.claude/handoffs/` files and copy or convert them into `.agent-context/handoffs/` without deleting originals.

## 5. Storage Layout

Default layout:

```text
.agent-context/
├── HANDOFF.md
├── config.json
└── handoffs/
    └── YYYY-MM-DD-HHMMSS-[slug].md
```

Requirements:

- The location MUST be configurable.
- `.agent-context/HANDOFF.md` MUST be a content copy of the latest validated handoff, not a symlink.
- Archived handoffs MUST record `continues_from` when applicable.
- Handoffs SHOULD be committed to Git by default, but projects MAY ignore them through configuration.

## 6. Required Document Schema

Every standard or full handoff MUST contain:

1. Metadata
2. Objective
3. Current State
4. Completed Work
5. Files Changed
6. Decisions
7. Attempts and Failures
8. Evidence and Verification
9. User Requirements and Constraints
10. User Corrections
11. Important Context
12. Open Questions and Blockers
13. Immediate Next Steps
14. Resume Instructions
15. References
16. Security Check

A section that does not apply MUST contain `N/A` and a reason.

Compact mode MAY shorten sections but MUST preserve:

- Objective
- Current State
- Decisions
- Attempts and Failures
- Evidence and Verification
- User Requirements and Constraints
- Immediate Next Steps
- Security Check

## 7. Information Semantics

The document MUST distinguish:

- `VERIFIED`: supported by commands, tests, repository state, or direct user statements.
- `INFERRED`: reasoned from available evidence but not directly confirmed.
- `UNVERIFIED`: not yet checked.

Uncertainty MUST be explicit. Unsupported assumptions MUST NOT be presented as facts.

## 8. Attempts and Failures

Each important failed or abandoned approach SHOULD record:

| Attempt | Evidence | Why It Failed | Retry Condition | Do Not Repeat |
|---|---|---|---|---|

The skill MUST prioritize preventing repeated failed work across sessions.

## 9. Evidence and Verification

The handoff MUST capture, where applicable:

- Commands executed
- Tests passed
- Tests failed
- Build results
- Error summaries
- Performance or experiment metrics
- Items not yet verified

Full command output and full diffs SHOULD NOT be copied when a path, commit, or concise excerpt is sufficient.

## 10. User Requirements and Corrections

Explicit user requirements, prohibitions, preferences, and later corrections MUST be preserved separately from model assumptions.

A later user correction MUST override an earlier conflicting requirement and SHOULD record the conflict.

## 11. Metadata Frontmatter

Every generated handoff MUST begin with YAML frontmatter containing at least:

```yaml
---
schema_version: "1.0"
handoff_id: "YYYYMMDD-HHMMSS-slug"
created_at: "ISO-8601 timestamp"
source_agent: "unknown"
target_agent: "any"
mode: "standard"
repository: null
branch: null
head_commit: null
status: "draft"
quality_score: 0
continues_from: null
---
```

The implementation MAY write YAML-compatible scalar values without depending on a YAML parser.

## 12. Automatic Collection

When available, collect:

- Repository root
- Current branch
- HEAD commit
- Recent commits
- Staged files
- Unstaged files
- Untracked files
- Remote URL
- Operating system
- Shell
- Python version
- Node version
- Detected package manager
- Environment variable names only

The implementation MUST NOT collect environment variable values.

Active process inspection MUST be disabled by default and MAY be enabled by configuration.

## 13. Configuration

Use JSON for Python 3.9 compatibility.

Configuration SHOULD support:

- Storage directory
- Default mode
- Default target agent
- Language preference
- Quality thresholds
- Staleness thresholds
- Include/exclude file patterns
- Process inspection toggle
- Custom secret patterns
- Git tracking preference

Default language behavior: follow the current conversation language.

## 14. Quality Scoring

Minimum passing scores:

- Compact: 70
- Standard: 80
- Full: 85

Scoring MUST consider:

- Required section completeness
- Specificity
- Actionability
- Decision rationale
- Failed-attempt preservation
- Evidence quality
- User-constraint preservation
- Resume clarity
- Security status

On validation failure:

- Save as `*.draft.md` when explicitly requested.
- Do not update `.agent-context/HANDOFF.md`.

Blocking failures:

- Detected secret or credential
- Missing Objective
- Missing Current State
- Missing Immediate Next Steps
- Invalid frontmatter required fields

Warnings or score deductions:

- TODO placeholders
- Missing referenced files
- Unavailable Git state
- Empty optional sections

## 15. Security

Secret scanning MUST cover:

- Common API key formats
- Private key blocks
- Passwords
- Access tokens
- Session cookies
- Connection strings
- User-defined regex patterns

The markers `[REDACTED]` and `[SECRET_NAME_ONLY]` MUST be accepted and SHOULD be recommended.

Email addresses, usernames, and IP addresses MUST NOT be treated as secrets by default.

## 16. Staleness

Staleness analysis MUST consider:

- Time elapsed
- Commits since handoff
- Branch changes
- Critical file changes
- Working tree changes
- Deleted referenced files

Thresholds MUST be configurable.

Possible results:

- FRESH
- SLIGHTLY_STALE
- STALE
- VERY_STALE

## 17. Compatibility and Dependencies

- Python 3.9+
- Standard library only
- UTF-8 files
- Windows, WSL/Linux, and macOS
- Paths containing spaces and non-ASCII characters
- Git worktrees
- Monorepo subdirectories
- Graceful operation without Git

## 18. Installation

Document and support:

- `npx skills add`
- Manual copy
- Bash installation
- PowerShell installation
- `.agents/skills/` as the preferred shared location
- Agent-specific locations as alternatives

## 19. Documentation

Provide:

- English README
- Chinese README
- Schema reference
- Claude Code adapter
- Codex adapter
- OpenCode adapter
- Generic Agent Skills adapter
- Migration guide

The fork MUST retain upstream authorship and license notices.

## 20. Testing and CI

Required tests:

- Unit tests
- CLI integration tests
- Git and non-Git execution
- Windows-style and POSIX paths
- Spaces and Chinese characters in paths
- Secret detection
- Quality scoring
- Staleness evaluation
- Golden handoff snapshots
- Legacy migration

GitHub Actions SHOULD run on Ubuntu, Windows, and macOS with supported Python versions, plus Markdown and secret checks where practical.

## 21. Delivery

Development MUST occur on `feat-unified-handoff-v1`.

Commits SHOULD be staged by concern:

1. Requirements
2. Design
3. Scaffold and schema
4. Validation and security
5. Resume and staleness
6. Tests and CI
7. Documentation and migration

The final result MUST be delivered as a Draft PR against the fork's `main` branch and MUST NOT be automatically merged.
