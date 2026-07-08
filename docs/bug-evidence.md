# Bug Evidence Log

Portfolio principle: **bugs found by tests are evidence, not embarrassment**
— each entry records what surfaced the problem, what it would have cost, and
where the fix is pinned so it cannot regress silently.

---

## 1. pytest collected the domain models as test classes

- **Sprint:** S1 (models session, commit `f370f02`)
- **Surfaced by:** the first run of the suite against the new Pydantic models.
- **The problem:** `TestStatus` and `TestRunRecord` begin with `Test`, so
  pytest picked them up as candidate test classes and emitted collection
  warnings on every run.
- **Why it mattered:** a flaky-test tool whose own suite is noisy undermines
  the exact trust it is meant to build — and permanent warnings are where
  real ones go to hide.
- **Pinned by:** `__test__ = False` markers on both models
  (`src/flakysense/models.py`) with comments explaining they are domain
  vocabulary; the suite runs warning-free.

## 2. Ordering flakiness would masquerade as an environment issue

- **Sprint:** S2 (classifier session); counterfactual re-verified 2026-07-08.
- **Surfaced by:** developing the classifier heuristics against the fixture
  scenarios.
- **The problem:** JUnit's `hostname` attribute looks like environment data.
  If the parser treated it as such, the ordering-flaky fixture
  (`test_user_profile_cache`) would classify as **ENVIRONMENT (0.90)**
  instead of **ORDERING (0.80)** — all four of its failures happen to land
  on `ci-linux-02` while no passing run does, purely by scheduling
  coincidence, and the environment heuristic outscores the ordering one.
- **Why it mattered:** the report would send a QA lead diffing OS and runner
  configurations instead of isolating shared test state — a confident,
  evidence-backed *wrong* diagnosis, the worst failure mode for this tool.
  In small run histories, "the machine it ran on" correlates with almost
  anything.
- **Pinned by:** the parser maps only explicit `<property>` elements into
  `environment` (`src/flakysense/ingest/junit.py`); the fixture integration
  tests assert the ordering scenario classifies as ORDERING
  (`tests/test_agents/test_classifier.py`).

## 3. The package declared no runtime dependencies

- **Sprint:** S3 (docker session, fixed in commit `d31e5e0`)
- **Surfaced by:** writing the Dockerfile, which installs from
  `pyproject.toml` alone.
- **The problem:** `[project]` declared no `dependencies`, so
  `pip install flakysense` produced a package that crashes on import
  (`ModuleNotFoundError: pydantic`). Local development and CI never noticed
  because both install `requirements.txt` first — the dev setup masked the
  packaging gap.
- **Why it mattered:** the container image — the deliverable whose whole job
  is "run it without a Python setup" — would have shipped broken.
- **Pinned by:** `dependencies = ["pydantic>=2.7"]` in `pyproject.toml`;
  the image is verified live per ADR-007 (compose run reproduces the local
  report with the correct exit code).
