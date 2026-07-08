"""Flakiness detector — System 1 stage (see ADR-001)."""

from __future__ import annotations

from collections import defaultdict

from flakysense.agents.base import BaseAgent
from flakysense.models import FlakinessDetection, TestRunRecord, TestStatus


class DetectorAgent(BaseAgent[list[TestRunRecord], list[FlakinessDetection]]):
    """Scores each test's flakiness from its run history.

    v0 fallback: score is the failure ratio over terminal (non-skipped)
    runs; a test is flaky when its history mixes passes and failures.
    Refined in S2 with duration drift and ordering correlation.
    """

    name = "detector"
    system = "system1"

    METHOD = "rule_based_v0"

    def fallback(self, payload: list[TestRunRecord]) -> list[FlakinessDetection]:
        by_test: dict[str, list[TestRunRecord]] = defaultdict(list)
        for record in payload:
            by_test[record.test_id].append(record)

        detections: list[FlakinessDetection] = []
        # Sorted by test_id so output order never depends on input order.
        for test_id, records in sorted(by_test.items()):
            terminal = [r for r in records if r.status is not TestStatus.SKIPPED]
            failed = [
                r
                for r in terminal
                if r.status in (TestStatus.FAILED, TestStatus.ERROR)
            ]
            passed = [r for r in terminal if r.status is TestStatus.PASSED]
            detections.append(
                FlakinessDetection(
                    test_id=test_id,
                    score=len(failed) / len(terminal) if terminal else 0.0,
                    is_flaky=bool(failed) and bool(passed),
                    evidence=records,
                    method=self.METHOD,
                )
            )
        return detections
