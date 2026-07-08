# ADR-004: System 2 LLM Integration Pattern

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

ADR-001 defines the Explainer and Recommender as System 2 stages: LLM-backed
deep reasoning with a mandatory deterministic fallback. Turning that into
code raises four forces:

1. **Zero-API-key invariant** (principle #1): the suite and CI must stay
   green with no key and no vendor SDK installed.
2. **Free by default** (principle #5): an LLM call is an optional
   enhancement a user opts into, never a cost the project imposes.
3. **Vendor churn:** the LLM provider must be swappable without touching
   agent code.
4. **No network in tests, ever** — including on a developer machine that
   happens to have an API key configured.

## Decision

- **Provider-neutral protocol.** Agents depend only on a minimal
  `LLMClient` protocol: `complete(system, user) -> str`
  (`src/flakysense/llm.py`). No agent imports a vendor SDK.
- **Reference implementation: Anthropic.** `AnthropicClient` wraps the
  Messages API (model `claude-opus-4-8`, adaptive thinking). The `anthropic`
  SDK lives in the optional dependency group `llm`
  (`pip install -e .[llm]`), not in `requirements.txt` — CI never installs
  it.
- **Environment-gated activation.** `client_from_env()` returns a client
  only when `ANTHROPIC_API_KEY` is set *and* the SDK is importable;
  otherwise `None` and the agent is natively in fallback mode. Other
  credential sources (OAuth profiles, etc.) are deliberately not
  auto-detected: activation must be predictable from one env var.
- **Graceful degradation.** A System 2 agent's `run()` tries the LLM path
  and falls back on *any* exception (network, quota, refusal, empty
  response). The `generated_by` field on the output model is the audit
  trail of which path actually ran.
- **Zero network in tests, by construction.** An autouse pytest fixture
  scrubs `ANTHROPIC_API_KEY` for the whole suite; the LLM path itself is
  exercised through an injected fake client.

## Options Considered

1. **Hard dependency on one vendor SDK, mocked in tests** — Pros: simplest
   wiring. Cons: violates the zero-key and free-by-default principles; CI
   installs a vendor SDK it never uses; swapping providers touches agents.
2. **Local model (Ollama) as the default LLM path** — Pros: fully free.
   Cons: heavyweight local setup breaks "solo-buildable in minutes"; CI
   cannot run it; still non-deterministic, so the fallback is needed anyway.
3. **Protocol + optional vendor client + env gating (chosen)** — Pros: core
   stays vendor-free; CI stays key-free; agents are testable by injection;
   the Recommender reuses the layer wholesale. Cons: the real LLM path is
   only exercised manually by a developer with a key.

## Consequences

- **Positive:** the pipeline produces identically-shaped output with or
  without keys; the S2 Recommender session inherits this layer with no new
  design work; tests are network-free even on key-configured machines.
- **Negative:** real-LLM behavior (prompt quality, response drift) is not
  covered by CI — accepted, since the enhancement layer is best-effort by
  design and the deterministic floor is what CI guarantees.
- **Follow-ups:** the Recommender adopts the same pattern next session;
  prompt iteration happens in S3 alongside report assembly; a provider
  other than Anthropic would be a new `LLMClient` implementation plus an
  ADR note, nothing more.
