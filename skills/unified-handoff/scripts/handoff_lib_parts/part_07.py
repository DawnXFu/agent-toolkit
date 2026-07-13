from __future__ import annotations

def is_na_with_reason(value: str) -> bool:
    stripped = value.strip()
    return bool(re.match(r"(?is)^N/A\s*[-:]\s*\S+", stripped))

def placeholder_matches(content: str) -> List[str]:
    matches: List[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches.extend(match.group(0) for match in pattern.finditer(content))
    return matches

def meaningful_section(name: str, value: Optional[str], mode: str) -> Tuple[bool, str]:
    if value is None:
        return False, "missing"
    stripped = value.strip()
    if not stripped:
        return False, "empty"
    if name in BLOCKING_SECTIONS and is_na_with_reason(stripped):
        return False, "cannot be N/A"
    placeholders = placeholder_matches(stripped)
    if placeholders:
        return False, "contains placeholder"
    if is_na_with_reason(stripped):
        return True, "not applicable with reason"
    min_length = {"compact": 25, "standard": 40, "full": 60}.get(mode, 40)
    if name == "Immediate Next Steps":
        actionable = bool(re.search(r"(?m)^(?:\d+\.|- \[[ xX]\])\s+\S+", stripped))
        if not actionable:
            return False, "no actionable ordered or task-list item"
    if len(re.sub(r"[`|#*_\-]", "", stripped).strip()) < min_length:
        return False, "too short"
    return True, "complete"

def line_number_for_offset(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1

def scan_secrets(content: str, custom_patterns: Sequence[str] = ()) -> Tuple[List[Dict[str, Any]], List[str]]:
    sanitized = content
    findings: List[Dict[str, Any]] = []
    warnings: List[str] = []
    patterns: List[Tuple[str, str]] = list(BUILTIN_SECRET_PATTERNS)
    for index, pattern in enumerate(custom_patterns, 1):
        patterns.append(("Custom secret pattern {}".format(index), str(pattern)))
    for description, pattern in patterns:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            warnings.append("Invalid custom secret regex for {}: {}".format(description, exc))
            continue
        for match in regex.finditer(sanitized):
            findings.append(
                {
                    "type": description,
                    "line": line_number_for_offset(sanitized, match.start()),
                }
            )
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in findings:
        key = (item["type"], item["line"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped, warnings

def extract_file_references(content: str) -> List[str]:
    candidates: List[str] = []
    patterns = (
        r"`([^`\n]+?\.[A-Za-z0-9]{1,12}(?::\d+(?:-\d+)?)?)`",
        r"(?m)^\|\s*`?([^|`\n]+?\.[A-Za-z0-9]{1,12}(?::\d+(?:-\d+)?)?)`?\s*\|",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            raw = match.group(1).strip().split(":", 1)[0]
            raw = raw.replace("\\", "/")
            if raw.startswith(("http://", "https://", "git@", "mailto:")):
                continue
            if raw.startswith(("-", "$")) or " " in raw and "/" not in raw:
                continue
            if any(char in raw for char in ("*", "?", "<", ">", "|")):
                continue
            if "/" in raw or raw.startswith("."):
                candidates.append(raw)
    deduped: List[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped

def verify_file_references(content: str, project_root: Path) -> Tuple[List[str], List[str]]:
    existing: List[str] = []
    missing: List[str] = []
    root = project_root.resolve()
    for reference in extract_file_references(content):
        candidate = (root / reference).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            existing.append(reference)
        else:
            missing.append(reference)
    return existing, missing
