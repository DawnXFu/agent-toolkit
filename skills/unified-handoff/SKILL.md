---
name: unified-handoff
description: Create, validate, and resume standardized cross-agent session handoff documents. Use when the user asks to save context, continue in a fresh session, transfer work between Claude Code, Codex, OpenCode, or another agent, inspect handoff quality, or migrate old .claude/handoffs files.
license: MIT
compatibility: Python 3.9+; Git is optional. Supports Claude Code, Codex, OpenCode, and Agent Skills-compatible tools.
metadata:
  version: "1.0.0"
  protocol: "unified-handoff/1.0"
  origin: "Adapted from softaworks/agent-toolkit session-handoff"
---

# Unified Handoff

Create a portable Markdown handoff that lets a fresh agent continue with minimal ambiguity. The validated document, not a vendor session ID, is the source of truth.

## Invocation policy

- Create or modify handoff files only after the user explicitly asks to save, export, hand off, pause, or resume work.
- After substantial work, you may suggest creating a handoff, but do not create one automatically.
- Do not silently finalize a draft.
- Do not fabricate commands, tests, decisions, user corrections, or evidence.

## Locate the CLI

Set `SKILL_DIR` to the directory containing this `SKILL.md`. Run:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" <command> [options]
```

On Windows PowerShell:

```powershell
python "$env:SKILL_DIR\scripts\unified_handoff.py" <command> [options]
```

If the agent runtime exposes its own skill-directory variable, use that variable instead of guessing the installation path.

## Select the workflow

Interpret the user request as one of these modes:

| Intent | CLI command |
|---|---|
| Save/export current session | `create` then `validate --finalize` |
| Resume latest session | `resume` and `staleness` |
| Check document quality | `validate` or `check` |
| List handoffs | `list` |
| Inspect freshness | `staleness` |
| Migrate `.claude/handoffs/` | `migrate` |
| Initialize project config | `init` |

Default to `standard` mode and target `any` when the user does not specify them.

## CREATE workflow

### 1. Choose mode

- `compact`: small task or brief pause; threshold 70.
- `standard`: normal implementation, debugging, research, or documentation; threshold 80.
- `full`: complex architecture, prolonged investigation, or high-risk work; threshold 85.

### 2. Generate a draft

Use a concise slug and include the next-session objective when known:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" create <slug> \
  --goal "<next-session objective>" \
  --mode standard \
  --source <claude-code|codex|opencode|generic|auto> \
  --target <any|claude-code|codex|opencode|kilo-code|generic>
```

Use `--continues-from <archive-file>` when continuing an explicit predecessor. Otherwise the CLI links the latest validated handoff when available.

The command creates `.agent-context/handoffs/<timestamp>-<slug>.draft.md` and captures Git and environment metadata without embedding a full diff or environment variable values.

### 3. Fill the draft from current evidence

Read the complete generated draft. Replace every placeholder using the current conversation, repository, Git state, commands, test output, and user instructions.

Follow these evidence priorities:

1. Current files, command output, tests, builds, and measured results
2. Git history and working-tree state
3. Explicit user requirements and corrections
4. Existing plans, ADRs, issues, and validated handoffs
5. Agent inference, clearly labeled as inference
6. Unverified assumptions, clearly labeled with a validation step

Required content rules:

- `Objective`: exact outcome and purpose; never `N/A`.
- `Current State`: what works, what is incomplete, and the precise stopping point; never `N/A`.
- `Immediate Next Steps`: ordered, actionable items with files, commands, or verification targets; never `N/A`.
- `Attempts and Failures`: include the attempt, evidence, failure reason, retry condition, and whether repetition should be avoided.
- `Evidence and Verification`: distinguish commands actually run from candidate commands inferred by the scaffold.
- `User Corrections`: record corrections that supersede earlier assumptions.
- `Knowledge Status`: separate Verified Fact, Agent Inference, and Unverified Assumption.
- Use `N/A - <specific reason>` only for genuinely inapplicable non-blocking sections.
- Reference existing files, commits, plans, and issues instead of copying full diffs or long documents.
- Write section bodies in the user's conversation language unless configuration requires another language. Keep protocol headings unchanged.

### 4. Protect secrets

Never include:

- API keys, passwords, tokens, cookies, authorization headers, or private keys
- Credential-bearing connection strings or URLs
- Environment variable values
- Unnecessary personal information

Use `[REDACTED]` or `[SECRET_NAME_ONLY]` where the existence of a secret matters.

### 5. Validate and finalize

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" validate <draft-file> --finalize
```

Finalization is allowed only when:

- No secret finding exists.
- Objective, Current State, and Immediate Next Steps are complete.
- The mode-specific quality threshold is met.

On success, the CLI:

1. Creates the timestamped validated archive.
2. Removes the corresponding `.draft.md`.
3. Copies the validated content to `.agent-context/HANDOFF.md`.

On failure, keep the draft, report the blocking errors and warnings, improve the document, and rerun validation. Never replace `HANDOFF.md` with a failed draft.

### 6. Report completion

Tell the user:

- Validated archive path
- `HANDOFF.md` path
- Quality score and threshold
- First next action
- Any remaining warning that materially affects resumption

## RESUME workflow

### 1. Locate and assess

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" resume --target <agent>
python "$SKILL_DIR/scripts/unified_handoff.py" staleness
```

A specific archive may be passed as the positional file argument.

### 2. Read before acting

Read the complete handoff. If `continues_from` is present, read the predecessor only when the latest handoff refers to context that is not self-contained.

### 3. Verify current reality

Before editing:

1. Confirm project root, working directory, branch, and HEAD.
2. Inspect commits and file changes since the recorded commit.
3. Verify referenced critical files still exist.
4. Re-check blockers and assumptions.
5. Treat repository evidence and explicit User Corrections as authoritative when they conflict with old prose.
6. Do not rerun an attempt marked `Do Not Repeat: Yes` unless its Retry Condition is satisfied.

### 4. Continue

Start with `Immediate Next Steps` item 1. Record new evidence as work proceeds. For a later pause, create a new handoff that points to the current archive through `continues_from`.

## CHECK, LIST, and MIGRATE workflows

Validate without finalizing:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" check <file>
```

List unified and legacy files:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" list --include-legacy
```

Copy legacy Claude handoffs without deleting sources:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" migrate
```

Migrated files have `status: legacy` and are not promoted automatically to `HANDOFF.md`.

## Configuration

Create `.agent-context/config.json`:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" init
```

Read [references/protocol-schema.md](references/protocol-schema.md) for the schema and scoring contract. Read [references/handoff-template.md](references/handoff-template.md) when filling a document, [references/resume-checklist.md](references/resume-checklist.md) when resuming, and the relevant file under [references/adapters/](references/adapters/) for agent-specific discovery behavior.
