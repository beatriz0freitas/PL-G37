"""Simplificações de fluxo de controlo em IR."""

from __future__ import annotations

from src.representacao_intermedia.instrucoes import (
    IRCJump,
    IRInstr,
    IRJump,
    IRLabelInstr,
    IRProcBegin,
    IRProcEnd,
    IRReturn,
    IRStop,
)

from .utils import is_false_literal, is_true_literal


def jump_simplification(instructions: list[IRInstr]) -> list[IRInstr]:
    """Simplifica saltos redundantes e condicionais com constantes."""

    result: list[IRInstr] = []
    i = 0
    while i < len(instructions):
        instr = instructions[i]
        next_instr = instructions[i + 1] if i + 1 < len(instructions) else None

        if isinstance(instr, IRJump) and isinstance(next_instr, IRLabelInstr):
            if instr.label == next_instr.label:
                i += 1
                continue

        if isinstance(instr, IRCJump):
            if instr.true_label == instr.false_label:
                result.append(IRJump(instr.true_label))
                i += 1
                continue
            if is_false_literal(instr.cond):
                result.append(IRJump(instr.false_label))
                i += 1
                continue
            if is_true_literal(instr.cond):
                result.append(IRJump(instr.true_label))
                i += 1
                continue

        result.append(instr)
        i += 1

    return result


def dead_code_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Remove instruções inalcançáveis após salto incondicional ou paragem."""

    result: list[IRInstr] = []
    unreachable = False

    for instr in instructions:
        if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
            unreachable = False

        if not unreachable:
            result.append(instr)

        if isinstance(instr, (IRJump, IRStop, IRReturn)):
            unreachable = True

    return result
