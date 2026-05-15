"""Testes da representacao intermédia (IR): AST -> IR."""

import src.analise_sintatica.ast_nodes as ast
from conftest import parse_fixture
from src.representacao_intermedia.gerador import IRGenerator
from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCJump,
    IRCall,
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
)
from src.analise_semantica import analyze


def parse_str(parser, code: str, source_format: str = "free", filename: str = "<ir-test>"):
    tree = parser.parse(code, filename=filename, source_format=source_format)
    return analyze(tree, filename=filename)


def gen_ir(tree: ast.Program):
    tree = analyze(tree, filename="<ir-test>")
    generator = IRGenerator()
    generator.generate(tree)
    return generator.instructions


class TestIRBasic:

    def test_assign_binop_gera_temporario_e_assign(self, parser):
        src = """PROGRAM P
                 INTEGER A, B, C
                 B = 1
                 C = 2
                 A = B + C
                 END
              """
        tree = parse_str(parser, src, source_format="free")
        ir = gen_ir(tree)

        binops = [i for i in ir if isinstance(i, IROp)]
        assigns = [i for i in ir if isinstance(i, IRAssign) and i.dest == "A"]

        assert len(binops) == 1
        assert binops[0].op == "+"
        assert len(assigns) == 1
        assert assigns[0].dest == "A"

    def test_if_else_gera_salto_condicional(self, parser):
        src = """PROGRAM P
                 INTEGER N
                 N = 1
                 IF (N .GT. 0) THEN
                    N = N - 1
                 ELSE
                    N = N + 1
                 ENDIF
                 END
              """
        tree = parse_str(parser, src, source_format="free")
        ir = gen_ir(tree)

        assert any(isinstance(i, IRCJump) for i in ir)
        assert any(isinstance(i, IRLabelInstr) for i in ir)
        assert any(isinstance(i, IRJump) for i in ir)


class TestIRLabelsAndFlow:

    def test_primo_goto_tem_label_alvo_na_ir(self, parser):
        tree = parse_fixture(parser, "primo.f", source_format="fixed")
        ir = gen_ir(tree)

        gotos = [i for i in ir if isinstance(i, IRJump)]
        labels = [i for i in ir if isinstance(i, IRLabelInstr)]

        assert any(j.label.name == "F20" for j in gotos)
        assert any(lbl.label.name == "F20" for lbl in labels)

    def test_do_continue_classico_gera_loop(self, parser):
        tree = parse_fixture(parser, "fatorial.f", source_format="fixed")
        ir = gen_ir(tree)

        labels = [i for i in ir if isinstance(i, IRLabelInstr)]
        jumps = [i for i in ir if isinstance(i, IRJump)]
        plus_ops = [i for i in ir if isinstance(i, IROp) and i.op == "+"]

        # Label terminal do DO deve existir na IR.
        assert any(lbl.label.name == "F10" for lbl in labels)
        # O corpo deve voltar ao teste do ciclo.
        assert any(j.label.name.startswith("DO_TEST") for j in jumps)
        # O incremento do indice e expresso como soma.
        assert any(op.left == "I" for op in plus_ops)

    def test_arith_if_gera_duas_decisoes(self, parser):
        src = """      PROGRAM P
      INTEGER X
      X = 1
      IF (X) 10, 20, 30
 10   CONTINUE
 20   CONTINUE
 30   CONTINUE
      END
"""
        tree = parse_str(parser, src, source_format="fixed", filename="arith_if.f")
        ir = gen_ir(tree)

        cjumps = [i for i in ir if isinstance(i, IRCJump)]
        labels = [i for i in ir if isinstance(i, IRLabelInstr)]

        assert len(cjumps) == 2
        assert any(lbl.label.name == "F10" for lbl in labels)
        assert any(lbl.label.name == "F20" for lbl in labels)
        assert any(lbl.label.name == "F30" for lbl in labels)

    def test_arith_if_com_goto_resolve_todos_os_destinos(self, parser):
        src = """      PROGRAM P
      INTEGER X
      X = 1
      IF (X) 10, 20, 30
 10   GOTO 40
 20   GOTO 40
 30   GOTO 40
 40   CONTINUE
      END
"""
        tree = parse_str(parser, src, source_format="fixed", filename="arith_if_goto.f")
        ir = gen_ir(tree)

        cjumps = [i for i in ir if isinstance(i, IRCJump)]
        gotos = [i for i in ir if isinstance(i, IRJump)]
        labels = [i for i in ir if isinstance(i, IRLabelInstr)]
        cjump_targets = {
            target.name
            for jump in cjumps
            for target in (jump.true_label, jump.false_label)
        }

        assert {"F10", "F20", "F30"} <= cjump_targets
        assert any(jump.label.name == "F40" for jump in gotos)
        assert any(label.label.name == "F40" for label in labels)


class TestIRIOAndCalls:

    def test_read_print_call_sao_gerados(self, parser):
        src = """      PROGRAM P
      INTEGER N
      READ *, N
      PRINT *, MOD(N, 2)
      CALL FOO(N)
      END
      SUBROUTINE FOO(X)
      INTEGER X
      RETURN
      END
"""
        tree = parse_str(parser, src, source_format="fixed", filename="io_call.f")
        ir = gen_ir(tree)

        reads = [i for i in ir if isinstance(i, IRRead)]
        prints = [i for i in ir if isinstance(i, IRPrint)]
        calls = [i for i in ir if isinstance(i, IRCall)]

        assert len(reads) == 1
        assert len(prints) == 1
        # MOD (CallExpr) + FOO (CallStmt)
        assert len(calls) == 2
        assert any(c.name == "MOD" and c.dest is not None for c in calls)
        assert any(c.name == "FOO" and c.dest is None for c in calls)

    def test_intrinsecas_em_expressao_complexa_geram_calls_aninhados(self, parser):
        src = """PROGRAM P
                 INTEGER I, J, K
                 REAL R
                 I = 9
                 J = 4
                 K = 2
                 R = SQRT(ABS(I - J) + MAX(MIN(I, J), MOD(I, K)))
                 PRINT *, R
                 END
              """
        tree = parse_str(parser, src, source_format="free", filename="intr_complex.f")
        ir = gen_ir(tree)

        calls = [i for i in ir if isinstance(i, IRCall)]
        call_names = [call.name for call in calls]

        assert call_names == ["ABS", "MIN", "MOD", "MAX", "SQRT"]
        assert all(call.dest is not None for call in calls)
        assert any(isinstance(i, IROp) and i.op == "+" for i in ir)

    def test_assign_array_gera_store_array(self, parser):
        src = """PROGRAM P
                 INTEGER A(10)
                 A(1) = 3
                 END
              """
        tree = parse_str(parser, src, source_format="free", filename="arr_assign.f")
        ir = gen_ir(tree)

        stores = [i for i in ir if isinstance(i, IRStoreArray)]
        assert len(stores) == 1
        assert stores[0].name == "A"
        assert stores[0].src == 3

    def test_somaarr_gera_read_array_e_load_array(self, parser):
        tree = analyze(parse_fixture(parser, "somaarr.f", source_format="fixed"), filename="somaarr.f")
        ir = gen_ir(tree)

        reads = [i for i in ir if isinstance(i, IRRead)]
        loads = [i for i in ir if isinstance(i, IRLoadArray)]

        assert len(reads) >= 1
        assert any(str(arg).startswith("NUMS[") for read in reads for arg in read.args)
        assert any(load.name == "NUMS" for load in loads)

    def test_conversor_emite_main_e_subprograma(self, parser):
        tree = parse_fixture(parser, "conversor.f", source_format="fixed")
        ir = gen_ir(tree)

        proc_begins = [i for i in ir if isinstance(i, IRProcBegin)]
        proc_ends = [i for i in ir if isinstance(i, IRProcEnd)]
        calls = [i for i in ir if isinstance(i, IRCall)]

        assert any(isinstance(i, IRStop) for i in ir)
        assert len(proc_begins) == 1
        assert proc_begins[0].name == "CONVRT"
        assert proc_begins[0].kind == "function"
        assert proc_begins[0].params == ["N", "B"]
        assert len(proc_ends) == 1
        assert any(c.name == "CONVRT" and c.dest is not None for c in calls)
        assert any(isinstance(i, IRReturn) for i in ir)
