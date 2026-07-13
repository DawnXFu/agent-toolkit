from __future__ import annotations

def legacy_timestamp(path: Path) -> datetime:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-(\d{6})", path.name)
    if match:
        try:
            parsed = datetime.strptime("{} {}".format(match.group(1), match.group(2)), "%Y-%m-%d %H%M%S")
            return parsed.replace(tzinfo=now_local().tzinfo)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=now_local().tzinfo)

def migrate_legacy(project_root: Path, config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    paths = resolve_paths(project_root, config)
    paths.handoffs_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    if not paths.legacy_dir.is_dir():
        return results
    for source in sorted(paths.legacy_dir.glob("*.md")):
        target = paths.handoffs_dir / ("legacy-" + source.name)
        if target.exists():
            results.append({"source": str(source), "target": str(target), "status": "skipped-existing"})
            continue
        content = source.read_text(encoding="utf-8", errors="replace")
        metadata, body = split_frontmatter(content)
        if not metadata:
            timestamp = legacy_timestamp(source)
            metadata = {
                "schema_version": SCHEMA_VERSION,
                "handoff_id": generate_handoff_id(timestamp, source.stem),
                "created_at": timestamp.isoformat(timespec="seconds"),
                "updated_at": iso_now(),
                "source_agent": "claude-code",
                "target_agent": "any",
                "mode": "standard",
                "language": "auto",
                "status": "legacy",
                "repository": None,
                "working_directory": ".",
                "branch": None,
                "head_commit": None,
                "quality_score": None,
                "continues_from": None,
            }
            migrated = render_frontmatter(metadata) + body.lstrip("\n")
        else:
            metadata["schema_version"] = metadata.get("schema_version") or SCHEMA_VERSION
            metadata["status"] = "legacy"
            metadata["updated_at"] = iso_now()
            migrated = replace_frontmatter(content, metadata)
        atomic_write(target, migrated)
        results.append({"source": str(source), "target": str(target), "status": "copied"})
    return results

def write_default_config(project_root: Path, overwrite: bool = False) -> Path:
    path = project_root / ".agent-context" / "config.json"
    if path.exists() and not overwrite:
        return path
    atomic_write(path, json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n")
    return path

def find_handoff_argument(value: Optional[str], project_root: Path, config: Mapping[str, Any]) -> Optional[Path]:
    paths = resolve_paths(project_root, config)
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            direct = (project_root / candidate).resolve()
            archive = (paths.handoffs_dir / candidate.name).resolve()
            if direct.exists():
                return direct
            if archive.exists():
                return archive
        elif candidate.exists():
            return candidate.resolve()
        return None
    return find_latest_validated(paths)
