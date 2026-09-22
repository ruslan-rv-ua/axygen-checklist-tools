# /// script
# requires-python = ">=3.12"
# dependencies = ["jsonschema>=4.23,<5"]
# ///
"""Check a checklist file for the Axygen Checklist add-on beyond what its schema can say.

Usage:
    validate.py CHECKLIST
    validate.py CHECKLIST --before SNAPSHOT

The schema next to this script (../references/checklist-v1.schema.json) says what a
valid file looks like, and this script runs it first. Then it adds the checks the
schema cannot express: an `id` that repeats, a key that looks like a misspelled field
name, a backtick left without its pair, and, given `--before`, everything an edit
of a live checklist must leave alone: the tester's `status` and `comment`, the
numbers of existing items, and the rule that a new item takes the next unused number.

Exit code 0: no errors (warnings may be printed). 1: at least one error. 2: the
checklist or the snapshot could not be read as JSON at all.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "references" / "checklist-v1.schema.json"

PENDING = "pending"
KNOWN_KEYS: dict[str, frozenset[str]] = {
    "document": frozenset({"$schema", "format_version", "checklist_name", "sections"}),
    "section": frozenset({"section_name", "items"}),
    "item": frozenset({"id", "text", "status", "note", "comment"}),
}
# Two keys closer than this are taken for one key spelled twice.
TYPO_RATIO = 0.75

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.level}: [{self.code}] {self.message}"


@dataclass(frozen=True)
class Located:
    section: int
    index: int
    item: dict[str, Any]

    @property
    def where(self) -> str:
        place = f"sections[{self.section}].items[{self.index}]"
        item_id = self.item.get("id")
        return f"{place} (id {item_id})" if isinstance(item_id, int) else place


class Unreadable(Exception):
    """The file is not a JSON document; nothing further can be checked."""


def load_json(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Unreadable(f"{path}: cannot read: {exc.strerror}") from exc
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Unreadable(f"{path}: not UTF-8 (byte {exc.start}); the add-on refuses such a file") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise Unreadable(f"{path}: not JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}") from exc


def sections(data: Any) -> list[tuple[int, dict[str, Any]]]:
    if not isinstance(data, dict):
        return []
    found: Any = cast(dict[str, Any], data).get("sections")
    if not isinstance(found, list):
        return []
    return [
        (index, cast(dict[str, Any], section))
        for index, section in enumerate(cast(list[Any], found))
        if isinstance(section, dict)
    ]


def items(data: Any) -> list[Located]:
    located: list[Located] = []
    for section_index, section in sections(data):
        found: Any = section.get("items")
        if not isinstance(found, list):
            continue
        for index, item in enumerate(cast(list[Any], found)):
            if isinstance(item, dict):
                located.append(Located(section_index, index, cast(dict[str, Any], item)))
    return located


def status_of(item: dict[str, Any]) -> Any:
    return item.get("status", PENDING)


def check_schema(data: Any) -> list[Finding]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[jsonschema.ValidationError] = sorted(
        validator.iter_errors(data),  # pyright: ignore[reportUnknownMemberType]
        key=lambda error: error.json_path,
    )
    return [Finding(ERROR, "schema", f"{error.json_path}: {error.message}") for error in errors]


def check_ids(data: Any) -> list[Finding]:
    seen: dict[int, str] = {}
    findings: list[Finding] = []
    for located in items(data):
        item_id = located.item.get("id")
        if not isinstance(item_id, int):
            continue
        if item_id in seen:
            findings.append(
                Finding(
                    ERROR,
                    "duplicate-id",
                    f"{located.where} repeats id {item_id} of {seen[item_id]}; the add-on refuses the file",
                ),
            )
        else:
            seen[item_id] = located.where
    return findings


def suspicious_keys(obj: dict[str, Any], known: frozenset[str]) -> list[tuple[str, str]]:
    """Unknown keys that look like a known key which the object does not carry.

    A key is only a typo candidate while the key it resembles is absent: when both
    are present, the unknown one is a distinct field the author meant to add, which
    the format allows.
    """
    found: list[tuple[str, str]] = []
    for key in obj:
        if key in known:
            continue
        lowered = key.lower()
        for candidate in sorted(known):
            if candidate in obj:
                continue
            if (
                lowered == candidate.lower()
                or difflib.SequenceMatcher(None, lowered, candidate).ratio() >= TYPO_RATIO
            ):
                found.append((key, candidate))
                break
    return found


def check_keys(data: Any) -> list[Finding]:
    findings: list[Finding] = []

    def report(where: str, obj: dict[str, Any], level: str) -> None:
        for key, candidate in suspicious_keys(obj, KNOWN_KEYS[level]):
            findings.append(
                Finding(
                    ERROR,
                    "suspicious-key",
                    f"{where}: {key!r} looks like {candidate!r} misspelled; the add-on would ignore it",
                ),
            )

    if isinstance(data, dict):
        report("document", cast(dict[str, Any], data), "document")
    for index, section in sections(data):
        report(f"sections[{index}]", section, "section")
    for located in items(data):
        report(located.where, located.item, "item")
    return findings


def check_fragments(data: Any) -> list[Finding]:
    findings: list[Finding] = []
    for located in items(data):
        for field in ("text", "note"):
            value = located.item.get(field)
            if not isinstance(value, str):
                continue
            for number, line in enumerate(value.split("\n"), start=1):
                if line.count("`") % 2:
                    findings.append(
                        Finding(
                            WARNING,
                            "unpaired-backtick",
                            f"{located.where}: {field} line {number} has an odd number of backticks; "
                            "one is left as plain text and marks no fragment",
                        ),
                    )
                if "``" in line:
                    findings.append(
                        Finding(
                            WARNING,
                            "empty-fragment",
                            f"{located.where}: {field} line {number} has an empty backtick pair, "
                            "which produces no fragment",
                        ),
                    )
    return findings


def check_results_in_new(data: Any) -> list[Finding]:
    """Results in a file that has no snapshot to compare with.

    Fine for a file the tester has run; a claim nobody made in a freshly written one.
    The script cannot tell the two apart, so it warns.
    """
    findings: list[Finding] = []
    for located in items(data):
        carried: list[str] = []
        if status_of(located.item) != PENDING:
            carried.append(f"status {status_of(located.item)!r}")
        if "comment" in located.item:
            carried.append("a comment")
        if carried:
            findings.append(
                Finding(
                    WARNING,
                    "result-present",
                    f"{located.where} carries {' and '.join(carried)}; a result belongs to the tester, "
                    "so in a freshly written file it is a claim nobody made",
                ),
            )
    return findings


def by_id(data: Any) -> dict[int, Located]:
    indexed: dict[int, Located] = {}
    for located in items(data):
        item_id = located.item.get("id")
        if isinstance(item_id, int) and item_id not in indexed:
            indexed[item_id] = located
    return indexed


def check_against(before: Any, after: Any) -> list[Finding]:
    """Everything an edit of a live checklist must leave alone."""
    findings: list[Finding] = []
    old_items = by_id(before)
    new_items = by_id(after)
    added = {item_id: located for item_id, located in new_items.items() if item_id not in old_items}

    for item_id, old in old_items.items():
        new = new_items.get(item_id)
        if new is None:
            findings.append(removed_item(item_id, old, added))
            continue
        old_status, new_status = status_of(old.item), status_of(new.item)
        if old_status != new_status:
            findings.append(
                Finding(
                    ERROR,
                    "status-changed",
                    f"{new.where}: status went from {old_status!r} to {new_status!r}; "
                    "the tester's result was rewritten",
                ),
            )
        if old.item.get("comment") != new.item.get("comment"):
            findings.append(
                Finding(
                    ERROR,
                    "comment-changed",
                    f"{new.where}: comment differs from the snapshot; the tester's conclusion was rewritten",
                ),
            )

    highest = max(old_items, default=0)
    for item_id, new in added.items():
        if item_id <= highest:
            findings.append(
                Finding(
                    ERROR,
                    "id-reused",
                    f"{new.where}: new item takes id {item_id}, below the highest id in the snapshot "
                    f"({highest}); a new item takes the next unused number and gaps stay gaps",
                ),
            )
        if status_of(new.item) != PENDING or "comment" in new.item:
            findings.append(
                Finding(
                    ERROR,
                    "result-invented",
                    f"{new.where}: new item carries a status or a comment; nobody has tested it",
                ),
            )
    return findings


def removed_item(item_id: int, old: Located, added: dict[int, Located]) -> Finding:
    text = old.item.get("text")
    for new in added.values():
        if new.item.get("text") == text:
            return Finding(
                ERROR,
                "renumbered",
                f"item {item_id} reappears as {new.where} with the same text; existing items keep their number",
            )
    had_result = status_of(old.item) != PENDING or "comment" in old.item
    if had_result:
        return Finding(
            ERROR,
            "result-lost",
            f"item {item_id} ({old.where} in the snapshot) is gone together with its result; "
            "an obsolete item is for a human to remove",
        )
    return Finding(
        WARNING,
        "item-removed",
        f"item {item_id} ({old.where} in the snapshot) is gone; it had no result, but removal is a human's call",
    )


def validate(checklist: Path, before: Path | None = None) -> list[Finding]:
    data = load_json(checklist)
    findings = check_schema(data) + check_ids(data) + check_keys(data) + check_fragments(data)
    if before is None:
        findings += check_results_in_new(data)
    else:
        findings += check_against(load_json(before), data)
    return findings


def has_errors(findings: Iterable[Finding]) -> bool:
    return any(finding.level == ERROR for finding in findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("checklist", type=Path, help="the checklist file to check")
    parser.add_argument(
        "--before",
        type=Path,
        metavar="SNAPSHOT",
        help="copy of the same file taken right before the edit; enables the live-checklist checks",
    )
    args = parser.parse_args(argv)
    try:
        findings = validate(args.checklist, args.before)
    except Unreadable as exc:
        print(f"error: [unreadable] {exc}")
        return 2
    for finding in findings:
        print(finding)
    errors = sum(1 for finding in findings if finding.level == ERROR)
    warnings = len(findings) - errors
    print(f"{args.checklist}: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
