"""Validações e utilitários transversais da análise semântica."""

from __future__ import annotations

from typing import Any

import src.analise_sintatica.ast_nodes as ast
from src.errors import SemanticError, SourceLocation

from .symbols import Symbol
from .types import NUMERIC_TYPES, REAL_LIKE_TYPES


class SemanticChecksMixin:
    """Helpers pequenos partilhados pelas fases da análise semântica."""

    def _implicit_typing_enabled(self) -> bool:
        """Indica se a tipagem implícita Fortran pode ser usada no escopo atual."""
        return self.implicit_typing and not self.implicit_none

    def _implicit_type(self, name: str) -> str:
        """Calcula o tipo implícito Fortran 77 para um identificador."""
        first = name.strip().upper()[:1]
        if "I" <= first <= "N":
            return "INTEGER"
        return "REAL"

    def _require_scalar(self, name: str, lineno: int) -> Symbol:
        """Obtém um símbolo escalar, declarando-o implicitamente quando permitido."""
        symbol = self.symbols.lookup(name)
        if symbol is None and self._implicit_typing_enabled():
            symbol = self.symbols.declare_scalar(name, self._implicit_type(name), lineno, filename=self.filename)
        if symbol is None:
            self._error(lineno, f"Identificador '{name.upper()}' usado sem declaração")
        return symbol

    def _check_intrinsic_call(self, name: str, arg_types: list[str], lineno: int) -> str:
        """Valida uma chamada intrínseca suportada e devolve o tipo resultante."""
        if name == "MOD":
            if arg_types != ["INTEGER", "INTEGER"]:
                self._error(lineno, "MOD exige dois argumentos INTEGER")
            return "INTEGER"

        if name in {"INT", "REAL", "FLOAT", "ABS", "SQRT"}:
            if len(arg_types) != 1 or arg_types[0] not in NUMERIC_TYPES:
                self._error(lineno, f"{name} exige um argumento numérico")
            if name == "INT":
                return "INTEGER"
            if name in {"REAL", "FLOAT", "SQRT"}:
                return "REAL"
            return arg_types[0]

        if name in {"MAX", "MIN"}:
            if len(arg_types) != 2 or any(arg not in NUMERIC_TYPES for arg in arg_types):
                self._error(lineno, f"{name} exige dois argumentos numéricos")
            return "REAL" if set(arg_types) & REAL_LIKE_TYPES else "INTEGER"

        self._error(lineno, f"Intrínseca não suportada: {name}")

    def _is_negative_int_literal(self, node: ast.Node) -> bool:
        """Reconhece o caso especial de literal inteiro negativo em potência."""
        return (
            isinstance(node, ast.UnaryOp)
            and node.op == "-"
            and isinstance(node.operand, ast.IntLit)
        )

    def _check_callable_arity(self, symbol: Symbol, arity: int, lineno: int) -> None:
        """Confirma que uma função/subrotina recebe o número esperado de argumentos."""
        if symbol.arity is not None and symbol.arity != arity:
            kind_name = "Função" if symbol.kind == "function" else "Subrotina"
            self._error(lineno, f"{kind_name} '{symbol.name}' espera {symbol.arity} argumentos, recebeu {arity}")

    def _require_callable(self, name: str, lineno: int) -> Symbol:
        """Procura uma função/subrotina declarada ou falha com erro semântico."""
        symbol = self.callables.lookup(name)
        if symbol is None:
            self._error(lineno, f"Subprograma '{name}' não declarado")
        return symbol

    def _const_array_dim(self, node: Any, name: str, lineno: int) -> int:
        """Valida uma dimensão de array e devolve o valor inteiro constante."""
        rewritten, dtype = self._rewrite_expr(node)
        if dtype != "INTEGER" or not isinstance(rewritten, ast.IntLit):
            self._error(lineno, f"Dimensão de array '{name}' tem de ser um inteiro constante")
        if rewritten.value <= 0:
            self._error(lineno, f"Dimensão de array '{name}' tem de ser positiva")
        return rewritten.value

    def _ensure_assignable(self, target_type: str, value_type: str, lineno: int) -> None:
        """Garante que um valor pode ser atribuído a um alvo do tipo indicado."""
        if target_type == value_type:
            return
        if target_type in NUMERIC_TYPES and value_type in NUMERIC_TYPES:
            return
        self._error(lineno, f"Atribuição inválida: esperado {target_type}, recebido {value_type}")

    def _ensure_type(self, actual: str, expected: str, lineno: int) -> None:
        """Valida igualdade exata entre tipo recebido e tipo esperado."""
        if actual != expected:
            self._error(lineno, f"Tipo inválido: esperado {expected}, recebido {actual}")

    def _mark_initialized(self, name: str) -> None:
        """Marca um identificador como inicializado no escopo atual."""
        self.initialized.add(name.upper())

    def _require_label(self, label: int, lineno: int) -> ast.Node:
        """Resolve uma label numérica já recolhida ou emite erro semântico."""
        target = self.labels.get(label)
        if target is None:
            self._error(lineno, f"Label {label} não definida")
        return target

    def _annotate(self, node: ast.Node, sem_type: str, symbol: Symbol | None = None) -> None:
        """Anexa tipo semântico e, opcionalmente, símbolo ao nó da AST."""
        setattr(node, "sem_type", sem_type)
        if symbol is not None:
            setattr(node, "symbol", symbol)

    def _error(self, lineno: int, message: str) -> None:
        """Lança um SemanticError com localização uniforme."""
        source_line = None
        if 1 <= lineno <= len(self.source_lines):
            source_line = self.source_lines[lineno - 1]
        raise SemanticError(
            message,
            SourceLocation(self.filename, lineno, 1),
            source_line=source_line,
        )
