"""Configuration, project-root, and storage-path resolution."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .constants import DEFAULT_CONFIG, VALID_MODES
from .git import find_git_root
from .models import Paths
from .system import atomic_write, deep_merge


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path and config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid config file {}: {}".format(config_path, exc))
        if not isinstance(raw, dict):
            raise ValueError("Config root must be a JSON object: {}".format(config_path))
        deep_merge(config, raw)
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    mode = config.get("default_mode")
    if mode not in VALID_MODES:
        raise ValueError("default_mode must be one of: {}".format(", ".join(VALID_MODES)))
    thresholds = config.get("quality_thresholds")
    if not isinstance(thresholds, Mapping):
        raise ValueError("quality_thresholds must be an object")
    for mode_name in VALID_MODES:
        value = thresholds.get(mode_name)
        if not isinstance(value, int) or value < 0 or value > 100:
            raise ValueError("quality threshold for {} must be 0-100".format(mode_name))
    for list_field in ("test_commands", "environment_variable_names", "custom_secret_patterns"):
        if not isinstance(config.get(list_field), list):
            raise ValueError("{} must be a JSON array".format(list_field))


def nearest_context_root(start: Path, git_root: Optional[Path]) -> Optional[Path]:
    current = start.resolve()
    stop = git_root.resolve() if git_root else None
    while True:
        if (current / ".agent-context" / "config.json").is_file():
            return current
        if current.parent == current:
            break
        if stop and current == stop:
            break
        current = current.parent
    if stop and (stop / ".agent-context" / "config.json").is_file():
        return stop
    return None


def resolve_project_root(start: Path, explicit: Optional[Path] = None) -> Path:
    if explicit:
        return explicit.expanduser().resolve()
    start = start.expanduser().resolve()
    git_root = find_git_root(start)
    context_root = nearest_context_root(start, git_root)
    if context_root:
        return context_root
    if git_root:
        return git_root
    return start


def resolve_paths(project_root: Path, config: Mapping[str, Any]) -> Paths:
    storage = Path(str(config["storage_dir"]))
    if not storage.is_absolute():
        storage = project_root / storage
    handoffs = storage / str(config["handoffs_subdir"])
    latest = storage / str(config["latest_file"])
    return Paths(
        project_root=project_root,
        storage_root=storage,
        handoffs_dir=handoffs,
        latest_file=latest,
        config_file=storage / "config.json",
        legacy_dir=project_root / ".claude" / "handoffs",
    )


def write_default_config(project_root: Path, overwrite: bool = False) -> Path:
    path = project_root / ".agent-context" / "config.json"
    if path.exists() and not overwrite:
        return path
    atomic_write(path, json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n")
    return path
