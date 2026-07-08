# ADR-007: Container Packaging Scope

- **Status:** Accepted
- **Date:** 2026-07-08
- **Deciders:** Jérémy Bazan

## Context

S3 commits to a docker-compose deliverable, under a hard project constraint:
**CI must not require Docker for the core suite** (CLAUDE.md environment
rule). So the question is not *whether* to containerize but *what role* the
container plays. Forces:

1. The natural deployment unit for a CI-side QA tool is a container image a
   pipeline can `docker run` against its artifacts.
2. The test suite already runs everywhere Python does; a Docker-based dev or
   test environment would duplicate that for no gain and violate the CI
   constraint.
3. The CLI contract (ADR-006) already gives a container everything it needs:
   one directory in, reports and a gateable exit code out.

## Decision

- **The container packages the CLI as a one-shot analysis job** — nothing
  else. No dev container, no test-runner image; CI keeps running the suite
  natively.
- **Runtime-only image:** `python:3.14-slim`, non-root user, installs the
  package from `pyproject.toml` (whose `dependencies` now correctly declare
  pydantic — found and fixed in this session; `requirements.txt` remains the
  dev setup with pytest). pytest never enters the image.
- **The optional `[llm]` extra is baked in.** The Anthropic SDK is present so
  the *same image* upgrades to the System 2 path when `ANTHROPIC_API_KEY` is
  provided at runtime; without the key, activation stays off (ADR-004 env
  gate). Free by default is preserved — an installed SDK is not a paid call.
- **docker-compose is the demo harness:** `docker compose run --rm
  flakysense` builds the image, mounts the bundled sample history read-only
  at `/runs`, and passes `ANTHROPIC_API_KEY` through when set. Exit codes
  propagate (ADR-006), so the containerized CLI is CI-gateable as-is.

## Options Considered

1. **No container (pip install is enough)** — Pros: zero maintenance. Cons:
   drops a committed S3 deliverable; "run it against your CI artifacts
   without a Python setup" is the realistic adoption path for a QA tool.
2. **Dev/test-runner image (suite runs in Docker, maybe in CI)** — Pros:
   uniform environment. Cons: directly violates the Docker-free-CI
   constraint; duplicates what the venv already provides; conflates product
   packaging with development tooling.
3. **Runtime CLI image + compose demo harness (chosen)** — Pros: container
   has exactly one job; CI constraint untouched; LLM enhancement available
   by env var without rebuilding. Cons: the image is not used by CI, so
   image rot is only caught manually (accepted at portfolio scale).

## Consequences

- **Positive:** a pipeline can gate on flakiness with `docker run` and the
  ADR-006 exit codes; the packaging gap in `pyproject.toml` (undeclared
  pydantic dependency) was surfaced and fixed by this session; compose gives
  reviewers a one-liner demo.
- **Negative:** the image is rebuilt/verified manually, not in CI (accepted:
  adding a Docker build job would contradict the constraint's spirit for a
  portfolio project); baking `[llm]` in grows the image by the SDK's size.
- **Follow-ups:** the senior README session documents the container as the
  recommended CI integration; if a dashboard service ever lands, it becomes
  a second compose service reusing this image.
