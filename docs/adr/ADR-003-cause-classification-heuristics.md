# ADR-003: Cause Classification Heuristics

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

The Classifier (System 1 per ADR-001) must map a flaky test's run history to
a probable root-cause category (`FlakyCause`) with a confidence. Same
constraints as ADR-002: deterministic, explainable, meaningful on ~10 runs.
Two extra forces:

1. **Multiple causes can leave evidence at once** (a Windows-only failure
   whose message mentions a file lock reads as both ENVIRONMENT and
   RESOURCE_CONTENTION). The design must weigh evidence, not stop at the
   first match.
2. **Never guess.** A wrong-but-confident cause sends a QA lead down the
   wrong path; UNKNOWN with honest signals is strictly better.

## Decision

One deterministic heuristic per cause scores the detection evidence
independently; the strongest wins (argmax), ties resolved by fixed
evaluation order (TIMING, ORDERING, ENVIRONMENT, RESOURCE_CONTENTION):

| Cause | Heuristic | Strength |
|---|---|---|
| TIMING | every failing run slower than the slowest passing run | 0.7 (0.85 with a timing keyword in the failure message) |
| TIMING | timing keyword only (`timeout`, `timed out`, `deadline`) | 0.5 |
| ORDERING | failing and passing suite positions form disjoint sets (≥2 of each) | 0.8 |
| ENVIRONMENT | an environment key perfectly splits failures from passes (≥2 failures) | 0.9 |
| RESOURCE_CONTENTION | contention keyword in the failure message (`locked`, `deadlock`, `connection refused`, …) | 0.5 |

The winning strength is dampened by `min(1, failures/2)` — a single failing
run is never enough for a diagnosis — and becomes the classification's
confidence. Below a **0.4 confidence floor** the result is UNKNOWN with
confidence 0.0. The `signals` list always carries *every* heuristic that
fired, not just the winner's: it is the evidence feed for the Explainer.

`TEST_DATA` has no v1 heuristic (no fixture exercises it yet); the honest
outcome for such a case is UNKNOWN.

## Options Considered

1. **First-match decision tree** — Pros: simplest. Cons: rule order silently
   decides multi-evidence cases; concurrent evidence is discarded instead of
   surfaced.
2. **LLM classification** — Pros: handles messy real-world messages. Cons:
   the Classifier is a System 1 stage (ADR-001): it must stay deterministic
   and key-free; cost would scale with every flaky test.
3. **Per-cause scoring + argmax with floor (chosen)** — Pros: deterministic,
   each strength constant is inspectable and tunable; losing evidence still
   reaches the report via `signals`; UNKNOWN is a first-class outcome. Cons:
   strength constants are judgment calls; heuristics look at one test's
   history in isolation.

## Consequences

- **Positive:** on the fixture scenarios the three documented flaky tests
  classify as TIMING / ORDERING / ENVIRONMENT with confidence 0.8–0.9, and
  the export test's lock-file message correctly surfaces as a secondary
  signal under its ENVIRONMENT classification.
- **Negative:** position-based ORDERING detects *that* order matters, not
  *which* predecessor is the culprit — identifying it needs the cross-test
  view only the orchestrator has (deferred to S3). Keyword lists are
  English-centric and minimal by design (false positives cost more than
  misses).
- **Follow-ups:** S3 orchestrator may enrich ORDERING with predecessor
  analysis; add a TEST_DATA fixture + heuristic when a realistic scenario is
  designed; revisit strength constants against real CI data.
