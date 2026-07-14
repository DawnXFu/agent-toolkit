"""Public API for the unified-handoff implementation.

The package keeps the original ``handoff_lib`` import surface stable while the
implementation is organized into conventional, independently testable modules.
"""

from .config import (
    load_config,
    nearest_context_root,
    resolve_paths,
    resolve_project_root,
    validate_config,
    write_default_config,
)
from .constants import (
    BLOCKING_SECTIONS,
    BUILTIN_SECRET_PATTERNS,
    DEFAULT_CONFIG,
    FRONTMATTER_ORDER,
    MODE_RECOMMENDED_SECTIONS,
    SCHEMA_VERSION,
    VALID_AGENTS,
    VALID_MODES,
)
from .drafts import create_draft, find_latest_validated, normalize_predecessor
from .environment import (
    adapter_resume_text,
    collect_environment,
    detect_source_agent,
    executable_version,
    format_bullets,
    format_file_table,
    generate_handoff_id,
    infer_package_manager,
    infer_test_commands,
)
from .git import (
    collect_git_info,
    detect_base_branch,
    find_git_root,
    lines,
    repository_name_from_remote,
    sanitize_remote_url,
)
from .markdown import (
    extract_sections,
    json_scalar,
    parse_scalar,
    render_frontmatter,
    replace_frontmatter,
    sanitize_slug,
    split_frontmatter,
)
from .migration import find_handoff_argument, legacy_timestamp, migrate_legacy
from .models import CommandResult, Paths, ValidationResult
from .security import (
    extract_file_references,
    is_na_with_reason,
    line_number_for_offset,
    meaningful_section,
    placeholder_matches,
    scan_secrets,
    verify_file_references,
)
from .staleness import git_commit_exists, parse_datetime, resume_prompt, staleness_report
from .system import atomic_write, deep_merge, iso_now, now_local, run_command
from .validation import finalize_handoff, finalized_name, list_handoffs, validate_handoff

__all__ = [
    "BLOCKING_SECTIONS",
    "BUILTIN_SECRET_PATTERNS",
    "CommandResult",
    "DEFAULT_CONFIG",
    "FRONTMATTER_ORDER",
    "MODE_RECOMMENDED_SECTIONS",
    "Paths",
    "SCHEMA_VERSION",
    "VALID_AGENTS",
    "VALID_MODES",
    "ValidationResult",
    "adapter_resume_text",
    "atomic_write",
    "collect_environment",
    "collect_git_info",
    "create_draft",
    "deep_merge",
    "detect_base_branch",
    "detect_source_agent",
    "executable_version",
    "extract_file_references",
    "extract_sections",
    "finalize_handoff",
    "finalized_name",
    "find_git_root",
    "find_handoff_argument",
    "find_latest_validated",
    "format_bullets",
    "format_file_table",
    "generate_handoff_id",
    "git_commit_exists",
    "infer_package_manager",
    "infer_test_commands",
    "is_na_with_reason",
    "iso_now",
    "json_scalar",
    "legacy_timestamp",
    "line_number_for_offset",
    "lines",
    "list_handoffs",
    "load_config",
    "meaningful_section",
    "migrate_legacy",
    "nearest_context_root",
    "normalize_predecessor",
    "now_local",
    "parse_datetime",
    "parse_scalar",
    "placeholder_matches",
    "render_frontmatter",
    "replace_frontmatter",
    "repository_name_from_remote",
    "resolve_paths",
    "resolve_project_root",
    "resume_prompt",
    "run_command",
    "sanitize_remote_url",
    "sanitize_slug",
    "scan_secrets",
    "split_frontmatter",
    "staleness_report",
    "validate_config",
    "validate_handoff",
    "verify_file_references",
    "write_default_config",
]
