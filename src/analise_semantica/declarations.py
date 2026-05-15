"""Declarações, labels e escopos da análise semântica."""

from __future__ import annotations

from dataclasses import dataclass

import src.analise_sintatica.ast_nodes as ast
from src.config import config

from .symbols import SymbolTable


@dataclass
class _ScopeState:
    symbols: SymbolTable
    initialized: set[str]
    labels: dict[int, ast.Node]
    current_function: ast.FunctionDef | None
    implicit_none: bool
    implicit_typing: bool


class DeclarationAnalyzerMixin:
    """Responsável por escopos, símbolos declarados e normalização de decls."""

    def _declare_subprogram_signatures(self, program: ast.Program) -> None:
        for subprogram in program.subprograms:
            if isinstance(subprogram, ast.FunctionDef):
                self.callables.declare_function(
                    subprogram.name,
                    subprogram.return_type,
                    len(subprogram.params),
                    subprogram.lineno,
                    filename=self.filename,
                )
                continue

            if isinstance(subprogram, ast.SubroutineDef):
                self.callables.declare_subroutine(
                    subprogram.name,
                    len(subprogram.params),
                    subprogram.lineno,
                    filename=self.filename,
                )
                continue

            raise TypeError(f"Subprograma nao suportado: {type(subprogram).__name__}")

    def _capture_scope(self) -> _ScopeState:
        return _ScopeState(
            symbols=self.symbols,
            initialized=self.initialized,
            labels=self.labels,
            current_function=self.current_function,
            implicit_none=self.implicit_none,
            implicit_typing=self.implicit_typing,
        )

    def _restore_scope(self, state: _ScopeState) -> None:
        self.symbols = state.symbols
        self.initialized = state.initialized
        self.labels = state.labels
        self.current_function = state.current_function
        self.implicit_none = state.implicit_none
        self.implicit_typing = state.implicit_typing

    def _reset_scope(self, decls: list[ast.Node], current_function: ast.FunctionDef | None = None) -> None:
        self.symbols = SymbolTable()
        self.initialized = set()
        self.labels = {}
        self.current_function = current_function
        self.implicit_none = self._scan_implicit_none(decls)
        self.implicit_typing = config.implicit_typing

    def _analyze_subprogram(self, subprogram: ast.FunctionDef | ast.SubroutineDef) -> ast.Node:
        previous = self._capture_scope()
        current_function = subprogram if isinstance(subprogram, ast.FunctionDef) else None
        self._reset_scope(subprogram.decls, current_function=current_function)

        if isinstance(subprogram, ast.FunctionDef):
            subprogram.return_type = subprogram.return_type.upper()
            self.symbols.declare_scalar(
                subprogram.name,
                subprogram.return_type,
                subprogram.lineno,
                filename=self.filename,
            )
            subprogram.result_name = subprogram.name.upper()

        subprogram.name = subprogram.name.upper()
        subprogram.params = [param.upper() for param in subprogram.params]
        self._declare_symbols(subprogram.decls, self.symbols)
        self._declare_parameters(subprogram)
        self._collect_labels(subprogram.stmts)

        subprogram.decls = [self._visit_decl(decl) for decl in subprogram.decls]
        subprogram.stmts = self._visit_stmt_list(subprogram.stmts)
        setattr(subprogram, "symbol_table", self.symbols)

        self._restore_scope(previous)
        return subprogram

    def _scan_implicit_none(self, decls: list[ast.Node]) -> bool:
        return any(isinstance(decl, ast.ImplicitNone) for decl in decls)

    def _declare_symbols(
        self,
        decls: list[ast.Node],
        target: SymbolTable,
        *,
        allow_function_typing: bool = False,
    ) -> None:
        for decl in decls:
            if isinstance(decl, ast.ImplicitNone):
                continue
            if not isinstance(decl, ast.TypeDecl):
                continue
            typename = decl.typename.upper()
            for var in decl.variables:
                if isinstance(var, str):
                    name = var.upper()
                    callable_symbol = self.callables.lookup(name)
                    if allow_function_typing and callable_symbol is not None and callable_symbol.kind == "function":
                        if callable_symbol.type_name != typename:
                            self._error(decl.lineno, f"Tipo incompatível para função '{name}'")
                        continue
                    target.declare_scalar(name, typename, decl.lineno, filename=self.filename)
                    continue
                if isinstance(var, ast.ArrayDecl):
                    dims = [self._const_array_dim(dim, var.name, var.lineno) for dim in var.dimensions]
                    target.declare_array(var.name, typename, dims, var.lineno, filename=self.filename)
                    continue
                raise TypeError(f"Declaração não suportada: {type(var).__name__}")

    def _declare_parameters(self, subprogram: ast.FunctionDef | ast.SubroutineDef) -> None:
        for param in subprogram.params:
            symbol = self.symbols.lookup(param)
            if symbol is None:
                if self._implicit_typing_enabled():
                    typename = self._implicit_type(param)
                    symbol = self.symbols.declare_scalar(param, typename, subprogram.lineno, filename=self.filename)
                else:
                    self._error(subprogram.lineno, f"Parâmetro '{param}' usado sem declaração de tipo")
            if symbol.kind != "scalar":
                self._error(subprogram.lineno, f"Parâmetro '{param}' tem de ser escalar")
            self._mark_initialized(param)

    def _collect_labels(self, stmts: list[ast.Node]) -> None:
        for stmt in stmts:
            label = getattr(stmt, "source_label", None)
            if label is not None:
                if label in self.labels:
                    self._error(stmt.lineno, f"Label {label} declarado mais do que uma vez")
                self.labels[label] = stmt
            if isinstance(stmt, ast.IfStmt):
                self._collect_labels(stmt.then_stmts)
                self._collect_labels(stmt.else_stmts)

    def _visit_decl(self, decl: ast.Node) -> ast.Node:
        if isinstance(decl, ast.ImplicitNone):
            return decl
        if not isinstance(decl, ast.TypeDecl):
            return decl

        decl.typename = decl.typename.upper()
        normalized: list[str | ast.ArrayDecl] = []
        for var in decl.variables:
            if isinstance(var, str):
                normalized.append(var.upper())
                continue
            var.name = var.name.upper()
            var.dimensions = [self._rewrite_expr(dim)[0] for dim in var.dimensions]
            normalized.append(var)
        decl.variables = normalized
        return decl
