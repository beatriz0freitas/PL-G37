"""Gerador AST -> IR para Fortran 77."""

from typing import Any

import src.analise_sintatica.ast_nodes as ast

from .instrucoes import (
    IRAssign,
    IRCJump,
    IRCall,
    IRInstr,
    IRJump,
    IRLabelInstr,
    IRLoadArray,
    IROp,
    IRPrint,
    IRProcBegin,
    IRProcEnd,
    IRRead,
    IRReturn,
    IRStop,
    IRStoreArray,
    IRUnaryOp,
    IRWrite,
)
from .operadores import IRArrayRef, IRStringLit, Label, LoopContext, Temp


class IRGenerator:
    """Gera codigo intermedio a partir da AST."""

    def __init__(self):
        """Inicializa contadores e pilhas usados durante a geração de IR."""
        self.instructions: list[IRInstr] = []
        self._temp_count = 0
        self._label_count = 0
        self._numeric_labels: dict[int, Label] = {}
        self._loop_stack: list[LoopContext] = []

    def new_temp(self) -> Temp:
        """Cria um novo temporário IR."""
        self._temp_count += 1
        return Temp(self._temp_count)

    def new_label(self, prefix: str = "L") -> Label:
        """Cria uma nova label interna com o prefixo indicado."""
        self._label_count += 1
        return Label(f"{prefix}{self._label_count}")

    def emit(self, instr: IRInstr) -> None:
        """Acrescenta uma instrução ao programa IR corrente."""
        self.instructions.append(instr)

    def _label_for_number(self, num: int) -> Label:
        """Mapeia uma label numérica Fortran para uma label IR estável."""
        if num not in self._numeric_labels:
            self._numeric_labels[num] = Label(f"F{num}")
        return self._numeric_labels[num]

    def _normalize_binop(self, op: str) -> str:
        """Converte operadores Fortran para a forma usada pela IR."""
        raw = op.upper()
        mapping = {
            ".EQ.": "==",
            ".NE.": "!=",
            ".LT.": "<",
            ".LE.": "<=",
            ".GT.": ">",
            ".GE.": ">=",
            ".AND.": "AND",
            ".OR.": "OR",
            ".EQV.": "EQV",
            ".NEQV.": "NEQV",
            "//": "CONCAT",
        }
        return mapping.get(raw, op)

    def _normalize_unary(self, op: str) -> str:
        """Converte operadores unários Fortran para a forma da IR."""
        raw = op.upper()
        if raw == ".NOT.":
            return "NOT"
        if raw == "-":
            return "NEG"
        return op

    def _emit_source_label_if_any(self, stmt: Any) -> None:
        """Emite label IR antes de uma instrução labelada no fonte."""
        source_label = getattr(stmt, "source_label", None)
        if source_label is not None:
            self.emit(IRLabelInstr(self._label_for_number(source_label)))

    def _visit_stmt_sequence(self, stmts: list[Any]) -> None:
        """Gera IR para uma lista de instruções, preservando labels."""
        for stmt in stmts:
            if not isinstance(stmt, ast.ContinueStmt):
                self._emit_source_label_if_any(stmt)
            self.generate(stmt)

    def generate(self, node: Any):
        """Despacha um nó AST para o método visit_* correspondente."""
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Any):
        """Falha quando não existe tradução IR para um tipo de nó AST."""
        raise NotImplementedError(f"Geracao de IR nao implementada para: {type(node).__name__}")

    def visit_Program(self, node: ast.Program) -> list[IRInstr]:
        """Gera IR do programa principal e depois dos subprogramas."""
        self._visit_stmt_sequence(node.stmts)
        if not self.instructions or not isinstance(self.instructions[-1], IRStop):
            self.emit(IRStop())

        for subprogram in node.subprograms:
            self.generate(subprogram)

        if self._loop_stack:
            pending = ", ".join(str(ctx.target_label) for ctx in self._loop_stack)
            raise ValueError(f"DO sem label terminal CONTINUE para label(s): {pending}")
        return self.instructions

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Gera marcadores e corpo IR de uma função externa."""
        self.emit(
            IRProcBegin(
                name=node.name,
                params=node.params,
                kind="function",
                result_name=getattr(node, "result_name", node.name),
            )
        )
        self._visit_stmt_sequence(node.stmts)
        if not node.stmts or not isinstance(node.stmts[-1], ast.ReturnStmt):
            self.emit(IRReturn())
        self.emit(IRProcEnd(node.name))
        return None

    def visit_SubroutineDef(self, node: ast.SubroutineDef):
        """Gera marcadores e corpo IR de uma subrotina externa."""
        self.emit(IRProcBegin(name=node.name, params=node.params, kind="subroutine"))
        self._visit_stmt_sequence(node.stmts)
        if not node.stmts or not isinstance(node.stmts[-1], ast.ReturnStmt):
            self.emit(IRReturn())
        self.emit(IRProcEnd(node.name))
        return None

    def visit_TypeDecl(self, node: ast.TypeDecl):
        """Ignora declarações, já consumidas pela semântica/backend."""
        return None

    def visit_ArrayDecl(self, node: ast.ArrayDecl):
        """Ignora declarações de arrays durante geração de instruções."""
        return None

    def visit_IntLit(self, node: ast.IntLit):
        """Traduz literal inteiro para valor Python na IR."""
        return node.value

    def visit_RealLit(self, node: ast.RealLit):
        """Traduz literal real para valor Python na IR."""
        return node.value

    def visit_BoolLit(self, node: ast.BoolLit):
        """Traduz literal lógico para bool Python na IR."""
        return node.value

    def visit_StringLit(self, node: ast.StringLit):
        """Traduz literal CHARACTER para wrapper distinto de variável."""
        return IRStringLit(node.value)

    def visit_VarRef(self, node: ast.VarRef):
        """Traduz referência escalar para o nome da variável."""
        return node.name

    def visit_ArrayRef(self, node: ast.ArrayRef):
        """Gera load de array para temporário e devolve esse temporário."""
        indices = [self.generate(idx) for idx in node.indices]
        dest = self.new_temp()
        self.emit(IRLoadArray(dest=dest, name=node.name, indices=indices))
        return dest

    def visit_CallExpr(self, node: ast.CallExpr):
        """Gera chamada de função com retorno num temporário."""
        args = [self.generate(arg) for arg in node.args]
        dest = self.new_temp()
        self.emit(IRCall(name=node.name, args=args, dest=dest))
        return dest

    def visit_UnaryOp(self, node: ast.UnaryOp):
        """Gera operação unária para um novo temporário."""
        operand = self.generate(node.operand)
        dest = self.new_temp()
        op = self._normalize_unary(node.op)
        self.emit(IRUnaryOp(op=op, dest=dest, operand=operand))
        return dest

    def visit_BinOp(self, node: ast.BinOp):
        """Gera operação binária para um novo temporário."""
        left = self.generate(node.left)
        right = self.generate(node.right)
        dest = self.new_temp()
        op = self._normalize_binop(node.op)
        self.emit(IROp(op=op, dest=dest, left=left, right=right))
        return dest

    def visit_AssignStmt(self, node: ast.AssignStmt):
        """Gera atribuição escalar ou store em array."""
        expr_val = self.generate(node.value)
        if isinstance(node.target, ast.VarRef):
            self.emit(IRAssign(dest=node.target.name, src=expr_val))
            return None

        if isinstance(node.target, ast.ArrayRef):
            indices = [self.generate(idx) for idx in node.target.indices]
            self.emit(IRStoreArray(name=node.target.name, indices=indices, src=expr_val))
            return None

        raise NotImplementedError(f"Lvalue nao suportado: {type(node.target).__name__}")

    def visit_IfStmt(self, node: ast.IfStmt):
        """Gera labels e saltos para IF/ELSE estruturado."""
        cond = self.generate(node.condition)
        then_label = self.new_label("THEN")
        end_label = self.new_label("ENDIF")

        if node.else_stmts:
            else_label = self.new_label("ELSE")
            self.emit(IRCJump(cond=cond, true_label=then_label, false_label=else_label))

            self.emit(IRLabelInstr(then_label))
            self._visit_stmt_sequence(node.then_stmts)
            self.emit(IRJump(end_label))

            self.emit(IRLabelInstr(else_label))
            self._visit_stmt_sequence(node.else_stmts)
            self.emit(IRLabelInstr(end_label))
            return None

        self.emit(IRCJump(cond=cond, true_label=then_label, false_label=end_label))
        self.emit(IRLabelInstr(then_label))
        self._visit_stmt_sequence(node.then_stmts)
        self.emit(IRLabelInstr(end_label))
        return None

    def visit_ArithIfStmt(self, node: ast.ArithIfStmt):
        """Gera as duas decisões necessárias para IF aritmético."""
        expr_val = self.generate(node.expr)

        neg_cond = self.new_temp()
        self.emit(IROp(op="<", dest=neg_cond, left=expr_val, right=0))

        zero_check = self.new_label("ARZ")
        self.emit(
            IRCJump(
                cond=neg_cond,
                true_label=self._label_for_number(node.label_neg),
                false_label=zero_check,
            )
        )

        self.emit(IRLabelInstr(zero_check))
        zero_cond = self.new_temp()
        self.emit(IROp(op="==", dest=zero_cond, left=expr_val, right=0))
        self.emit(
            IRCJump(
                cond=zero_cond,
                true_label=self._label_for_number(node.label_zero),
                false_label=self._label_for_number(node.label_pos),
            )
        )
        return None

    def visit_DoStmt(self, node: ast.DoStmt):
        """Gera cabeçalho de DO e empilha contexto até ao CONTINUE terminal."""
        start_val = self.generate(node.start)
        end_val = self.generate(node.end)
        step_val = self.generate(node.step) if node.step is not None else 1

        self.emit(IRAssign(dest=node.var, src=start_val))

        test_label = self.new_label("DO_TEST")
        body_label = self.new_label("DO_BODY")
        end_label = self.new_label("DO_END")
        pos_check_label = self.new_label("DO_POS")
        neg_check_label = self.new_label("DO_NEG")

        self.emit(IRLabelInstr(test_label))

        step_nonneg = self.new_temp()
        self.emit(IROp(op=">=", dest=step_nonneg, left=step_val, right=0))
        self.emit(IRCJump(cond=step_nonneg, true_label=pos_check_label, false_label=neg_check_label))

        self.emit(IRLabelInstr(pos_check_label))
        pos_cond = self.new_temp()
        self.emit(IROp(op="<=", dest=pos_cond, left=node.var, right=end_val))
        self.emit(IRCJump(cond=pos_cond, true_label=body_label, false_label=end_label))

        self.emit(IRLabelInstr(neg_check_label))
        neg_cond = self.new_temp()
        self.emit(IROp(op=">=", dest=neg_cond, left=node.var, right=end_val))
        self.emit(IRCJump(cond=neg_cond, true_label=body_label, false_label=end_label))

        self.emit(IRLabelInstr(body_label))

        self._loop_stack.append(
            LoopContext(
                target_label=node.label,
                var_name=node.var,
                step_value=step_val,
                test_label=test_label,
                end_label=end_label,
            )
        )
        return None

    def _close_do_loops_for_label(self, label_num: int) -> None:
        """Fecha ciclos DO cujo label terminal corresponde ao CONTINUE atual."""
        closed_any = False
        while self._loop_stack and self._loop_stack[-1].target_label == label_num:
            closed_any = True
            ctx = self._loop_stack.pop()
            next_val = self.new_temp()
            self.emit(IROp(op="+", dest=next_val, left=ctx.var_name, right=ctx.step_value))
            self.emit(IRAssign(dest=ctx.var_name, src=next_val))
            self.emit(IRJump(ctx.test_label))
            self.emit(IRLabelInstr(ctx.end_label))

        if closed_any:
            return

        if any(ctx.target_label == label_num for ctx in self._loop_stack):
            raise ValueError(f"Estrutura DO invalida: label {label_num} fora do topo da pilha")

    def visit_GotoStmt(self, node: ast.GotoStmt):
        """Gera salto incondicional para label Fortran."""
        self.emit(IRJump(self._label_for_number(node.label)))
        return None

    def visit_ContinueStmt(self, node: ast.ContinueStmt):
        """Emite label de CONTINUE e fecha DOs pendentes associados."""
        if node.label is not None:
            self._emit_source_label_if_any(node)
            self._close_do_loops_for_label(node.label)
        return None

    def visit_PrintStmt(self, node: ast.PrintStmt):
        """Gera instrução IRPrint com valores já traduzidos."""
        args = [self.generate(item) for item in node.items]
        self.emit(IRPrint(args=args))
        return None

    def visit_ReadStmt(self, node: ast.ReadStmt):
        """Gera IRRead para escalares e referências de array."""
        args: list[Any] = []
        for target in node.variables:
            if isinstance(target, ast.VarRef):
                args.append(target.name)
            elif isinstance(target, ast.ArrayRef):
                indices = [self.generate(idx) for idx in target.indices]
                args.append(IRArrayRef(target.name, indices))
            else:
                raise NotImplementedError(f"Alvo READ nao suportado: {type(target).__name__}")

        self.emit(IRRead(args=args))
        return None

    def visit_WriteStmt(self, node: ast.WriteStmt):
        """Gera IRWrite preservando unidade, formato e itens."""
        unit = self.generate(node.unit) if node.unit is not None else None
        fmt = self.generate(node.fmt) if isinstance(node.fmt, ast.Node) else node.fmt
        items = [self.generate(item) for item in node.items]
        self.emit(IRWrite(unit=unit, fmt=fmt, items=items))
        return None

    def visit_CallStmt(self, node: ast.CallStmt):
        """Gera chamada de subrotina sem destino de retorno."""
        args = [self.generate(arg) for arg in node.args]
        self.emit(IRCall(name=node.name, args=args, dest=None))
        return None

    def visit_StopStmt(self, node: ast.StopStmt):
        """Gera paragem explícita do programa."""
        self.emit(IRStop())
        return None

    def visit_ReturnStmt(self, node: ast.ReturnStmt):
        """Gera retorno de subprograma."""
        self.emit(IRReturn())
        return None
