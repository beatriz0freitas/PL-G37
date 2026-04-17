"""Instrucoes da representacao intermedia (IR)."""

from dataclasses import dataclass
from typing import Any, Optional

from .operadores import IRArrayRef, Label


class IRInstr:
    """Classe base para instrucoes IR."""


@dataclass
class IRAssign(IRInstr):
    """Atribuicao simples: dest = src."""

    dest: Any
    src: Any

    def __str__(self) -> str:
        return f"{self.dest} = {self.src}"


@dataclass
class IRUnaryOp(IRInstr):
    """Operacao unaria: dest = op operand."""

    op: str
    dest: Any
    operand: Any

    def __str__(self) -> str:
        return f"{self.dest} = {self.op} {self.operand}"


@dataclass
class IROp(IRInstr):
    """Operacao binaria: dest = left op right."""

    op: str
    dest: Any
    left: Any
    right: Any

    def __str__(self) -> str:
        return f"{self.dest} = {self.left} {self.op} {self.right}"


@dataclass
class IRLabelInstr(IRInstr):
    """Marcador de label: Lx:."""

    label: Label

    def __str__(self) -> str:
        return f"{self.label}:"


@dataclass
class IRJump(IRInstr):
    """Salto incondicional: GOTO label."""

    label: Label

    def __str__(self) -> str:
        return f"GOTO {self.label}"


@dataclass
class IRCJump(IRInstr):
    """Salto condicional: IF cond THEN true_label ELSE false_label."""

    cond: Any
    true_label: Label
    false_label: Label

    def __str__(self) -> str:
        return f"IF {self.cond} GOTO {self.true_label} ELSE GOTO {self.false_label}"


@dataclass
class IRCall(IRInstr):
    """Chamada de funcao/subrotina; opcionalmente guarda retorno em dest."""

    name: str
    args: list[Any]
    dest: Optional[Any] = None

    def __str__(self) -> str:
        rendered_args = ", ".join(str(a) for a in self.args)
        if self.dest is None:
            return f"CALL {self.name}({rendered_args})"
        return f"{self.dest} = CALL {self.name}({rendered_args})"


@dataclass
class IRLoadArray(IRInstr):
    """Leitura de array: dest = A[idx...]."""

    dest: Any
    name: str
    indices: list[Any]

    def __str__(self) -> str:
        ref = IRArrayRef(self.name, self.indices)
        return f"{self.dest} = {ref}"


@dataclass
class IRStoreArray(IRInstr):
    """Escrita em array: A[idx...] = src."""

    name: str
    indices: list[Any]
    src: Any

    def __str__(self) -> str:
        ref = IRArrayRef(self.name, self.indices)
        return f"{ref} = {self.src}"


@dataclass
class IRPrint(IRInstr):
    """Output textual."""

    args: list[Any]

    def __str__(self) -> str:
        rendered_args = ", ".join(str(a) for a in self.args)
        return f"PRINT {rendered_args}"


@dataclass
class IRRead(IRInstr):
    """Input para variaveis/alvos."""

    args: list[Any]

    def __str__(self) -> str:
        rendered_args = ", ".join(str(a) for a in self.args)
        return f"READ {rendered_args}"


@dataclass
class IRWrite(IRInstr):
    """WRITE(unit, fmt) items."""

    unit: Any
    fmt: Any
    items: list[Any]

    def __str__(self) -> str:
        rendered_items = ", ".join(str(a) for a in self.items)
        return f"WRITE ({self.unit}, {self.fmt}) {rendered_items}"


@dataclass
class IRStop(IRInstr):
    """Terminacao de programa."""

    def __str__(self) -> str:
        return "STOP"


@dataclass
class IRReturn(IRInstr):
    """Retorno de subprograma."""

    def __str__(self) -> str:
        return "RETURN"
