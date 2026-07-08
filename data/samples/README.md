# Sample Fixtures

Synthetic pytest/JUnit run logs used as deterministic test fixtures.
The "shopapp" suite below is entirely invented — never real company data.

## Layout

```
ci_runs/
├── run_01/junit.xml … run_10/junit.xml   # 10 CI runs of the same 5-test suite
└── run_07/pytest_output.txt              # raw pytest console output for one run
```

Each `junit.xml` is a pytest-style JUnit report: per-test duration, failure
messages, execution order (document order), and environment via
`<properties>` (os, runner, python). Timestamps are naive local time, as
real pytest emits them — attaching a timezone is the parser's job (S2).

## Scenarios encoded across the 10 runs

| Test | Scenario | Signature in the data |
|---|---|---|
| `test_checkout_total` | stable | passes 10/10, constant duration (~0.12s) |
| `test_payment_gateway_timeout` | flaky — timing | duration drifts 1.9s → 3.4s across runs; fails 3/10 (runs 04, 07, 09) at the 5.0s timeout ceiling |
| `test_user_profile_cache` | flaky — ordering | fails exactly in the 4 runs (02, 05, 07, 10) where it executes **after** `test_bulk_import`; passes in the 6 runs where it runs before |
| `test_bulk_import` | stable (but the ordering culprit) | passes 10/10; pre-populates the shared cache the previous test trips on |
| `test_report_export` | flaky — environment | fails 2/2 on the Windows runner (`ci-win-01`, runs 03, 08); skipped once (run 06, missing optional dependency); passes on Linux |

## Regenerating

```
python data/samples/generate_fixtures.py
```

The generator is fully deterministic (hard-coded tables, no randomness):
regeneration always produces identical files. Treat the generated XML as
static deliverables; change scenarios in the generator, not in the XML.
