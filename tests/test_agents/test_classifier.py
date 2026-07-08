"""Contract tests for ClassifierAgent — interface + fallback only (logic lands in S2)."""

from flakysense.agents import ClassifierAgent, DetectorAgent
from flakysense.models import FlakinessClassification, FlakyCause, TestStatus


def test_declares_system1_contract():
    assert ClassifierAgent.system == "system1"
    assert ClassifierAgent.name == "classifier"


def test_fallback_runs_without_api_key(record_factory):
    (detection,) = DetectorAgent().run(
        [
            record_factory(run_id="run_01", status=TestStatus.PASSED),
            record_factory(run_id="run_02", status=TestStatus.FAILED),
        ]
    )

    classification = ClassifierAgent().run(detection)

    assert isinstance(classification, FlakinessClassification)
    assert classification.test_id == detection.test_id
    # v0 contract: honest UNKNOWN until S2 heuristics land.
    assert classification.cause is FlakyCause.UNKNOWN
    assert 0.0 <= classification.confidence <= 1.0
