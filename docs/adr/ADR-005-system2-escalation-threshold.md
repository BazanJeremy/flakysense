# ADR-005: System 2 Escalation Threshold

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

ADR-001 fixed the escalation policy (score-threshold based) and left the
threshold value and its enforcement point to the S3 orchestrator session.
ADR-002 fixed the *detection* threshold at 0.3 and explicitly deferred the
*escalation* threshold as a distinct knob. The two answer different
questions:

- **Detection (0.3):** is this test flaky enough to appear in the report?
- **Escalation:** is the evidence strong enough to spend LLM reasoning on it?

Forces:

1. **Bounded LLM cost** (ADR-001): System 2 spend must scale with the number
   of *strongly* flaky tests, not everything that clears detection.
2. **Identical output shape** either way (ADR-004): escalation may only
   change *how* a report's narrative is produced, never *whether* a report
   exists.
3. **Demo credibility:** the synthetic fixtures should exercise both sides of
   the threshold, so the two-tier behavior is visible in the sample data.
   Detector v1 scores the fixture flaky tests at 0.497, 0.673, and 0.703.

## Decision

- **`ESCALATION_THRESHOLD = 0.5`**, a constant on the orchestrator — the
  single place where the escalation decision lives. Agents stay
  escalation-unaware.
- **Semantics:** at or above the threshold, the orchestrator invokes System 2
  agents through `run()` — the LLM path is attempted when available, with
  ADR-004's graceful degradation. Below it, the orchestrator pins them to
  `fallback()` directly: no LLM attempt, even with an API key configured.
- **Grounding for 0.5:** it splits the fixture scores — the borderline case
  (0.497) stays fully deterministic while the two strong cases (0.673, 0.703)
  escalate — and it sits comfortably above the 0.3 detection floor, so
  weak-evidence detections never trigger LLM spend.
- **Report assembly aggregates conservatively.** The report-level
  `generated_by` is `system2_llm` only when *every* System 2 stage produced
  LLM output — any fallback anywhere demotes the whole report — and the
  report `confidence` is the minimum of the stage confidences. A QA lead
  reading a report gets a floor guarantee, never an overclaim.

## Options Considered

1. **Escalate everything detected as flaky (single 0.3 threshold)** — Pros:
   one knob, no tuning. Cons: LLM spend on the detections whose evidence is
   weakest; erases the two-tier behavior ADR-001 was designed around; the
   demo dataset would show only one path.
2. **Gate on classification confidence instead of detection score** — Pros:
   escalates on diagnostic quality, not just instability. Cons: UNKNOWN
   classifications carry confidence 0.0 and would *never* escalate — yet a
   strongly flaky test the heuristics cannot diagnose is precisely where LLM
   reasoning over the raw signals adds the most value.
3. **Score threshold at 0.5, enforced by the orchestrator (chosen)** — Pros:
   LLM cost bounded to strong cases; UNKNOWN-cause tests still escalate when
   instability is high; one constant, one owner; both paths visible in the
   fixtures. Cons: another hand-tuned constant; threshold cliffs are
   inherent (0.49 and 0.51 get different treatment).

## Consequences

- **Positive:** the escalation decision deferred since ADR-001 now has a
  single enforcement point; LLM spend is proportional to strong flakiness
  evidence; the fixture dataset demonstrates deterministic, escalated, and
  degraded behavior without any API key.
- **Negative:** 0.5 is hand-tuned against synthetic fixtures — real-world
  score distributions may need retuning; mixed LLM/fallback reports are
  reported under the conservative label, hiding partial LLM success (accepted:
  honesty over marketing).
- **Follow-ups:** the S3 CLI session may expose the threshold as a flag;
  revisit the value if real CI history replaces the synthetic fixtures.
