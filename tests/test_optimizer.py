"""Testes dos passes de otimização IR.

Cobre:
  - constant_folding       (dobramento de constantes)
  - constant_propagation   (propagação de constantes)
  - dead_code_elimination  (eliminação de código morto)
  - optimize               (pipeline completo)
"""

import pytest

from src.optimizer import (
    constant_folding,
    constant_propagation,
    dead_code_elimination,
    optimize,
)
from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCJump,
    IRJump,
    IRLabelInstr,
    IROp,
    IRPrint,
    IRProcBegin,
    IRProcEnd,
    IRRead,
    IRReturn,
    IRStop,
    IRUnaryOp,
)
from src.representacao_intermedia.operadores import Label, Temp


# ---------------------------------------------------------------------------
# Atalhos de construção
# ---------------------------------------------------------------------------

def t(n: int) -> Temp:
    return Temp(n)


def lbl(name: str) -> Label:
    return Label(name)


# ---------------------------------------------------------------------------
# 1. Constant Folding
# ---------------------------------------------------------------------------

class TestConstantFolding:

    def test_fold_addition(self):
        ir = [IROp(op="+", dest=t(1), left=3, right=4)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 7

    def test_fold_subtraction(self):
        ir = [IROp(op="-", dest=t(1), left=10, right=3)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 7

    def test_fold_multiplication(self):
        ir = [IROp(op="*", dest=t(1), left=6, right=7)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 42

    def test_fold_integer_division_truncates(self):
        """Divisão inteira em Fortran 77 trunca para zero."""
        ir = [IROp(op="/", dest=t(1), left=10, right=3)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 3

    def test_no_fold_division_by_zero(self):
        """Divisão por zero não é dobrada — seria erro em runtime."""
        ir = [IROp(op="/", dest=t(1), left=10, right=0)]
        result = constant_folding(ir)
        assert isinstance(result[0], IROp)

    def test_fold_comparison_true(self):
        ir = [IROp(op="<", dest=t(1), left=3, right=4)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 1

    def test_fold_comparison_false(self):
        ir = [IROp(op=">", dest=t(1), left=3, right=4)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 0

    def test_fold_unary_neg(self):
        ir = [IRUnaryOp(op="NEG", dest=t(1), operand=5)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == -5

    def test_fold_unary_not_true(self):
        ir = [IRUnaryOp(op="NOT", dest=t(1), operand=0)]
        result = constant_folding(ir)
        assert isinstance(result[0], IRAssign)
        assert result[0].src == 1

    def test_no_fold_with_variable_operand(self):
        """Não dobra se um operando é variável (valor desconhecido)."""
        ir = [IROp(op="+", dest=t(1), left="X", right=3)]
        result = constant_folding(ir)
        assert isinstance(result[0], IROp)

    def test_preserves_non_constant_instructions(self):
        ir = [
            IRAssign(dest="X", src=1),
            IROp(op="+", dest=t(1), left=2, right=3),
            IRPrint(args=[t(1)]),
        ]
        result = constant_folding(ir)
        assert len(result) == 3
        assert isinstance(result[0], IRAssign)
        assert isinstance(result[1], IRAssign)  # dobrado
        assert isinstance(result[2], IRPrint)


# ---------------------------------------------------------------------------
# 2. Constant Propagation
# ---------------------------------------------------------------------------

class TestConstantPropagation:

    def test_propagate_temp_into_op(self):
        ir = [
            IRAssign(dest=t(1), src=42),
            IROp(op="+", dest=t(2), left=t(1), right=1),
        ]
        result = constant_propagation(ir)
        assert result[1].left == 42  # t1 substituído por 42

    def test_propagate_named_var_into_op(self):
        ir = [
            IRAssign(dest="X", src=10),
            IROp(op="*", dest=t(1), left="X", right=2),
        ]
        result = constant_propagation(ir)
        assert result[1].left == 10  # X substituído por 10

    def test_clear_env_at_label(self):
        """Após um label, o ambiente é limpo (ponto de junção conservativo)."""
        ir = [
            IRAssign(dest=t(1), src=99),
            IRLabelInstr(lbl("L1")),
            IROp(op="+", dest=t(2), left=t(1), right=0),
        ]
        result = constant_propagation(ir)
        # t1 NÃO deve ser substituído após o label
        assert result[2].left == t(1)

    def test_clear_env_at_proc_begin(self):
        """IRProcBegin inicia novo escopo — ambiente limpo."""
        ir = [
            IRAssign(dest=t(1), src=5),
            IRProcBegin(name="FOO", params=[], kind="subroutine"),
            IROp(op="+", dest=t(2), left=t(1), right=1),
        ]
        result = constant_propagation(ir)
        assert result[2].left == t(1)

    def test_invalidate_on_reassign(self):
        """Reatribuição invalida o valor anterior."""
        ir = [
            IRAssign(dest="X", src=1),
            IRAssign(dest="X", src=2),
            IROp(op="+", dest=t(1), left="X", right=0),
        ]
        result = constant_propagation(ir)
        assert result[2].left == 2  # Propaga o valor mais recente (2)

    def test_propagate_into_cjump(self):
        ir = [
            IRAssign(dest=t(1), src=1),
            IRCJump(cond=t(1), true_label=lbl("T"), false_label=lbl("F")),
        ]
        result = constant_propagation(ir)
        assert result[1].cond == 1

    def test_propagate_into_print(self):
        ir = [
            IRAssign(dest=t(1), src=7),
            IRPrint(args=[t(1)]),
        ]
        result = constant_propagation(ir)
        assert result[1].args[0] == 7

    def test_no_propagate_after_read(self):
        """READ sobrescreve variáveis — invalida o ambiente."""
        ir = [
            IRAssign(dest="N", src=5),
            IRRead(args=["N"]),
            IROp(op="+", dest=t(1), left="N", right=0),
        ]
        result = constant_propagation(ir)
        assert result[2].left == "N"  # N não é substituído por 5


# ---------------------------------------------------------------------------
# 3. Dead Code Elimination
# ---------------------------------------------------------------------------

class TestDeadCodeElimination:

    def test_remove_after_unconditional_jump(self):
        ir = [
            IRAssign(dest="X", src=1),
            IRJump(lbl("L1")),
            IRAssign(dest="Y", src=2),   # ← morto
            IRLabelInstr(lbl("L1")),
            IRStop(),
        ]
        result = dead_code_elimination(ir)
        types = [type(i).__name__ for i in result]
        assert "IRAssign" in types       # X = 1 mantido
        assert types.count("IRAssign") == 1  # Y = 2 eliminado
        assert "IRLabelInstr" in types
        assert "IRStop" in types

    def test_remove_after_stop(self):
        ir = [
            IRStop(),
            IRAssign(dest="X", src=1),   # ← morto
        ]
        result = dead_code_elimination(ir)
        assert len(result) == 1
        assert isinstance(result[0], IRStop)

    def test_remove_after_return(self):
        ir = [
            IRReturn(),
            IRAssign(dest="X", src=1),   # ← morto
            IRProcEnd("F"),              # ← restaura alcançabilidade
        ]
        result = dead_code_elimination(ir)
        assert len(result) == 2          # IRReturn + IRProcEnd
        assert isinstance(result[0], IRReturn)
        assert isinstance(result[1], IRProcEnd)

    def test_keep_code_after_label(self):
        """Label restaura alcançabilidade — código seguinte é mantido."""
        ir = [
            IRJump(lbl("L1")),
            IRAssign(dest="X", src=1),   # ← morto
            IRLabelInstr(lbl("L1")),
            IRAssign(dest="Y", src=2),   # ← alcançável
        ]
        result = dead_code_elimination(ir)
        assert len(result) == 3
        assert isinstance(result[-1], IRAssign)
        assert result[-1].dest == "Y"

    def test_keep_proc_begin_after_stop(self):
        """IRProcBegin após IRStop deve ser mantido (início de subprograma)."""
        ir = [
            IRStop(),
            IRProcBegin(name="FOO", params=[], kind="subroutine"),
            IRReturn(),
            IRProcEnd("FOO"),
        ]
        result = dead_code_elimination(ir)
        types = [type(i).__name__ for i in result]
        assert "IRProcBegin" in types
        assert "IRProcEnd" in types


# ---------------------------------------------------------------------------
# 4. Pipeline optimize() completo
# ---------------------------------------------------------------------------

class TestOptimizePipeline:

    def test_propagation_then_folding(self):
        """Propagação + folding: X=3, Y=4, t=X+Y → t=7 como literal."""
        ir = [
            IRAssign(dest="X", src=3),
            IRAssign(dest="Y", src=4),
            IROp(op="+", dest=t(1), left="X", right="Y"),
            IRPrint(args=[t(1)]),
            IRStop(),
        ]
        result = optimize(ir)
        # PRINT deve usar o literal 7 directamente
        print_instr = next(i for i in result if isinstance(i, IRPrint))
        assert print_instr.args[0] == 7

    def test_dce_after_stop(self):
        ir = [
            IRAssign(dest="X", src=1),
            IRStop(),
            IRAssign(dest="Y", src=2),   # ← morto
        ]
        result = optimize(ir)
        assigns = [i for i in result if isinstance(i, IRAssign)]
        assert len(assigns) == 1
        assert assigns[0].dest == "X"

    def test_hello_fixture_passes_through(self, parser):
        """O optimizer não deve rebentar com programas reais."""
        from conftest import parse_fixture
        from src.representacao_intermedia.gerador import IRGenerator
        from src.analise_semantica import analyze

        tree = parse_fixture(parser, "hello.f", source_format="free")
        tree = analyze(tree, filename="hello.f")
        gen = IRGenerator()
        gen.generate(tree)
        result = optimize(gen.instructions)

        assert len(result) > 0
        assert any(isinstance(i, IRStop) for i in result)

    def test_fatorial_fixture_passes_through(self, parser):
        """Fixture com DO loop: optimizer não deve eliminar código de loop."""
        from conftest import parse_fixture
        from src.representacao_intermedia.gerador import IRGenerator
        from src.analise_semantica import analyze

        tree = parse_fixture(parser, "fatorial.f", source_format="fixed")
        tree = analyze(tree, filename="fatorial.f")
        gen = IRGenerator()
        gen.generate(tree)

        unoptimized_len = len(gen.instructions)
        result = optimize(gen.instructions)

        # Não deve eliminar instruções de loop (sem dead code real)
        assert len(result) > 0
        # Após otimização, pode haver menos ou igual número de instruções
        assert len(result) <= unoptimized_len