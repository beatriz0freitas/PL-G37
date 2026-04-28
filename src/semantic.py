"""Compatibilidade para imports antigos da analise semantica."""

from src.analise_semantica import (
    CHARACTER_TYPES,
    INTRINSICS,
    LOGICAL_TYPES,
    NUMERIC_TYPES,
    IntrinsicSpec,
    SemanticAnalyzer,
    analyze,
)

__all__ = [
    "CHARACTER_TYPES",
    "INTRINSICS",
    "LOGICAL_TYPES",
    "NUMERIC_TYPES",
    "IntrinsicSpec",
    "SemanticAnalyzer",
    "analyze",
]
