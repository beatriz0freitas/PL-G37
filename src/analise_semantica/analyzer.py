"""Analise semantica para o subconjunto de Fortran 77 suportado."""

from __future__ import annotations

import src.analise_sintatica.ast_nodes as ast
from src.config import config
from src.errors import SemanticError

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
        self.source_lines: list[str] = []

    def analyze(self, program: ast.Program, filename: str = "<stdin>") -> ast.Program:
        """Executa a análise semântica completa e devolve a AST anotada."""
        self.filename = filename
        self.source_lines = getattr(program, "_source_lines", [])
        try:
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
        except SemanticError as err:
            if err.location and err.source_line is None and 1 <= err.location.line <= len(self.source_lines):
                err.source_line = self.source_lines[err.location.line - 1]
            raise


def analyze(program: ast.Program, filename: str = "<stdin>") -> ast.Program:
    """Funcao de conveniencia para analise semantica."""

    return SemanticAnalyzer().analyze(program, filename=filename)
