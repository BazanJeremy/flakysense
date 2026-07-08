"""Tests for the CLI — exit-code contract and output formats (ADR-006)."""

import json
from pathlib import Path

from flakysense import cli
from flakysense.cli import EXIT_CLEAN, EXIT_ERROR, EXIT_FLAKY, main
from flakysense.orchestrator import Orchestrator

CI_RUNS = Path(__file__).resolve().parents[1] / "data" / "samples" / "ci_runs"

FLAKY_IDS = [
    "tests/test_payment.py::test_payment_gateway_timeout",
    "tests/test_reports.py::test_report_export",
    "tests/test_users.py::test_user_profile_cache",
]

_STABLE_JUNIT = """<?xml version="1.0"?>
<testsuite name="pytest" timestamp="2026-07-01T08:00:00" tests="1">
  <testcase classname="tests.test_ok" name="test_stable"
            file="tests/test_ok.py" time="0.1"/>
</testsuite>
"""


def test_flaky_history_exits_1_and_names_each_flaky_test(capsys):
    exit_code = main([str(CI_RUNS)])

    out = capsys.readouterr().out
    assert exit_code == EXIT_FLAKY
    assert all(test_id in out for test_id in FLAKY_IDS)
    assert "3 flaky" in out
    assert "recommendation:" in out


def test_stable_history_exits_0(tmp_path, capsys):
    run_dir = tmp_path / "run_01"
    run_dir.mkdir()
    (run_dir / "junit.xml").write_text(_STABLE_JUNIT)

    exit_code = main([str(tmp_path)])

    assert exit_code == EXIT_CLEAN
    assert "no flaky tests detected" in capsys.readouterr().out


def test_unusable_input_exits_2_with_stderr_message(tmp_path, capsys):
    exit_code = main([str(tmp_path)])  # empty dir: no junit.xml anywhere

    captured = capsys.readouterr()
    assert exit_code == EXIT_ERROR
    assert captured.out == ""
    assert "error:" in captured.err


def test_json_output_is_the_model_schema(capsys):
    exit_code = main([str(CI_RUNS), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == EXIT_FLAKY
    assert [report["test_id"] for report in payload] == FLAKY_IDS
    for report in payload:
        assert report["generated_by"] == "system1_fallback"  # no key in tests
        assert report["explanation"]
        assert report["recommendation"]
        assert report["detection"]["evidence"]  # full run history embedded


def test_escalation_threshold_flag_reaches_the_orchestrator(monkeypatch):
    captured = {}

    class SpyOrchestrator(Orchestrator):
        def __init__(self, **kwargs):
            captured.update(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(cli, "Orchestrator", SpyOrchestrator)

    main([str(CI_RUNS), "--escalation-threshold", "0.9"])

    assert captured["escalation_threshold"] == 0.9
