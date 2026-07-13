from __future__ import annotations

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

def find_git_root(start: Path) -> Optional[Path]:
    result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=start)
    if result.ok and result.stdout:
        return Path(result.stdout).resolve()
    return None

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

def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".handoff-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temp_name, str(path))
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise

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
