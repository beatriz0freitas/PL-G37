"""Eliminação de subexpressões comuns sobre IR."""

from __future__ import annotations

from typing import Any

from src.representacao_intermedia.instrucoes import IRAssign, IRInstr, IROp, IRUnaryOp
from src.representacao_intermedia.operadores import Temp

from .utils import BLOCK_BOUNDARY_TYPES, is_literal, used_temps_in_value


def common_subexpression_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Elimina subexpressões comuns simples dentro de cada bloco."""

    def is_cse_value(value: Any) -> bool:
        """Filtra valores seguros para indexar numa chave de CSE."""
        return is_literal(value) or isinstance(value, Temp)

    def norm_value(value: Any) -> Any:
        """Normaliza literais e temporários para comparação estrutural."""
        if isinstance(value, Temp):
            return ("t", str(value))
        if is_literal(value):
            return ("l", value)
        return ("o", value)

    def key_for_binop(op: str, left: Any, right: Any) -> tuple | None:
        """Constrói a chave canónica de uma operação binária, se segura."""
        if not is_cse_value(left) or not is_cse_value(right):
            return None
        commutative = {"+", "*", "==", "!=", "AND", "OR", "EQV", "NEQV"}
        left_key = norm_value(left)
        right_key = norm_value(right)
        if op in commutative and left_key > right_key:
            left_key, right_key = right_key, left_key
        return ("bin", op, left_key, right_key)

    def key_for_unary(op: str, operand: Any) -> tuple | None:
        """Constrói a chave canónica de uma operação unária, se segura."""
        if not is_cse_value(operand):
            return None
        return ("un", op, norm_value(operand))

    def invalidate_for_temp(temp_name: str) -> None:
        """Remove expressões dependentes de um temporário redefinido."""
        to_remove = [key for key in expr_map if temp_name in key_deps[key]]
        for key in to_remove:
            expr_map.pop(key, None)
            key_deps.pop(key, None)

    result: list[IRInstr] = []
    expr_map: dict[tuple, Temp] = {}
    key_deps: dict[tuple, set[str]] = {}

    for instr in instructions:
        if isinstance(instr, BLOCK_BOUNDARY_TYPES):
            expr_map.clear()
            key_deps.clear()
            result.append(instr)
            continue

        if isinstance(instr, IROp):
            key = key_for_binop(instr.op, instr.left, instr.right)
            if key is not None and key in expr_map:
                result.append(IRAssign(dest=instr.dest, src=expr_map[key]))
            else:
                result.append(instr)
                if isinstance(instr.dest, Temp) and key is not None:
                    expr_map[key] = instr.dest
                    key_deps[key] = used_temps_in_value(instr.left) | used_temps_in_value(instr.right)
            if isinstance(instr.dest, Temp):
                invalidate_for_temp(str(instr.dest))
            continue

        if isinstance(instr, IRUnaryOp):
            key = key_for_unary(instr.op, instr.operand)
            if key is not None and key in expr_map:
                result.append(IRAssign(dest=instr.dest, src=expr_map[key]))
            else:
                result.append(instr)
                if isinstance(instr.dest, Temp) and key is not None:
                    expr_map[key] = instr.dest
                    key_deps[key] = used_temps_in_value(instr.operand)
            if isinstance(instr.dest, Temp):
                invalidate_for_temp(str(instr.dest))
            continue

        result.append(instr)

    return result
