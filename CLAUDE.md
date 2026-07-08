# CLAUDE.md — FlakySense

> Flaky test intelligence agent — log analysis, temporal correlation, and multi-step agent orchestration to detect, classify, and explain flaky tests.
> Portfolio project P4 of a 6-project AI Test Engineering portfolio.

## Project State — READ FIRST

- **Status: ✅ COMPLETE — all three sprints delivered (2026-07-08).**
- S1: ADR-001, Pydantic v2 models, four agent interfaces with deterministic fallback stubs, synthetic fixtures (10 CI runs), contract tests. S2: all four agents live (detector, classifier, explainer, recommender; ADR-002–004), JUnit ingestion, env-gated LLM layer, GitHub Actions CI. S3: orchestrator with score-gated escalation (ADR-005), CLI (ADR-006), docker packaging (ADR-007), senior README, bug-evidence log. Suite: 60 tests, zero API keys.
- Any future work follows the same discipline: **small, session-scoped increments** — one concern per session, plan validated before code, feature branch + PR.

## Project Goal

Detect and explain **flaky tests** from CI/test-run history:

- **Log analysis**: parse pytest/JUnit-style run logs and CI artifacts.
- **Temporal correlation**: correlate failures across runs (time of day, ordering, environment, duration drift).
- **Multi-step orchestration**: agents that chain (detect → classify → explain → recommend), demonstrating orchestration beyond P3's parallel agents.
- Output: a flakiness report (score + root-cause hypothesis + recommended action) consumable by a QA lead.

Differentiating skills this project must showcase (vs P1–P3): log parsing at scale, multi-step agent orchestration, temporal/statistical reasoning.

## Sprint Plan (3 simulated weeks — portfolio credibility)

- **S1 — Architecture**: ADRs, data models (Pydantic v2), agent interfaces + deterministic fallback stubs, sample log fixtures, test skeletons. No business logic beyond stubs.
- **S2 — Implementation**: agents one by one, each landing with its tests and its rule-based fallback. Detection first, then classification, then explanation.
- **S3 — Integration & hardening**: orchestrator, CLI/dashboard entry point, docker-compose, GitHub Actions CI, senior README, bug-evidence documentation.

## Reserved ADR — Resolved

**ADR-001 (System 1 / System 2 orchestration pattern)** was co-written with the user during the Phase 1 session (2026-07-08) and is **Accepted**: `docs/adr/ADR-001-orchestration-pattern.md`. The reservation is fulfilled; subsequent ADRs follow the normal flow (proposed in-session, validated by the user before commit).

## Architecture Principles (non-negotiable, portfolio-wide)

1. **Deterministic fallback on every AI agent.** Full test suite and CI run green with **zero API keys**. LLM calls are an enhancement layer.
2. **Pydantic v2** for all data models.
3. **ADRs in `docs/adr/`** are first-class deliverables. Superseded, never edited retroactively.
4. **Bugs found by tests = portfolio evidence.** Document (what the test caught, why it mattered) before fixing.
5. **Free/open-source only.** Solo-buildable. No paid services, no enterprise access.

## Environment

- OS: Windows 11, shell: PowerShell
- Python 3.14, virtualenv in `.venv` — activate: `.\.venv\Scripts\Activate.ps1`
- Run tests with: `python -m pytest` — **NEVER** bare `pytest`
- Docker Desktop available locally; CI must not require Docker for the core suite
- CI: GitHub Actions (free tier, repo private under `BazanJeremy` until portfolio-wide public release)

## Conventions

- Codebase, comments, README, ADRs: **professional English** (Swiss/international market). Conversation with the user: French.
- Commits: small, atomic, imperative English (`feat: …`, `test: …`, `docs: adr-002 …`).
- Branch workflow (since S2, user decision 2026-07-08): never commit to `main` directly. Each session works on a feature branch (`feat/…`, `docs/…`, `fix/…`) keeping its atomic commits, then opens a GitHub PR to `main` — even solo, for portfolio hygiene and CI-gated merges.
- Targeted changes only. The user runs everything locally and pastes exact errors — fix precisely, never rewrite broadly.
- Never scan `.venv/`, `data/` beyond `data/samples/`, or generated report folders (token waste).

## Definition of Done (per agent)

- [ ] Pydantic v2 models with validation
- [ ] Deterministic fallback implemented and tested
- [ ] Unit tests green via `python -m pytest`
- [ ] Docstrings + entry in README architecture section
- [ ] ADR updated/added if a design decision was made
