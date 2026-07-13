# Unified Handoff

A cross-agent Agent Skill for producing consistent, validated session handoff documents that can be resumed by Claude Code, Codex, OpenCode, Kilo Code, or another compatible agent.

[中文说明](README.zh-CN.md)

## Why

Normal session summaries vary by model and often omit decisions, failed attempts, verification evidence, user corrections, or actionable next steps. Unified Handoff standardizes the artifact rather than depending on a vendor-specific session store.

## Features

- Schema version `1.0` with YAML frontmatter
- Compact, standard, and full modes with thresholds 70/80/85
- Draft-first lifecycle; failed validation never replaces `HANDOFF.md`
- Dedicated Decisions, Attempts and Failures, Evidence, User Constraints, User Corrections, and Knowledge Status sections
- Blocking secret detection without echoing matched values
- Git metadata and staleness checks, with non-Git degradation
- Read-only discovery and copy migration for `.claude/handoffs/`
- Python 3.9+, standard library only
- Windows, WSL/Linux, macOS, Unicode paths, spaces, worktrees, and monorepo subprojects

## Installation

Using the Agent Skills installer:

```bash
npx skills add DawnXFu/agent-toolkit --skill unified-handoff
```

Bash:

```bash
bash skills/unified-handoff/install/install.sh --scope user --agent all
```

PowerShell:

```powershell
./skills/unified-handoff/install/install.ps1 -Scope User -Agent All
```

The shared destination is `.agents/skills/unified-handoff`; Claude Code receives a copy under `.claude/skills/unified-handoff`. Copying is the default. Symlinks are optional.

## Quick start

Set `SKILL_DIR` to the installed skill directory, then initialize optional project configuration:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" init
```

Create a draft:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" create auth-timeout \
  --goal "Fix and verify the authentication timeout bug" \
  --mode standard \
  --source claude-code \
  --target codex
```

Fill the generated `.agent-context/handoffs/*.draft.md` from actual conversation and repository evidence. Then validate and finalize:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" validate \
  .agent-context/handoffs/<file>.draft.md --finalize
```

Resume in another agent:

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" resume --target opencode
```

## Commands

| Command | Purpose |
|---|---|
| `init` | Create `.agent-context/config.json` |
| `create` | Generate a timestamped draft scaffold |
| `validate` / `check` | Score and optionally finalize a handoff |
| `list` | List unified handoffs |
| `staleness` | Compare a handoff with current project state |
| `resume` | Produce a target-agent continuation prompt |
| `migrate` | Copy legacy `.claude/handoffs/*.md` files |

Global options such as `--project-root`, `--config`, and `--json` appear before the subcommand.

## Storage

```text
.agent-context/
├── HANDOFF.md
├── config.json
└── handoffs/
    ├── 2026-07-13-230000-auth-timeout.md
    └── 2026-07-13-231500-auth-timeout-part-2.draft.md
```

A failed document remains a draft. A successful finalization creates an archive file and physically copies it to `HANDOFF.md`, avoiding cross-platform symlink problems.

## Quality model

| Mode | Minimum score | Use |
|---|---:|---|
| compact | 70 | Small task or brief pause |
| standard | 80 | Normal development or research |
| full | 85 | Complex architecture or investigation |

Secrets and incomplete Objective, Current State, or Immediate Next Steps are blocking. Other omissions reduce the score and produce warnings.

## Configuration

Run `init` or copy `config.example.json` to `.agent-context/config.json`. Options include storage paths, default mode/language/target, thresholds, base branch, test-command candidates, environment-variable names, custom secret regexes, and staleness thresholds.

## Migration

```bash
python "$SKILL_DIR/scripts/unified_handoff.py" list --include-legacy
python "$SKILL_DIR/scripts/unified_handoff.py" migrate
```

Migration leaves `.claude/handoffs/` untouched. Copied files receive `status: legacy` and are not automatically promoted to `HANDOFF.md`.

## Testing

```bash
python -m unittest discover -s skills/unified-handoff/tests -v
python -m py_compile \
  skills/unified-handoff/scripts/handoff_lib.py \
  skills/unified-handoff/scripts/handoff_lib_parts/*.py \
  skills/unified-handoff/scripts/unified_handoff.py
```

## Documentation

- [Protocol schema](references/protocol-schema.md)
- [Template guidance](references/handoff-template.md)
- [Resume checklist](references/resume-checklist.md)
- [Migration guide](references/migration-guide.md)
- [Agent adapters](references/adapters/)

## Origin and license

Based on the `session-handoff` skill from `softaworks/agent-toolkit` and retaining the upstream MIT license. The unified protocol and its adapters, validator, migration behavior, tests, and installers are maintained in this fork.
