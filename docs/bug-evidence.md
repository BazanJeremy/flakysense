# Bug Evidence Log

Series-wide principle: **bugs found by tests are evidence, not embarrassment**
— each entry records what surfaced the problem, what it would have cost, and
where the fix is pinned so it cannot regress silently.

---

## 1. pytest collected the domain models as test classes

- **Sprint:** S1 (models session, commit `f370f02`)
- **Surfaced by:** the first run of the suite against the new Pydantic models.
- **The problem:** `TestStatus` and `TestRunRecord` begin with `Test`, so
  pytest picked them up as candidate test classes and emitted collection
  warnings on every run.
- **Why it mattered:** a flaky-test tool whose own suite is noisy undermines
  the exact trust it is meant to build — and permanent warnings are where
  real ones go to hide.
- **Pinned by:** `__test__ = False` markers on both models
  (`src/flakysense/models.py`) with comments explaining they are domain
  vocabulary; the suite runs warning-free.

## 2. Ordering flakiness would masquerade as an environment issue

- **Sprint:** S2 (classifier session); counterfactual re-verified 2026-07-08.
- **Surfaced by:** developing the classifier heuristics against the fixture
  scenarios.
- **The problem:** JUnit's `hostname` attribute looks like environment data.
  If the parser treated it as such, the ordering-flaky fixture
  (`test_user_profile_cache`) would classify as **ENVIRONMENT (0.90)**
  instead of **ORDERING (0.80)** — all four of its failures happen to land
  on `ci-linux-02` while no passing run does, purely by scheduling
  coincidence, and the environment heuristic outscores the ordering one.
- **Why it mattered:** the report would send a QA lead diffing OS and runner
  configurations instead of isolating shared test state — a confident,
  evidence-backed *wrong* diagnosis, the worst failure mode for this tool.
  In small run histories, "the machine it ran on" correlates with almost
  anything.
- **Pinned by:** the parser maps only explicit `<property>` elements into
  `environment` (`src/flakysense/ingest/junit.py`); the fixture integration
  tests assert the ordering scenario classifies as ORDERING
  (`tests/test_agents/test_classifier.py`).

## 3. The package declared no runtime dependencies

- **Sprint:** S3 (docker session, fixed in commit `d31e5e0`)
- **Surfaced by:** writing the Dockerfile, which installs from
  `pyproject.toml` alone.
- **The problem:** `[project]` declared no `dependencies`, so
  `pip install flakysense` produced a package that crashes on import
  (`ModuleNotFoundError: pydantic`). Local development and CI never noticed
  because both install `requirements.txt` first — the dev setup masked the
  packaging gap.
- **Why it mattered:** the container image — the deliverable whose whole job
  is "run it without a Python setup" — would have shipped broken.
- **Pinned by:** `dependencies = ["pydantic>=2.7"]` in `pyproject.toml`;
  the image is verified live per ADR-007 (compose run reproduces the local
  report with the correct exit code).

## 4. A crash left through the "flaky tests found" exit code

- **Sprint:** post-S3 audit (2026-11-13)
- **Surfaced by:** a read-through of the JUnit parser, then reproduced on
  the installed CLI before any fix. The suite never fed the parser a
  malformed `time` attribute.
- **The problem:** `parse_junit_file` called `float(case.get("time"))`
  directly, and `main` caught `JUnitParseError` only. A report carrying
  `time="abc"` raised `ValueError`; `time="-1"` raised a Pydantic
  `ValidationError` (`duration_s` is `ge=0`). Both escaped as tracebacks,
  and Python exits 1 on an uncaught exception. Measured on the CLI: exit
  **1** in both cases, where ADR-006 promises 2.
- **Why it mattered:** 1 means "flaky tests found". A CI gating on that
  code would have blamed the test suite for a failure of the tool, and
  exit 2 — "the analysis could not run" — was unreachable for this whole
  class of input.
- **Pinned by:** `_case_duration` raises `JUnitParseError` on a
  non-numeric value, a negative value or NaN; `main` gained a last-resort guard that
  prints the traceback and exits 2 on anything unexpected, so a crash can
  no longer borrow a verdict's exit code. Three tests in
  `tests/test_cli.py` (suite: 60 -> 63). The same two reports now exit
  **2**; the sample history still exits 1.

## 5. Two tests in two classes were one test

- **Sprint:** post-S3 audit (2026-11-14)
- **Surfaced by:** wiring FlakySense and ReleaseGuard back to back on
  reports produced by a real pytest run, instead of the hand-built fixtures.
- **The problem:** the identity was `file::name` whenever a `<testcase>`
  carried a `file` attribute. That drops the class. Measured with pytest
  9.1.1 and `junit_family=xunit1`, on a file holding `TestLogin.test_ok`
  (fails every other run) and `TestLogout.test_ok` (always passes): one
  report instead of two, 12 records for 6 runs, 3 failures among 9 passes.
- **Why it mattered:** the histories of unrelated tests were merged, so a
  stable test diluted the score of a flaky one, or lent it its flakiness.
  And the identity changed with a JUnit option: pytest's default report has
  no `file` attribute, so the same suite had another identity there — which
  is also why ReleaseGuard's join found nothing on real reports.
- **Why it hid:** every fixture under `data/samples/` carries `file` and
  none has two classes in one file.
- **Pinned by:** [ADR-008](adr/ADR-008-test-identity.md) — the identity is
  `classname::name`, verbatim. Three tests in `tests/test_ingest.py`
  (suite: 63 -> 66). Measured after the fix on the same reports: one
  report, `tests.test_api.TestLogin::test_ok`, with its own 6 records; the
  stable `TestLogout.test_ok` is a separate test and is no longer mixed in.
