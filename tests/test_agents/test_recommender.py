"""Contract tests for RecommenderAgent — interface + fallback only (LLM path lands in S2)."""

from flakysense.agents import (
    ClassifierAgent,
    DetectorAgent,
    ExplainerAgent,
    RecommenderAgent,
)
from flakysense.models import Recommendation, TestStatus


def test_declares_system2_contract():
    assert RecommenderAgent.system == "system2"
    assert RecommenderAgent.name == "recommender"


def test_fallback_runs_without_api_key(record_factory):
    (detection,) = DetectorAgent().run(
        [
            record_factory(run_id="run_01", status=TestStatus.PASSED),
            record_factory(run_id="run_02", status=TestStatus.FAILED),
        ]
    )
    classification = ClassifierAgent().run(detection)
    explanation = ExplainerAgent().run((detection, classification))

    recommendation = RecommenderAgent().run((classification, explanation))

    assert isinstance(recommendation, Recommendation)
    assert recommendation.test_id == detection.test_id
    assert recommendation.text
    assert recommendation.generated_by == "system1_fallback"
