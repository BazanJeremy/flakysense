"""Abstract agent contract implementing ADR-001's dual-process pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, Literal, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Common contract for pipeline agents (see ADR-001).

    The default execution path is the deterministic fallback, so every agent
    runs with zero API keys. System 2 agents will override ``run()`` in S2 to
    attempt the LLM path first and degrade to ``fallback()``.
    """

    name: ClassVar[str]
    system: ClassVar[Literal["system1", "system2"]]

    def run(self, payload: InputT) -> OutputT:
        """Public entry point; deterministic unless a subclass opts into LLM use."""
        return self.fallback(payload)

    @abstractmethod
    def fallback(self, payload: InputT) -> OutputT:
        """Deterministic rule-based path — mandatory, never needs an API key."""
