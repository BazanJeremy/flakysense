"""Tests for the Orchestrator — pipeline chaining and ADR-005 escalation."""

from pathlib import Path

from flakysense.agents import DetectorAgent, ExplainerAgent, RecommenderAgent
from flakysense.ingest.junit import parse_junit_dir
from flakysense.models import FlakinessReport, TestStatus
from flakysense.orchestrator import Orchestrator

CI_RUNS = Path(__file__).resolve().parents[1] / "data" / "samples" / "ci_runs"

# Detector v1 scores on the fixture scenarios (see ADR-005): the borderline
# test sits below the 0.5 escalation threshold, the other two above it.
BORDERLINE_ID = "tests/test_reports.py::test_report_export"  # score 0.497
ESCALATED_IDS = {
    "tests/test_payment.py::test_payment_gateway_timeout",  # score 0.673
    "tests/test_users.py::test_user_profile_cache",  # score 0.703
}
FLAKY_IDS = sorted(ESCALATED_IDS | {BORDERLINE_ID})


class FakeLLMClient:
    """Injected stand-in for the LLM path — records calls, never networks."""

    def __init__(self, reply="Narrative from the fake LLM.", error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.error is not None:
            raise self.error
        return self.reply


def test_escalation_threshold_sits_above_detection_threshold():
    # The two-tier design (ADR-005): every escalated test is detected, but
    # not every detected test is escalated.
    assert Orchestrator.ESCALATION_THRESHOLD > DetectorAgent.DETECTION_THRESHOLD


def test_stable_history_produces_no_reports(record_factory):
    records = [
        record_factory(run_id=f"run_{i:02d}", status=TestStatus.PASSED)
        for i in range(6)
    ]

    assert Orchestrator().run(records) == []


def test_reports_exactly_the_flaky_fixture_tests():
    reports = Orchestrator().run(parse_junit_dir(CI_RUNS))

    assert [r.test_id for r in reports] == FLAKY_IDS  # sorted, reproducible
    assert all(isinstance(r, FlakinessReport) for r in reports)


def test_reports_are_self_contained_without_api_key():
    # Autouse conftest fixture scrubs ANTHROPIC_API_KEY: the full pipeline
    # must still assemble complete reports (ADR-001 principle #1).
    for report in Orchestrator().run(parse_junit_dir(CI_RUNS)):
        assert report.generated_by == "system1_fallback"
        assert report.explanation
        assert report.recommendation
        assert report.detection.test_id == report.test_id
        assert report.classification.test_id == report.test_id
        # Stage confidences currently inherit from the classifier, so the
        # min() aggregate resolves to it.
        assert report.confidence == report.classification.confidence


def test_escalation_gates_the_llm_attempt():
    explainer_fake = FakeLLMClient()
    recommender_fake = FakeLLMClient()
    orchestrator = Orchestrator(
        explainer=ExplainerAgent(llm_client=explainer_fake),
        recommender=RecommenderAgent(llm_client=recommender_fake),
    )

    reports = {r.test_id: r for r in orchestrator.run(parse_junit_dir(CI_RUNS))}

    for fake in (explainer_fake, recommender_fake):
        prompted = [user for (_, user) in fake.calls]
        assert len(prompted) == len(ESCALATED_IDS)
        assert all(BORDERLINE_ID not in user for user in prompted)
    assert reports[BORDERLINE_ID].generated_by == "system1_fallback"
    for test_id in ESCALATED_IDS:
        assert reports[test_id].generated_by == "system2_llm"
        assert reports[test_id].explanation == explainer_fake.reply
        assert reports[test_id].recommendation == recommender_fake.reply


def test_llm_failure_degrades_escalated_reports_to_fallback():
    broken = FakeLLMClient(error=ConnectionError("network down"))
    orchestrator = Orchestrator(
        explainer=ExplainerAgent(llm_client=broken),
        recommender=RecommenderAgent(llm_client=broken),
    )

    reports = orchestrator.run(parse_junit_dir(CI_RUNS))

    assert [r.test_id for r in reports] == FLAKY_IDS  # output shape unchanged
    for report in reports:
        assert report.generated_by == "system1_fallback"
        assert report.explanation
        assert report.recommendation


def test_partial_llm_success_demotes_report_generated_by():
    # Conservative aggregate (ADR-005): one stage falling back demotes the
    # report label, but LLM prose that did succeed is kept.
    explainer_fake = FakeLLMClient(reply="LLM explanation that succeeded.")
    orchestrator = Orchestrator(
        explainer=ExplainerAgent(llm_client=explainer_fake),
        recommender=RecommenderAgent(
            llm_client=FakeLLMClient(error=TimeoutError("quota"))
        ),
    )

    reports = {r.test_id: r for r in orchestrator.run(parse_junit_dir(CI_RUNS))}

    for test_id in ESCALATED_IDS:
        assert reports[test_id].generated_by == "system1_fallback"
        assert reports[test_id].explanation == "LLM explanation that succeeded."
