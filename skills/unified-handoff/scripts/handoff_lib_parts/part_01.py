"""Core logic for the unified-handoff Agent Skill.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import copy

import hashlib

import json

import os

import platform

import re

import shutil

import subprocess

import tempfile

from dataclasses import dataclass, field

from datetime import datetime, timezone

from pathlib import Path

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from urllib.parse import urlsplit, urlunsplit

SCHEMA_VERSION = "1.0"

VALID_MODES = ("compact", "standard", "full")

VALID_AGENTS = ("any", "claude-code", "codex", "opencode", "kilo-code", "generic")

DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "storage_dir": ".agent-context",
    "handoffs_subdir": "handoffs",
    "latest_file": "HANDOFF.md",
    "default_mode": "standard",
    "default_target_agent": "any",
    "default_language": "auto",
    "track_in_git": True,
    "quality_thresholds": {
        "compact": 70,
        "standard": 80,
        "full": 85,
    },
    "base_branch": "auto",
    "test_commands": [],
    "environment_variable_names": [],
    "custom_secret_patterns": [],
    "active_process_detection": False,
    "staleness": {
        "slight_days": 1,
        "stale_days": 7,
        "very_stale_days": 30,
        "slight_commits": 5,
        "stale_commits": 20,
        "very_stale_commits": 50,
        "slight_files": 5,
        "stale_files": 20,
    },
}

FRONTMATTER_ORDER = [
    "schema_version",
    "handoff_id",
    "created_at",
    "updated_at",
    "source_agent",
    "target_agent",
    "mode",
    "language",
    "status",
    "repository",
    "working_directory",
    "branch",
    "head_commit",
    "quality_score",
    "continues_from",
]

BLOCKING_SECTIONS = ("Objective", "Current State", "Immediate Next Steps")

MODE_RECOMMENDED_SECTIONS = {
    "compact": (
        "Completed Work",
        "Decisions",
        "Attempts and Failures",
        "Evidence and Verification",
        "User Requirements and Constraints",
        "Important Context",
        "Resume Instructions",
        "Security Check",
    ),
    "standard": (
        "Codebase Understanding",
        "Completed Work",
        "Files Changed",
        "Decisions",
        "Attempts and Failures",
        "Evidence and Verification",
        "User Requirements and Constraints",
        "User Corrections",
        "Knowledge Status",
        "Important Context",
        "Open Questions and Blockers",
        "Resume Instructions",
        "Environment State",
        "References",
        "Security Check",
    ),
    "full": (
        "Codebase Understanding",
        "Completed Work",
        "Files Changed",
        "Decisions",
        "Attempts and Failures",
        "Evidence and Verification",
        "User Requirements and Constraints",
        "User Corrections",
        "Knowledge Status",
        "Important Context",
        "Open Questions and Blockers",
        "Immediate Next Steps",
        "Resume Instructions",
        "Environment State",
        "References",
        "Security Check",
    ),
}

BUILTIN_SECRET_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("PEM private key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ("Bearer token", r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    ("GitHub token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b"),
    ("OpenAI-style API key", r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ("Slack token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    (
        "Credential assignment",
        r"(?i)\b(?:api[_-]?key|password|passwd|secret|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"']?(?!\[REDACTED\]|\[SECRET_NAME_ONLY\])[^\s\"']{10,}",
    ),
    (
        "Credential-bearing database URL",
        r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s/:]+:[^\s@]+@[^\s]+",
    ),
    (
        "Credential-bearing URL",
        r"(?i)\bhttps?://[^\s/@:]+:[^\s/@]+@[^\s]+",
    ),
)

PLACEHOLDER_PATTERNS = (
    re.compile(r"\[TODO(?::[^\]]*)?\]", re.IGNORECASE),
    re.compile(r"\[REPLACE[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[TASK_TITLE[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[DESCRIBE[^\]]*\]", re.IGNORECASE),
)

@dataclass
class CommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0

@dataclass
class Paths:
    project_root: Path
    storage_root: Path
    handoffs_dir: Path
    latest_file: Path
    config_file: Path
    legacy_dir: Path

@dataclass
class ValidationResult:
    path: str
    mode: str
    score: int
    threshold: int
    ready: bool
    status: str
    blocking_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    secret_findings: List[Dict[str, Any]] = field(default_factory=list)
    missing_references: List[str] = field(default_factory=list)
    placeholders: List[str] = field(default_factory=list)
    section_status: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "mode": self.mode,
            "score": self.score,
            "threshold": self.threshold,
            "ready": self.ready,
            "status": self.status,
            "blocking_errors": list(self.blocking_errors),
            "warnings": list(self.warnings),
            "secret_findings": list(self.secret_findings),
            "missing_references": list(self.missing_references),
            "placeholders": list(self.placeholders),
            "section_status": dict(self.section_status),
        }

def now_local() -> datetime:
    return datetime.now().astimezone()

def iso_now() -> str:
    return now_local().isoformat(timespec="seconds")

def run_command(
    args: Sequence[str],
    cwd: Optional[Path] = None,
    timeout: int = 10,
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            returncode=completed.returncode,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return CommandResult(ok=False, stderr=str(exc), returncode=127)

def deep_merge(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), MutableMapping):
            deep_merge(base[key], value)  # type: ignore[index]
        else:
            base[key] = copy.deepcopy(value)
    return base
