"""Handoff quality validation, finalization, and listing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .config import resolve_paths
from .constants import BLOCKING_SECTIONS, MODE_RECOMMENDED_SECTIONS, SCHEMA_VERSION, VALID_MODES
from .markdown import extract_sections, replace_frontmatter, split_frontmatter
from .models import ValidationResult
from .security import meaningful_section, placeholder_matches, scan_secrets, verify_file_references
from .system import atomic_write, iso_now


def validate_handoff(path: Path, project_root: Path, config: Mapping[str, Any]) -> ValidationResult:
    if not path.is_file():
        raise FileNotFoundError("Handoff not found: {}".format(path))
    content = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(content)
    mode = str(metadata.get("mode") or config.get("default_mode", "standard"))
    if mode not in VALID_MODES:
        mode = "standard"
    threshold = int(config["quality_thresholds"][mode])
    sections = extract_sections(body)
    blocking_errors: List[str] = []
    warnings: List[str] = []
    score = 100
    section_status: Dict[str, str] = {}

    required_metadata = ("schema_version", "handoff_id", "created_at", "status", "mode")
    for key in required_metadata:
        if metadata.get(key) in (None, ""):
            warnings.append("Missing frontmatter key: {}".format(key))
            score -= 3
    if metadata.get("schema_version") not in (SCHEMA_VERSION, None):
        warnings.append("Schema version {} is not supported by this release".format(metadata.get("schema_version")))
        score -= 5

    for section in BLOCKING_SECTIONS:
        complete, reason = meaningful_section(section, sections.get(section), mode)
        section_status[section] = reason
        if not complete:
            blocking_errors.append("{}: {}".format(section, reason))
            score -= 25

    recommended_weight = {"compact": 2, "standard": 3, "full": 4}[mode]
    for section in MODE_RECOMMENDED_SECTIONS[mode]:
        if section in BLOCKING_SECTIONS:
            continue
        complete, reason = meaningful_section(section, sections.get(section), mode)
        section_status[section] = reason
        if not complete:
            warnings.append("{}: {}".format(section, reason))
            score -= recommended_weight

    placeholders = placeholder_matches(body)
    if placeholders:
        unique_placeholders = list(dict.fromkeys(placeholders))
        warnings.append("{} unresolved placeholder(s) remain".format(len(placeholders)))
        score -= min(20, len(placeholders) * 2)
    else:
        unique_placeholders = []

    secret_findings, secret_warnings = scan_secrets(
        content,
        [str(item) for item in config.get("custom_secret_patterns", [])],
    )
    warnings.extend(secret_warnings)
    if secret_findings:
        blocking_errors.append("Potential secret material detected at {} location(s)".format(len(secret_findings)))
        score -= 30

    _, missing_references = verify_file_references(body, project_root)
    if missing_references:
        warnings.append("{} referenced file(s) were not found".format(len(missing_references)))
        score -= min(10, 2 * len(missing_references))

    knowledge = sections.get("Knowledge Status", "")
    if mode in ("standard", "full"):
        for label in ("Verified Fact", "Agent Inference", "Unverified Assumption"):
            if label not in knowledge:
                warnings.append("Knowledge Status does not distinguish {}".format(label))
                score -= 2

    constraints = sections.get("User Requirements and Constraints", "")
    if mode in ("standard", "full") and not meaningful_section(
        "User Requirements and Constraints",
        constraints,
        mode,
    )[0]:
        score -= 2

    score = max(0, min(100, score))
    ready = not blocking_errors and score >= threshold
    status = "ready" if ready else "blocked"
    if not blocking_errors and score < threshold:
        warnings.append("Score {} is below the {} threshold of {}".format(score, mode, threshold))

    return ValidationResult(
        path=str(path),
        mode=mode,
        score=score,
        threshold=threshold,
        ready=ready,
        status=status,
        blocking_errors=blocking_errors,
        warnings=warnings,
        secret_findings=secret_findings,
        missing_references=missing_references,
        placeholders=unique_placeholders,
        section_status=section_status,
    )


def finalized_name(path: Path) -> Path:
    if path.name.endswith(".draft.md"):
        return path.with_name(path.name[: -len(".draft.md")] + ".md")
    return path


def finalize_handoff(
    path: Path,
    project_root: Path,
    config: Mapping[str, Any],
) -> Tuple[ValidationResult, Optional[Path]]:
    result = validate_handoff(path, project_root, config)
    content = path.read_text(encoding="utf-8")
    metadata, _ = split_frontmatter(content)
    metadata["updated_at"] = iso_now()
    metadata["quality_score"] = result.score
    metadata["status"] = "validated" if result.ready else "draft"
    updated_content = replace_frontmatter(content, metadata)
    if not result.ready:
        atomic_write(path, updated_content)
        return result, None

    final_path = finalized_name(path)
    atomic_write(final_path, updated_content)
    if final_path != path and path.exists():
        path.unlink()
    paths = resolve_paths(project_root, config)
    atomic_write(paths.latest_file, updated_content)
    return result, final_path


def list_handoffs(
    project_root: Path,
    config: Mapping[str, Any],
    include_legacy: bool = False,
) -> List[Dict[str, Any]]:
    paths = resolve_paths(project_root, config)
    items: List[Dict[str, Any]] = []
    if paths.handoffs_dir.is_dir():
        for path in paths.handoffs_dir.glob("*.md"):
            try:
                metadata, body = split_frontmatter(path.read_text(encoding="utf-8"))
            except OSError:
                continue
            title_match = re.search(r"(?m)^#\s+(.+)$", body)
            items.append(
                {
                    "path": str(path),
                    "filename": path.name,
                    "title": title_match.group(1).strip() if title_match else path.stem,
                    "created_at": metadata.get("created_at"),
                    "status": metadata.get("status") or ("draft" if path.name.endswith(".draft.md") else "unknown"),
                    "mode": metadata.get("mode"),
                    "quality_score": metadata.get("quality_score"),
                    "legacy": path.name.startswith("legacy-"),
                    "mtime": path.stat().st_mtime,
                }
            )
    if include_legacy and paths.legacy_dir.is_dir():
        for path in paths.legacy_dir.glob("*.md"):
            items.append(
                {
                    "path": str(path),
                    "filename": path.name,
                    "title": path.stem,
                    "created_at": None,
                    "status": "legacy-source",
                    "mode": None,
                    "quality_score": None,
                    "legacy": True,
                    "mtime": path.stat().st_mtime,
                }
            )
    items.sort(key=lambda item: float(item["mtime"]), reverse=True)
    for item in items:
        item.pop("mtime", None)
    return items
