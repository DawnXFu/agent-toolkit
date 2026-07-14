# Unified Handoff Requirements

## 1. Purpose

Create a cross-agent Agent Skill that produces consistent, verifiable session handoff documents for Claude Code, Codex, OpenCode, and other Agent Skills-compatible tools. The skill must reduce context loss between sessions without requiring a persistent memory service, vector database, or vendor-specific session API.

## 2. Product Scope

The first release adds `skills/unified-handoff/` alongside the existing `skills/session-handoff/`. The existing skill remains unchanged for upstream compatibility.

Primary use cases:

- Software implementation and refactoring
- Debugging and incident investigation
- Research and evidence collection
- Technical writing and documentation
- Project planning and multi-session execution

The first release is optimized for code repositories but must degrade cleanly in non-Git directories.

## 3. Supported Agents

The skill must use the open Agent Skills layout and support:

- Claude Code
- OpenAI Codex CLI/IDE
- OpenCode
- Kilo Code where Agent Skills compatibility is available
- Generic Agent Skills-compatible tools

The canonical skill name is `unified-handoff`.

## 4. User Workflows

### 4.1 Create

The user or agent can create a draft handoff in compact, standard, or full mode. Creation must capture deterministic project metadata and generate a structured Markdown scaffold.

Example intent:

```text
/handoff next session should focus on the login timeout bug
```

Equivalent CLI:

```bash
python scripts/unified_handoff.py create login-timeout \
  --goal "Fix and verify the login timeout bug" \
  --mode standard \
  --target codex
```

### 4.2 Validate and finalize

Validation must score completeness, detect secrets, verify referenced files where practical, and identify blocking errors. Failed documents remain drafts and must not replace the current canonical handoff.

```bash
python scripts/unified_handoff.py validate <draft-file> --finalize
```

### 4.3 Resume

A new session must be able to locate the latest validated handoff, assess staleness, print a target-agent-specific continuation prompt, and begin from the first immediate next step.

```bash
python scripts/unified_handoff.py resume --target opencode
```

### 4.4 List and inspect

```bash
python scripts/unified_handoff.py list --include-legacy
python scripts/unified_handoff.py staleness <handoff-file>
python scripts/unified_handoff.py check <handoff-file>
```

### 4.5 Legacy migration

Existing `.claude/handoffs/*.md` files must remain readable. A migration command must copy them into the unified storage directory without deleting or modifying originals.

```bash
python scripts/unified_handoff.py migrate
```

## 5. Storage Requirements

Default project layout:

```text
.agent-context/
├── HANDOFF.md
├── config.json
└── handoffs/
    ├── 2026-07-13-230000-login-timeout.md
    └── 2026-07-13-231500-login-timeout-part-2.draft.md
```

Requirements:

- `.agent-context/handoffs/` stores timestamped history.
- `.agent-context/HANDOFF.md` is a physical copy of the latest validated handoff, not a symlink.
- Drafts end in `.draft.md`.
- A failed validation must never update `HANDOFF.md`.
- Each handoff records only its predecessor through `continues_from`.
- Storage paths are configurable through `.agent-context/config.json`.
- Paths must support Windows separators, WSL/Linux, spaces, Unicode, Git worktrees, and monorepo subprojects.
- Handoffs are tracked by Git by default; projects may override this in configuration.

## 6. Document Protocol

Every document must contain YAML frontmatter with machine-readable metadata:

```yaml
---
schema_version: "1.0"
handoff_id: "20260713T230000-abc123"
created_at: "2026-07-13T23:00:00-07:00"
updated_at: "2026-07-13T23:00:00-07:00"
source_agent: "claude-code"
target_agent: "any"
mode: "standard"
language: "auto"
status: "draft"
repository: "owner/repository"
working_directory: "."
branch: "feat/example"
head_commit: "0123456789abcdef"
quality_score: null
continues_from: null
---
```

The Markdown body must use stable English section identifiers so validators can work across output languages. Content inside sections should follow the user's conversation language unless configuration says otherwise.

Required protocol sections:

1. Objective
2. Current State
3. Codebase Understanding
4. Completed Work
5. Files Changed
6. Decisions
7. Attempts and Failures
8. Evidence and Verification
9. User Requirements and Constraints
10. User Corrections
11. Knowledge Status
12. Important Context
13. Open Questions and Blockers
14. Immediate Next Steps
15. Resume Instructions
16. Environment State
17. References
18. Security Check

A section that does not apply must contain `N/A - <reason>`. Objective, Current State, and Immediate Next Steps may not be `N/A`.

## 7. Information Quality Requirements

The handoff must explicitly separate:

- Verified facts and their evidence
- Agent inferences and their basis
- Unverified assumptions and how to validate them

The handoff must capture:

- What was completed
- What changed and why
- Decisions and rejected alternatives
- Failed attempts, evidence, failure cause, retry condition, and whether to avoid repetition
- Commands executed
- Tests, builds, and measured results
- Errors or failure summaries
- Items not yet verified
- User requirements and explicit corrections
- Blockers and open questions
- Concrete next steps, ordered by priority
- A target-agent-specific resume prompt

The document must reference existing plans, ADRs, commits, issues, and source files rather than duplicating large bodies of information or full diffs.

## 8. Modes and Quality Thresholds

| Mode | Intended use | Minimum score |
|---|---|---:|
| compact | Quick pause or small task | 70 |
| standard | Default development handoff | 80 |
| full | Complex debugging, architecture, or long research | 85 |

All modes use the same protocol. Compact mode permits more justified `N/A` sections; full mode requires stronger evidence and coverage.

Blocking conditions:

- A secret, credential, private key, or credential-bearing connection string is detected.
- Objective is missing or incomplete.
- Current State is missing or incomplete.
- Immediate Next Steps is missing, incomplete, or non-actionable.

Warnings and score deductions:

- Unresolved placeholders outside blocking sections
- Missing recommended content
- Broken file references
- Git metadata unavailable
- Stale handoff state
- Unverified claims not labeled as such

Allowed redaction markers:

- `[REDACTED]`
- `[SECRET_NAME_ONLY]`

## 9. Automatic Metadata Collection

When Git is available, collect:

- Repository root
- Current working directory relative to repository root
- Current branch or detached HEAD state
- HEAD commit
- Recent commits
- Staged files
- Unstaged files
- Untracked files
- Remote URL with embedded credentials removed
- Base branch when detectable
- Changed files relative to the base branch

Never embed a complete diff automatically.

Environment collection:

- Operating system
- Shell
- Python version
- Node.js version when available
- Detected package managers
- Inferred test/build commands
- Configured environment variable names only, never values

Active process detection is disabled by default and may be enabled through configuration in a future release.

## 10. Configuration

The implementation must support Python 3.9+ using only the standard library. Configuration therefore uses JSON rather than TOML or YAML.

Default configuration fields:

```json
{
  "schema_version": "1.0",
  "storage_dir": ".agent-context",
  "handoffs_subdir": "handoffs",
  "latest_file": "HANDOFF.md",
  "default_mode": "standard",
  "default_target_agent": "any",
  "default_language": "auto",
  "track_in_git": true,
  "quality_thresholds": {
    "compact": 70,
    "standard": 80,
    "full": 85
  },
  "base_branch": "auto",
  "test_commands": [],
  "environment_variable_names": [],
  "custom_secret_patterns": [],
  "active_process_detection": false
}
```

Unknown configuration fields should be preserved where possible and ignored safely.

## 11. Security Requirements

The validator must detect common forms of:

- API keys
- Password assignments
- Bearer tokens
- GitHub tokens
- OpenAI-style keys
- Slack tokens
- PEM private keys
- Database connection strings containing credentials
- Generic high-entropy credential assignments
- User-supplied regular expressions

The scanner must report finding type and line number without printing the suspected secret value.

No environment variable values, cookies, authorization headers, or full credential-bearing URLs may be written into a handoff.

## 12. Installation Requirements

Supported installation methods:

- `npx skills add DawnXFu/agent-toolkit --skill unified-handoff`
- Manual copy
- Bash installer
- PowerShell installer

Recommended shared locations:

- Codex and OpenCode: `.agents/skills/unified-handoff/` or `~/.agents/skills/unified-handoff/`
- Claude Code: `.claude/skills/unified-handoff/` or `~/.claude/skills/unified-handoff/`

The installers must support project and user scope. Symlinks may be optional; copying is the default for Windows reliability.

## 13. Documentation Requirements

Deliver:

- English `README.md`
- Chinese `README.zh-CN.md`
- `SKILL.md`
- Protocol schema reference
- Handoff template reference
- Resume checklist
- Claude Code, Codex, OpenCode, and generic adapter notes
- Migration guide
- Example configuration

Upstream authorship and MIT licensing must be retained and acknowledged.

## 14. Testing and CI Requirements

Automated tests must cover:

- Git and non-Git projects
- Unicode and spaces in paths
- Draft creation
- Frontmatter parsing and updating
- Quality thresholds by mode
- Blocking required-section failures
- Secret detection and redaction markers
- Finalization and `HANDOFF.md` update rules
- Legacy migration
- Staleness checks
- Windows-compatible path handling

A dedicated GitHub Actions workflow must test Python 3.9 through current supported versions on Ubuntu, Windows, and macOS. Markdown and secret scanning may run as separate jobs.

## 15. Acceptance Criteria

The release is accepted when:

1. A draft can be created in a Git or non-Git directory.
2. The generated document follows schema version 1.0.
3. A valid standard handoff scores at least 80 and can be finalized.
4. A failing handoff remains `.draft.md` and does not update `HANDOFF.md`.
5. A finalized handoff can be resumed by Claude Code, Codex, or OpenCode using the same Markdown file.
6. Secret findings block finalization without revealing secret values.
7. Legacy `.claude/handoffs/` files can be listed and copied into unified storage.
8. Unit tests pass on Python 3.9+.
9. Documentation explains installation and all primary workflows.
