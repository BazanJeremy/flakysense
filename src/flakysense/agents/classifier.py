"""Flaky-cause classifier — System 1 stage (see ADR-001)."""

from __future__ import annotations

from flakysense.agents.base import BaseAgent
from flakysense.models import FlakinessClassification, FlakinessDetection, FlakyCause


class ClassifierAgent(BaseAgent[FlakinessDetection, FlakinessClassification]):
    """Assigns a probable root-cause category to a detected flaky test.

    v0 fallback: always UNKNOWN with zero confidence — an honest placeholder
    until the S2 heuristics (duration variance, ordering correlation,
    environment diffing) land.
    """

    name = "classifier"
    system = "system1"

    def fallback(self, payload: FlakinessDetection) -> FlakinessClassification:
        return FlakinessClassification(
            test_id=payload.test_id,
            cause=FlakyCause.UNKNOWN,
            confidence=0.0,
            signals=["rule_based_v0: no heuristics implemented yet (planned for S2)"],
        )
