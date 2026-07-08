"""Flakiness detector — System 1 stage (see ADR-001)."""

from __future__ import annotations

from collections import defaultdict
from statistics import pstdev

from flakysense.agents.base import BaseAgent
from flakysense.models import FlakinessDetection, TestRunRecord, TestStatus


class DetectorAgent(BaseAgent[list[TestRunRecord], list[FlakinessDetection]]):
    """Scores each test's flakiness from its run history.

    v1 fallback (see ADR-002): weighted blend of three deterministic
    signals — intermittency, flip rate, duration instability. Intermittency
    peaks at a 50% failure rate and vanishes at 100%: a test that always
    fails is broken, not flaky.
    """

    name = "detector"
    system = "system1"

    METHOD = "rule_based_v1"

    # ADR-002 constants — hand-tuned against the data/samples scenarios.
    WEIGHT_INTERMITTENCY = 0.4
    WEIGHT_FLIP_RATE = 0.4
    WEIGHT_DURATION = 0.2
    MIN_RUNS = 4
    DETECTION_THRESHOLD = 0.3

    def fallback(self, payload: list[TestRunRecord]) -> list[FlakinessDetection]:
        by_test: dict[str, list[TestRunRecord]] = defaultdict(list)
        for record in payload:
            by_test[record.test_id].append(record)

        detections: list[FlakinessDetection] = []
        # Sorted by test_id so output order never depends on input order.
        for test_id, records in sorted(by_test.items()):
            score = self._score(records)
            detections.append(
                FlakinessDetection(
                    test_id=test_id,
                    score=score,
                    is_flaky=score >= self.DETECTION_THRESHOLD,
                    evidence=records,
                    method=self.METHOD,
                )
            )
        return detections

    def _score(self, records: list[TestRunRecord]) -> float:
        terminal = sorted(
            (r for r in records if r.status is not TestStatus.SKIPPED),
            key=lambda r: (r.started_at, r.run_id),
        )
        if not terminal:
            return 0.0

        failed = [
            r.status in (TestStatus.FAILED, TestStatus.ERROR) for r in terminal
        ]
        failure_ratio = sum(failed) / len(failed)
        intermittency = 4.0 * failure_ratio * (1.0 - failure_ratio)

        flip_rate = (
            sum(a != b for a, b in zip(failed, failed[1:])) / (len(failed) - 1)
            if len(failed) > 1
            else 0.0
        )

        durations = [r.duration_s for r in terminal]
        mean_duration = sum(durations) / len(durations)
        duration_instability = (
            min(1.0, pstdev(durations) / mean_duration) if mean_duration > 0 else 0.0
        )

        raw = (
            self.WEIGHT_INTERMITTENCY * intermittency
            + self.WEIGHT_FLIP_RATE * flip_rate
            + self.WEIGHT_DURATION * duration_instability
        )
        # Thin histories must not produce confident scores (ADR-002).
        return raw * min(1.0, len(terminal) / self.MIN_RUNS)
