"""Estruturas auxiliares de memória para o backend EWVM."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryLayout:
    """Layout simples de memória global."""

    next_addr: int = 0

    def __post_init__(self) -> None:
        self.scalars: dict[str, int] = {}
        self.arrays: dict[str, tuple[int, list[int]]] = {}

    def allocate_scalar(self, name: str) -> int:
        if name in self.scalars:
            return self.scalars[name]
        addr = self.next_addr
        self.scalars[name] = addr
        self.next_addr += 1
        return addr

    def allocate_array(self, name: str, dims: list[int]) -> int:
        if name in self.arrays:
            return self.arrays[name][0]
        total = 1
        for dim in dims:
            total *= dim
        base = self.next_addr
        self.arrays[name] = (base, dims)
        self.next_addr += total
        return base

    def addr_of_scalar(self, name: str) -> int:
        return self.scalars[name]

    def array_info(self, name: str) -> tuple[int, list[int]]:
        return self.arrays[name]

    @property
    def total_cells(self) -> int:
        return self.next_addr


@dataclass
class FrameLayout:
    """Layout relativo ao FP para um subprograma."""

    name: str
    kind: str
    param_offsets: dict[str, int] = field(default_factory=dict)
    local_offsets: dict[str, int] = field(default_factory=dict)
    local_array_offsets: dict[str, int] = field(default_factory=dict)
    result_slot: int = 0

    @property
    def local_slot_count(self) -> int:
        if not self.local_offsets:
            return 0
        return max(self.local_offsets.values())
