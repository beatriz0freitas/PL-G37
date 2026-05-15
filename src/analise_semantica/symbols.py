"""Tabela de simbolos usada pela analise semantica."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.errors import SemanticError, SourceLocation


VALID_KINDS = {"scalar", "array", "function", "subroutine", "intrinsic"}


@dataclass
class Symbol:
    """Informacao semantica associada a um identificador."""

    name: str
    kind: str
    type_name: str
    dimensions: tuple[int, ...] = field(default_factory=tuple)
    arity: int | None = None
    lineno: int = 0

    def __post_init__(self) -> None:
        """Normaliza campos textuais e valida a categoria do símbolo."""
        self.name = self.name.upper()
        self.kind = self.kind.lower()
        self.type_name = self.type_name.upper()
        self.dimensions = tuple(self.dimensions)
        if self.kind not in VALID_KINDS:
            raise ValueError(f"Tipo de simbolo invalido: {self.kind}")


class SymbolTable:
    """Tabela simples de simbolos ao nivel do programa."""

    def __init__(self):
        """Cria uma tabela vazia indexada por identificador normalizado."""
        self._table: dict[str, Symbol] = {}

    def declare(self, symbol: Symbol, filename: str = "<stdin>") -> Symbol:
        """Regista um simbolo. Rejeita declaracoes duplicadas."""

        if symbol.name in self._table:
            prev = self._table[symbol.name]
            raise SemanticError(
                f"Identificador '{symbol.name}' já declarado",
                SourceLocation(filename, symbol.lineno or prev.lineno, 1),
            )
        self._table[symbol.name] = symbol
        return symbol

    def declare_scalar(self, name: str, type_name: str, lineno: int, filename: str = "<stdin>") -> Symbol:
        """Declara uma variável escalar."""
        return self.declare(
            Symbol(name=name, kind="scalar", type_name=type_name, lineno=lineno),
            filename=filename,
        )

    def declare_array(
        self,
        name: str,
        type_name: str,
        dimensions: list[int] | tuple[int, ...],
        lineno: int,
        filename: str = "<stdin>",
    ) -> Symbol:
        """Declara um array com dimensões já validadas."""
        return self.declare(
            Symbol(
                name=name,
                kind="array",
                type_name=type_name,
                dimensions=tuple(dimensions),
                lineno=lineno,
            ),
            filename=filename,
        )

    def declare_function(
        self,
        name: str,
        type_name: str,
        arity: int,
        lineno: int,
        filename: str = "<stdin>",
    ) -> Symbol:
        """Declara a assinatura de uma função externa."""
        return self.declare(
            Symbol(
                name=name,
                kind="function",
                type_name=type_name,
                arity=arity,
                lineno=lineno,
            ),
            filename=filename,
        )

    def declare_subroutine(
        self,
        name: str,
        arity: int,
        lineno: int,
        filename: str = "<stdin>",
    ) -> Symbol:
        """Declara a assinatura de uma subrotina externa."""
        return self.declare(
            Symbol(
                name=name,
                kind="subroutine",
                type_name="SUBROUTINE",
                arity=arity,
                lineno=lineno,
            ),
            filename=filename,
        )

    def lookup(self, name: str) -> Symbol | None:
        """Procura um identificador sem produzir erro se estiver ausente."""
        return self._table.get(name.upper())

    def require(self, name: str, lineno: int, filename: str = "<stdin>") -> Symbol:
        """Procura um identificador e falha se ele não tiver sido declarado."""
        symbol = self.lookup(name)
        if symbol is None:
            raise SemanticError(
                f"Identificador '{name.upper()}' usado sem declaração",
                SourceLocation(filename, lineno, 1),
            )
        return symbol

    def values(self):
        """Itera os símbolos registados."""
        return self._table.values()

    def items(self):
        """Itera pares (nome, símbolo) registados."""
        return self._table.items()

    def __len__(self) -> int:
        """Devolve o número de símbolos registados."""
        return len(self._table)
