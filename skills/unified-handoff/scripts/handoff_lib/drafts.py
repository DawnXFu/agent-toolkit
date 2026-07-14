"""Draft discovery, predecessor linking, and scaffold generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .config import resolve_paths
from .constants import SCHEMA_VERSION, VALID_AGENTS, VALID_MODES
from .environment import (
    adapter_resume_text,
    collect_environment,
    detect_source_agent,
    format_bullets,
    format_file_table,
    generate_handoff_id,
)
from .git import collect_git_info
from .markdown import render_frontmatter, sanitize_slug, split_frontmatter
from .models import Paths
from .system import atomic_write, now_local


def find_latest_validated(paths: Paths) -> Optional[Path]:
    if paths.latest_file.is_file():
        return paths.latest_file
    if not paths.handoffs_dir.is_dir():
        return None
    candidates = [
        path
        for path in paths.handoffs_dir.glob("*.md")
        if not path.name.endswith(".draft.md") and not path.name.startswith("legacy-")
    ]
    return max(candidates, key=lambda item: item.stat().st_mtime) if candidates else None


def normalize_predecessor(value: Optional[str], paths: Paths) -> Optional[str]:
    if value:
        candidate = Path(value)
        if candidate.is_absolute() and candidate.exists():
            return candidate.name
        direct = paths.handoffs_dir / candidate.name
        if direct.exists():
            return direct.name
        return candidate.name
    latest = find_latest_validated(paths)
    if latest and latest != paths.latest_file:
        return latest.name
    if latest == paths.latest_file:
        metadata, _ = split_frontmatter(latest.read_text(encoding="utf-8"))
        handoff_id = metadata.get("handoff_id")
        for candidate in paths.handoffs_dir.glob("*.md"):
            if candidate.name.endswith(".draft.md"):
                continue
            try:
                candidate_meta, _ = split_frontmatter(candidate.read_text(encoding="utf-8"))
            except OSError:
                continue
            if candidate_meta.get("handoff_id") == handoff_id:
                return candidate.name
    return None


def create_draft(
    project_root: Path,
    config: Mapping[str, Any],
    slug: Optional[str] = None,
    mode: Optional[str] = None,
    source_agent: str = "auto",
    target_agent: Optional[str] = None,
    language: Optional[str] = None,
    goal: Optional[str] = None,
    continues_from: Optional[str] = None,
) -> Path:
    selected_mode = mode or str(config.get("default_mode", "standard"))
    if selected_mode not in VALID_MODES:
        raise ValueError("mode must be one of: {}".format(", ".join(VALID_MODES)))
    target = target_agent or str(config.get("default_target_agent", "any"))
    if target not in VALID_AGENTS:
        raise ValueError("target agent must be one of: {}".format(", ".join(VALID_AGENTS)))
    selected_language = language or str(config.get("default_language", "auto"))
    paths = resolve_paths(project_root, config)
    paths.handoffs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = now_local()
    clean_slug = sanitize_slug(slug or goal)
    filename = "{}-{}.draft.md".format(timestamp.strftime("%Y-%m-%d-%H%M%S"), clean_slug)
    draft_path = paths.handoffs_dir / filename
    counter = 2
    while draft_path.exists():
        draft_path = paths.handoffs_dir / "{}-{}-{}.draft.md".format(
            timestamp.strftime("%Y-%m-%d-%H%M%S"), clean_slug, counter
        )
        counter += 1

    git_info = collect_git_info(project_root, config)
    environment = collect_environment(project_root, config)
    predecessor = normalize_predecessor(continues_from, paths)
    source = detect_source_agent(source_agent)

    metadata: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "handoff_id": generate_handoff_id(timestamp, clean_slug),
        "created_at": timestamp.isoformat(timespec="seconds"),
        "updated_at": timestamp.isoformat(timespec="seconds"),
        "source_agent": source,
        "target_agent": target,
        "mode": selected_mode,
        "language": selected_language,
        "status": "draft",
        "repository": git_info.get("repository"),
        "working_directory": git_info.get("working_directory") or str(project_root),
        "branch": git_info.get("branch"),
        "head_commit": git_info.get("head_commit"),
        "quality_score": None,
        "continues_from": predecessor,
    }

    title = goal.strip() if goal else "[TASK_TITLE - replace this]"
    objective = goal.strip() if goal else "[TODO: State the outcome the next session must achieve and why it matters.]"
    latest_rel = str(Path(str(config["storage_dir"])) / str(config["latest_file"])).replace("\\", "/")
    resume_text = adapter_resume_text(target, latest_rel)
    recent_commits = format_bullets(git_info.get("recent_commits", []), "N/A - no Git commits detected")
    candidate_commands = format_bullets(
        environment.get("candidate_commands", []),
        "N/A - determine commands from project documentation",
    )
    package_managers = ", ".join(environment.get("package_managers", [])) or "none detected"
    env_names = ", ".join(environment.get("environment_variable_names", [])) or "none detected"
    predecessor_text = "`{}`".format(predecessor) if predecessor else "N/A - first handoff in this chain"

    body = f"""# Unified Handoff: {title}

## Objective

{objective}

## Current State

[TODO: Describe the exact current state, what works, what does not, and where the previous session stopped.]

## Codebase Understanding

### Architecture Overview

[TODO: Summarize only architecture needed to continue. Use `N/A - <reason>` when the task is not code-related.]

### Critical Files

| File | Purpose | Relevance |
|---|---|---|
| [TODO: repository-relative path] | [TODO] | [TODO] |

### Key Patterns Discovered

[TODO: Record conventions, APIs, data flow, or project-specific idioms the next agent must follow.]

## Completed Work

- [ ] [TODO: Replace with completed tasks using checked boxes.]

## Files Changed

| File | Git state | Change | Rationale |
|---|---|---|---|
{format_file_table(git_info)}

## Decisions

| Decision | Alternatives Considered | Evidence | Rationale |
|---|---|---|---|
| [TODO] | [TODO] | [TODO] | [TODO] |

## Attempts and Failures

| Attempt | Evidence/Result | Why It Failed | Retry Condition | Do Not Repeat |
|---|---|---|---|---|
| [TODO: Include failed or abandoned approaches. Use `N/A - no failed attempts` only when true.] | [TODO] | [TODO] | [TODO] | Yes/No |

## Evidence and Verification

### Commands Executed

- [TODO: Record commands actually executed, not inferred candidates.]

### Tests and Builds

- [TODO: Record pass/fail status and relevant output summary.]

### Errors and Measurements

- [TODO: Record error summaries, logs, performance values, or experimental metrics.]

### Unverified Items

- [TODO: Label every material claim that has not been verified.]

Candidate commands detected during scaffold creation:

{candidate_commands}

## User Requirements and Constraints

- [TODO: Record explicit user requirements, scope limits, compatibility targets, and prohibited approaches.]

## User Corrections

- [TODO: Record user corrections that override earlier assumptions. Use `N/A - no corrections` when true.]

## Knowledge Status

| Type | Statement | Evidence or Basis | Validation Needed |
|---|---|---|---|
| Verified Fact | [TODO] | [TODO] | None |
| Agent Inference | [TODO] | [TODO] | [TODO] |
| Unverified Assumption | [TODO] | [TODO] | [TODO] |

## Important Context

[TODO: Capture non-obvious context that cannot be recovered quickly from source files, Git history, or linked documents.]

### Potential Gotchas

- [TODO: Record edge cases, misleading behavior, or traps.]

## Open Questions and Blockers

- [ ] [TODO: State the blocker/question, owner, and exact condition for resolution.]

## Immediate Next Steps

1. [TODO: Give the first concrete action, including a file, command, or verification target.]
2. [TODO: Give the second action.]
3. [TODO: Give the completion check.]

## Resume Instructions

{resume_text}

- Verify predecessor: {predecessor_text}
- Run: `python <skill-dir>/scripts/unified_handoff.py staleness {latest_rel}`
- Treat User Corrections as higher priority than agent inferences.
- Re-check all Unverified Assumptions before relying on them.

## Environment State

- Operating system: `{environment['operating_system']}`
- Shell: `{environment['shell']}`
- Python: `{environment['python']}`
- Node.js: `{environment['node']}`
- Package managers: {package_managers}
- Environment variable names present: {env_names}
- Active process detection: {'enabled' if environment['active_process_detection'] else 'disabled'}
- Git repository: {'yes' if git_info['is_git_repo'] else 'no - metadata collection degraded'}
- Repository root: `{git_info.get('repo_root') or 'N/A'}`
- Base branch: `{git_info.get('base_branch') or 'N/A'}`

### Recent Commits

{recent_commits}

## References

- Continues from: {predecessor_text}
- [TODO: Link plans, ADRs, issues, commits, documentation, and repository-relative files. Do not paste full diffs.]

## Security Check

- [ ] No API keys, passwords, tokens, private keys, cookies, or credential-bearing URLs are present.
- [ ] Environment variable names may be listed; values are not included.
- [ ] Sensitive values are replaced with `[REDACTED]` or `[SECRET_NAME_ONLY]`.
- [ ] The validator has been run and the mode threshold has been met.
"""
    atomic_write(draft_path, render_frontmatter(metadata) + body)
    return draft_path
