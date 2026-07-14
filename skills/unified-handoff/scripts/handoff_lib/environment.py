"""Environment inspection, command inference, and adapter text generation."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .system import run_command


def executable_version(name: str, args: Sequence[str]) -> Optional[str]:
    if not shutil.which(name):
        return None
    result = run_command([name] + list(args), timeout=5)
    if result.ok and result.stdout:
        return result.stdout.splitlines()[0].strip()
    return None


def infer_package_manager(project_root: Path) -> List[str]:
    markers = (
        ("uv", "uv.lock"),
        ("poetry", "poetry.lock"),
        ("pnpm", "pnpm-lock.yaml"),
        ("yarn", "yarn.lock"),
        ("npm", "package-lock.json"),
        ("bun", "bun.lockb"),
        ("bun", "bun.lock"),
        ("pip", "requirements.txt"),
    )
    found: List[str] = []
    for manager, marker in markers:
        if (project_root / marker).exists() and manager not in found:
            found.append(manager)
    return found


def infer_test_commands(project_root: Path, config: Mapping[str, Any]) -> List[str]:
    configured = [str(item) for item in config.get("test_commands", []) if str(item).strip()]
    if configured:
        return configured
    commands: List[str] = []
    package_json = project_root / "package.json"
    if package_json.is_file():
        manager = "npm"
        if (project_root / "pnpm-lock.yaml").exists():
            manager = "pnpm"
        elif (project_root / "yarn.lock").exists():
            manager = "yarn"
        elif (project_root / "bun.lockb").exists() or (project_root / "bun.lock").exists():
            manager = "bun"
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        except (OSError, json.JSONDecodeError):
            scripts = {}
        if isinstance(scripts, dict):
            for script in ("test", "lint", "typecheck", "build"):
                if script in scripts:
                    if manager == "npm" and script == "test":
                        commands.append("npm test")
                    elif manager == "yarn":
                        commands.append("yarn {}".format(script))
                    elif manager == "bun":
                        commands.append("bun run {}".format(script))
                    else:
                        commands.append("{} run {}".format(manager, script))

    python_markers = any(
        (project_root / name).exists()
        for name in ("pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg")
    ) or (project_root / "tests").is_dir()
    if python_markers:
        if (project_root / "pytest.ini").exists() or (project_root / "pyproject.toml").exists():
            commands.append("python -m pytest")
        else:
            commands.append("python -m unittest discover")

    makefile = project_root / "Makefile"
    if makefile.is_file():
        try:
            make_text = makefile.read_text(encoding="utf-8", errors="replace")
            for target in ("test", "lint", "check", "build"):
                if re.search(r"(?m)^{}\s*:".format(re.escape(target)), make_text):
                    commands.append("make {}".format(target))
        except OSError:
            pass

    deduped: List[str] = []
    for command in commands:
        if command not in deduped:
            deduped.append(command)
    return deduped


def detect_source_agent(explicit: str = "auto") -> str:
    if explicit and explicit != "auto":
        return explicit
    env_names = set(os.environ.keys())
    if {"CLAUDE_CODE_ENTRYPOINT", "CLAUDE_SESSION_ID"} & env_names:
        return "claude-code"
    if {"CODEX_HOME", "CODEX_THREAD_ID"} & env_names:
        return "codex"
    if {"OPENCODE", "OPENCODE_SESSION_ID"} & env_names:
        return "opencode"
    return "unknown"


def collect_environment(project_root: Path, config: Mapping[str, Any]) -> Dict[str, Any]:
    shell_value = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "unknown"
    node_version = executable_version("node", ["--version"])
    managers = infer_package_manager(project_root)
    detected_versions: Dict[str, str] = {}
    for manager in ("uv", "poetry", "pnpm", "yarn", "npm", "bun"):
        if manager in managers:
            version = executable_version(manager, ["--version"])
            if version:
                detected_versions[manager] = version
    configured_names = [str(name) for name in config.get("environment_variable_names", [])]
    safe_defaults = ("CI", "NODE_ENV", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV")
    env_names = sorted({name for name in configured_names + list(safe_defaults) if name in os.environ})
    return {
        "operating_system": "{} {}".format(platform.system(), platform.release()).strip(),
        "shell": Path(shell_value).name if shell_value else "unknown",
        "python": platform.python_version(),
        "node": node_version or "not detected",
        "package_managers": managers,
        "package_manager_versions": detected_versions,
        "candidate_commands": infer_test_commands(project_root, config),
        "environment_variable_names": env_names,
        "active_process_detection": bool(config.get("active_process_detection", False)),
    }


def format_bullets(values: Iterable[str], empty: str = "N/A - none detected") -> str:
    items = [str(value) for value in values if str(value).strip()]
    if not items:
        return "- {}".format(empty)
    return "\n".join("- `{}`".format(item) for item in items)


def format_file_table(git_info: Mapping[str, Any]) -> str:
    states: List[Tuple[str, str]] = []
    for state, key in (
        ("staged", "staged_files"),
        ("unstaged", "unstaged_files"),
        ("untracked", "untracked_files"),
        ("branch diff", "changed_from_base"),
    ):
        for path in git_info.get(key, []) or []:
            entry = (str(path), state)
            if entry not in states:
                states.append(entry)
    if not states:
        return "| N/A - no changed files detected | N/A | N/A | N/A |"
    rows = []
    for path, state in states[:30]:
        rows.append("| `{}` | {} | [TODO: summarize change] | [TODO: explain rationale] |".format(path, state))
    if len(states) > 30:
        rows.append("| ... {} additional files | mixed | See Git status | N/A |".format(len(states) - 30))
    return "\n".join(rows)


def adapter_resume_text(target_agent: str, latest_rel: str) -> str:
    prompt = (
        "Read `{}` completely. Verify the current branch and run the staleness check before editing. "
        "Resolve contradictions in favor of repository evidence and explicit user corrections. "
        "Then begin with Immediate Next Steps item 1."
    ).format(latest_rel)
    if target_agent == "claude-code":
        return "Start Claude Code with `claude`, then send:\n\n> {}".format(prompt)
    if target_agent == "codex":
        return "Start Codex with `codex`, explicitly invoke `$unified-handoff` when needed, then send:\n\n> {}".format(prompt)
    if target_agent == "opencode":
        return "Start OpenCode with `opencode`, load the `unified-handoff` skill, then send:\n\n> {}".format(prompt)
    if target_agent == "kilo-code":
        return "Open a new Kilo Code session, load the `unified-handoff` skill if available, then send:\n\n> {}".format(prompt)
    return "In the new agent session, send:\n\n> {}".format(prompt)


def generate_handoff_id(timestamp: datetime, slug: str) -> str:
    digest = hashlib.sha256((timestamp.isoformat() + slug).encode("utf-8")).hexdigest()[:6]
    return "{}-{}".format(timestamp.strftime("%Y%m%dT%H%M%S"), digest)
