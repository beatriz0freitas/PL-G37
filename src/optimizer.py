"""Fachada pública dos passes de otimização sobre IR.

Os passes vivem em ``src.otimizacao`` para manter cada transformação pequena,
mas este módulo preserva a API usada pelos testes e pela CLI.
"""

from __future__ import annotations

from collections.abc import Callable

from src.otimizacao import (
    common_subexpression_elimination,
    constant_folding,
    constant_propagation,
    copy_propagation,
    dead_code_elimination,
    dead_store_elimination,
    jump_simplification,
)
from src.representacao_intermedia.instrucoes import IRInstr


OptimizationPass = Callable[[list[IRInstr]], list[IRInstr]]

OPTIMIZATION_PIPELINE: tuple[OptimizationPass, ...] = (
    constant_propagation,
    constant_folding,
    copy_propagation,
    common_subexpression_elimination,
    constant_propagation,
    constant_folding,
    copy_propagation,
    constant_propagation,
    dead_store_elimination,
    jump_simplification,
    dead_code_elimination,
)


def optimize(instructions: list[IRInstr]) -> list[IRInstr]:
    """Aplica os passes de otimização em sequência."""

    for optimization_pass in OPTIMIZATION_PIPELINE:
        instructions = optimization_pass(instructions)
    return instructions


__all__ = [
    "common_subexpression_elimination",
    "constant_folding",
    "constant_propagation",
    "copy_propagation",
    "dead_code_elimination",
    "dead_store_elimination",
    "jump_simplification",
    "optimize",
]
