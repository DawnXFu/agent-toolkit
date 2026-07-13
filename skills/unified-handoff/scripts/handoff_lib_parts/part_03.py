from __future__ import annotations

def sanitize_remote_url(remote: str) -> str:
    remote = remote.strip()
    if not remote:
        return remote
    if re.match(r"^[^@\s]+@[^:]+:.+$", remote):
        return remote
    try:
        parsed = urlsplit(remote)
    except ValueError:
        return remote
    if parsed.scheme in ("http", "https") and "@" in parsed.netloc:
        hostname = parsed.hostname or ""
        if parsed.port:
            hostname = "{}:{}".format(hostname, parsed.port)
        return urlunsplit((parsed.scheme, hostname, parsed.path, parsed.query, parsed.fragment))
    return remote

def repository_name_from_remote(remote: str) -> Optional[str]:
    if not remote:
        return None
    path = remote
    ssh_match = re.match(r"^[^@\s]+@[^:]+:(.+)$", remote)
    if ssh_match:
        path = ssh_match.group(1)
    else:
        try:
            parsed = urlsplit(remote)
            if parsed.path:
                path = parsed.path
        except ValueError:
            pass
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return None

def lines(value: str) -> List[str]:
    return [item.strip() for item in value.splitlines() if item.strip()]

def detect_base_branch(repo_root: Path, configured: str = "auto") -> Optional[str]:
    candidates: List[str]
    if configured and configured != "auto":
        candidates = [configured]
    else:
        candidates = ["origin/main", "main", "origin/master", "master", "upstream/main", "upstream/master"]
    for candidate in candidates:
        result = run_command(["git", "rev-parse", "--verify", "--quiet", candidate], cwd=repo_root)
        if result.ok:
            return candidate
    return None

def collect_git_info(project_root: Path, config: Mapping[str, Any]) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "is_git_repo": False,
        "repo_root": None,
        "working_directory": str(project_root),
        "branch": None,
        "head_commit": None,
        "remote_url": None,
        "repository": None,
        "recent_commits": [],
        "staged_files": [],
        "unstaged_files": [],
        "untracked_files": [],
        "base_branch": None,
        "changed_from_base": [],
    }
    repo_root = find_git_root(project_root)
    if not repo_root:
        return info
    info["is_git_repo"] = True
    info["repo_root"] = str(repo_root)
    try:
        relative = project_root.resolve().relative_to(repo_root.resolve())
        info["working_directory"] = str(relative) if str(relative) else "."
    except ValueError:
        info["working_directory"] = str(project_root)

    branch = run_command(["git", "branch", "--show-current"], cwd=repo_root)
    if branch.ok and branch.stdout:
        info["branch"] = branch.stdout
    else:
        detached = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root)
        info["branch"] = "detached@{}".format(detached.stdout) if detached.ok else "detached"

    head = run_command(["git", "rev-parse", "HEAD"], cwd=repo_root)
    if head.ok:
        info["head_commit"] = head.stdout

    recent = run_command(["git", "log", "--oneline", "-5", "--no-decorate"], cwd=repo_root)
    if recent.ok:
        info["recent_commits"] = lines(recent.stdout)

    unstaged = run_command(["git", "diff", "--name-only"], cwd=repo_root)
    staged = run_command(["git", "diff", "--name-only", "--cached"], cwd=repo_root)
    untracked = run_command(["git", "ls-files", "--others", "--exclude-standard"], cwd=repo_root)
    info["unstaged_files"] = lines(unstaged.stdout) if unstaged.ok else []
    info["staged_files"] = lines(staged.stdout) if staged.ok else []
    info["untracked_files"] = lines(untracked.stdout) if untracked.ok else []

    remote = run_command(["git", "remote", "get-url", "origin"], cwd=repo_root)
    if remote.ok and remote.stdout:
        clean_remote = sanitize_remote_url(remote.stdout)
        info["remote_url"] = clean_remote
        info["repository"] = repository_name_from_remote(clean_remote)

    base_branch = detect_base_branch(repo_root, str(config.get("base_branch", "auto")))
    info["base_branch"] = base_branch
    if base_branch:
        changed = run_command(["git", "diff", "--name-only", "{}...HEAD".format(base_branch)], cwd=repo_root)
        if changed.ok:
            info["changed_from_base"] = lines(changed.stdout)
    return info

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
