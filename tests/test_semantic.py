"""Testes da análise semântica."""

import pytest

import src.analise_sintatica.ast_nodes as ast
from src.errors import SemanticError
from src.semantic import analyze


def analyze_str(parser, code: str, filename: str = "<sem-test>", source_format: str = "free"):
    tree = parser.parse(code, filename=filename, source_format=source_format)
    return analyze(tree, filename=filename)


class TestSemanticBasics:

    def test_declara_variaveis_e_anexa_tabela(self, parser):
        src = """PROGRAM P
                 INTEGER X
                 X = 1
                 END
              """
        tree = analyze_str(parser, src)

        assert hasattr(tree, "symbol_table")
        assert tree.symbol_table.lookup("X").type_name == "INTEGER"

    def test_erro_variavel_nao_declarada(self, parser):
        src = """PROGRAM P
                 INTEGER X
                 X = Y
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src, filename="undeclared.f")

        assert "sem declaração" in str(exc_info.value)
        assert "undeclared.f:" in str(exc_info.value)

    def test_erro_duplicado(self, parser):
        src = """PROGRAM P
                 INTEGER X
                 REAL X
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "já declarado" in str(exc_info.value)

    def test_erro_variavel_nao_inicializada(self, parser):
        src = """PROGRAM P
                 INTEGER X, Y
                 X = Y
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "antes de inicialização" in str(exc_info.value)

    def test_erro_tipo_invalido_em_atribuicao(self, parser):
        src = """PROGRAM P
                 INTEGER X
                 LOGICAL L
                 L = .TRUE.
                 X = L
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "Atribuição inválida" in str(exc_info.value)


class TestSemanticArrays:

    def test_resolve_call_expr_para_array_ref(self, parser):
        src = """PROGRAM P
                 INTEGER A(10), I, X
                 I = 1
                 A(I) = 3
                 X = A(I)
                 END
              """
        tree = analyze_str(parser, src)
        assign = next(stmt for stmt in tree.stmts if isinstance(stmt, ast.AssignStmt) and isinstance(stmt.target, ast.VarRef) and stmt.target.name == "X")

        assert isinstance(assign.value, ast.ArrayRef)
        assert getattr(assign.value, "sem_type") == "INTEGER"

    def test_rejeita_array_sem_indices(self, parser):
        src = """PROGRAM P
                 INTEGER A(10), X
                 X = A
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "usado sem índices" in str(exc_info.value)

    def test_rejeita_indice_nao_inteiro(self, parser):
        src = """PROGRAM P
                 INTEGER A(10), X
                 REAL R
                 A(1) = 0
                 R = 1.0
                 X = A(R)
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "esperado INTEGER" in str(exc_info.value)


class TestSemanticLabels:

    def test_do_exige_continue_com_mesma_label(self, parser):
        src = """      PROGRAM P
      INTEGER I
      DO 10 I = 1, 3
      I = I + 1
      END
"""
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src, filename="bad_do.f", source_format="fixed")

        assert "Label 10 não definida" in str(exc_info.value)

    def test_goto_para_label_inexistente_falha(self, parser):
        src = """PROGRAM P
                 GOTO 99
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "Label 99 não definida" in str(exc_info.value)
