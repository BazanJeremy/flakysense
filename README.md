# FlakySense

> Flaky test intelligence agent — detect, classify, and explain flaky tests from CI run history using log analysis, temporal correlation, and multi-step AI agent orchestration.

**Status:** 🚧 Sprint S3 — Integration & hardening.

## Why

Flaky tests erode trust in CI signals and waste engineering time. FlakySense analyzes test-run history to score flakiness, hypothesize root causes (timing, ordering, environment, resource contention), and recommend actions — with a fully deterministic fallback so it runs in CI without any API key.

## Architecture

Multi-step agent pipeline following the System 1 / System 2 dual-process
pattern ([ADR-001](docs/adr/ADR-001-orchestration-pattern.md)):

| Stage | Agent | System | Role |
|---|---|---|---|
| 1 | `DetectorAgent` | System 1 — deterministic, always runs | Scores flakiness: intermittency + flip rate + duration instability ([ADR-002](docs/adr/ADR-002-flakiness-scoring-heuristic.md)) |
| 2 | `ClassifierAgent` | System 1 — deterministic, always runs | Names the probable cause: duration outliers, order splits, environment diffs ([ADR-003](docs/adr/ADR-003-cause-classification-heuristics.md)) |
| 3 | `ExplainerAgent` | System 2 — LLM with deterministic fallback | Root-cause narrative grounded in System 1 evidence ([ADR-004](docs/adr/ADR-004-system2-llm-integration.md)) |
| 4 | `RecommenderAgent` | System 2 — LLM with deterministic fallback | Corrective action tailored from a per-cause playbook floor ([ADR-004](docs/adr/ADR-004-system2-llm-integration.md)) |

System 2 is engaged only above the flakiness-score threshold and degrades to
its rule-based fallback, so the full pipeline runs with **zero API keys**.
To enable the LLM enhancement layer: `pip install -e .[llm]` and set
`ANTHROPIC_API_KEY` — nothing else changes; without it every stage runs its
deterministic path.
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
