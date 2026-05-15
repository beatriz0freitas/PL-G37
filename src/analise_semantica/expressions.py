"""Reescrita e validação de expressões na análise semântica."""

from __future__ import annotations

from typing import Any

import src.analise_sintatica.ast_nodes as ast

from .intrinsics import INTRINSICS
from .symbols import Symbol
from .types import NUMERIC_TYPES, REAL_LIKE_TYPES


class ExpressionAnalyzerMixin:
    """Resolve identificadores, chamadas, arrays e tipos de expressões."""

    def _rewrite_lvalue(self, node: ast.Node) -> tuple[ast.VarRef | ast.ArrayRef, str]:
        if isinstance(node, ast.VarRef):
            symbol = self._require_scalar(node.name, node.lineno)
            node.name = symbol.name
            if symbol.kind != "scalar":
                self._error(node.lineno, f"'{node.name}' não é uma variável escalar")
            self._annotate(node, symbol.type_name, symbol)
            return node, symbol.type_name

        if isinstance(node, ast.ArrayRef):
            symbol = self.symbols.require(node.name, node.lineno, filename=self.filename)
            node.name = symbol.name
            if symbol.kind != "array":
                self._error(node.lineno, f"'{node.name}' não é um array")
            node.indices = self._rewrite_array_indices(node, symbol)
            self._annotate(node, symbol.type_name, symbol)
            return node, symbol.type_name

        self._error(getattr(node, "lineno", 0), f"Lvalue inválido: {type(node).__name__}")

    def _rewrite_expr(self, node: Any) -> tuple[Any, str]:
        if isinstance(node, ast.IntLit):
            self._annotate(node, "INTEGER")
            return node, "INTEGER"
        if isinstance(node, ast.RealLit):
            self._annotate(node, "REAL")
            return node, "REAL"
        if isinstance(node, ast.BoolLit):
            self._annotate(node, "LOGICAL")
            return node, "LOGICAL"
        if isinstance(node, ast.StringLit):
            self._annotate(node, "CHARACTER")
            return node, "CHARACTER"
        if isinstance(node, ast.VarRef):
            return self._rewrite_var_expr(node)
        if isinstance(node, ast.ArrayRef):
            return self._rewrite_array_expr(node)
        if isinstance(node, ast.CallExpr):
            return self._rewrite_call_expr(node)
        if isinstance(node, ast.UnaryOp):
            return self._rewrite_unary(node)
        if isinstance(node, ast.BinOp):
            return self._rewrite_binop(node)
        return node, getattr(node, "sem_type")

    def _rewrite_var_expr(self, node: ast.VarRef) -> tuple[ast.VarRef, str]:
        symbol = self._require_scalar(node.name, node.lineno)
        node.name = symbol.name
        if symbol.kind == "array":
            self._error(node.lineno, f"Array '{node.name}' usado sem índices")
        if symbol.kind != "scalar":
            self._error(node.lineno, f"'{node.name}' não pode ser usado como expressão escalar")
        if node.name not in self.initialized:
            self._error(node.lineno, f"Variável '{node.name}' usada antes de inicialização")
        self._annotate(node, symbol.type_name, symbol)
        return node, symbol.type_name

    def _rewrite_array_expr(self, node: ast.ArrayRef) -> tuple[ast.ArrayRef, str]:
        symbol = self.symbols.require(node.name, node.lineno, filename=self.filename)
        node.name = symbol.name
        if symbol.kind != "array":
            self._error(node.lineno, f"'{node.name}' não é um array")
        if node.name not in self.initialized:
            self._error(node.lineno, f"Array '{node.name}' usado antes de inicialização")
        node.indices = self._rewrite_array_indices(node, symbol)
        self._annotate(node, symbol.type_name, symbol)
        return node, symbol.type_name

    def _rewrite_call_expr(self, node: ast.CallExpr) -> tuple[ast.Node, str]:
        name = node.name.upper()
        symbol = self.symbols.lookup(name)

        if symbol is not None and symbol.kind == "array":
            array_node = ast.ArrayRef(name=name, indices=node.args, lineno=node.lineno)
            return self._rewrite_array_expr(array_node)

        if symbol is not None and symbol.kind == "scalar":
            self._error(node.lineno, f"'{name}' é uma variável escalar, não uma função")

        callable_symbol = self.callables.lookup(name)
        if callable_symbol is not None:
            if callable_symbol.kind != "function":
                self._error(node.lineno, f"'{name}' não é uma função")
            rewritten_args = [self._rewrite_expr(arg) for arg in node.args]
            self._check_callable_arity(callable_symbol, len(rewritten_args), node.lineno)
            node.name = name
            node.args = [arg for arg, _ in rewritten_args]
            self._annotate(node, callable_symbol.type_name, callable_symbol)
            return node, callable_symbol.type_name

        spec = INTRINSICS.get(name)
        if spec is None:
            self._error(node.lineno, f"Função '{name}' não declarada nem intrínseca suportada")

        rewritten_args = [self._rewrite_expr(arg) for arg in node.args]
        if spec.arity is not None and len(rewritten_args) != spec.arity:
            self._error(node.lineno, f"Função '{name}' espera {spec.arity} argumentos, recebeu {len(rewritten_args)}")

        arg_nodes = [arg for arg, _ in rewritten_args]
        arg_types = [typ for _, typ in rewritten_args]
        result_type = self._check_intrinsic_call(name, arg_types, node.lineno)

        node.name = name
        node.args = arg_nodes
        self._annotate(node, result_type, Symbol(name=name, kind="intrinsic", type_name=result_type, arity=len(arg_nodes)))
        return node, result_type

    def _rewrite_unary(self, node: ast.UnaryOp) -> tuple[ast.UnaryOp, str]:
        operand, operand_type = self._rewrite_expr(node.operand)
        node.operand = operand
        op = node.op.upper()
        if op == ".NOT.":
            self._ensure_type(operand_type, "LOGICAL", node.lineno)
            self._annotate(node, "LOGICAL")
            return node, "LOGICAL"
        if op == "-":
            if operand_type not in NUMERIC_TYPES:
                self._error(node.lineno, f"Operador unário '-' exige operando numérico, recebeu {operand_type}")
            self._annotate(node, operand_type)
            return node, operand_type
        self._error(node.lineno, f"Operador unário não suportado: {node.op}")

    def _rewrite_binop(self, node: ast.BinOp) -> tuple[ast.BinOp, str]:
        left, left_type = self._rewrite_expr(node.left)
        right, right_type = self._rewrite_expr(node.right)
        node.left = left
        node.right = right
        op = node.op.upper()

        if op == "**":
            if left_type != "INTEGER" or right_type != "INTEGER":
                self._error(node.lineno, "Operador '**' suporta apenas base e expoente INTEGER")
            if self._is_negative_int_literal(right):
                self._error(node.lineno, "Operador '**' não suporta expoentes negativos")
            self._annotate(node, "INTEGER")
            return node, "INTEGER"

        if op in {"+", "-", "*", "/"}:
            if left_type not in NUMERIC_TYPES or right_type not in NUMERIC_TYPES:
                self._error(node.lineno, f"Operador '{node.op}' exige operandos numéricos")
            result_type = "REAL" if {left_type, right_type} & REAL_LIKE_TYPES else "INTEGER"
            self._annotate(node, result_type)
            return node, result_type

        if op in {".EQ.", ".NE.", ".LT.", ".LE.", ".GT.", ".GE."}:
            if left_type not in NUMERIC_TYPES or right_type not in NUMERIC_TYPES:
                self._error(node.lineno, f"Operador relacional '{node.op}' exige operandos numéricos")
            self._annotate(node, "LOGICAL")
            return node, "LOGICAL"

        if op in {".AND.", ".OR.", ".EQV.", ".NEQV."}:
            self._ensure_type(left_type, "LOGICAL", node.lineno)
            self._ensure_type(right_type, "LOGICAL", node.lineno)
            self._annotate(node, "LOGICAL")
            return node, "LOGICAL"

        if op == "//":
            self._ensure_type(left_type, "CHARACTER", node.lineno)
            self._ensure_type(right_type, "CHARACTER", node.lineno)
            self._annotate(node, "CHARACTER")
            return node, "CHARACTER"

        self._error(node.lineno, f"Operador binário não suportado: {node.op}")

    def _rewrite_array_indices(self, node: ast.ArrayRef, symbol: Symbol) -> list[Any]:
        if len(node.indices) != len(symbol.dimensions):
            self._error(
                node.lineno,
                f"Array '{symbol.name}' espera {len(symbol.dimensions)} índices, recebeu {len(node.indices)}",
            )

        rewritten_indices = []
        for idx in node.indices:
            rewritten, idx_type = self._rewrite_expr(idx)
            self._ensure_type(idx_type, "INTEGER", node.lineno)
            rewritten_indices.append(rewritten)
        return rewritten_indices
