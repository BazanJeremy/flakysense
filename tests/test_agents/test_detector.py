"""Contract tests for DetectorAgent — interface + fallback only (logic lands in S2)."""

from flakysense.agents import DetectorAgent
from flakysense.models import FlakinessDetection, TestStatus


def test_declares_system1_contract():
    assert DetectorAgent.system == "system1"
    assert DetectorAgent.name == "detector"


def test_fallback_runs_without_api_key(record_factory):
    records = [
        record_factory(run_id="run_01", status=TestStatus.PASSED),
        record_factory(run_id="run_02", status=TestStatus.FAILED),
    ]

    result = DetectorAgent().run(records)

    assert isinstance(result, list)
    (detection,) = result
    assert isinstance(detection, FlakinessDetection)
    assert 0.0 <= detection.score <= 1.0
    assert detection.is_flaky is True
    assert detection.evidence == records
