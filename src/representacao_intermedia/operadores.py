"""operadores e estruturas auxiliares da representacao intermedia."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Temp:
    """Variavel temporaria gerada pelo compilador (t1, t2, ...)."""

    id: int

    def __str__(self) -> str:
        return f"t{self.id}"


@dataclass(frozen=True)
class Label:
    """Destino de salto (L1, L2, F10, ...)."""

    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class IRArrayRef:
    """Representa uma referencia indexada a array na IR."""

    name: str
    indices: list[Any]

    def __str__(self) -> str:
        inner = ", ".join(str(i) for i in self.indices)
        return f"{self.name}[{inner}]"


@dataclass
class LoopContext:
    """Contexto de um DO ativo para fechar no label terminal."""

    target_label: int
    var_name: str
    step_value: Any
    test_label: Label
    end_label: Label
