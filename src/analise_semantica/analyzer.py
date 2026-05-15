"""Analise semantica para o subconjunto de Fortran 77 suportado."""

from __future__ import annotations

import src.analise_sintatica.ast_nodes as ast
from src.config import config

from .checks import SemanticChecksMixin
from .declarations import DeclarationAnalyzerMixin
from .expressions import ExpressionAnalyzerMixin
from .statements import StatementAnalyzerMixin
from .symbols import SymbolTable


class SemanticAnalyzer(
    DeclarationAnalyzerMixin,
    StatementAnalyzerMixin,
    ExpressionAnalyzerMixin,
    SemanticChecksMixin,
):
    """Valida e anota a AST antes da geracao de IR."""

    def __init__(self):
        """Inicializa o estado reutilizável da análise semântica."""
        self.filename = "<stdin>"
        self.symbols = SymbolTable()
        self.callables = SymbolTable()
        self.initialized: set[str] = set()
        self.labels: dict[int, ast.Node] = {}
        self.current_function: ast.FunctionDef | None = None
        self.implicit_none = False
        self.implicit_typing = config.implicit_typing

    def analyze(self, program: ast.Program, filename: str = "<stdin>") -> ast.Program:
        """Executa a análise semântica completa e devolve a AST anotada."""
        self.filename = filename
        self.callables = SymbolTable()
        self._declare_subprogram_signatures(program)

        self._reset_scope(program.decls)
        self._declare_symbols(program.decls, self.symbols, allow_function_typing=True)
        self._collect_labels(program.stmts)

        program.decls = [self._visit_decl(decl) for decl in program.decls]
        program.stmts = self._visit_stmt_list(program.stmts)
        program.subprograms = [self._analyze_subprogram(subprogram) for subprogram in program.subprograms]

        setattr(program, "symbol_table", self.symbols)
        setattr(program, "callable_table", self.callables)
        setattr(program, "subprogram_map", {sub.name: sub for sub in program.subprograms})
        return program


def analyze(program: ast.Program, filename: str = "<stdin>") -> ast.Program:
    """Funcao de conveniencia para analise semantica."""

    return SemanticAnalyzer().analyze(program, filename=filename)
