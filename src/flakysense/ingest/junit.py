"""JUnit XML ingestion — parses pytest-style CI reports into run records.

Timezone policy: JUnit ``timestamp`` attributes are naive local time (that is
what pytest emits). Bare timestamps are interpreted as UTC so the resulting
records satisfy the timezone-aware constraint of ``TestRunRecord`` — CI
runners are UTC in the overwhelmingly common case, and a consistent (even if
occasionally wrong) offset preserves the *relative* ordering temporal
correlation depends on.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from flakysense.models import TestRunRecord, TestStatus

# First matching child element decides the outcome; no match means passed.
_STATUS_CHILDREN = (
    ("failure", TestStatus.FAILED),
    ("error", TestStatus.ERROR),
    ("skipped", TestStatus.SKIPPED),
)


class JUnitParseError(ValueError):
    """Raised when a JUnit XML file cannot be turned into run records."""


def parse_junit_file(path: str | Path, run_id: str | None = None) -> list[TestRunRecord]:
    """Parse one pytest-style JUnit XML report into run records.

    ``run_id`` resolution order: explicit argument, then a ``run_id``
    ``<property>`` in the report, then the report's parent directory name.
    """
    path = Path(path)
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise JUnitParseError(f"{path}: cannot parse ({exc})") from exc

    records: list[TestRunRecord] = []
    for suite in root.iter("testsuite"):
        started_at = _suite_timestamp(suite, path)
        properties = {
            prop.get("name"): prop.get("value")
            for prop in suite.iter("property")
            if prop.get("name") is not None and prop.get("value") is not None
        }
        # run_id is report metadata, not environment — always strip it.
        property_run_id = properties.pop("run_id", None)
        resolved_run_id = run_id or property_run_id or path.parent.name

        for index, case in enumerate(suite.iter("testcase")):
            status, error_message = _case_outcome(case)
            records.append(
                TestRunRecord(
                    test_id=_case_test_id(case, path),
                    run_id=resolved_run_id,
                    status=status,
                    duration_s=float(case.get("time", 0.0)),
                    started_at=started_at,
                    execution_index=index,
                    environment=properties,
                    error_message=error_message,
                )
            )

    if not records:
        raise JUnitParseError(f"{path}: no <testcase> elements found")
    return records


def parse_junit_dir(path: str | Path) -> list[TestRunRecord]:
    """Parse every ``junit.xml`` found under ``path`` (recursively).

    Files are visited in sorted order so the combined record list is
    deterministic regardless of filesystem enumeration order.
    """
    path = Path(path)
    xml_files = sorted(path.rglob("junit.xml"))
    if not xml_files:
        raise JUnitParseError(f"{path}: no junit.xml files found")

    records: list[TestRunRecord] = []
    for xml_file in xml_files:
        records.extend(parse_junit_file(xml_file))
    return records


def _suite_timestamp(suite: ET.Element, path: Path) -> datetime:
    raw = suite.get("timestamp")
    if raw is None:
        raise JUnitParseError(f"{path}: <testsuite> missing timestamp attribute")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise JUnitParseError(f"{path}: bad testsuite timestamp {raw!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _case_outcome(case: ET.Element) -> tuple[TestStatus, str | None]:
    for tag, status in _STATUS_CHILDREN:
        node = case.find(tag)
        if node is not None:
            return status, node.get("message")
    return TestStatus.PASSED, None


def _case_test_id(case: ET.Element, path: Path) -> str:
    name = case.get("name")
    if not name:
        raise JUnitParseError(f"{path}: <testcase> missing name attribute")
    # pytest-style nodeid when the file is known; classname otherwise.
    prefix = case.get("file") or case.get("classname") or "unknown"
    return f"{prefix}::{name}"
