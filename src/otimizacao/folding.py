"""Constant folding sobre IR."""

from __future__ import annotations

from typing import Any

from src.representacao_intermedia.instrucoes import IRAssign, IRInstr, IROp, IRUnaryOp

from .utils import is_literal


def _eval_binop(op: str, left: Any, right: Any) -> Any:
    """Avalia op(left, right) em tempo de compilação."""

    match op:
        case "+":
            return left + right
        case "-":
            return left - right
        case "*":
            return left * right
        case "/":
            if right == 0:
                raise ArithmeticError("divisão por zero")
            if isinstance(left, int) and isinstance(right, int):
                return int(left / right)
            return left / right
        case "==":
            return int(left == right)
        case "!=":
            return int(left != right)
        case "<":
            return int(left < right)
        case "<=":
            return int(left <= right)
        case ">":
            return int(left > right)
        case ">=":
            return int(left >= right)
        case "AND":
            return int(bool(left) and bool(right))
        case "OR":
            return int(bool(left) or bool(right))
        case "EQV":
            return int(bool(left) == bool(right))
        case "NEQV":
            return int(bool(left) != bool(right))
    raise ValueError(f"Operador sem avaliação estática: {op!r}")


def _eval_unary(op: str, operand: Any) -> Any:
    match op:
        case "NEG":
            return -operand
        case "NOT":
            return int(not bool(operand))
    raise ValueError(f"Operador unário sem avaliação estática: {op!r}")


def constant_folding(instructions: list[IRInstr]) -> list[IRInstr]:
    """Substitui IROp/IRUnaryOp com operandos literais pelo resultado."""

    result: list[IRInstr] = []

    for instr in instructions:
        if isinstance(instr, IROp) and is_literal(instr.left) and is_literal(instr.right):
            try:
                value = _eval_binop(instr.op, instr.left, instr.right)
                result.append(IRAssign(dest=instr.dest, src=value))
                continue
            except (ArithmeticError, ValueError):
                pass

        if isinstance(instr, IRUnaryOp) and is_literal(instr.operand):
            try:
                value = _eval_unary(instr.op, instr.operand)
                result.append(IRAssign(dest=instr.dest, src=value))
                continue
            except ValueError:
                pass

        result.append(instr)

    return result
