#!/usr/bin/env python3
"""CLI for creating, validating, resuming, and migrating unified handoffs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from handoff_lib import (
    VALID_AGENTS,
    VALID_MODES,
    create_draft,
    finalize_handoff,
    find_handoff_argument,
    list_handoffs,
    load_config,
    migrate_legacy,
    resolve_project_root,
    resume_prompt,
    staleness_report,
    validate_handoff,
    write_default_config,
)


def emit_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def load_project(args: argparse.Namespace) -> tuple[Path, Dict[str, Any]]:
    explicit = Path(args.project_root).expanduser() if args.project_root else None
    root = resolve_project_root(Path.cwd(), explicit)
    config_path: Optional[Path] = None
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
    else:
        candidate = root / ".agent-context" / "config.json"
        if candidate.exists():
            config_path = candidate
    return root, load_config(config_path)


def validation_payload(result: Any) -> Dict[str, Any]:
    return {
        "path": result.path,
        "mode": result.mode,
        "score": result.score,
        "threshold": result.threshold,
        "ready": result.ready,
        "status": result.status,
        "blocking_errors": result.blocking_errors,
        "warnings": result.warnings,
        "secret_findings": result.secret_findings,
        "missing_references": result.missing_references,
        "placeholders": result.placeholders,
        "section_status": result.section_status,
    }


def print_validation(result: Any) -> None:
    print(f"Quality: {result.score}/100 (threshold {result.threshold})")
    print("Verdict: READY" if result.ready else "Verdict: BLOCKED")
    if result.blocking_errors:
        print("Blocking errors:")
        for item in result.blocking_errors:
            print(f"  - {item}")
    if result.warnings:
        print("Warnings:")
        for item in result.warnings:
            print(f"  - {item}")
    if result.secret_findings:
        print("Secret findings:")
        for item in result.secret_findings:
            print(f"  - {item['type']} at line {item['line']}")


def cmd_init(args: argparse.Namespace) -> int:
    root, _ = load_project(args)
    path = write_default_config(root, overwrite=args.force)
    print(path)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    root, config = load_project(args)
    path = create_draft(
        project_root=root,
        config=config,
        slug=args.slug,
        mode=args.mode,
        source_agent=args.source,
        target_agent=args.target,
        language=args.language,
        goal=args.goal,
        continues_from=args.continues_from,
    )
    if args.json:
        emit_json({"status": "draft", "path": str(path)})
    else:
        print(path)
        print("Fill all placeholders, then run validate --finalize.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root, config = load_project(args)
    path = find_handoff_argument(args.file, root, config)
    if path is None:
        print("Handoff not found", file=sys.stderr)
        return 2
    if args.finalize:
        result, final_path = finalize_handoff(path, root, config)
    else:
        result = validate_handoff(path, root, config)
        final_path = None
    payload = validation_payload(result)
    payload["finalized_path"] = str(final_path) if final_path else None
    if args.json:
        emit_json(payload)
    else:
        print_validation(result)
        if final_path:
            print(f"Finalized: {final_path}")
    return 0 if result.ready else 1


def cmd_list(args: argparse.Namespace) -> int:
    root, config = load_project(args)
    items = list_handoffs(root, config, include_legacy=args.include_legacy)
    if args.json:
        emit_json(items)
        return 0
    if not items:
        print("No handoffs found.")
        return 0
    for item in items:
        score = item.get("quality_score")
        score_text = "-" if score is None else str(score)
        print(f"{item['filename']}\t{item['status']}\t{item.get('mode') or '-'}\t{score_text}\t{item['title']}")
    return 0


def cmd_staleness(args: argparse.Namespace) -> int:
    root, config = load_project(args)
    path = find_handoff_argument(args.file, root, config)
    if path is None:
        print("Handoff not found", file=sys.stderr)
        return 2
    report = staleness_report(path, root, config)
    if args.json:
        emit_json(report)
    else:
        print(f"Level: {report['level']}")
        print(f"Recommendation: {report['recommendation']}")
        for issue in report["issues"]:
            print(f"  - {issue}")
    return 0 if report["level"] in {"FRESH", "SLIGHTLY_STALE"} else 1


def cmd_resume(args: argparse.Namespace) -> int:
    root, config = load_project(args)
    path = find_handoff_argument(args.file, root, config)
    if path is None:
        print("No validated handoff found", file=sys.stderr)
        return 2
    result = resume_prompt(path, root, config, args.target)
    if args.json:
        emit_json(result)
    else:
        print(result["prompt"])
        print(f"Staleness: {result['staleness']['level']}")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    root, config = load_project(args)
    results = migrate_legacy(root, config)
    if args.json:
        emit_json(results)
    else:
        if not results:
            print("No legacy handoffs found.")
        for item in results:
            print(f"{item['status']}: {item['source']} -> {item['target']}")
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root")
    parser.add_argument("--config")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="unified_handoff.py")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create default project configuration")
    add_common(init)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    create = sub.add_parser("create", help="Create a draft handoff")
    add_common(create)
    create.add_argument("slug", nargs="?")
    create.add_argument("--goal")
    create.add_argument("--mode", choices=VALID_MODES)
    create.add_argument("--source", default="auto")
    create.add_argument("--target", choices=VALID_AGENTS)
    create.add_argument("--language")
    create.add_argument("--continues-from")
    create.set_defaults(func=cmd_create)

    for name in ("validate", "check"):
        validate = sub.add_parser(name, help="Validate a handoff")
        add_common(validate)
        validate.add_argument("file", nargs="?")
        validate.add_argument("--finalize", action="store_true")
        validate.set_defaults(func=cmd_validate)

    listing = sub.add_parser("list", help="List handoffs")
    add_common(listing)
    listing.add_argument("--include-legacy", action="store_true")
    listing.set_defaults(func=cmd_list)

    stale = sub.add_parser("staleness", help="Assess handoff staleness")
    add_common(stale)
    stale.add_argument("file", nargs="?")
    stale.set_defaults(func=cmd_staleness)

    resume = sub.add_parser("resume", help="Generate resume instructions")
    add_common(resume)
    resume.add_argument("file", nargs="?")
    resume.add_argument("--target", choices=VALID_AGENTS, default="any")
    resume.set_defaults(func=cmd_resume)

    migrate = sub.add_parser("migrate", help="Copy legacy Claude handoffs")
    add_common(migrate)
    migrate.set_defaults(func=cmd_migrate)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
