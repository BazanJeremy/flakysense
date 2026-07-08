"""Command-line entry point — run the pipeline over a JUnit report directory.

Contract (ADR-006): exit codes follow the grep convention — 0 = analysis ran
and found no flaky test, 1 = flaky tests found (so CI can gate on it), 2 =
the analysis could not run. ``--json`` serializes the reports straight from
the Pydantic models, so the machine-readable schema is the model schema.
"""

from __future__ import annotations

import argparse
import json
import sys

from flakysense.ingest.junit import JUnitParseError, parse_junit_dir
from flakysense.models import FlakinessReport, TestRunRecord
from flakysense.orchestrator import Orchestrator

EXIT_CLEAN = 0
EXIT_FLAKY = 1
EXIT_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        records = parse_junit_dir(args.runs_dir)
    except JUnitParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    reports = Orchestrator(
        escalation_threshold=args.escalation_threshold
    ).run(records)

    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in reports], indent=2))
    else:
        print(_render_console(reports, records))
    return EXIT_FLAKY if reports else EXIT_CLEAN


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flakysense",
        description=(
            "Detect, classify, and explain flaky tests from a directory of "
            "JUnit XML CI reports."
        ),
    )
    parser.add_argument(
        "runs_dir",
        help="directory searched recursively for junit.xml reports",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the reports as JSON instead of the console summary",
    )
    parser.add_argument(
        "--escalation-threshold",
        type=float,
        default=None,
        metavar="SCORE",
        help=(
            "flakiness score at which the LLM path is attempted "
            "(default 0.5, ADR-005; >1 disables escalation)"
        ),
    )
    return parser


def _render_console(
    reports: list[FlakinessReport], records: list[TestRunRecord]
) -> str:
    tests = len({r.test_id for r in records})
    runs = len({r.run_id for r in records})
    # ASCII only: legacy Windows consoles garble non-ASCII in cp1252/cp850.
    if not reports:
        return (
            f"FlakySense - analyzed {tests} tests across {runs} runs: "
            "no flaky tests detected."
        )

    lines = [
        f"FlakySense - analyzed {tests} tests across {runs} runs: "
        f"{len(reports)} flaky",
    ]
    for report in reports:
        lines += [
            "",
            report.test_id,
            f"  flakiness {report.detection.score:.2f}"
            f" | cause: {report.classification.cause.value}"
            f" (confidence {report.confidence:.2f})"
            f" | path: {report.generated_by}",
            f"  explanation:    {report.explanation}",
            f"  recommendation: {report.recommendation}",
        ]
    return "\n".join(lines)
