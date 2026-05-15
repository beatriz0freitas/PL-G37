"""Inferência de tipos temporários para o backend EWVM."""

from __future__ import annotations

from typing import Any

from src.analise_semantica.types import REAL_LIKE_TYPES
from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCall,
    IRInstr,
    IRLoadArray,
    IROp,
    IRProcBegin,
    IRProcEnd,
    IRUnaryOp,
)
from src.representacao_intermedia.operadores import IRArrayRef, IRStringLit, Temp


class TypeInferenceMixin:
    """Responsável por inferir tipos de temporários e valores IR."""

    def _infer_temp_types(self, instructions: list[IRInstr]) -> None:
        changed = True
        while changed:
            changed = False
            for instr in instructions:
                if isinstance(instr, IRProcBegin):
                    self._set_current_subprogram(instr.name)
                    continue
                if isinstance(instr, IRProcEnd):
                    self._set_current_subprogram(None)
                    continue
                inferred = self._infer_instr_type(instr)
                if inferred is None:
                    continue
                name, typename = inferred
                if self.temp_types.get(name) != typename:
                    self.temp_types[name] = typename
                    changed = True
        self._set_current_subprogram(None)

    def _infer_instr_type(self, instr: IRInstr) -> tuple[str, str] | None:
        if isinstance(instr, IRAssign) and isinstance(instr.dest, Temp):
            return str(instr.dest), self._type_of(instr.src)

        if isinstance(instr, IRLoadArray):
            array_type, _ = self._active_array_types()[instr.name]
            return str(instr.dest), array_type

        if isinstance(instr, IRUnaryOp):
            if not isinstance(instr.dest, Temp):
                return None
            if instr.op == "NOT":
                return str(instr.dest), "LOGICAL"
            return str(instr.dest), self._type_of(instr.operand)

        if isinstance(instr, IROp):
            if not isinstance(instr.dest, Temp):
                return None
            if instr.op in {"<", "<=", ">", ">=", "==", "!=", "AND", "OR", "EQV", "NEQV"}:
                return str(instr.dest), "LOGICAL"
            if instr.op == "CONCAT":
                return str(instr.dest), "CHARACTER"
            left_type = self._type_of(instr.left)
            right_type = self._type_of(instr.right)
            if self._is_real_type(left_type) or self._is_real_type(right_type):
                return str(instr.dest), "REAL"
            return str(instr.dest), "INTEGER"

        if isinstance(instr, IRCall) and isinstance(instr.dest, Temp):
            name = instr.name.upper()
            if name in {"SQRT", "REAL", "FLOAT"}:
                return str(instr.dest), "REAL"
            if name in {"MOD", "INT"}:
                return str(instr.dest), "INTEGER"
            if name == "ABS" and instr.args:
                return str(instr.dest), self._type_of(instr.args[0])
            if name in {"MAX", "MIN"} and instr.args:
                if any(self._is_real_type(self._type_of(arg)) for arg in instr.args):
                    return str(instr.dest), "REAL"
                return str(instr.dest), "INTEGER"
            if name in self.subprograms:
                info = self.subprograms[name]
                result_name = info.result_name or name
                return str(instr.dest), info.scalar_types.get(result_name, "INTEGER")
            return str(instr.dest), "INTEGER"

        return None

    def _type_of(self, value: Any) -> str:
        if isinstance(value, bool):
            return "LOGICAL"
        if isinstance(value, int):
            return "INTEGER"
        if isinstance(value, float):
            return "REAL"
        if isinstance(value, Temp):
            return self.temp_types.get(str(value), "INTEGER")
        if isinstance(value, IRArrayRef):
            return self._active_array_types().get(value.name, ("INTEGER", []))[0]
        if isinstance(value, IRStringLit):
            return "CHARACTER"
        if isinstance(value, str):
            if value in self._active_scalar_types():
                return self._active_scalar_types()[value]
            if value in self.temp_types:
                return self.temp_types[value]
            if value in self._active_array_types():
                return self._active_array_types()[value][0]
        return "INTEGER"

    @staticmethod
    def _is_real_type(type_name: str) -> bool:
        return type_name in REAL_LIKE_TYPES
