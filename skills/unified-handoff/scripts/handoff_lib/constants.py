"""Protocol constants and default configuration."""

from __future__ import annotations

from typing import Any, Dict, Tuple

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

PLACEHOLDER_PATTERN_STRINGS = (
    r"\[TODO(?::[^\]]*)?\]",
    r"\[REPLACE[^\]]*\]",
    r"\[TASK_TITLE[^\]]*\]",
    r"\[DESCRIBE[^\]]*\]",
)
