"""Validation contract of the shared Pydantic models — no business logic."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from flakysense.models import FlakinessDetection


def test_naive_started_at_is_rejected(record_factory):
    with pytest.raises(ValidationError, match="timezone-aware"):
        record_factory(started_at=datetime(2026, 7, 1, 8, 0))


def test_flakiness_score_is_bounded():
    with pytest.raises(ValidationError):
        FlakinessDetection(
            test_id="tests/test_demo.py::test_example",
            score=1.5,
            is_flaky=True,
            evidence=[],
            method="rule_based_v0",
        )


def test_run_records_are_immutable(record_factory):
    record = record_factory()
    with pytest.raises(ValidationError):
        record.duration_s = 2.0
