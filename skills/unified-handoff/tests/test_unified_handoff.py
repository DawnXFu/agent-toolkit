from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
CLI = SCRIPTS_DIR / "unified_handoff.py"
sys.path.insert(0, str(SCRIPTS_DIR))

import handoff_lib as lib  # noqa: E402


def valid_document(created_at: str | None = None, mode: str = "standard") -> str:
    created = created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    metadata = {
        "schema_version": "1.0",
        "handoff_id": "20260714T120000-test01",
        "created_at": created,
        "updated_at": created,
        "source_agent": "generic",
        "target_agent": "any",
        "mode": mode,
        "language": "en",
        "status": "draft",
        "repository": None,
        "working_directory": ".",
        "branch": None,
        "head_commit": None,
        "quality_score": None,
        "continues_from": None,
    }
    body = """# Unified Handoff: Test implementation

## Objective

Finish and verify the portable session handoff implementation so another agent can continue without reconstructing decisions or state.

## Current State

The core workflow is implemented and the document is ready for validation. No production blocker remains, but final automated checks still need to run.

## Codebase Understanding

The skill separates agent instructions, command-line orchestration, and reusable domain logic. Markdown remains the portable source of truth.

## Completed Work

- [x] Implemented deterministic metadata collection, validation, finalization, resume guidance, and legacy migration behavior.

## Files Changed

The implementation and its documentation were updated together. The exact changes are available from version control rather than duplicated here.

## Decisions

A vendor-neutral Markdown protocol was selected instead of proprietary session identifiers because portability is the primary requirement.

## Attempts and Failures

N/A - no failed implementation attempts need to be repeated or avoided in the next session.

## Evidence and Verification

The Python sources compile, unit tests exercise critical workflows, and no external service or third-party package is required for execution.

## User Requirements and Constraints

The solution must work across Claude Code, Codex, and OpenCode, use Python standard library only, and degrade safely without Git.

## User Corrections

N/A - no unresolved user correction remains after the latest command-line behavior changes.

## Knowledge Status

| Type | Statement | Evidence or Basis | Validation Needed |
|---|---|---|---|
| Verified Fact | The document follows schema version one. | Parsed frontmatter and section checks. | None |
| Agent Inference | The workflow is portable across supported agents. | It avoids vendor session identifiers. | Run adapter smoke checks. |
| Unverified Assumption | All future agent versions retain skill discovery compatibility. | Current adapter documentation. | Recheck on major releases. |

## Important Context

Validated archives are immutable by convention. Continued work creates a new handoff linked to its predecessor rather than editing historical state.

## Open Questions and Blockers

N/A - no blocking question remains for the current implementation and validation scope.

## Immediate Next Steps

1. Run the complete automated test suite on every supported operating-system and Python-version combination.
2. Review the resulting branch diff for temporary bootstrap assets and remove any delivery-only files.
3. Confirm continuous integration is green before marking the pull request ready for review.

## Resume Instructions

Read the latest validated handoff completely, verify its freshness against current project state, and begin with the first immediate next step.

## Environment State

The implementation requires Python three point nine or newer, uses only the standard library, and does not require an active background service.

## References

N/A - version control history and the bundled protocol documentation contain all required references.

## Security Check

No credentials, private keys, authorization headers, cookies, or environment-variable values are included in this handoff document.
"""
    return lib.render_frontmatter(metadata) + body


class FrontmatterTests(unittest.TestCase):
    def test_round_trip_preserves_unicode_and_unknown_fields(self) -> None:
        metadata = {
            "schema_version": "1.0",
            "handoff_id": "测试-001",
            "quality_score": 88,
            "custom_field": "保留未知字段",
        }
        rendered = lib.render_frontmatter(metadata) + "# Body\n"
        parsed, body = lib.split_frontmatter(rendered)
        self.assertEqual(parsed, metadata)
        self.assertEqual(body, "# Body\n")


class DraftTests(unittest.TestCase):
    def test_create_draft_in_non_git_unicode_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "项目 space"
            root.mkdir()
            config = lib.load_config()
            draft = lib.create_draft(
                root,
                config,
                slug="登录 超时",
                goal="Continue investigating the login timeout with reproducible evidence.",
                source_agent="generic",
                target_agent="codex",
            )
            self.assertTrue(draft.is_file())
            self.assertEqual(draft.parent, root / ".agent-context" / "handoffs")
            metadata, body = lib.split_frontmatter(draft.read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "draft")
            self.assertEqual(metadata["target_agent"], "codex")
            self.assertIn("## Attempts and Failures", body)
            self.assertIn("## User Corrections", body)
            self.assertIn("## Knowledge Status", body)


class ValidationTests(unittest.TestCase):
    def test_generated_placeholder_draft_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = lib.load_config()
            draft = lib.create_draft(root, config, slug="unfinished")
            result = lib.validate_handoff(draft, root, config)
            self.assertFalse(result.ready)
            self.assertTrue(result.blocking_errors)
            self.assertTrue(result.placeholders)

    def test_secret_report_never_echoes_secret_value(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
        findings, warnings = lib.scan_secrets(f"api_key = {secret}\n")
            
        self.assertFalse(warnings)
        self.assertTrue(findings)
        self.assertNotIn(secret, json.dumps(findings))
        self.assertTrue(all("type" in item and "line" in item for item in findings))

    def test_finalize_updates_latest_and_removes_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = lib.load_config()
            draft = root / ".agent-context" / "handoffs" / "2026-07-14-test.draft.md"
            draft.parent.mkdir(parents=True)
            draft.write_text(valid_document(), encoding="utf-8")

            result, final_path = lib.finalize_handoff(draft, root, config)

            self.assertTrue(result.ready, result.to_dict())
            self.assertIsNotNone(final_path)
            assert final_path is not None
            self.assertTrue(final_path.is_file())
            self.assertFalse(draft.exists())
            latest = root / ".agent-context" / "HANDOFF.md"
            self.assertTrue(latest.is_file())
            self.assertEqual(latest.read_text(encoding="utf-8"), final_path.read_text(encoding="utf-8"))
            metadata, _ = lib.split_frontmatter(latest.read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "validated")
            self.assertGreaterEqual(metadata["quality_score"], 80)


class MigrationTests(unittest.TestCase):
    def test_legacy_migration_keeps_source_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / ".claude" / "handoffs" / "2026-07-14-120000-old.md"
            legacy.parent.mkdir(parents=True)
            original = "# Old handoff\n\nLegacy content remains available.\n"
            legacy.write_text(original, encoding="utf-8")

            results = lib.migrate_legacy(root, lib.load_config())

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["status"], "copied")
            self.assertEqual(legacy.read_text(encoding="utf-8"), original)
            target = Path(results[0]["target"])
            metadata, body = lib.split_frontmatter(target.read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "legacy")
            self.assertIn("Legacy content", body)


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_init_force_repairs_invalid_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / ".agent-context" / "config.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("{not valid json", encoding="utf-8")

            result = self.run_cli("init", "--project-root", str(root), "--force")

            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["default_mode"], "standard")

    def test_validate_requires_an_explicit_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("validate", "--project-root", tmp)
            self.assertEqual(result.returncode, 2)
            self.assertIn("file", result.stderr.lower())

    def test_resume_returns_warning_exit_for_stale_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / ".agent-context" / "HANDOFF.md"
            latest.parent.mkdir(parents=True)
            latest.write_text(valid_document("2000-01-01T00:00:00+00:00"), encoding="utf-8")

            result = self.run_cli("resume", "--project-root", str(root), "--target", "codex")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Staleness:", result.stdout)


if __name__ == "__main__":
    unittest.main()
