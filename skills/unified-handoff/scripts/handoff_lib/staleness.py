"""Staleness analysis and resume prompt generation."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .environment import adapter_resume_text
from .git import collect_git_info, lines
from .markdown import split_frontmatter
from .security import verify_file_references
from .system import now_local, run_command


def parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def git_commit_exists(repo_root: Path, commit: str) -> bool:
    if not commit:
        return False
    result = run_command(["git", "cat-file", "-e", "{}^{{commit}}".format(commit)], cwd=repo_root)
    return result.ok


def staleness_report(path: Path, project_root: Path, config: Mapping[str, Any]) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError("Handoff not found: {}".format(path))
    content = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(content)
    created = parse_datetime(metadata.get("created_at"))
    now = now_local()
    age_days = None
    if created:
        age_days = max(0.0, (now - created.astimezone(now.tzinfo)).total_seconds() / 86400.0)

    git_info = collect_git_info(project_root, config)
    issues: List[str] = []
    points = 0
    commits_since = None
    changed_files: List[str] = []
    baseline_available = False
    recorded_commit = str(metadata.get("head_commit") or "")

    thresholds = config.get("staleness", {})
    slight_days = float(thresholds.get("slight_days", 1))
    stale_days = float(thresholds.get("stale_days", 7))
    very_stale_days = float(thresholds.get("very_stale_days", 30))

    if age_days is not None:
        if age_days > very_stale_days:
            points += 3
            issues.append("Handoff is {:.1f} days old".format(age_days))
        elif age_days > stale_days:
            points += 2
            issues.append("Handoff is {:.1f} days old".format(age_days))
        elif age_days > slight_days:
            points += 1
            issues.append("Handoff is {:.1f} days old".format(age_days))

    repo_root_text = git_info.get("repo_root")
    if git_info.get("is_git_repo") and repo_root_text:
        repo_root = Path(str(repo_root_text))
        recorded_branch = metadata.get("branch")
        current_branch = git_info.get("branch")
        if recorded_branch and current_branch and recorded_branch != current_branch:
            points += 2
            issues.append("Current branch differs from recorded branch")

        if recorded_commit and git_commit_exists(repo_root, recorded_commit):
            baseline_available = True
            count = run_command(["git", "rev-list", "--count", "{}..HEAD".format(recorded_commit)], cwd=repo_root)
            if count.ok and count.stdout.isdigit():
                commits_since = int(count.stdout)
            changed = run_command(["git", "diff", "--name-only", "{}..HEAD".format(recorded_commit)], cwd=repo_root)
            if changed.ok:
                changed_files = lines(changed.stdout)
        elif recorded_commit:
            issues.append("Recorded HEAD commit is unavailable in the current repository")
            points += 2

        if commits_since is not None:
            if commits_since > int(thresholds.get("very_stale_commits", 50)):
                points += 3
                issues.append("{} commits have been added since the handoff".format(commits_since))
            elif commits_since > int(thresholds.get("stale_commits", 20)):
                points += 2
                issues.append("{} commits have been added since the handoff".format(commits_since))
            elif commits_since > int(thresholds.get("slight_commits", 5)):
                points += 1
                issues.append("{} commits have been added since the handoff".format(commits_since))

        changed_count = len(changed_files)
        if changed_count > int(thresholds.get("stale_files", 20)):
            points += 2
            issues.append("{} files changed since the recorded commit".format(changed_count))
        elif changed_count > int(thresholds.get("slight_files", 5)):
            points += 1
            issues.append("{} files changed since the recorded commit".format(changed_count))

        working_changes = (
            len(git_info.get("staged_files", []))
            + len(git_info.get("unstaged_files", []))
            + len(git_info.get("untracked_files", []))
        )
        if working_changes:
            points += 1
            issues.append("Current working tree has {} changed or untracked file(s)".format(working_changes))
    else:
        current_branch = None
        recorded_branch = metadata.get("branch")
        working_changes = None
        issues.append("Git metadata unavailable; staleness is based mainly on age and references")

    _, missing_refs = verify_file_references(body, project_root)
    if missing_refs:
        points += 2 if len(missing_refs) > 5 else 1
        issues.append("{} referenced file(s) no longer exist".format(len(missing_refs)))

    if not git_info.get("is_git_repo") and age_days is None:
        level = "UNKNOWN"
        recommendation = "Insufficient metadata; inspect the handoff and current files manually"
    elif points == 0:
        level = "FRESH"
        recommendation = "Safe to resume after a normal branch and assumptions check"
    elif points <= 2:
        level = "SLIGHTLY_STALE"
        recommendation = "Review repository changes and assumptions before continuing"
    elif points <= 4:
        level = "STALE"
        recommendation = "Re-verify critical files, decisions, and blockers before editing"
    else:
        level = "VERY_STALE"
        recommendation = "Create a new handoff or substantially refresh this one before use"

    return {
        "path": str(path),
        "level": level,
        "recommendation": recommendation,
        "points": points,
        "age_days": age_days,
        "recorded_branch": recorded_branch,
        "current_branch": current_branch,
        "recorded_commit": recorded_commit or None,
        "baseline_commit_available": baseline_available,
        "commits_since": commits_since,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files[:20],
        "missing_references": missing_refs,
        "issues": issues,
    }


def resume_prompt(
    path: Path,
    project_root: Path,
    config: Mapping[str, Any],
    target_agent: str,
) -> Dict[str, Any]:
    report = staleness_report(path, project_root, config)
    rel = os.path.relpath(str(path), str(project_root)).replace("\\", "/")
    prompt = adapter_resume_text(target_agent, rel)
    return {
        "handoff": str(path),
        "target_agent": target_agent,
        "staleness": report,
        "prompt": prompt,
    }
