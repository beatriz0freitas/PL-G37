"""Basic blocks e CFG leve para passes de otimização."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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


@dataclass
class BasicBlock:
    """Bloco básico linear, identificado pela ordem na IR original."""

    id: int
    start: int
    instructions: list[IRInstr]
    successors: set[int] = field(default_factory=set)
    predecessors: set[int] = field(default_factory=set)

    @property
    def first(self) -> IRInstr:
        """Primeira instrução do bloco."""
        return self.instructions[0]

    @property
    def last(self) -> IRInstr:
        """Última instrução do bloco."""
        return self.instructions[-1]


@dataclass
class ControlFlowGraph:
    """CFG intraprocedural leve sobre a lista linear de IR."""

    blocks: list[BasicBlock]
    label_to_block: dict[Any, int]
    entry_blocks: list[int]

    def reachable_blocks(self) -> set[int]:
        """Calcula blocos alcançáveis a partir do main e de cada subprograma."""
        reachable: set[int] = set()
        stack = list(reversed(self.entry_blocks))

        while stack:
            block_id = stack.pop()
            if block_id in reachable or block_id < 0 or block_id >= len(self.blocks):
                continue
            reachable.add(block_id)
            stack.extend(sorted(self.blocks[block_id].successors, reverse=True))

        return reachable


def _is_terminator(instr: IRInstr) -> bool:
    """Indica se a instrução termina o fluxo linear do bloco."""
    return isinstance(instr, (IRJump, IRCJump, IRStop, IRReturn, IRProcEnd))


def _starts_subprogram(block: BasicBlock) -> bool:
    """Reconhece blocos que são entrada de subprograma."""
    return isinstance(block.first, IRProcBegin)


def _target_block(cfg: ControlFlowGraph, label: Any) -> int | None:
    """Resolve uma label para o id de bloco correspondente."""
    return cfg.label_to_block.get(label)


def build_cfg(instructions: list[IRInstr]) -> ControlFlowGraph:
    """Constrói basic blocks e arestas de controlo a partir de IR linear."""
    if not instructions:
        return ControlFlowGraph(blocks=[], label_to_block={}, entry_blocks=[])

    leaders: set[int] = {0}
    for idx, instr in enumerate(instructions):
        if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
            leaders.add(idx)
        if _is_terminator(instr) and idx + 1 < len(instructions):
            leaders.add(idx + 1)

    sorted_leaders = sorted(leaders)
    blocks: list[BasicBlock] = []
    for block_id, start in enumerate(sorted_leaders):
        end = sorted_leaders[block_id + 1] if block_id + 1 < len(sorted_leaders) else len(instructions)
        blocks.append(BasicBlock(block_id, start, instructions[start:end]))

    label_to_block: dict[Any, int] = {}
    for block in blocks:
        if isinstance(block.first, IRLabelInstr):
            label_to_block[block.first.label] = block.id

    cfg = ControlFlowGraph(
        blocks=blocks,
        label_to_block=label_to_block,
        entry_blocks=[],
    )
    cfg.entry_blocks = _entry_blocks(cfg)
    _connect_successors(cfg)
    return cfg


def _entry_blocks(cfg: ControlFlowGraph) -> list[int]:
    """Entradas independentes: programa principal e corpos de subprogramas."""
    entries: list[int] = []
    if cfg.blocks:
        entries.append(0)
    for block in cfg.blocks:
        if _starts_subprogram(block) and block.id not in entries:
            entries.append(block.id)
    return entries


def _connect_successors(cfg: ControlFlowGraph) -> None:
    """Preenche sucessores e predecessores de cada bloco."""
    for block in cfg.blocks:
        last = block.last
        next_block = cfg.blocks[block.id + 1] if block.id + 1 < len(cfg.blocks) else None

        if isinstance(last, IRJump):
            target = _target_block(cfg, last.label)
            if target is not None:
                block.successors.add(target)
        elif isinstance(last, IRCJump):
            for label in (last.true_label, last.false_label):
                target = _target_block(cfg, label)
                if target is not None:
                    block.successors.add(target)
        elif isinstance(last, (IRStop, IRReturn, IRProcEnd)):
            pass
        elif next_block is not None and not _starts_subprogram(next_block):
            block.successors.add(next_block.id)

    for block in cfg.blocks:
        for succ in block.successors:
            cfg.blocks[succ].predecessors.add(block.id)


def flatten_cfg(cfg: ControlFlowGraph, keep_blocks: set[int] | None = None) -> list[IRInstr]:
    """Volta a serializar blocos por ordem original."""
    result: list[IRInstr] = []
    for block in cfg.blocks:
        if keep_blocks is None or block.id in keep_blocks:
            result.extend(block.instructions)
    return result
