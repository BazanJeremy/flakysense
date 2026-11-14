# ADR-008: Test Identity Is `classname::name`

- **Status:** Accepted
- **Date:** 2026-11-14
- **Deciders:** Jérémy Bazan

## Context

Every stage groups run records by `test_id`, and ReleaseGuard joins its own
JUnit reading against the `test_id` values of a FlakySense report. The
identity is therefore both an internal key and a published contract.

Until now it was `file::name` when a `<testcase>` carried a `file`
attribute, and `classname::name` otherwise. The intent was a readable
pytest node id. Two measurements, made on 2026-11-14 with real pytest 9.1.1
reports, show the rule did not hold up:

- **The `file` branch drops the class.** Two tests named `test_ok`, in
  `TestLogin` and `TestLogout` of one file, came out as a single identity:
  one report, 12 records for 6 runs, the failures of one test mixed with the
  passes of the other. An always-green test was diluting the score of a
  flaky one.
- **The rule depends on a JUnit option the user did not choose for us.**
  pytest's default report carries no `file` attribute; `junit_family=xunit1`
  does, with a backslash path on Windows. The same suite therefore had two
  different identities depending on that option, and three depending on the
  operating system. Playwright puts a file path in `classname` and emits no
  `file` either.

The fixtures under `data/samples/` all carry `file`, which is why the suite
never saw either problem.

## Decision

The identity is `classname::name`, verbatim, whether or not a `file`
attribute is present. `file` is used only when `classname` is missing, and
`unknown` when both are.

Nothing is normalized: separators and case are the report's own bytes.

## Options Considered

1. **`classname::name`, verbatim** — one rule, no dependence on
   `junit_family`, keeps the class, and is what the reports of every runner
   seen so far already carry. Less pretty than a node id for pytest. **Chosen.**
2. **Keep `file::name` and append the class parsed out of `classname`** —
   yields a real pytest node id, but needs a heuristic to tell module
   segments from class segments, and that heuristic breaks on runners whose
   `classname` is a path. ReleaseGuard already had to stop guessing for that
   reason (its ADR-004). Rejected: a second copy of a heuristic known to fail.
3. **Leave the rule, document the limitation** — keeps a measured defect
   that silently merges histories. Rejected.

## Consequences

- **Breaking for reports that carry `file`:** `tests/test_users.py::test_x`
  becomes `tests.test_users::test_x`. Reports without `file` — pytest's
  default, Playwright — are unchanged.
- Same-named tests in different classes are now distinct tests.
- A consumer joining on `test_id` needs exactly one rule: `classname::name`.
  ReleaseGuard's `path` dialect already computes that.
- Pinned by `tests/test_ingest.py`: two classes stay two tests; the identity
  ignores `file` when `classname` is present; `file` remains the fallback.
- Two tests that share both `classname` and `name` — parametrized cases
  whose ids collide, for instance — still share an identity. Not addressed
  here: no report showing it was observed.
