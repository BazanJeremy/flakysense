"""Flaky-cause classifier — System 1 stage (see ADR-001)."""

from __future__ import annotations

from flakysense.agents.base import BaseAgent
from flakysense.models import (
    FlakinessClassification,
    FlakinessDetection,
    FlakyCause,
    TestRunRecord,
    TestStatus,
)

_TIMING_KEYWORDS = ("timeout", "timed out", "deadline")
_CONTENTION_KEYWORDS = (
    "locked",
    "deadlock",
    "connection refused",
    "address already in use",
    "resource busy",
)


def _first_keyword_hit(
    records: list[TestRunRecord], keywords: tuple[str, ...]
) -> str | None:
    for record in records:
        message = (record.error_message or "").lower()
        for keyword in keywords:
            if keyword in message:
                return keyword
    return None


class ClassifierAgent(BaseAgent[FlakinessDetection, FlakinessClassification]):
    """Assigns a probable root-cause category to a detected flaky test.

    v1 fallback (see ADR-003): one deterministic heuristic per cause scores
    the detection evidence independently; the strongest wins, dampened by
    evidence volume, and anything below the confidence floor is UNKNOWN —
    the classifier never guesses. ``signals`` carries every heuristic that
    fired, not just the winner's: it is the Explainer's evidence feed.
    """

    name = "classifier"
    system = "system1"

    METHOD = "rule_based_v1"

    # ADR-003 constants.
    STRENGTH_ENV_SPLIT = 0.9
    STRENGTH_TIMING_FULL = 0.85
    STRENGTH_ORDER_SPLIT = 0.8
    STRENGTH_DURATION_OUTLIER = 0.7
    STRENGTH_KEYWORD_ONLY = 0.5
    CONFIDENCE_FLOOR = 0.4
    MIN_FAILURES = 2

    def fallback(self, payload: FlakinessDetection) -> FlakinessClassification:
        failed = [
            r
            for r in payload.evidence
            if r.status in (TestStatus.FAILED, TestStatus.ERROR)
        ]
        passed = [r for r in payload.evidence if r.status is TestStatus.PASSED]

        # Fixed evaluation order doubles as the deterministic tie-breaker.
        scored: list[tuple[float, FlakyCause, list[str]]] = []
        signals: list[str] = []
        for cause, (strength, cause_signals) in (
            (FlakyCause.TIMING, self._timing(failed, passed)),
            (FlakyCause.ORDERING, self._ordering(failed, passed)),
            (FlakyCause.ENVIRONMENT, self._environment(failed, passed)),
            (FlakyCause.RESOURCE_CONTENTION, self._contention(failed)),
        ):
            if strength > 0.0:
                scored.append((strength, cause, cause_signals))
                signals.extend(cause_signals)

        if not scored:
            return FlakinessClassification(
                test_id=payload.test_id,
                cause=FlakyCause.UNKNOWN,
                confidence=0.0,
                signals=[f"{self.METHOD}: no cause heuristic matched"],
            )

        best_strength, best_cause, _ = max(scored, key=lambda item: item[0])
        # A single failing run is never enough for a diagnosis (ADR-003).
        confidence = best_strength * min(1.0, len(failed) / self.MIN_FAILURES)

        if confidence < self.CONFIDENCE_FLOOR:
            signals.append(
                f"{self.METHOD}: strongest evidence {confidence:.2f} below "
                f"confidence floor {self.CONFIDENCE_FLOOR}"
            )
            return FlakinessClassification(
                test_id=payload.test_id,
                cause=FlakyCause.UNKNOWN,
                confidence=0.0,
                signals=signals,
            )

        return FlakinessClassification(
            test_id=payload.test_id,
            cause=best_cause,
            confidence=confidence,
            signals=signals,
        )

    def _timing(
        self, failed: list[TestRunRecord], passed: list[TestRunRecord]
    ) -> tuple[float, list[str]]:
        if not failed:
            return 0.0, []
        strength = 0.0
        signals: list[str] = []

        if passed:
            slowest_pass = max(r.duration_s for r in passed)
            fastest_fail = min(r.duration_s for r in failed)
            if slowest_pass > 0 and fastest_fail > slowest_pass:
                strength = self.STRENGTH_DURATION_OUTLIER
                signals.append(
                    f"every failing run ({fastest_fail:.2f}s+) is slower than "
                    f"the slowest passing run ({slowest_pass:.2f}s)"
                )

        keyword = _first_keyword_hit(failed, _TIMING_KEYWORDS)
        if keyword:
            signals.append(f"timing keyword {keyword!r} in failure message")
            strength = (
                self.STRENGTH_TIMING_FULL if strength else self.STRENGTH_KEYWORD_ONLY
            )
        return strength, signals

    def _ordering(
        self, failed: list[TestRunRecord], passed: list[TestRunRecord]
    ) -> tuple[float, list[str]]:
        if len(failed) < self.MIN_FAILURES or len(passed) < 2:
            return 0.0, []
        failed_positions = {r.execution_index for r in failed}
        passed_positions = {r.execution_index for r in passed}
        if failed_positions.isdisjoint(passed_positions):
            return self.STRENGTH_ORDER_SPLIT, [
                f"failures only at suite position(s) {sorted(failed_positions)}, "
                f"passes only at {sorted(passed_positions)}"
            ]
        return 0.0, []

    def _environment(
        self, failed: list[TestRunRecord], passed: list[TestRunRecord]
    ) -> tuple[float, list[str]]:
        if len(failed) < self.MIN_FAILURES or not passed:
            return 0.0, []
        signals: list[str] = []
        for key in sorted(set.intersection(*(set(r.environment) for r in failed))):
            failing_values = {r.environment[key] for r in failed}
            if len(failing_values) != 1:
                continue
            (value,) = failing_values
            if all(r.environment.get(key) != value for r in passed):
                signals.append(
                    f"all failures on {key}={value}, no passing run on it"
                )
        if signals:
            return self.STRENGTH_ENV_SPLIT, signals
        return 0.0, []

    def _contention(self, failed: list[TestRunRecord]) -> tuple[float, list[str]]:
        keyword = _first_keyword_hit(failed, _CONTENTION_KEYWORDS)
        if keyword:
            return self.STRENGTH_KEYWORD_ONLY, [
                f"contention keyword {keyword!r} in failure message"
            ]
        return 0.0, []
