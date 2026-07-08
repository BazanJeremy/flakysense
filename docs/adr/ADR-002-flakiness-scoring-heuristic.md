# ADR-002: Flakiness Scoring Heuristic

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

The Detector (System 1 per ADR-001) must turn a test's run history into a
flakiness score in [0, 1] and a boolean flag. Constraints: fully
deterministic and reproducible, explainable signal-by-signal to a QA lead,
and meaningful on small histories (~10 runs, the realistic depth a team has
when a test first gets suspected).

The central semantic pitfall: **an always-failing test is broken, not
flaky.** Flakiness is non-determinism — the same code passing *and* failing
— so the score must peak for intermittent behaviour and vanish at both a 0%
and a 100% failure rate.

## Decision

Score = weighted blend of three deterministic signals over the test's
terminal (non-skipped) runs, ordered by start time:

| Signal | Formula | Weight |
|---|---|---|
| Intermittency | `4·p·(1−p)` where p = failure ratio | 0.4 |
| Flip rate | pass↔fail transitions between consecutive runs / (n−1) | 0.4 |
| Duration instability | coefficient of variation of durations, capped at 1 | 0.2 |

Histories shorter than 4 terminal runs are dampened by `n/4` (thin evidence
must not produce confident scores). Detection threshold: `is_flaky` when
score ≥ **0.3**. The System 2 *escalation* threshold (ADR-001) is a separate
knob, deferred to the orchestrator session (S3).

Method label: `rule_based_v1`.

## Options Considered

1. **Raw failure ratio** — Pros: trivial, obvious. Cons: conflates broken
   (p=1) with flaky (0<p<1), the exact confusion FlakySense exists to
   remove; blind to temporal patterns and duration drift.
2. **ML classifier over run features** — Pros: could learn subtle patterns.
   Cons: no labeled training data exists at this scale; opaque to a QA lead;
   conflicts with the determinism-first principle for System 1.
3. **Weighted heuristic blend (chosen)** — Pros: deterministic, each
   component individually explainable and reusable as Classifier evidence;
   tunable per deployment. Cons: weights are judgment calls, validated so
   far only against synthetic fixtures.

## Consequences

- **Positive:** scores are reproducible run-to-run and decomposable — the
  per-signal values can be surfaced as evidence and later feed the
  Classifier's heuristics; validated against the fixture scenarios (the
  three documented flaky tests score 0.497–0.703, stable tests < 0.01).
- **Negative:** the 0.4/0.4/0.2 weights and the 0.3 threshold are
  hand-tuned; real-world CI histories may need recalibration.
- **Follow-ups:** revisit weights against real OSS CI data if the project
  extends beyond the portfolio; the Classifier session decides whether to
  consume the per-signal values directly.
