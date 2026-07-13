from __future__ import annotations

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
