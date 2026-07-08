"""Tests for the JUnit XML ingestion layer."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest

from flakysense.ingest import JUnitParseError, parse_junit_dir, parse_junit_file
from flakysense.models import TestStatus

CI_RUNS = Path(__file__).resolve().parents[1] / "data" / "samples" / "ci_runs"


def test_parses_all_fixture_runs():
    records = parse_junit_dir(CI_RUNS)

    assert len(records) == 50  # 10 runs x 5 tests
    run_ids = {r.run_id for r in records}
    assert run_ids == {f"run_{i:02d}" for i in range(1, 11)}


def test_status_counts_match_documented_scenarios():
    statuses = Counter(r.status for r in parse_junit_dir(CI_RUNS))

    assert statuses == {
        TestStatus.PASSED: 40,
        TestStatus.FAILED: 9,  # 3 timing + 4 ordering + 2 environment
        TestStatus.SKIPPED: 1,
    }


def test_maps_metadata_onto_records():
    records = parse_junit_file(CI_RUNS / "run_07" / "junit.xml")

    assert all(
        r.started_at == datetime(2026, 7, 2, 8, 14, 39, tzinfo=timezone.utc)
        for r in records
    )
    by_name = {r.test_id: r for r in records}
    cache = by_name["tests/test_users.py::test_user_profile_cache"]
    bulk = by_name["tests/test_data_import.py::test_bulk_import"]
    assert cache.execution_index > bulk.execution_index  # order B preserved
    assert cache.status is TestStatus.FAILED
    assert "stale cached entry" in cache.error_message
    assert cache.environment["os"] == "linux"
    assert "run_id" not in cache.environment  # metadata, not environment


def test_explicit_run_id_overrides_report_property():
    records = parse_junit_file(CI_RUNS / "run_01" / "junit.xml", run_id="custom")
    assert {r.run_id for r in records} == {"custom"}


def test_rejects_malformed_xml(tmp_path):
    bad = tmp_path / "junit.xml"
    bad.write_text("<testsuites><unclosed", encoding="utf-8")

    with pytest.raises(JUnitParseError, match="cannot parse"):
        parse_junit_file(bad)


def test_rejects_report_without_testcases(tmp_path):
    empty = tmp_path / "junit.xml"
    empty.write_text(
        '<testsuites><testsuite name="pytest" timestamp="2026-07-01T00:00:00"/>'
        "</testsuites>",
        encoding="utf-8",
    )

    with pytest.raises(JUnitParseError, match="no <testcase>"):
        parse_junit_file(empty)


def test_rejects_directory_without_reports(tmp_path):
    with pytest.raises(JUnitParseError, match="no junit.xml"):
        parse_junit_dir(tmp_path)
