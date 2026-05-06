"""Testes da análise semântica."""

import pytest

import src.analise_sintatica.ast_nodes as ast
from src.errors import SemanticError
from src.analise_semantica import analyze


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

    def test_atribuicao_numerica_com_conversao_implicita_e_valida(self, parser):
        src = """PROGRAM P
                 INTEGER I
                 REAL R
                 I = 2.9
                 R = I
                 END
              """
        tree = analyze_str(parser, src)

        assert tree.symbol_table.lookup("I").type_name == "INTEGER"
        assert tree.symbol_table.lookup("R").type_name == "REAL"

    def test_power_so_suporta_inteiros(self, parser):
        src = """PROGRAM P
                 INTEGER I
                 REAL R
                 R = 2.0
                 I = 2 ** R
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "suporta apenas base e expoente INTEGER" in str(exc_info.value)

    def test_power_rejeita_expoente_negativo_literal(self, parser):
        src = """PROGRAM P
                 INTEGER I
                 I = 2 ** -1
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "não suporta expoentes negativos" in str(exc_info.value)


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


class TestSemanticSubprograms:

    def test_conversor_resolve_funcao_definida_pelo_utilizador(self, parser):
        from conftest import parse_fixture

        tree = analyze(parse_fixture(parser, "conversor.f", source_format="fixed"), filename="conversor.f")

        assert tree.callable_table.lookup("CONVRT").kind == "function"
        func = tree.subprograms[0]
        assert getattr(func, "result_name") == "CONVRT"
        assert func.symbol_table.lookup("N").type_name == "INTEGER"
        assert func.symbol_table.lookup("CONVRT").type_name == "INTEGER"

    def test_call_expr_valida_aridade_da_funcao(self, parser):
        src = """PROGRAM P
                 INTEGER X
                 X = FOO(1)
                 END
                 INTEGER FUNCTION FOO(A, B)
                 INTEGER A, B
                 FOO = A + B
                 RETURN
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "espera 2 argumentos" in str(exc_info.value)

    def test_call_stmt_exige_subrotina(self, parser):
        src = """PROGRAM P
                 CALL FOO(1)
                 END
                 INTEGER FUNCTION FOO(A)
                 INTEGER A
                 FOO = A
                 RETURN
                 END
              """
        with pytest.raises(SemanticError) as exc_info:
            analyze_str(parser, src)

        assert "não é uma subrotina" in str(exc_info.value)
