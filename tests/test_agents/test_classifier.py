"""Tests for ClassifierAgent — v1 heuristic cause scoring (ADR-003)."""

from pathlib import Path

from flakysense.agents import ClassifierAgent, DetectorAgent
from flakysense.ingest import parse_junit_dir
from flakysense.models import (
    FlakinessClassification,
    FlakinessDetection,
    FlakyCause,
    TestStatus,
)

CI_RUNS = Path(__file__).resolve().parents[2] / "data" / "samples" / "ci_runs"

P, F = TestStatus.PASSED, TestStatus.FAILED


def _detection(records) -> FlakinessDetection:
    return FlakinessDetection(
        test_id=records[0].test_id,
        score=0.6,
        is_flaky=True,
        evidence=records,
        method="rule_based_v1",
    )


def test_declares_system1_contract():
    assert ClassifierAgent.system == "system1"
    assert ClassifierAgent.name == "classifier"


def test_fallback_runs_without_api_key(record_factory):
    classification = ClassifierAgent().run(
        _detection([record_factory(run_id="run_01"), record_factory(run_id="run_02", status=F)])
    )

    assert isinstance(classification, FlakinessClassification)
    assert 0.0 <= classification.confidence <= 1.0


def test_timing_from_duration_outliers_and_keyword(record_factory):
    records = [
        record_factory(run_id=f"p{i}", status=P, duration_s=d)
        for i, d in enumerate([1.0, 1.5, 2.0, 2.5])
    ] + [
        record_factory(
            run_id=f"f{i}",
            status=F,
            duration_s=5.0,
            error_message="TimeoutError: gateway did not respond within 5.0s",
        )
        for i in range(3)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.TIMING
    assert classification.confidence == ClassifierAgent.STRENGTH_TIMING_FULL
    assert any("slower" in s for s in classification.signals)
    assert any("timeout" in s for s in classification.signals)


def test_ordering_from_disjoint_position_split(record_factory):
    records = [
        record_factory(run_id=f"p{i}", status=P, execution_index=1) for i in range(4)
    ] + [
        record_factory(run_id=f"f{i}", status=F, execution_index=3) for i in range(3)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.ORDERING
    assert classification.confidence == ClassifierAgent.STRENGTH_ORDER_SPLIT


def test_environment_from_perfect_key_split(record_factory):
    records = [
        record_factory(run_id=f"p{i}", status=P, environment={"os": "linux"})
        for i in range(4)
    ] + [
        record_factory(run_id=f"f{i}", status=F, environment={"os": "windows"})
        for i in range(2)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.ENVIRONMENT
    assert classification.confidence == ClassifierAgent.STRENGTH_ENV_SPLIT
    assert any("os=windows" in s for s in classification.signals)


def test_contention_from_keyword_only(record_factory):
    records = [
        record_factory(run_id=f"p{i}", status=P) for i in range(4)
    ] + [
        record_factory(
            run_id=f"f{i}",
            status=F,
            error_message="OSError: connection refused by message broker",
        )
        for i in range(2)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.RESOURCE_CONTENTION
    assert classification.confidence == ClassifierAgent.STRENGTH_KEYWORD_ONLY


def test_environment_beats_contention_but_keeps_its_signal(record_factory):
    """Concurrent evidence: the stronger heuristic wins, the weaker stays visible."""
    records = [
        record_factory(run_id=f"p{i}", status=P, environment={"os": "linux"})
        for i in range(4)
    ] + [
        record_factory(
            run_id=f"f{i}",
            status=F,
            environment={"os": "windows"},
            error_message="PermissionError: export file is locked by another process",
        )
        for i in range(2)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.ENVIRONMENT
    assert any("locked" in s for s in classification.signals)


def test_unknown_when_nothing_matches(record_factory):
    records = [
        record_factory(run_id=f"p{i}", status=P) for i in range(3)
    ] + [
        record_factory(run_id=f"f{i}", status=F, error_message="AssertionError: 1 != 2")
        for i in range(2)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.UNKNOWN
    assert classification.confidence == 0.0


def test_single_failure_is_dampened_below_the_floor(record_factory):
    """One slow failing run is not a diagnosis (ADR-003 dampening)."""
    records = [
        record_factory(run_id=f"p{i}", status=P, duration_s=0.1) for i in range(5)
    ] + [
        record_factory(run_id="f0", status=F, duration_s=9.0)
    ]

    classification = ClassifierAgent().run(_detection(records))

    assert classification.cause is FlakyCause.UNKNOWN
    assert any("below" in s for s in classification.signals)


def test_classifies_documented_fixture_causes():
    """Flagship integration: raw CI artifacts to named root causes, zero keys."""
    detections = DetectorAgent().run(parse_junit_dir(CI_RUNS))

    causes = {
        d.test_id: ClassifierAgent().run(d).cause for d in detections if d.is_flaky
    }

    assert causes == {
        "tests/test_payment.py::test_payment_gateway_timeout": FlakyCause.TIMING,
        "tests/test_users.py::test_user_profile_cache": FlakyCause.ORDERING,
        "tests/test_reports.py::test_report_export": FlakyCause.ENVIRONMENT,
    }
