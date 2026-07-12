# ADR-001: System 1 / System 2 Agent Orchestration Pattern

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

FlakySense chains four agents — Detector → Classifier → Explainer → Recommender —
to turn raw CI test-run history into an actionable flakiness report. Two forces
shape the orchestration design:

1. **Volume asymmetry.** Detection and classification must process every test of
   every run (thousands of data points); explanation and recommendation only
   matter for the small subset of tests confirmed flaky.
2. **Zero-API-key constraint** (series-wide principle #1): the full pipeline
   and CI must run green with no LLM access. LLM calls are an enhancement layer,
   never a dependency.

LinkedIn Engineering's autonomous QA agent addresses a similar tension with a
dual-process pattern borrowed from cognitive psychology (Kahneman): a fast,
cheap, heuristic **System 1** handles the high-volume routine path, while a
slow, deliberate, expensive **System 2** is engaged selectively for the cases
that warrant deep reasoning.

## Decision

FlakySense adopts the System 1 / System 2 dual-process pattern:

- **System 1 — Detector and Classifier.** Purely deterministic: statistical
  scoring (pass/fail instability, duration drift, ordering correlation) and
  rule-based cause classification. Always executed, on every input, with no
  LLM involvement. Reproducible by construction.
- **System 2 — Explainer and Recommender.** LLM-backed deep reasoning over the
  evidence assembled by System 1. Engaged only when (a) a test's flakiness
  score crosses the escalation threshold and (b) an LLM is available. Each
  System 2 agent ships a deterministic rule-based fallback producing a valid
  (if terser) report, so the pipeline's output shape is identical with or
  without API keys.

Escalation policy: score-threshold based. The threshold value is fixed in S2
once the scoring function exists; the S3 orchestrator applies it.

## Options Considered

1. **Sequential LLM chain (every stage an LLM call)** — Pros: simplest mental
   model, maximum reasoning at each step. Cons: violates the zero-API-key
   principle; non-deterministic detection (the numbers a QA lead acts on must
   be reproducible); cost scales with total test count instead of flaky count.
2. **Parallel independent agents (TestScribe pattern)** — Pros: proven in TestScribe, fast.
   Cons: the stages are causally dependent (classification consumes detection
   output; explanation consumes both), so parallelism buys little — and it
   would demonstrate no orchestration progression over TestScribe.
3. **System 1 / System 2 dual-process (chosen)** — Pros: determinism where the
   volume is, reasoning where the value is; bounded LLM cost; a real
   degraded-mode story; clean escalation semantics for the S3 orchestrator.
   Cons: two code paths per System 2 agent to maintain and test; an escalation
   threshold to tune.

## Consequences

- **Positive:** CI green with zero keys; LLM spend proportional to the number
  of flaky tests, not total tests; detection numbers reproducible run-to-run;
  the S3 orchestrator's job reduces to a well-defined escalation decision.
- **Negative:** every System 2 agent carries a dual implementation (LLM +
  fallback), each path needing tests; threshold tuning is deferred work with
  an over/under-escalation risk.
- **Follow-ups:** S2 fixes the scoring function and threshold; S3 implements
  escalation in the orchestrator; a future ADR will cover the LLM
  provider/prompt strategy if System 2 grows beyond one call per agent.
