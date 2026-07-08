# Runtime packaging of the flakysense CLI (ADR-007).
# CI never builds or runs this image: the core suite stays Docker-free.
FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
# [llm] bakes the optional Anthropic SDK in: the same image upgrades to the
# System 2 path when ANTHROPIC_API_KEY is provided at runtime (ADR-004);
# without the key every stage runs its deterministic fallback.
RUN pip install --no-cache-dir ".[llm]"

RUN useradd --create-home flakysense
USER flakysense

# Mount a directory of junit.xml reports at /runs (see docker-compose.yml).
# Exit codes follow ADR-006: 0 clean, 1 flaky tests found, 2 analysis error.
ENTRYPOINT ["flakysense"]
CMD ["/runs"]
