# ADR-006: CLI Contract

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

S3 delivers the pipeline's entry point: a command a QA lead (or a CI job)
points at a directory of JUnit XML reports to get flakiness reports back.
Forces:

1. **Two consumers, one command:** a human wants a readable summary; CI wants
   machine-readable output and a meaningful exit code to gate on.
2. **Free and lean** (principle #5): a two-flag CLI does not justify a new
   runtime dependency.
3. **One schema, one owner:** the Pydantic models are already the pipeline's
   contract (ADR-001); the CLI must not introduce a parallel output schema
   that can drift from them.

## Decision

- **Entry points:** console script `flakysense` (pyproject `[project.scripts]`)
  and `python -m flakysense` — same `main(argv) -> int`, stdlib `argparse`,
  no new dependency.
- **Usage:** `flakysense <runs_dir>` — the directory is searched recursively
  for `junit.xml` files (the existing ingestion contract).
- **Exit codes follow the grep convention:**
  - `0` — analysis ran, no flaky test detected;
  - `1` — analysis ran, flaky tests found (lets CI gate on flakiness);
  - `2` — the analysis could not run (bad path, no/unparseable reports;
    `argparse` usage errors also exit 2, consistently).
- **`--json`** emits the reports serialized directly from the
  `FlakinessReport` models (`model_dump(mode="json")`): the CLI schema *is*
  the model schema, by construction. Default output is a compact console
  summary (score, cause, confidence, path, explanation, recommendation per
  flaky test).
- **`--escalation-threshold SCORE`** overrides the ADR-005 default (0.5).
  The orchestrator gains an `escalation_threshold` constructor parameter
  (default unchanged). Out-of-range values are semantics, not errors:
  `> 1` disables escalation entirely, `<= 0` escalates every flaky test.

## Options Considered

1. **click / typer** — Pros: nicer help text, less boilerplate at scale.
   Cons: a new runtime dependency for two flags and one positional argument;
   nothing in the S3 scope needs subcommands.
2. **Always exit 0, report-only semantics** — Pros: no surprise for callers.
   Cons: the natural QA use — "fail the pipeline when flakiness appears" —
   would need output parsing; an exit-code contract is cheaper than a parser.
3. **argparse + grep-style exit codes + model-derived JSON (chosen)** — Pros:
   zero new dependencies; CI-gateable; JSON schema cannot drift from the
   models. Cons: breaking model changes are breaking CLI changes (accepted:
   they version together in one repo).

## Consequences

- **Positive:** the pipeline is usable end-to-end from a terminal or a CI
  step with zero API keys; the JSON mode gives the future dashboard/docker
  session a ready-made data feed; the ADR-005 threshold is now operable
  without touching code.
- **Negative:** console formatting is hand-rolled (no rich tables) — accepted
  as lean; JSON output embeds full run evidence, so large histories produce
  large payloads (acceptable at portfolio scale).
- **Follow-ups:** the docker/compose session wraps this entry point; the
  senior README documents the exit-code contract for CI usage.
