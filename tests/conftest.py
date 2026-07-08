"""Shared factories for the S1 contract test suites."""

from datetime import datetime, timezone

import pytest

from flakysense.models import TestRunRecord, TestStatus


@pytest.fixture(autouse=True)
def _no_llm_env(monkeypatch):
    # The suite must never touch an LLM (ADR-004): scrub the activation key
    # so System 2 agents resolve to their deterministic fallback, even on a
    # developer machine that has a real key configured.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def record_factory():
    """Build valid ``TestRunRecord`` instances with overridable defaults."""

    def make(**overrides) -> TestRunRecord:
        defaults = dict(
            test_id="tests/test_demo.py::test_example",
            run_id="run_01",
            status=TestStatus.PASSED,
            duration_s=0.1,
            started_at=datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc),
            execution_index=0,
        )
        defaults.update(overrides)
        return TestRunRecord(**defaults)

    return make
