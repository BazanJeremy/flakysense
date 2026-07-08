"""Tests for RecommenderAgent — System 2 dual-path behavior (ADR-004)."""

from flakysense.agents import (
    ClassifierAgent,
    DetectorAgent,
    ExplainerAgent,
    RecommenderAgent,
)
from flakysense.models import Recommendation, TestStatus


class FakeLLMClient:
    """Injected stand-in for the LLM path — records calls, never networks."""

    def __init__(self, reply="Tailored action from the fake LLM.", error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.error is not None:
            raise self.error
        return self.reply


def _upstream_outputs(record_factory):
    (detection,) = DetectorAgent().run(
        [
            record_factory(run_id="run_01", status=TestStatus.PASSED),
            record_factory(
                run_id="run_02",
                status=TestStatus.FAILED,
                error_message="TimeoutError: gateway did not respond within 5.0s",
            ),
        ]
    )
    classification = ClassifierAgent().run(detection)
    explanation = ExplainerAgent().run((detection, classification))
    return classification, explanation


def test_declares_system2_contract():
    assert RecommenderAgent.system == "system2"
    assert RecommenderAgent.name == "recommender"


def test_fallback_runs_without_api_key(record_factory):
    classification, explanation = _upstream_outputs(record_factory)

    recommendation = RecommenderAgent().run((classification, explanation))

    assert isinstance(recommendation, Recommendation)
    assert recommendation.test_id == classification.test_id
    assert recommendation.text
    assert recommendation.generated_by == "system1_fallback"


def test_llm_path_produces_system2_recommendation(record_factory):
    classification, explanation = _upstream_outputs(record_factory)
    fake = FakeLLMClient(reply="Raise the gateway timeout margin and poll.")

    recommendation = RecommenderAgent(llm_client=fake).run(
        (classification, explanation)
    )

    assert recommendation.generated_by == "system2_llm"
    assert recommendation.text == "Raise the gateway timeout margin and poll."


def test_llm_prompt_is_grounded_in_upstream_evidence(record_factory):
    classification, explanation = _upstream_outputs(record_factory)
    fake = FakeLLMClient()

    RecommenderAgent(llm_client=fake).run((classification, explanation))

    (system, user) = fake.calls[0]
    assert classification.test_id in user
    assert classification.cause.value in user
    assert explanation.text in user  # upstream narrative reaches the prompt
    assert "Baseline playbook action:" in user  # the deterministic floor too
    assert "never invent" in system


def test_llm_failure_degrades_to_fallback(record_factory):
    classification, explanation = _upstream_outputs(record_factory)
    fake = FakeLLMClient(error=ConnectionError("network down"))

    recommendation = RecommenderAgent(llm_client=fake).run(
        (classification, explanation)
    )

    assert recommendation.generated_by == "system1_fallback"
    assert recommendation.text  # degraded, but still a valid recommendation
