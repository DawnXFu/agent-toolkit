"""Markdown frontmatter and section parsing helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .constants import FRONTMATTER_ORDER


def json_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in ("null", "~", ""):
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith(('"', "'")):
        try:
            if value.startswith('"'):
                return json.loads(value)
            return value[1:-1].replace("''", "'")
        except (json.JSONDecodeError, IndexError):
            return value.strip('"\'')
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            pass
    return value


def split_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    normalized = content.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized
    marker = normalized.find("\n---\n", 4)
    if marker < 0:
        return {}, normalized
    raw = normalized[4:marker]
    metadata: Dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]+", key):
            metadata[key] = parse_scalar(value)
    body = normalized[marker + 5 :]
    return metadata, body


def render_frontmatter(metadata: Mapping[str, Any]) -> str:
    keys = [key for key in FRONTMATTER_ORDER if key in metadata]
    keys.extend(sorted(key for key in metadata.keys() if key not in keys))
    lines = ["---"]
    for key in keys:
        lines.append("{}: {}".format(key, json_scalar(metadata.get(key))))
    lines.append("---")
    return "\n".join(lines) + "\n"


def replace_frontmatter(content: str, metadata: Mapping[str, Any]) -> str:
    _, body = split_frontmatter(content)
    return render_frontmatter(metadata) + body.lstrip("\n")


def extract_sections(body: str) -> Dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", body))
    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip()
    return sections


def sanitize_slug(value: Optional[str]) -> str:
    if not value:
        return "handoff"
    value = value.strip().lower().replace("_", " ")
    chars: List[str] = []
    previous_hyphen = False
    for char in value:
        if char.isalnum():
            chars.append(char)
            previous_hyphen = False
        elif not previous_hyphen:
            chars.append("-")
            previous_hyphen = True
    slug = "".join(chars).strip("-")
    return slug[:80] or "handoff"
