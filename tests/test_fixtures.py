"""Guards the synthetic fixture deliverables in data/samples/ci_runs/.

Not business logic: these only check that the files exist, parse, and match
the scenarios documented in data/samples/README.md, so the fixtures cannot
silently drift away from their documentation.
"""

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

CI_RUNS = Path(__file__).resolve().parents[1] / "data" / "samples" / "ci_runs"


def _suites():
    for xml_path in sorted(CI_RUNS.glob("run_*/junit.xml")):
        yield xml_path.parent.name, ET.parse(xml_path).getroot()


def test_ten_runs_of_five_tests_each():
    suites = list(_suites())
    assert len(suites) == 10
    for _, root in suites:
        assert len(root.findall(".//testcase")) == 5


def test_scenario_outcome_counts_match_documentation():
    failures: Counter[str] = Counter()
    skips: Counter[str] = Counter()
    for _, root in _suites():
        for case in root.iter("testcase"):
            if case.find("failure") is not None:
                failures[case.attrib["name"]] += 1
            if case.find("skipped") is not None:
                skips[case.attrib["name"]] += 1

    assert failures == {
        "test_payment_gateway_timeout": 3,
        "test_user_profile_cache": 4,
        "test_report_export": 2,
    }
    assert skips == {"test_report_export": 1}


def test_cache_failures_correlate_with_execution_order():
    # The ordering scenario's core invariant: the cache test fails exactly
    # when it executes after the bulk import (document order = run order).
    for run_id, root in _suites():
        names = [case.attrib["name"] for case in root.iter("testcase")]
        cache_after_import = names.index("test_user_profile_cache") > names.index(
            "test_bulk_import"
        )
        (cache_case,) = [
            case
            for case in root.iter("testcase")
            if case.attrib["name"] == "test_user_profile_cache"
        ]
        cache_failed = cache_case.find("failure") is not None
        assert cache_failed == cache_after_import, run_id
