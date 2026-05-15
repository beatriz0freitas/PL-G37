"""Analise semantica para o subconjunto de Fortran 77 suportado."""

from __future__ import annotations

from typing import Any

import src.analise_sintatica.ast_nodes as ast
from src.config import config
from src.errors import SemanticError, SourceLocation

from .intrinsics import INTRINSICS
from .symbols import Symbol, SymbolTable
from .types import NUMERIC_TYPES


REAL_LIKE_TYPES = {"REAL", "DOUBLE PRECISION"}


class SemanticAnalyzer:
    """Valida e anota a AST antes da geracao de IR."""

    def __init__(self):
        self.filename = "<stdin>"
        self.symbols = SymbolTable()
        self.callables = SymbolTable()
        self.initialized: set[str] = set()
        self.labels: dict[int, ast.Node] = {}
        self.current_function: ast.FunctionDef | None = None
        self.implicit_none = False
        self.implicit_typing = config.implicit_typing

    def analyze(self, program: ast.Program, filename: str = "<stdin>") -> ast.Program:
        self.filename = filename
        self.callables = SymbolTable()
        self._declare_subprogram_signatures(program)

        self.symbols = SymbolTable()
        self.initialized = set()
        self.labels = {}
        self.current_function = None
        self.implicit_none = self._scan_implicit_none(program.decls)
        self.implicit_typing = config.implicit_typing

        self._declare_symbols(program.decls, self.symbols, allow_function_typing=True)
        self._collect_labels(program.stmts)

        program.decls = [self._visit_decl(decl) for decl in program.decls]
        program.stmts = self._visit_stmt_list(program.stmts)
        program.subprograms = [self._analyze_subprogram(subprogram) for subprogram in program.subprograms]

        setattr(program, "symbol_table", self.symbols)
        setattr(program, "callable_table", self.callables)
        setattr(program, "subprogram_map", {sub.name: sub for sub in program.subprograms})
        return program

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

    def _analyze_subprogram(self, subprogram: ast.FunctionDef | ast.SubroutineDef) -> ast.Node:
        prev_symbols = self.symbols
        prev_initialized = self.initialized
        prev_labels = self.labels
        prev_function = self.current_function
        prev_implicit_none = self.implicit_none
        prev_implicit_typing = self.implicit_typing

        self.symbols = SymbolTable()
        self.initialized = set()
        self.labels = {}
        self.current_function = subprogram if isinstance(subprogram, ast.FunctionDef) else None
        self.implicit_none = self._scan_implicit_none(subprogram.decls)
        self.implicit_typing = config.implicit_typing

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

        self.symbols = prev_symbols
        self.initialized = prev_initialized
        self.labels = prev_labels
        self.current_function = prev_function
        self.implicit_none = prev_implicit_none
        self.implicit_typing = prev_implicit_typing
        return subprogram

    def _scan_implicit_none(self, decls: list[ast.Node]) -> bool:
        return any(isinstance(decl, ast.ImplicitNone) for decl in decls)

    def _declare_symbols(
        self,
        decls: list[ast.TypeDecl],
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
            if label is None:
                continue
            if label in self.labels:
                self._error(stmt.lineno, f"Label {label} declarado mais do que uma vez")
            self.labels[label] = stmt
            if isinstance(stmt, ast.IfStmt):
                self._collect_labels(stmt.then_stmts)
                self._collect_labels(stmt.else_stmts)

    def _visit_decl(self, decl: ast.TypeDecl) -> ast.TypeDecl:
        if isinstance(decl, ast.ImplicitNone):
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

    def _visit_stmt_list(self, stmts: list[ast.Node]) -> list[ast.Node]:
        rewritten: list[ast.Node] = []
        for stmt in stmts:
            rewritten.append(self._visit_stmt(stmt))
        return rewritten

    def _visit_stmt(self, stmt: ast.Node) -> ast.Node:
        if isinstance(stmt, ast.AssignStmt):
            return self._visit_assign(stmt)
        if isinstance(stmt, ast.IfStmt):
            return self._visit_if(stmt)
        if isinstance(stmt, ast.ArithIfStmt):
            return self._visit_arith_if(stmt)
        if isinstance(stmt, ast.DoStmt):
            return self._visit_do(stmt)
        if isinstance(stmt, ast.GotoStmt):
            return self._visit_goto(stmt)
        if isinstance(stmt, ast.ContinueStmt):
            return stmt
        if isinstance(stmt, ast.PrintStmt):
            return self._visit_print(stmt)
        if isinstance(stmt, ast.ReadStmt):
            return self._visit_read(stmt)
        if isinstance(stmt, ast.WriteStmt):
            return self._visit_write(stmt)
        if isinstance(stmt, ast.CallStmt):
            return self._visit_call_stmt(stmt)
        if isinstance(stmt, ast.StopStmt):
            return stmt
        if isinstance(stmt, ast.ReturnStmt):
            return self._visit_return(stmt)
        raise NotImplementedError(f"Análise semântica não implementada para {type(stmt).__name__}")

    def _visit_assign(self, stmt: ast.AssignStmt) -> ast.AssignStmt:
        target, target_type = self._rewrite_lvalue(stmt.target)
        value, value_type = self._rewrite_expr(stmt.value)
        self._ensure_assignable(target_type, value_type, stmt.lineno)
        stmt.target = target
        stmt.value = value
        self._mark_initialized(target.name)
        return stmt

    def _visit_if(self, stmt: ast.IfStmt) -> ast.IfStmt:
        condition, cond_type = self._rewrite_expr(stmt.condition)
        self._ensure_type(cond_type, "LOGICAL", stmt.lineno)
        stmt.condition = condition

        before = set(self.initialized)
        self.initialized = set(before)
        stmt.then_stmts = self._visit_stmt_list(stmt.then_stmts)
        then_after = set(self.initialized)

        self.initialized = set(before)
        stmt.else_stmts = self._visit_stmt_list(stmt.else_stmts)
        else_after = set(self.initialized)

        self.initialized = then_after & else_after if stmt.else_stmts else before
        return stmt

    def _visit_arith_if(self, stmt: ast.ArithIfStmt) -> ast.ArithIfStmt:
        expr, expr_type = self._rewrite_expr(stmt.expr)
        if expr_type not in NUMERIC_TYPES:
            self._error(stmt.lineno, f"IF aritmético exige expressão numérica, recebeu {expr_type}")
        stmt.expr = expr
        self._require_label(stmt.label_neg, stmt.lineno)
        self._require_label(stmt.label_zero, stmt.lineno)
        self._require_label(stmt.label_pos, stmt.lineno)
        return stmt

    def _visit_do(self, stmt: ast.DoStmt) -> ast.DoStmt:
        symbol = self._require_scalar(stmt.var, stmt.lineno)
        if symbol.kind != "scalar":
            self._error(stmt.lineno, f"Variável de controlo do DO tem de ser escalar: {stmt.var}")
        if symbol.type_name not in NUMERIC_TYPES:
            self._error(stmt.lineno, f"Variável de controlo do DO tem de ser numérica: {stmt.var}")

        stmt.start, start_type = self._rewrite_expr(stmt.start)
        stmt.end, end_type = self._rewrite_expr(stmt.end)
        if start_type not in NUMERIC_TYPES or end_type not in NUMERIC_TYPES:
            self._error(stmt.lineno, "Expressões de limite do DO têm de ser numéricas")
        if stmt.step is not None:
            stmt.step, step_type = self._rewrite_expr(stmt.step)
            if step_type not in NUMERIC_TYPES:
                self._error(stmt.lineno, "Expressão STEP do DO tem de ser numérica")

        target = self._require_label(stmt.label, stmt.lineno)
        if not isinstance(target, ast.ContinueStmt):
            self._error(stmt.lineno, f"DO {stmt.label} tem de terminar num CONTINUE com a mesma label")

        self._mark_initialized(stmt.var)
        return stmt

    def _visit_goto(self, stmt: ast.GotoStmt) -> ast.GotoStmt:
        self._require_label(stmt.label, stmt.lineno)
        return stmt

    def _visit_print(self, stmt: ast.PrintStmt) -> ast.PrintStmt:
        stmt.items = [self._rewrite_expr(item)[0] for item in stmt.items]
        return stmt

    def _visit_read(self, stmt: ast.ReadStmt) -> ast.ReadStmt:
        rewritten: list[ast.VarRef | ast.ArrayRef] = []
        for var in stmt.variables:
            lvalue, _ = self._rewrite_lvalue(var)
            rewritten.append(lvalue)
            self._mark_initialized(lvalue.name)
        stmt.variables = rewritten
        return stmt

    def _visit_write(self, stmt: ast.WriteStmt) -> ast.WriteStmt:
        if stmt.unit is not None:
            stmt.unit = self._rewrite_expr(stmt.unit)[0]
        if isinstance(stmt.fmt, ast.Node):
            stmt.fmt = self._rewrite_expr(stmt.fmt)[0]
        stmt.items = [self._rewrite_expr(item)[0] for item in stmt.items]
        return stmt

    def _visit_call_stmt(self, stmt: ast.CallStmt) -> ast.CallStmt:
        stmt.name = stmt.name.upper()
        symbol = self._require_callable(stmt.name, stmt.lineno)
        if symbol.kind != "subroutine":
            self._error(stmt.lineno, f"'{stmt.name}' não é uma subrotina")

        rewritten_args = [self._rewrite_expr(arg) for arg in stmt.args]
        self._check_callable_arity(symbol, len(rewritten_args), stmt.lineno)
        stmt.args = [arg for arg, _ in rewritten_args]
        return stmt

    def _visit_return(self, stmt: ast.ReturnStmt) -> ast.ReturnStmt:
        return stmt

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
            self._validate_array_indices(node.indices, symbol, node.lineno)
            node.indices = [self._rewrite_expr(idx)[0] for idx in node.indices]
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
        self._validate_array_indices(node.indices, symbol, node.lineno)
        node.indices = [self._rewrite_expr(idx)[0] for idx in node.indices]
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

    def _implicit_typing_enabled(self) -> bool:
        return self.implicit_typing and not self.implicit_none

    def _implicit_type(self, name: str) -> str:
        first = name.strip().upper()[:1]
        if "I" <= first <= "N":
            return "INTEGER"
        return "REAL"

    def _require_scalar(self, name: str, lineno: int) -> Symbol:
        symbol = self.symbols.lookup(name)
        if symbol is None and self._implicit_typing_enabled():
            symbol = self.symbols.declare_scalar(name, self._implicit_type(name), lineno, filename=self.filename)
        if symbol is None:
            self._error(lineno, f"Identificador '{name.upper()}' usado sem declaração")
        return symbol

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

    def _validate_array_indices(self, indices: list[Any], symbol: Symbol, lineno: int) -> None:
        if len(indices) != len(symbol.dimensions):
            self._error(
                lineno,
                f"Array '{symbol.name}' espera {len(symbol.dimensions)} índices, recebeu {len(indices)}",
            )
        for idx in indices:
            _, idx_type = self._rewrite_expr(idx)
            self._ensure_type(idx_type, "INTEGER", lineno)

    def _check_intrinsic_call(self, name: str, arg_types: list[str], lineno: int) -> str:
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
        return (
            isinstance(node, ast.UnaryOp)
            and node.op == "-"
            and isinstance(node.operand, ast.IntLit)
        )

    def _check_callable_arity(self, symbol: Symbol, arity: int, lineno: int) -> None:
        if symbol.arity is not None and symbol.arity != arity:
            kind_name = "Função" if symbol.kind == "function" else "Subrotina"
            self._error(lineno, f"{kind_name} '{symbol.name}' espera {symbol.arity} argumentos, recebeu {arity}")

    def _require_callable(self, name: str, lineno: int) -> Symbol:
        symbol = self.callables.lookup(name)
        if symbol is None:
            self._error(lineno, f"Subprograma '{name}' não declarado")
        return symbol

    def _const_array_dim(self, node: Any, name: str, lineno: int) -> int:
        rewritten, dtype = self._rewrite_expr(node)
        if dtype != "INTEGER" or not isinstance(rewritten, ast.IntLit):
            self._error(lineno, f"Dimensão de array '{name}' tem de ser um inteiro constante")
        if rewritten.value <= 0:
            self._error(lineno, f"Dimensão de array '{name}' tem de ser positiva")
        return rewritten.value

    def _ensure_assignable(self, target_type: str, value_type: str, lineno: int) -> None:
        if target_type == value_type:
            return
        if target_type in NUMERIC_TYPES and value_type in NUMERIC_TYPES:
            return
        self._error(lineno, f"Atribuição inválida: esperado {target_type}, recebido {value_type}")

    def _ensure_type(self, actual: str, expected: str, lineno: int) -> None:
        if actual != expected:
            self._error(lineno, f"Tipo inválido: esperado {expected}, recebido {actual}")

    def _mark_initialized(self, name: str) -> None:
        self.initialized.add(name.upper())

    def _require_label(self, label: int, lineno: int) -> ast.Node:
        target = self.labels.get(label)
        if target is None:
            self._error(lineno, f"Label {label} não definida")
        return target

    def _annotate(self, node: ast.Node, sem_type: str, symbol: Symbol | None = None) -> None:
        setattr(node, "sem_type", sem_type)
        if symbol is not None:
            setattr(node, "symbol", symbol)

    def _error(self, lineno: int, message: str) -> None:
        raise SemanticError(message, SourceLocation(self.filename, lineno, 1))


def analyze(program: ast.Program, filename: str = "<stdin>") -> ast.Program:
    """Funcao de conveniencia para analise semantica."""

    return SemanticAnalyzer().analyze(program, filename=filename)
