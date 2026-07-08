"""Tests for ExplainerAgent — System 2 dual-path behavior (ADR-004)."""

from flakysense.agents import ClassifierAgent, DetectorAgent, ExplainerAgent
from flakysense.models import Explanation, TestStatus


class FakeLLMClient:
    """Injected stand-in for the LLM path — records calls, never networks."""

    def __init__(self, reply="Grounded explanation from the fake LLM.", error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.error is not None:
            raise self.error
        return self.reply


def _system1_outputs(record_factory):
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
    return detection, ClassifierAgent().run(detection)


def test_declares_system2_contract():
    assert ExplainerAgent.system == "system2"
    assert ExplainerAgent.name == "explainer"


def test_fallback_runs_without_api_key(record_factory):
    detection, classification = _system1_outputs(record_factory)

    explanation = ExplainerAgent().run((detection, classification))

    assert isinstance(explanation, Explanation)
    assert explanation.test_id == detection.test_id
    assert explanation.text
    assert explanation.generated_by == "system1_fallback"


def test_fallback_surfaces_classifier_signals(record_factory):
    detection, classification = _system1_outputs(record_factory)

    explanation = ExplainerAgent().run((detection, classification))

    assert classification.signals  # v1 classifier always leaves a trace
    assert any(signal in explanation.text for signal in classification.signals)


def test_llm_path_produces_system2_explanation(record_factory):
    detection, classification = _system1_outputs(record_factory)
    fake = FakeLLMClient(reply="The timeout drifts upward before each failure.")

    explanation = ExplainerAgent(llm_client=fake).run((detection, classification))

    assert explanation.generated_by == "system2_llm"
    assert explanation.text == "The timeout drifts upward before each failure."


def test_llm_prompt_is_grounded_in_system1_evidence(record_factory):
    detection, classification = _system1_outputs(record_factory)
    fake = FakeLLMClient()

    ExplainerAgent(llm_client=fake).run((detection, classification))

    (system, user) = fake.calls[0]
    assert detection.test_id in user
    assert classification.cause.value in user
    assert "TimeoutError" in user  # last failure message reaches the prompt
    assert "never invent" in system


def test_llm_failure_degrades_to_fallback(record_factory):
    detection, classification = _system1_outputs(record_factory)
    fake = FakeLLMClient(error=ConnectionError("network down"))

    explanation = ExplainerAgent(llm_client=fake).run((detection, classification))

    assert explanation.generated_by == "system1_fallback"
    assert explanation.text  # degraded, but still a valid explanation
