"""Flakiness explainer — System 2 stage (see ADR-001, ADR-004)."""

from __future__ import annotations

from flakysense.agents.base import BaseAgent
from flakysense.llm import LLMClient, client_from_env
from flakysense.models import (
    Explanation,
    FlakinessClassification,
    FlakinessDetection,
    TestStatus,
)

ExplainerInput = tuple[FlakinessDetection, FlakinessClassification]

_SYSTEM_PROMPT = (
    "You are a senior QA engineer explaining a flaky test to a QA lead. "
    "Ground every statement in the evidence provided; never invent runs, "
    "numbers, or causes. Reply with one short paragraph and no preamble."
)


class ExplainerAgent(BaseAgent[ExplainerInput, Explanation]):
    """Produces a root-cause narrative for one flaky test.

    System 2 agent (ADR-004): ``run()`` attempts the LLM path when a client
    is available and degrades to the deterministic fallback on any failure.
    ``generated_by`` on the output records which path actually ran.
    """

    name = "explainer"
    system = "system2"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        # None = resolve from the environment (ADR-004); inject in tests.
        self._llm_client = llm_client if llm_client is not None else client_from_env()

    def run(self, payload: ExplainerInput) -> Explanation:
        if self._llm_client is None:
            return self.fallback(payload)
        detection, classification = payload
        try:
            text = self._llm_client.complete(
                _SYSTEM_PROMPT, _render_evidence(payload)
            )
            return Explanation(
                test_id=detection.test_id,
                text=text,
                confidence=classification.confidence,
                generated_by="system2_llm",
            )
        except Exception:
            # Graceful degradation (ADR-001): the pipeline must yield a valid
            # explanation whether or not the LLM path is healthy.
            return self.fallback(payload)

    def fallback(self, payload: ExplainerInput) -> Explanation:
        detection, classification = payload
        text = (
            f"Test '{detection.test_id}' failed {_failed_count(detection)} of "
            f"{len(detection.evidence)} recorded runs "
            f"(flakiness score {detection.score:.2f}). "
            f"Probable cause: {classification.cause.value} "
            f"(confidence {classification.confidence:.2f})."
        )
        if classification.signals:
            text += " Evidence: " + "; ".join(classification.signals) + "."
        return Explanation(
            test_id=detection.test_id,
            text=text,
            confidence=classification.confidence,
            generated_by="system1_fallback",
        )


def _failed_count(detection: FlakinessDetection) -> int:
    return sum(
        1
        for r in detection.evidence
        if r.status in (TestStatus.FAILED, TestStatus.ERROR)
    )


def _render_evidence(payload: ExplainerInput) -> str:
    """Render the System 1 evidence as the LLM user prompt — facts only."""
    detection, classification = payload
    lines = [
        f"Test: {detection.test_id}",
        f"Flakiness score: {detection.score:.2f} (method: {detection.method})",
        f"Runs recorded: {len(detection.evidence)}, "
        f"failed: {_failed_count(detection)}",
        f"Classified cause: {classification.cause.value} "
        f"(confidence {classification.confidence:.2f})",
    ]
    if classification.signals:
        lines.append("Signals:")
        lines.extend(f"- {signal}" for signal in classification.signals)
    last_error = next(
        (r.error_message for r in reversed(detection.evidence) if r.error_message),
        None,
    )
    if last_error:
        lines.append(f"Most recent failure message: {last_error}")
    lines.append(
        "\nExplain to the QA lead why this test is likely flaky and what the "
        "evidence shows."
    )
    return "\n".join(lines)
