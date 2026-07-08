"""Pydantic v2 data models shared across the FlakySense agent pipeline.

Model flow mirrors the pipeline stages (see ADR-001):

    TestRunRecord -> FlakinessDetection -> FlakinessClassification
     (parsed log)     (Detector, S1)        (Classifier, S1)
        -> Explanation / Recommendation -> FlakinessReport
           (Explainer / Recommender, S2)    (assembled by the orchestrator, S3)

All intermediate models are frozen: pipeline stages consume immutable inputs,
which keeps deterministic runs reproducible by construction.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Which execution path produced an output (see ADR-001): the deterministic
# rule-based fallback, or the LLM-backed System 2 path.
PipelinePath = Literal["system1_fallback", "system2_llm"]


class TestStatus(str, Enum):
    """Outcome of a single test execution."""

    # Tell pytest this is domain vocabulary, not a collectable test class.
    __test__ = False

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestRunRecord(BaseModel):
    """One test executed in one CI run — the pipeline's base unit."""

    # Tell pytest this is domain vocabulary, not a collectable test class.
    __test__ = False

    model_config = ConfigDict(frozen=True)

    test_id: str = Field(
        min_length=1,
        description="pytest node id, e.g. 'tests/test_api.py::test_login'",
    )
    run_id: str = Field(
        min_length=1,
        description="CI run identifier; the key for temporal correlation",
    )
    status: TestStatus
    duration_s: float = Field(ge=0)
    started_at: datetime
    execution_index: int = Field(
        ge=0, description="Position of the test within its suite run"
    )
    environment: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None

    @field_validator("started_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        # Temporal correlation compares timestamps across CI runs; a naive
        # datetime makes those comparisons silently wrong across timezones.
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("started_at must be timezone-aware")
        return value


class FlakinessDetection(BaseModel):
    """Detector output (System 1): flakiness score plus its supporting evidence.

    Embeds the full run records so downstream agents and the final report
    are self-contained — no external store to join against.
    """

    model_config = ConfigDict(frozen=True)

    test_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    is_flaky: bool
    evidence: list[TestRunRecord]
    method: str = Field(
        min_length=1, description="Detection method label, e.g. 'rule_based_v1'"
    )


class FlakyCause(str, Enum):
    """Probable root-cause category of a flaky test."""

    TIMING = "timing"
    ORDERING = "ordering"
    ENVIRONMENT = "environment"
    RESOURCE_CONTENTION = "resource_contention"
    TEST_DATA = "test_data"
    UNKNOWN = "unknown"


class FlakinessClassification(BaseModel):
    """Classifier output (System 1): probable cause with supporting signals."""

    model_config = ConfigDict(frozen=True)

    test_id: str = Field(min_length=1)
    cause: FlakyCause
    confidence: float = Field(ge=0, le=1)
    signals: list[str] = Field(
        default_factory=list,
        description="Human-readable evidence, e.g. 'duration variance 8x median'",
    )


class Explanation(BaseModel):
    """Explainer output (System 2): root-cause narrative for one flaky test."""

    model_config = ConfigDict(frozen=True)

    test_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    generated_by: PipelinePath


class Recommendation(BaseModel):
    """Recommender output (System 2): suggested action for one flaky test."""

    model_config = ConfigDict(frozen=True)

    test_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    generated_by: PipelinePath


class FlakinessReport(BaseModel):
    """Final pipeline output for a QA lead — self-contained, embeds all upstream evidence."""

    test_id: str = Field(min_length=1)
    detection: FlakinessDetection
    classification: FlakinessClassification
    explanation: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    generated_by: PipelinePath
    created_at: datetime
