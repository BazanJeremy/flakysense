"""Contract tests for ExplainerAgent — interface + fallback only (LLM path lands in S2)."""

from flakysense.agents import ClassifierAgent, DetectorAgent, ExplainerAgent
from flakysense.models import Explanation, TestStatus


def test_declares_system2_contract():
    assert ExplainerAgent.system == "system2"
    assert ExplainerAgent.name == "explainer"


def test_fallback_runs_without_api_key(record_factory):
    (detection,) = DetectorAgent().run(
        [
            record_factory(run_id="run_01", status=TestStatus.PASSED),
            record_factory(run_id="run_02", status=TestStatus.FAILED),
        ]
    )
    classification = ClassifierAgent().run(detection)

    explanation = ExplainerAgent().run((detection, classification))

    assert isinstance(explanation, Explanation)
    assert explanation.test_id == detection.test_id
    assert explanation.text
    assert explanation.generated_by == "system1_fallback"
