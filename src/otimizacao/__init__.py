"""Passes de otimização sobre IR."""

from .cfg import BasicBlock, ControlFlowGraph, build_cfg
from .control_flow import dead_code_elimination, jump_simplification
from .cse import common_subexpression_elimination
from .folding import constant_folding
from .liveness import dead_store_elimination
from .propagation import constant_propagation, copy_propagation

__all__ = [
    "BasicBlock",
    "ControlFlowGraph",
    "build_cfg",
    "common_subexpression_elimination",
    "constant_folding",
    "constant_propagation",
    "copy_propagation",
    "dead_code_elimination",
    "dead_store_elimination",
    "jump_simplification",
]
