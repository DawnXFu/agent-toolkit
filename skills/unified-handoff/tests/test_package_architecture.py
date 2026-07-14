from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import handoff_lib  # noqa: E402


class PackageArchitectureTests(unittest.TestCase):
    def test_public_import_is_a_package(self) -> None:
        self.assertTrue(hasattr(handoff_lib, "__path__"))
        self.assertTrue((SCRIPTS_DIR / "handoff_lib" / "__init__.py").is_file())
        self.assertFalse((SCRIPTS_DIR / "handoff_lib.py").exists())

    def test_domain_modules_import_independently(self) -> None:
        modules = (
            "config",
            "constants",
            "drafts",
            "environment",
            "git",
            "markdown",
            "migration",
            "models",
            "security",
            "staleness",
            "system",
            "validation",
        )
        for name in modules:
            loaded = importlib.import_module("handoff_lib." + name)
            self.assertEqual(loaded.__name__, "handoff_lib." + name)

    def test_public_api_preserves_cli_contract(self) -> None:
        expected = {
            "VALID_AGENTS",
            "VALID_MODES",
            "create_draft",
            "finalize_handoff",
            "find_handoff_argument",
            "list_handoffs",
            "load_config",
            "migrate_legacy",
            "resolve_project_root",
            "resume_prompt",
            "staleness_report",
            "validate_handoff",
            "write_default_config",
        }
        self.assertTrue(expected.issubset(set(handoff_lib.__all__)))
        self.assertTrue(all(hasattr(handoff_lib, name) for name in expected))

    def test_dynamic_part_loader_cannot_return(self) -> None:
        package_dir = SCRIPTS_DIR / "handoff_lib"
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in package_dir.glob("*.py")
        )
        self.assertNotIn("exec(compile(", source)
        self.assertFalse((SCRIPTS_DIR / "handoff_lib_parts").exists())


if __name__ == "__main__":
    unittest.main()
