"""Provider-neutral model adapter interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from ..schemas import ModelInfo
from .schemas import ModelAdaptiveProposals, ModelAnalysis, ModelFix


@dataclass
class AnalysisInput:
    skill_name: Optional[str]
    description: Optional[str]
    files: dict[str, str]  # bounded excerpts: path -> text
    hidden_content: list[dict] = field(default_factory=list)  # extracted concealed snippets for context
    rule_summary: list[str] = field(default_factory=list)


@dataclass
class AdapterResult:
    info: ModelInfo
    analysis: Optional[ModelAnalysis] = None
    fix: Optional[ModelFix] = None
    proposals: Optional[ModelAdaptiveProposals] = None
    errors: list[str] = field(default_factory=list)


class ModelAdapter(Protocol):
    def health(self) -> ModelInfo: ...

    def analyze_skill(self, data: AnalysisInput) -> AdapterResult: ...

    def suggest_fix(self, files: dict[str, str], findings: list[dict]) -> AdapterResult: ...
