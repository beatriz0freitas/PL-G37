"""Validação de instruções na análise semântica."""

from __future__ import annotations

import src.analise_sintatica.ast_nodes as ast

from .types import NUMERIC_TYPES


class StatementAnalyzerMixin:
    """Percorre e valida a lista de instruções da AST."""

    def _visit_stmt_list(self, stmts: list[ast.Node]) -> list[ast.Node]:
        return [self._visit_stmt(stmt) for stmt in stmts]

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
