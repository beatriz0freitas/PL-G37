"""Pacote de geração de código."""

from .decls import ArrayTypes, ScalarTypes, extract_decl_info
from .ewvm import EWVMBackend, EWVMGenerator
from .intrinsics_codegen import IntrinsicsCodegenMixin
from .layout import MemoryLayout
from .stack_emitter import StackEmitterMixin
from .type_inference import TypeInferenceMixin

__all__ = [
    "ArrayTypes",
    "EWVMBackend",
    "EWVMGenerator",
    "IntrinsicsCodegenMixin",
    "MemoryLayout",
    "ScalarTypes",
    "StackEmitterMixin",
    "TypeInferenceMixin",
    "extract_decl_info",
]
