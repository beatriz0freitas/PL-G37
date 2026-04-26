"""Pacote de geração de código."""

from .decls import ArrayTypes, ScalarTypes, extract_decl_info
from .ewvm import EWVMBackend, EWVMGenerator
from .layout import MemoryLayout

__all__ = [
    "ArrayTypes",
    "EWVMBackend",
    "EWVMGenerator",
    "MemoryLayout",
    "ScalarTypes",
    "extract_decl_info",
]
