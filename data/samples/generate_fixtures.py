"""Deterministic generator for the synthetic CI-run fixtures in ci_runs/.

Regenerate with:

    python data/samples/generate_fixtures.py

Every value below is a hard-coded table — no randomness, no clock reads —
so regeneration always produces identical fixtures. The scenarios the data
encodes are documented in README.md next to this file.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent
CI_RUNS_DIR = SAMPLES_DIR / "ci_runs"

# The simulated suite: an invented e-commerce app ("shopapp"). Keys are the
# short handles used in the run tables below.
TESTS = {
    "checkout": ("tests/test_checkout.py", "tests.test_checkout", "test_checkout_total"),
    "payment": ("tests/test_payment.py", "tests.test_payment", "test_payment_gateway_timeout"),
    "cache": ("tests/test_users.py", "tests.test_users", "test_user_profile_cache"),
    "import": ("tests/test_data_import.py", "tests.test_data_import", "test_bulk_import"),
    "export": ("tests/test_reports.py", "tests.test_reports", "test_report_export"),
}

# Execution order varies between runs (simulating pytest-randomly). The
# ordering-flaky test fails exactly when it executes AFTER the bulk import.
ORDER_CACHE_BEFORE_IMPORT = ["checkout", "payment", "cache", "import", "export"]
ORDER_CACHE_AFTER_IMPORT = ["checkout", "payment", "import", "cache", "export"]

FAILURES = {
    "payment": (
        "TimeoutError: payment gateway did not respond within 5.0s",
        "tests/test_payment.py:47: in test_payment_gateway_timeout\n"
        "    response = gateway.charge(order, timeout=5.0)\n"
        "E   TimeoutError: payment gateway did not respond within 5.0s",
    ),
    "cache": (
        "AssertionError: expected fresh profile for user 'u-1042', found stale cached entry",
        "tests/test_users.py:88: in test_user_profile_cache\n"
        '    assert profile.email == "u-1042@example.test"\n'
        "E   AssertionError: expected fresh profile for user 'u-1042', found stale cached entry\n"
        "E   (cache was pre-populated by tests/test_data_import.py::test_bulk_import)",
    ),
    "export": (
        "PermissionError: [WinError 32] export file is locked by another process",
        "tests/test_reports.py:61: in test_report_export\n"
        "    report_path.unlink()\n"
        "E   PermissionError: [WinError 32] export file is locked by another process:"
        " 'reports\\\\export.xlsx'",
    ),
}

EXPORT_SKIP_MESSAGE = "openpyxl not installed on this runner"

# One entry per CI run. Signatures encoded across the 10 runs:
#   payment  — duration drifts upward, fails 3/10 at the 5.0s timeout ceiling
#   cache    — fails 4/4 when ordered after the bulk import, passes 6/6 before
#   export   — fails 2/2 on the Windows runner, skipped once, passes elsewhere
RUNS = [
    {"id": "run_01", "timestamp": "2026-06-29T08:14:52", "hostname": "ci-linux-01", "os": "linux",
     "cache_after_import": False, "payment_fails": False, "export": "pass",
     "durations": {"checkout": 0.118, "payment": 1.912, "cache": 0.312, "import": 2.412, "export": 1.183}},
    {"id": "run_02", "timestamp": "2026-06-29T14:41:07", "hostname": "ci-linux-02", "os": "linux",
     "cache_after_import": True, "payment_fails": False, "export": "pass",
     "durations": {"checkout": 0.124, "payment": 2.134, "cache": 0.293, "import": 2.487, "export": 1.201}},
    {"id": "run_03", "timestamp": "2026-06-30T08:16:33", "hostname": "ci-win-01", "os": "windows",
     "cache_after_import": False, "payment_fails": False, "export": "fail",
     "durations": {"checkout": 0.121, "payment": 2.318, "cache": 0.318, "import": 2.451, "export": 0.912}},
    {"id": "run_04", "timestamp": "2026-06-30T14:39:48", "hostname": "ci-linux-01", "os": "linux",
     "cache_after_import": False, "payment_fails": True, "export": "pass",
     "durations": {"checkout": 0.119, "payment": 5.003, "cache": 0.315, "import": 2.503, "export": 1.194}},
    {"id": "run_05", "timestamp": "2026-07-01T08:15:21", "hostname": "ci-linux-02", "os": "linux",
     "cache_after_import": True, "payment_fails": False, "export": "pass",
     "durations": {"checkout": 0.126, "payment": 2.607, "cache": 0.291, "import": 2.466, "export": 1.217}},
    {"id": "run_06", "timestamp": "2026-07-01T14:42:55", "hostname": "ci-linux-01", "os": "linux",
     "cache_after_import": False, "payment_fails": False, "export": "skip",
     "durations": {"checkout": 0.122, "payment": 2.841, "cache": 0.321, "import": 2.529, "export": 0.001}},
    {"id": "run_07", "timestamp": "2026-07-02T08:14:39", "hostname": "ci-linux-02", "os": "linux",
     "cache_after_import": True, "payment_fails": True, "export": "pass",
     "durations": {"checkout": 0.125, "payment": 5.002, "cache": 0.296, "import": 2.441, "export": 1.189}},
    {"id": "run_08", "timestamp": "2026-07-02T14:40:12", "hostname": "ci-win-01", "os": "windows",
     "cache_after_import": False, "payment_fails": False, "export": "fail",
     "durations": {"checkout": 0.120, "payment": 3.096, "cache": 0.317, "import": 2.518, "export": 0.937}},
    {"id": "run_09", "timestamp": "2026-07-03T08:17:05", "hostname": "ci-linux-01", "os": "linux",
     "cache_after_import": False, "payment_fails": True, "export": "pass",
     "durations": {"checkout": 0.123, "payment": 5.004, "cache": 0.314, "import": 2.474, "export": 1.206}},
    {"id": "run_10", "timestamp": "2026-07-03T14:38:26", "hostname": "ci-linux-02", "os": "linux",
     "cache_after_import": True, "payment_fails": False, "export": "pass",
     "durations": {"checkout": 0.127, "payment": 3.412, "cache": 0.289, "import": 2.495, "export": 1.198}},
]

# Raw pytest console output archived for run_07 (order B, payment timeout +
# ordering failure in the same run) — the kind of artifact a real CI keeps.
RUN_07_CONSOLE = """\
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.2.0, pluggy-1.5.0
rootdir: /home/runner/work/shopapp/shopapp
configfile: pyproject.toml
plugins: randomly-3.15.0
Using --randomly-seed=2417
collected 5 items

tests/test_checkout.py .                                                 [ 20%]
tests/test_payment.py F                                                  [ 40%]
tests/test_data_import.py .                                              [ 60%]
tests/test_users.py F                                                    [ 80%]
tests/test_reports.py .                                                  [100%]

=================================== FAILURES ===================================
_________________________ test_payment_gateway_timeout _________________________

tests/test_payment.py:47: in test_payment_gateway_timeout
    response = gateway.charge(order, timeout=5.0)
E   TimeoutError: payment gateway did not respond within 5.0s
___________________________ test_user_profile_cache ____________________________

tests/test_users.py:88: in test_user_profile_cache
    assert profile.email == "u-1042@example.test"
E   AssertionError: expected fresh profile for user 'u-1042', found stale cached entry
E   (cache was pre-populated by tests/test_data_import.py::test_bulk_import)
=========================== short test summary info ============================
FAILED tests/test_payment.py::test_payment_gateway_timeout - TimeoutError: p...
FAILED tests/test_users.py::test_user_profile_cache - AssertionError: expect...
========================= 2 failed, 3 passed in 9.42s ==========================
"""


def _case_outcome(run: dict, key: str) -> str:
    if key == "payment" and run["payment_fails"]:
        return "fail"
    if key == "cache" and run["cache_after_import"]:
        return "fail"
    if key == "export":
        return run["export"]
    return "pass"


def build_junit(run: dict) -> ET.ElementTree:
    order = (
        ORDER_CACHE_AFTER_IMPORT
        if run["cache_after_import"]
        else ORDER_CACHE_BEFORE_IMPORT
    )
    outcomes = {key: _case_outcome(run, key) for key in order}
    suite_time = round(sum(run["durations"].values()) + 0.42, 3)

    suite = ET.Element(
        "testsuite",
        name="pytest",
        errors="0",
        failures=str(sum(1 for o in outcomes.values() if o == "fail")),
        skipped=str(sum(1 for o in outcomes.values() if o == "skip")),
        tests=str(len(order)),
        time=f"{suite_time:.3f}",
        timestamp=run["timestamp"],
        hostname=run["hostname"],
    )
    properties = ET.SubElement(suite, "properties")
    for name, value in [
        ("run_id", run["id"]),
        ("os", run["os"]),
        ("python", "3.12.3"),
        ("ci_runner", "github-actions"),
    ]:
        ET.SubElement(properties, "property", name=name, value=value)

    for key in order:
        file, classname, name = TESTS[key]
        case = ET.SubElement(
            suite,
            "testcase",
            classname=classname,
            name=name,
            file=file,
            time=f"{run['durations'][key]:.3f}",
        )
        if outcomes[key] == "fail":
            message, body = FAILURES[key]
            failure = ET.SubElement(case, "failure", message=message)
            failure.text = body
        elif outcomes[key] == "skip":
            ET.SubElement(
                case, "skipped", message=EXPORT_SKIP_MESSAGE, type="pytest.skip"
            )

    root = ET.Element("testsuites")
    root.append(suite)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    return tree


def main() -> None:
    for run in RUNS:
        run_dir = CI_RUNS_DIR / run["id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        build_junit(run).write(
            run_dir / "junit.xml", encoding="utf-8", xml_declaration=True
        )
    (CI_RUNS_DIR / "run_07" / "pytest_output.txt").write_text(
        RUN_07_CONSOLE, encoding="utf-8", newline="\n"
    )
    print(f"Wrote {len(RUNS)} runs to {CI_RUNS_DIR}")


if __name__ == "__main__":
    main()
