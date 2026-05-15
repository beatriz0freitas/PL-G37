"""Utilitários partilhados pelos passes de otimização."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCJump,
    IRCall,
    IRInstr,
    IRLabelInstr,
    IRLoadArray,
    IROp,
    IRPrint,
    IRProcBegin,
    IRProcEnd,
    IRRead,
    IRStoreArray,
    IRUnaryOp,
    IRWrite,
)
from src.representacao_intermedia.operadores import IRArrayRef, Temp


Substituter = Callable[[Any], Any]
BLOCK_BOUNDARY_TYPES = (IRLabelInstr, IRProcBegin, IRProcEnd)


def is_literal(value: Any) -> bool:
    """Verdadeiro se value é um literal Python dobrável."""

    return isinstance(value, (int, float, bool))


def temp_key(value: Any) -> str | None:
    """Converte um temporário em chave de ambiente, ignorando outros valores."""
    return str(value) if isinstance(value, Temp) else None


def is_copy_source(value: Any) -> bool:
    """Indica se um valor pode ser propagado como cópia direta."""
    return isinstance(value, (Temp, str))


def is_false_literal(value: Any) -> bool:
    """Reconhece literais que tornam uma condição falsa na IR."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value == 0
    return False


def is_true_literal(value: Any) -> bool:
    """Reconhece literais que tornam uma condição verdadeira na IR."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return False


def used_temps_in_value(value: Any) -> set[str]:
    """Extrai temporários usados dentro de um valor IR."""
    if isinstance(value, Temp):
        return {str(value)}
    if isinstance(value, IRArrayRef):
        used: set[str] = set()
        for idx in value.indices:
            used |= used_temps_in_value(idx)
        return used
    return set()


def used_temps_in_instr(instr: IRInstr) -> set[str]:
    """Extrai temporários lidos por uma instrução IR."""
    used: set[str] = set()
    if isinstance(instr, IRAssign):
        used |= used_temps_in_value(instr.src)
    elif isinstance(instr, IROp):
        used |= used_temps_in_value(instr.left)
        used |= used_temps_in_value(instr.right)
    elif isinstance(instr, IRUnaryOp):
        used |= used_temps_in_value(instr.operand)
    elif isinstance(instr, IRLoadArray):
        for idx in instr.indices:
            used |= used_temps_in_value(idx)
    elif isinstance(instr, IRCJump):
        used |= used_temps_in_value(instr.cond)
    elif isinstance(instr, IRPrint):
        for arg in instr.args:
            used |= used_temps_in_value(arg)
    elif isinstance(instr, IRWrite):
        if instr.unit is not None:
            used |= used_temps_in_value(instr.unit)
        if instr.fmt is not None:
            used |= used_temps_in_value(instr.fmt)
        for item in instr.items:
            used |= used_temps_in_value(item)
    elif isinstance(instr, IRRead):
        for arg in instr.args:
            if isinstance(arg, IRArrayRef):
                used |= used_temps_in_value(arg)
    elif isinstance(instr, IRStoreArray):
        used |= used_temps_in_value(instr.src)
        for idx in instr.indices:
            used |= used_temps_in_value(idx)
    elif isinstance(instr, IRCall):
        for arg in instr.args:
            used |= used_temps_in_value(arg)
    return used


def defined_temp(instr: IRInstr) -> str | None:
    """Devolve o temporário definido por uma instrução, se existir."""
    if isinstance(instr, IRAssign) and isinstance(instr.dest, Temp):
        return str(instr.dest)
    if isinstance(instr, IROp) and isinstance(instr.dest, Temp):
        return str(instr.dest)
    if isinstance(instr, IRUnaryOp) and isinstance(instr.dest, Temp):
        return str(instr.dest)
    if isinstance(instr, IRLoadArray) and isinstance(instr.dest, Temp):
        return str(instr.dest)
    if isinstance(instr, IRCall) and isinstance(instr.dest, Temp):
        return str(instr.dest)
    return None


def is_side_effect_free(instr: IRInstr) -> bool:
    """Indica se uma definição morta pode ser removida sem alterar efeitos."""
    return isinstance(instr, (IRAssign, IROp, IRUnaryOp, IRLoadArray))


def split_basic_blocks(instructions: list[IRInstr]) -> list[list[IRInstr]]:
    """Divide IR em blocos lineares separados por labels/fronteiras de escopo."""
    blocks: list[list[IRInstr]] = []
    current: list[IRInstr] = []
    for instr in instructions:
        if isinstance(instr, BLOCK_BOUNDARY_TYPES):
            if current:
                blocks.append(current)
                current = []
            blocks.append([instr])
            continue
        current.append(instr)
    if current:
        blocks.append(current)
    return blocks


def rewrite_with_subst(instr: IRInstr, subst: Substituter) -> IRInstr | None:
    """Reescreve usos de uma instrução com uma função de substituição."""

    def rewrite_value(value: Any) -> Any:
        """Aplica substituição também dentro de referências indexadas."""
        if isinstance(value, IRArrayRef):
            return IRArrayRef(value.name, [rewrite_value(idx) for idx in value.indices])
        return subst(value)

    if isinstance(instr, IRAssign):
        return IRAssign(dest=instr.dest, src=rewrite_value(instr.src))
    if isinstance(instr, IROp):
        return IROp(
            op=instr.op,
            dest=instr.dest,
            left=rewrite_value(instr.left),
            right=rewrite_value(instr.right),
        )
    if isinstance(instr, IRUnaryOp):
        return IRUnaryOp(
            op=instr.op,
            dest=instr.dest,
            operand=rewrite_value(instr.operand),
        )
    if isinstance(instr, IRCJump):
        return IRCJump(
            cond=rewrite_value(instr.cond),
            true_label=instr.true_label,
            false_label=instr.false_label,
        )
    if isinstance(instr, IRPrint):
        return IRPrint(args=[rewrite_value(arg) for arg in instr.args])
    if isinstance(instr, IRWrite):
        return IRWrite(
            unit=rewrite_value(instr.unit) if instr.unit is not None else None,
            fmt=rewrite_value(instr.fmt) if instr.fmt is not None else None,
            items=[rewrite_value(item) for item in instr.items],
        )
    if isinstance(instr, IRLoadArray):
        return IRLoadArray(
            dest=instr.dest,
            name=instr.name,
            indices=[rewrite_value(idx) for idx in instr.indices],
        )
    if isinstance(instr, IRStoreArray):
        return IRStoreArray(
            name=instr.name,
            indices=[rewrite_value(idx) for idx in instr.indices],
            src=rewrite_value(instr.src),
        )
    if isinstance(instr, IRRead):
        return IRRead(
            args=[
                rewrite_value(arg) if isinstance(arg, IRArrayRef) else arg
                for arg in instr.args
            ],
        )
    if isinstance(instr, IRCall):
        return IRCall(
            name=instr.name,
            args=[rewrite_value(arg) for arg in instr.args],
            dest=instr.dest,
        )
    return None
