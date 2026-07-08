"""Flakiness explainer — System 2 stage (see ADR-001)."""

from __future__ import annotations

from flakysense.agents.base import BaseAgent
from flakysense.models import (
    Explanation,
    FlakinessClassification,
    FlakinessDetection,
    TestStatus,
)

ExplainerInput = tuple[FlakinessDetection, FlakinessClassification]


class ExplainerAgent(BaseAgent[ExplainerInput, Explanation]):
    """Produces a root-cause narrative for one flaky test.

    System 2 agent: the LLM path lands in S2 as a ``run()`` override. The
    fallback renders a deterministic template from the System 1 evidence,
    so the pipeline yields a valid (if terse) explanation with zero keys.
    """

    name = "explainer"
    system = "system2"

    def fallback(self, payload: ExplainerInput) -> Explanation:
        detection, classification = payload
        failed = sum(
            1
            for r in detection.evidence
            if r.status in (TestStatus.FAILED, TestStatus.ERROR)
        )
        text = (
            f"Test '{detection.test_id}' failed {failed} of "
            f"{len(detection.evidence)} recorded runs "
            f"(flakiness score {detection.score:.2f}). "
            f"Probable cause: {classification.cause.value} "
            f"(confidence {classification.confidence:.2f})."
        )
        return Explanation(
            test_id=detection.test_id,
            text=text,
            confidence=classification.confidence,
            generated_by="system1_fallback",
        )
