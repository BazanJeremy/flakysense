"""Tests for DetectorAgent — v1 statistical scoring (ADR-002)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from flakysense.agents import DetectorAgent
from flakysense.ingest import parse_junit_dir
from flakysense.models import FlakinessDetection, TestStatus

CI_RUNS = Path(__file__).resolve().parents[2] / "data" / "samples" / "ci_runs"

P, F, S = TestStatus.PASSED, TestStatus.FAILED, TestStatus.SKIPPED


def _history(record_factory, statuses, duration_s=0.1):
    """Build a run history with strictly increasing timestamps."""
    start = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
    return [
        record_factory(
            run_id=f"run_{i:02d}",
            status=status,
            duration_s=duration_s,
            started_at=start + timedelta(hours=6 * i),
        )
        for i, status in enumerate(statuses, start=1)
    ]


def test_declares_system1_contract():
    assert DetectorAgent.system == "system1"
    assert DetectorAgent.name == "detector"


def test_fallback_runs_without_api_key(record_factory):
    result = DetectorAgent().run(_history(record_factory, [P, F]))

    assert isinstance(result, list)
    (detection,) = result
    assert isinstance(detection, FlakinessDetection)
    assert 0.0 <= detection.score <= 1.0
    assert detection.method == "rule_based_v1"


def test_alternating_history_scores_high(record_factory):
    (detection,) = DetectorAgent().run(
        _history(record_factory, [P, F, P, F, P, F, P, F])
    )

    assert detection.is_flaky is True
    assert detection.score > 0.5


def test_always_failing_test_is_broken_not_flaky(record_factory):
    """The v1 semantic core: a 100% failure rate means a bug, not flakiness."""
    (detection,) = DetectorAgent().run(_history(record_factory, [F] * 8))

    assert detection.is_flaky is False
    assert detection.score < DetectorAgent.DETECTION_THRESHOLD


def test_stable_test_scores_near_zero(record_factory):
    (detection,) = DetectorAgent().run(_history(record_factory, [P] * 8))

    assert detection.is_flaky is False
    assert detection.score < 0.05


def test_duration_variance_alone_stays_below_threshold(record_factory):
    records = [
        record_factory(
            run_id=f"run_{i:02d}",
            status=P,
            duration_s=duration,
            started_at=datetime(2026, 7, 1, 8 + i, 0, tzinfo=timezone.utc),
        )
        for i, duration in enumerate([0.1, 3.0, 0.2, 5.0, 0.1, 4.0])
    ]

    (detection,) = DetectorAgent().run(records)

    assert detection.is_flaky is False


def test_thin_history_is_dampened(record_factory):
    (short,) = DetectorAgent().run(_history(record_factory, [P, F]))
    (long,) = DetectorAgent().run(_history(record_factory, [P, F, P, F, P, F, P, F]))

    assert short.score < long.score


def test_skipped_only_history_scores_zero(record_factory):
    (detection,) = DetectorAgent().run(_history(record_factory, [S, S, S]))

    assert detection.score == 0.0
    assert detection.is_flaky is False


def test_flags_exactly_the_documented_flaky_fixtures():
    detections = DetectorAgent().run(parse_junit_dir(CI_RUNS))

    assert len(detections) == 5
    flagged = {d.test_id for d in detections if d.is_flaky}
    assert flagged == {
        "tests/test_payment.py::test_payment_gateway_timeout",
        "tests/test_users.py::test_user_profile_cache",
        "tests/test_reports.py::test_report_export",
    }
