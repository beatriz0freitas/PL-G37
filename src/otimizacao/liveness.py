"""Análise de liveness e eliminação de stores mortos para temporários."""

from __future__ import annotations

from src.representacao_intermedia.instrucoes import IRInstr

from .cfg import build_cfg
from .utils import defined_temp, is_side_effect_free, used_temps_in_instr


def _block_use_def(block: list[IRInstr]) -> tuple[set[str], set[str]]:
    """Calcula USE/DEF clássicos para temporários dentro de um bloco."""
    uses: set[str] = set()
    defs: set[str] = set()

    for instr in block:
        for temp in used_temps_in_instr(instr):
            if temp not in defs:
                uses.add(temp)
        defined = defined_temp(instr)
        if defined is not None:
            defs.add(defined)

    return uses, defs


def _compute_liveness(instructions: list[IRInstr]) -> dict[int, set[str]]:
    """Calcula live-out por bloco sobre a CFG."""
    cfg = build_cfg(instructions)
    use_def = {
        block.id: _block_use_def(block.instructions)
        for block in cfg.blocks
    }
    live_in: dict[int, set[str]] = {block.id: set() for block in cfg.blocks}
    live_out: dict[int, set[str]] = {block.id: set() for block in cfg.blocks}

    changed = True
    while changed:
        changed = False
        for block in reversed(cfg.blocks):
            uses, defs = use_def[block.id]
            new_out: set[str] = set()
            for succ in block.successors:
                new_out |= live_in[succ]
            new_in = uses | (new_out - defs)

            if new_out != live_out[block.id] or new_in != live_in[block.id]:
                live_out[block.id] = new_out
                live_in[block.id] = new_in
                changed = True

    return live_out


def dead_store_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Remove definições de temporários mortas usando liveness global."""
    cfg = build_cfg(instructions)
    if not cfg.blocks:
        return []

    live_out = _compute_liveness(instructions)

    result: list[IRInstr] = []
    for block in cfg.blocks:
        live = set(live_out[block.id])
        kept: list[IRInstr] = []

        for instr in reversed(block.instructions):
            defined = defined_temp(instr)
            used = used_temps_in_instr(instr)
            if defined is not None and defined not in live and is_side_effect_free(instr):
                continue
            kept.append(instr)
            if defined is not None and defined in live:
                live.remove(defined)
            live |= used

        result.extend(reversed(kept))

    return result
