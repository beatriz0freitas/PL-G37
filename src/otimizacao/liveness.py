"""Eliminação de stores mortos para temporários."""

from __future__ import annotations

from src.representacao_intermedia.instrucoes import IRInstr

from .utils import BLOCK_BOUNDARY_TYPES, defined_temp, split_basic_blocks, used_temps_in_instr


def dead_store_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Remove stores para temporários que não são usados no bloco."""

    result: list[IRInstr] = []
    for block in split_basic_blocks(instructions):
        if len(block) == 1 and isinstance(block[0], BLOCK_BOUNDARY_TYPES):
            result.extend(block)
            continue

        live: set[str] = set()
        kept: list[IRInstr] = []
        for instr in reversed(block):
            defined = defined_temp(instr)
            used = used_temps_in_instr(instr)
            if defined is not None and defined not in live:
                continue
            kept.append(instr)
            if defined is not None and defined in live:
                live.remove(defined)
            live |= used

        result.extend(reversed(kept))

    return result
