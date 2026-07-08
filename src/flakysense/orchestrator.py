"""Pipeline orchestrator — chains the four agents into flakiness reports.

Owns the escalation decision deferred by ADR-001 and fixed by ADR-005: the
orchestrator, not the agents, decides whether a test's evidence warrants
attempting the System 2 LLM path.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flakysense.agents import (
    ClassifierAgent,
    DetectorAgent,
    ExplainerAgent,
    RecommenderAgent,
)
from flakysense.models import FlakinessReport, PipelinePath, TestRunRecord


class Orchestrator:
    """Runs detect → classify → explain → recommend over a run history.

    Produces one ``FlakinessReport`` per detected flaky test; non-flaky tests
    yield no report. System 2 stages are invoked through ``run()`` (LLM
    attempted when available) only at or above ``ESCALATION_THRESHOLD``;
    below it they are pinned to their deterministic ``fallback()`` — no LLM
    attempt, even with an API key configured (ADR-005).
    """

    # ADR-005 — distinct from the 0.3 detection threshold: "flaky enough to
    # report" vs "evidence strong enough to spend LLM reasoning on".
    ESCALATION_THRESHOLD = 0.5

    def __init__(
        self,
        detector: DetectorAgent | None = None,
        classifier: ClassifierAgent | None = None,
        explainer: ExplainerAgent | None = None,
        recommender: RecommenderAgent | None = None,
        escalation_threshold: float | None = None,
    ) -> None:
        # None = build the default agent; inject in tests.
        self._detector = detector if detector is not None else DetectorAgent()
        self._classifier = classifier if classifier is not None else ClassifierAgent()
        self._explainer = explainer if explainer is not None else ExplainerAgent()
        self._recommender = (
            recommender if recommender is not None else RecommenderAgent()
        )
        # Out-of-range values are semantics, not errors (ADR-006): > 1
        # disables escalation entirely, <= 0 escalates every flaky test.
        self._escalation_threshold = (
            escalation_threshold
            if escalation_threshold is not None
            else self.ESCALATION_THRESHOLD
        )

    def run(self, records: list[TestRunRecord]) -> list[FlakinessReport]:
        """Turn raw run records into one report per flaky test.

        Report order follows the detector's output (sorted by ``test_id``),
        so identical histories always produce identical report sets.
        """
        reports: list[FlakinessReport] = []
        for detection in self._detector.run(records):
            if not detection.is_flaky:
                continue

            classification = self._classifier.run(detection)
            escalate = detection.score >= self._escalation_threshold

            explainer_input = (detection, classification)
            explanation = (
                self._explainer.run(explainer_input)
                if escalate
                else self._explainer.fallback(explainer_input)
            )
            recommender_input = (classification, explanation)
            recommendation = (
                self._recommender.run(recommender_input)
                if escalate
                else self._recommender.fallback(recommender_input)
            )

            # Conservative aggregates (ADR-005): "system2_llm" is a floor
            # guarantee that every narrative field was LLM-produced; any
            # fallback anywhere demotes the whole report.
            generated_by: PipelinePath = (
                "system2_llm"
                if explanation.generated_by
                == recommendation.generated_by
                == "system2_llm"
                else "system1_fallback"
            )
            reports.append(
                FlakinessReport(
                    test_id=detection.test_id,
                    detection=detection,
                    classification=classification,
                    explanation=explanation.text,
                    recommendation=recommendation.text,
                    confidence=min(
                        classification.confidence,
                        explanation.confidence,
                        recommendation.confidence,
                    ),
                    generated_by=generated_by,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return reports
