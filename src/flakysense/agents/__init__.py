"""Agent pipeline: Detector -> Classifier -> Explainer -> Recommender.

Every agent MUST ship with a deterministic rule-based fallback
so the full pipeline runs in CI with zero API keys.
"""

from flakysense.agents.base import BaseAgent
from flakysense.agents.classifier import ClassifierAgent
from flakysense.agents.detector import DetectorAgent
from flakysense.agents.explainer import ExplainerAgent
from flakysense.agents.recommender import RecommenderAgent

__all__ = [
    "BaseAgent",
    "ClassifierAgent",
    "DetectorAgent",
    "ExplainerAgent",
    "RecommenderAgent",
]
