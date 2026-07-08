# FlakySense

> Flaky test intelligence agent — detect, classify, and explain flaky tests from CI run history using log analysis, temporal correlation, and multi-step AI agent orchestration.

**Status:** 🚧 Sprint S1 — Architecture & scaffolding.

## Why

Flaky tests erode trust in CI signals and waste engineering time. FlakySense analyzes test-run history to score flakiness, hypothesize root causes (timing, ordering, environment, resource contention), and recommend actions — with a fully deterministic fallback so it runs in CI without any API key.

## Architecture

Multi-step agent pipeline following the System 1 / System 2 dual-process
pattern ([ADR-001](docs/adr/ADR-001-orchestration-pattern.md)):

| Stage | Agent | System | Role |
|---|---|---|---|
| 1 | `DetectorAgent` | System 1 — deterministic, always runs | Scores flakiness: intermittency + flip rate + duration instability ([ADR-002](docs/adr/ADR-002-flakiness-scoring-heuristic.md)) |
| 2 | `ClassifierAgent` | System 1 — deterministic, always runs | Assigns a probable root-cause category |
| 3 | `ExplainerAgent` | System 2 — LLM with deterministic fallback | Produces a root-cause narrative |
| 4 | `RecommenderAgent` | System 2 — LLM with deterministic fallback | Suggests a concrete corrective action |

System 2 is engaged only above the flakiness-score threshold and degrades to
its rule-based fallback, so the full pipeline runs with **zero API keys**.
Shared data models live in `src/flakysense/models.py` (Pydantic v2); JUnit
XML ingestion in `src/flakysense/ingest/` turns CI artifacts into run
records; synthetic CI-run fixtures in `data/samples/` (see its README).

## Quickstart (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m pytest
```

## License

MIT
