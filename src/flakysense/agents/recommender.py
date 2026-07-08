"""Action recommender — System 2 stage (see ADR-001, ADR-004)."""

from __future__ import annotations

from flakysense.agents.base import BaseAgent
from flakysense.llm import LLMClient, client_from_env
from flakysense.models import (
    Explanation,
    FlakinessClassification,
    FlakyCause,
    Recommendation,
)

RecommenderInput = tuple[FlakinessClassification, Explanation]

_SYSTEM_PROMPT = (
    "You are a senior QA engineer recommending a corrective action for a "
    "flaky test to a QA lead. Ground the recommendation in the evidence "
    "provided; never invent tooling, code, or causes. Start from the "
    "baseline playbook action and tailor it to the specific evidence — "
    "do not contradict it without justification from the evidence. Reply "
    "with one short, actionable paragraph and no preamble."
)

# One canned action per cause — the deterministic floor the LLM path (ADR-004)
# must build on, never a branch it can skip.
_PLAYBOOK: dict[FlakyCause, str] = {
    FlakyCause.TIMING: (
        "Replace fixed sleeps with explicit waits or polling assertions, "
        "and review timeout margins against the observed duration drift."
    ),
    FlakyCause.ORDERING: (
        "Isolate shared state between tests; rerun the test alone and under "
        "randomized ordering to confirm the dependency, then remove it."
    ),
    FlakyCause.ENVIRONMENT: (
        "Diff the failing and passing environments (OS, dependency versions, "
        "CI runner) and reproduce on the failing configuration."
    ),
    FlakyCause.RESOURCE_CONTENTION: (
        "Audit shared resources (ports, files, databases); give the test "
        "isolated resources or serialize access to the contended one."
    ),
    FlakyCause.TEST_DATA: (
        "Make test data deterministic: fixed seeds, isolated fixtures, no "
        "reliance on shared mutable datasets."
    ),
    FlakyCause.UNKNOWN: (
        "Quarantine the test and keep collecting run history until a cause "
        "signal emerges."
    ),
}


class RecommenderAgent(BaseAgent[RecommenderInput, Recommendation]):
    """Suggests a concrete action for one flaky test.

    System 2 agent (ADR-004): ``run()`` attempts the LLM path when a client
    is available and degrades to the playbook fallback on any failure.
    ``generated_by`` on the output records which path actually ran.
    """

    name = "recommender"
    system = "system2"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        # None = resolve from the environment (ADR-004); inject in tests.
        self._llm_client = llm_client if llm_client is not None else client_from_env()

    def run(self, payload: RecommenderInput) -> Recommendation:
        if self._llm_client is None:
            return self.fallback(payload)
        classification, _explanation = payload
        try:
            text = self._llm_client.complete(
                _SYSTEM_PROMPT, _render_evidence(payload)
            )
            return Recommendation(
                test_id=classification.test_id,
                text=text,
                confidence=classification.confidence,
                generated_by="system2_llm",
            )
        except Exception:
            # Graceful degradation (ADR-001): the pipeline must yield a valid
            # recommendation whether or not the LLM path is healthy.
            return self.fallback(payload)

    def fallback(self, payload: RecommenderInput) -> Recommendation:
        classification, _explanation = payload
        return Recommendation(
            test_id=classification.test_id,
            text=_PLAYBOOK[classification.cause],
            confidence=classification.confidence,
            generated_by="system1_fallback",
        )


def _render_evidence(payload: RecommenderInput) -> str:
    """Render the upstream evidence as the LLM user prompt — facts only."""
    classification, explanation = payload
    lines = [
        f"Test: {classification.test_id}",
        f"Classified cause: {classification.cause.value} "
        f"(confidence {classification.confidence:.2f})",
    ]
    if classification.signals:
        lines.append("Signals:")
        lines.extend(f"- {signal}" for signal in classification.signals)
    lines.append(f"Explanation: {explanation.text}")
    lines.append(f"Baseline playbook action: {_PLAYBOOK[classification.cause]}")
    lines.append(
        "\nRecommend the most effective corrective action for this specific "
        "test, tailored to the evidence above."
    )
    return "\n".join(lines)
