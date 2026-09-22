"""Tests for the validator shipped inside the `write` skill.

The script is loaded from its place in the plugin rather than installed: it is a
PEP 723 script meant to run with `uv run --script`, and there is no package to import.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "axygen-checklist" / "skills" / "write" / "scripts" / "validate.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIVE = FIXTURES / "live"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their deferred annotations through sys.modules, so a module
    # executed straight from a path must be registered there first.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate = load_script()


def codes(findings: list[Any], level: str | None = None) -> list[str]:
    return [f.code for f in findings if level is None or f.level == level]


class SchemaAndStructure(unittest.TestCase):
    def test_valid_file_has_no_findings(self) -> None:
        self.assertEqual(validate.validate(FIXTURES / "valid.json"), [])

    def test_schema_breach_is_an_error(self) -> None:
        findings = validate.validate(FIXTURES / "schema-missing-text.json")
        self.assertEqual(codes(findings, "error"), ["schema"])
        self.assertIn("$.sections[0].items[0]", findings[0].message)

    def test_duplicate_id_is_an_error(self) -> None:
        findings = validate.validate(FIXTURES / "duplicate-id.json")
        self.assertEqual(codes(findings), ["duplicate-id"])
        self.assertIn("sections[1].items[0] (id 1)", findings[0].message)


class SuspiciousKeys(unittest.TestCase):
    def test_misspelled_optional_keys_are_errors(self) -> None:
        findings = validate.validate(FIXTURES / "typo-status.json")
        self.assertEqual(codes(findings), ["suspicious-key"] * 3)
        messages = "\n".join(f.message for f in findings)
        self.assertIn("'stauts' looks like 'status'", messages)
        self.assertIn("'notes' looks like 'note'", messages)
        self.assertIn("'Status' looks like 'status'", messages)

    def test_distinct_unknown_fields_pass(self) -> None:
        # `section_note` sits beside `section_name`, `ticket` is nothing like a field:
        # both are the unknown fields the format promises to keep.
        self.assertEqual(validate.validate(FIXTURES / "distinct-unknown-fields.json"), [])


class Fragments(unittest.TestCase):
    def test_backtick_problems_are_warnings(self) -> None:
        findings = validate.validate(FIXTURES / "unpaired-backtick.json")
        self.assertEqual(codes(findings, "error"), [])
        self.assertEqual(
            sorted(codes(findings)),
            ["empty-fragment", "unpaired-backtick", "unpaired-backtick", "unpaired-backtick"],
        )
        # The note spanning a line break reports both lines, each with its own number.
        note_lines = [f.message for f in findings if "note line" in f.message]
        self.assertEqual(len(note_lines), 2)


class ResultsWithoutSnapshot(unittest.TestCase):
    def test_results_are_warned_not_refused(self) -> None:
        findings = validate.validate(FIXTURES / "results-present.json")
        self.assertEqual(codes(findings, "error"), [])
        self.assertEqual(codes(findings), ["result-present", "result-present"])
        self.assertIn("status 'passed'", findings[0].message)
        self.assertIn("a comment", findings[1].message)


class LiveChecklist(unittest.TestCase):
    def check(self, name: str) -> list[Any]:
        return validate.validate(LIVE / name, LIVE / "before.json")

    def test_good_edit_is_clean(self) -> None:
        # Text and note changed, an item added with the next number: the author's work.
        self.assertEqual(self.check("good-edit.json"), [])

    def test_status_rewritten(self) -> None:
        findings = self.check("status-rewritten.json")
        self.assertEqual(codes(findings), ["status-changed"])
        self.assertIn("from 'passed' to 'pending'", findings[0].message)

    def test_comment_removed(self) -> None:
        self.assertEqual(codes(self.check("comment-removed.json")), ["comment-changed"])

    def test_item_removed_with_result(self) -> None:
        findings = self.check("item-removed-with-result.json")
        self.assertEqual(codes(findings), ["result-lost"])
        self.assertEqual(findings[0].level, "error")

    def test_item_removed_while_pending_is_a_warning(self) -> None:
        findings = self.check("item-removed-pending.json")
        self.assertEqual(codes(findings), ["item-removed"])
        self.assertEqual(findings[0].level, "warning")

    def test_id_reused_in_a_gap(self) -> None:
        findings = self.check("id-reused.json")
        self.assertEqual(codes(findings), ["id-reused"])
        self.assertIn("id 3, below the highest id in the snapshot (4)", findings[0].message)

    def test_renumbered_item(self) -> None:
        findings = self.check("renumbered.json")
        self.assertEqual(codes(findings), ["renumbered"])
        self.assertIn("item 4 reappears", findings[0].message)

    def test_new_item_with_result(self) -> None:
        self.assertEqual(codes(self.check("new-with-result.json")), ["result-invented"])


class Encoding(unittest.TestCase):
    def test_bom_is_tolerated(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bom.json"
            path.write_bytes(b"\xef\xbb\xbf" + (FIXTURES / "valid.json").read_bytes())
            self.assertEqual(validate.validate(path), [])

    def test_other_encoding_is_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cp1251.json"
            path.write_bytes('{"checklist_name": "Меню", "sections": []}'.encode("cp1251"))
            with self.assertRaises(validate.Unreadable) as raised:
                validate.validate(path)
            self.assertIn("not UTF-8", str(raised.exception))


class CommandLine(unittest.TestCase):
    def run_main(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = validate.main(list(args))
        return code, out.getvalue()

    def test_clean_file_exits_zero(self) -> None:
        code, out = self.run_main(str(FIXTURES / "valid.json"))
        self.assertEqual(code, 0)
        self.assertIn("0 error(s), 0 warning(s)", out)

    def test_warnings_alone_exit_zero(self) -> None:
        code, out = self.run_main(str(FIXTURES / "results-present.json"))
        self.assertEqual(code, 0)
        self.assertIn("warning: [result-present]", out)

    def test_errors_exit_one(self) -> None:
        code, out = self.run_main(str(FIXTURES / "duplicate-id.json"))
        self.assertEqual(code, 1)
        self.assertIn("error: [duplicate-id]", out)

    def test_before_enables_live_checks(self) -> None:
        code, out = self.run_main(str(LIVE / "status-rewritten.json"), "--before", str(LIVE / "before.json"))
        self.assertEqual(code, 1)
        self.assertIn("[status-changed]", out)

    def test_unreadable_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            path.write_text("{", encoding="utf-8")
            code, out = self.run_main(str(path))
        self.assertEqual(code, 2)
        self.assertIn("[unreadable]", out)


if __name__ == "__main__":
    unittest.main()
