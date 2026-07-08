"""Action recommender — System 2 stage (see ADR-001)."""

from __future__ import annotations

from flakysense.agents.base import BaseAgent
from flakysense.models import (
    Explanation,
    FlakinessClassification,
    FlakyCause,
    Recommendation,
)

RecommenderInput = tuple[FlakinessClassification, Explanation]

# One canned action per cause — the deterministic floor the LLM path (S2)
# must beat, never a branch it can skip.
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

    System 2 agent: the LLM path lands in S2 as a ``run()`` override. The
    fallback maps the classified cause to a canned playbook action.
    """

    name = "recommender"
    system = "system2"

    def fallback(self, payload: RecommenderInput) -> Recommendation:
        classification, _explanation = payload
        return Recommendation(
            test_id=classification.test_id,
            text=_PLAYBOOK[classification.cause],
            confidence=classification.confidence,
            generated_by="system1_fallback",
        )
