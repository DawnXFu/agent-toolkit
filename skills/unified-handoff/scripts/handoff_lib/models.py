"""Shared data models for unified handoff workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


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
