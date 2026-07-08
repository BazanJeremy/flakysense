"""Tests for the LLM client layer (ADR-004) — no network, ever."""

from flakysense.llm import AnthropicClient, client_from_env


def test_no_api_key_means_no_client():
    # The autouse fixture scrubs ANTHROPIC_API_KEY: fallback mode by default.
    assert client_from_env() is None


def test_missing_sdk_degrades_to_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-never-used")
    client = client_from_env()
    # CI has no `anthropic` SDK installed → None. On a dev machine with the
    # `llm` extra, construction succeeds — either way, never a crash.
    assert client is None or isinstance(client, AnthropicClient)
