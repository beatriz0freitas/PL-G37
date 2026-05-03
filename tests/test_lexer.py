# tests/test_lexer.py
#
# Testes da análise léxica (Fortran77Lexer).
# Nomes de tokens seguem o padrão:
#   - keywords: tipo == nome (IF, DO, PRINT, ...)
#   - operadores pontuados: EQ, LE, AND, OR, ...
#   - literais lógicos: BOOL_LIT
#   - literais: INT_LIT, REAL_LIT, STRING_LIT

import pytest
from conftest import tokenize, token_types, token_values, FIXTURES
from src.errors import LexError


# ---------------------------------------------------------------------------
# Utilitários locais
# ---------------------------------------------------------------------------

def lex_str(lexer, code: str, source_format: str = "free"):
    """Tokeniza uma string inline (free-form por omissão, mais cómodo)."""
    return lexer.tokenize(code, filename="<test>", source_format=source_format)


def types(lexer, code: str, source_format: str = "free") -> list[str]:
    return token_types(lex_str(lexer, code, source_format))


def values(lexer, code: str, source_format: str = "free") -> list:
    return token_values(lex_str(lexer, code, source_format))


# ---------------------------------------------------------------------------
# 1. Programas completos dos fixtures
# ---------------------------------------------------------------------------

class TestFixturePrograms:
    """Smoke tests: o lexer não deve rebentar nos exemplos do enunciado."""

    def test_hello_nao_lanca_excecao(self, lexer):
        toks = tokenize(lexer, "hello.f")
        assert len(toks) > 0

    def test_hello_comeca_com_program(self, lexer):
        toks = tokenize(lexer, "hello.f")
        assert toks[0].type  == "PROGRAM"
        assert toks[0].value == "PROGRAM"

    def test_hello_token_types(self, lexer):
        tipos = token_types(tokenize(lexer, "hello.f"))
        assert "PROGRAM"    in tipos
        assert "PRINT"      in tipos
        assert "STRING_LIT" in tipos
        assert "END"        in tipos

    def test_fatorial_nao_lanca_excecao(self, lexer):
        assert len(tokenize(lexer, "fatorial.f")) > 0

    def test_fatorial_tem_label_10(self, lexer):
        labels = [t for t in tokenize(lexer, "fatorial.f") if t.type == "LABEL"]
        assert len(labels) == 1
        assert labels[0].value == 10

    def test_fatorial_tem_do_e_continue(self, lexer):
        tipos = token_types(tokenize(lexer, "fatorial.f"))
        assert "DO"       in tipos
        assert "CONTINUE" in tipos

    def test_primo_nao_lanca_excecao(self, lexer):
        assert len(tokenize(lexer, "primo.f")) > 0

    def test_primo_tem_label_20(self, lexer):
        labels = [t for t in tokenize(lexer, "primo.f") if t.type == "LABEL"]
        assert any(lb.value == 20 for lb in labels)

    def test_primo_operadores_logicos(self, lexer):
        tipos = token_types(tokenize(lexer, "primo.f"))
        assert "LE"  in tipos   # .LE.
        assert "AND" in tipos   # .AND.
        assert "EQ"  in tipos   # .EQ.

    def test_primo_literais_logicos(self, lexer):
        vals = token_values(tokenize(lexer, "primo.f"))
        assert True  in vals   # .TRUE.
        assert False in vals   # .FALSE.

    def test_somaarr_nao_lanca_excecao(self, lexer):
        assert len(tokenize(lexer, "somaarr.f")) > 0

    def test_somaarr_tem_array_e_label_30(self, lexer):
        toks = tokenize(lexer, "somaarr.f")
        tipos = token_types(toks)
        labels = [t for t in toks if t.type == "LABEL"]

        assert "READ" in tipos
        assert "DO" in tipos
        assert any(lb.value == 30 for lb in labels)

    def test_conversor_lexer_reconhece_function_e_label_20(self, lexer):
        toks = tokenize(lexer, "conversor.f")
        tipos = token_types(toks)
        labels = [t for t in toks if t.type == "LABEL"]

        assert "FUNCTION" in tipos
        assert "RETURN" in tipos
        assert any(lb.value == 20 for lb in labels)

    def test_free_form_tambem_extrai_labels_no_inicio_da_linha(self, lexer):
        toks = lex_str(lexer, "10 CONTINUE\n20 IF (.TRUE.) THEN\nENDIF\n", source_format="free")
        labels = [tok.value for tok in toks if tok.type == "LABEL"]

        assert labels == [10, 20]
        assert token_types(toks).count("CONTINUE") == 1


# ---------------------------------------------------------------------------
# 2. Palavras-chave 
# ---------------------------------------------------------------------------

class TestKeywords:

    @pytest.mark.parametrize("kw", [
        "PROGRAM", "END", "INTEGER", "REAL", "LOGICAL",
        "IF", "THEN", "ELSE", "ENDIF", "DO", "CONTINUE",
        "GOTO", "READ", "PRINT", "STOP", "RETURN", "CALL",
    ])
    def test_keyword_maiusculas(self, lexer, kw):
        toks = lex_str(lexer, kw)
        assert toks[0].type == kw

    @pytest.mark.parametrize("kw", [
        "program", "integer", "logical", "if", "do", "goto", "print",
    ])
    def test_keyword_minusculas(self, lexer, kw):
        """F77 é case-insensitive: minúsculas devem ser reconhecidas."""
        toks = lex_str(lexer, kw)
        assert toks[0].type == kw.upper()

    @pytest.mark.parametrize("kw,expected", [
        ("Program", "PROGRAM"),
        ("Integer", "INTEGER"),
        ("GoTo",    "GOTO"),
    ])
    def test_keyword_mixed_case(self, lexer, kw, expected):
        toks = lex_str(lexer, kw)
        assert toks[0].type == expected


# ---------------------------------------------------------------------------
# 3. Identificadores
# ---------------------------------------------------------------------------

class TestIdentifiers:

    def test_id_simples(self, lexer):
        toks = lex_str(lexer, "XPTO")
        assert toks[0].type  == "ID"
        assert toks[0].value == "XPTO"

    def test_id_normalizado_maiusculas(self, lexer):
        toks = lex_str(lexer, "myVar")
        assert toks[0].value == "MYVAR"

    def test_id_com_digitos(self, lexer):
        assert lex_str(lexer, "A1B2")[0].type == "ID"

    def test_id_nao_comeca_com_digito(self, lexer):
        toks = lex_str(lexer, "1A")
        assert toks[0].type == "INT_LIT"
        assert toks[1].type == "ID"


# ---------------------------------------------------------------------------
# 4. Literais numéricos
# ---------------------------------------------------------------------------

class TestNumericLiterals:

    @pytest.mark.parametrize("src,expected", [
        ("0", 0), ("1", 1), ("42", 42), ("1000", 1000),
    ])
    def test_int_lit(self, lexer, src, expected):
        toks = lex_str(lexer, src)
        assert toks[0].type  == "INT_LIT"
        assert toks[0].value == expected

    @pytest.mark.parametrize("src", [
        "1.0", "3.14", ".5", "1.", "1.0E3", "1.5E-2", "1.0D0",
    ])
    def test_real_lit_tipo(self, lexer, src):
        assert lex_str(lexer, src)[0].type == "REAL_LIT"

    def test_real_valor(self, lexer):
        assert abs(lex_str(lexer, "3.14")[0].value - 3.14) < 1e-9

    def test_real_notacao_cientifica(self, lexer):
        assert abs(lex_str(lexer, "1.5E2")[0].value - 150.0) < 1e-9

    def test_real_notacao_d(self, lexer):
        t = lex_str(lexer, "1.0D0")[0]
        assert t.type == "REAL_LIT"
        assert abs(t.value - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# 5. Literais de string
# ---------------------------------------------------------------------------

class TestStringLiterals:

    def test_string_simples(self, lexer):
        t = lex_str(lexer, "'hello'")[0]
        assert t.type  == "STRING_LIT"
        assert t.value == "hello"

    def test_string_com_espacos(self, lexer):
        assert lex_str(lexer, "'Ola, Mundo!'")[0].value == "Ola, Mundo!"

    def test_string_aspa_escapada(self, lexer):
        """Em F77, '' dentro de string representa um apóstrofe."""
        assert lex_str(lexer, "'it''s'")[0].value == "it's"

    def test_string_vazia(self, lexer):
        t = lex_str(lexer, "''")[0]
        assert t.type  == "STRING_LIT"
        assert t.value == ""


# ---------------------------------------------------------------------------
# 6. Literais lógicos 
# ---------------------------------------------------------------------------

class TestBoolLit:

    def test_true(self, lexer):
        t = lex_str(lexer, ".TRUE.")[0]
        assert t.type  == "BOOL_LIT"
        assert t.value is True

    def test_false(self, lexer):
        t = lex_str(lexer, ".FALSE.")[0]
        assert t.type  == "BOOL_LIT"
        assert t.value is False

    def test_true_minusculas(self, lexer):
        t = lex_str(lexer, ".true.")[0]
        assert t.type  == "BOOL_LIT"
        assert t.value is True

    def test_false_minusculas(self, lexer):
        t = lex_str(lexer, ".false.")[0]
        assert t.type  == "BOOL_LIT"
        assert t.value is False


# ---------------------------------------------------------------------------
# 7. Operadores 
# ---------------------------------------------------------------------------

class TestOperators:

    @pytest.mark.parametrize("src,expected_type", [
        ("+",  "PLUS"),
        ("-",  "MINUS"),
        ("*",  "STAR"),
        ("/",  "SLASH"),
        ("**", "POWER"),
        ("//", "CONCAT"),
        ("=",  "EQUALS"),
    ])
    def test_operador_aritmetico(self, lexer, src, expected_type):
        assert lex_str(lexer, src)[0].type == expected_type

    @pytest.mark.parametrize("src,expected_type", [
        (".EQ.", "EQ"), (".NE.", "NE"), (".LT.", "LT"),
        (".LE.", "LE"), (".GT.", "GT"), (".GE.", "GE"),
    ])
    def test_operador_relacional(self, lexer, src, expected_type):
        assert lex_str(lexer, src)[0].type == expected_type

    @pytest.mark.parametrize("src,expected_type", [
        (".AND.",  "AND"), (".OR.",  "OR"),  (".NOT.",  "NOT"),
        (".EQV.",  "EQV"), (".NEQV.", "NEQV"),
    ])
    def test_operador_logico(self, lexer, src, expected_type):
        assert lex_str(lexer, src)[0].type == expected_type

    @pytest.mark.parametrize("src,expected_type", [
        (".le.", "LE"), (".and.", "AND"),
    ])
    def test_operadores_minusculas(self, lexer, src, expected_type):
        assert lex_str(lexer, src)[0].type == expected_type


# ---------------------------------------------------------------------------
# 8. Pontuação
# ---------------------------------------------------------------------------

class TestPunctuation:

    @pytest.mark.parametrize("src,expected_type", [
        ("(", "LPAREN"), (")", "RPAREN"), (",", "COMMA"), (":", "COLON"),
    ])
    def test_pontuacao(self, lexer, src, expected_type):
        assert lex_str(lexer, src)[0].type == expected_type


# ---------------------------------------------------------------------------
# 9. Fixed-form: labels e continuação
# ---------------------------------------------------------------------------

class TestFixedForm:

    def test_label_emitido(self, lexer):
        toks = lex_str(lexer, "  10     CONTINUE\n", source_format="fixed")
        assert toks[0].type  == "LABEL"
        assert toks[0].value == 10

    def test_label_seguido_de_continue(self, lexer):
        toks = lex_str(lexer, "  10     CONTINUE\n", source_format="fixed")
        assert toks[1].type == "CONTINUE"

    def test_label_de_dois_digitos(self, lexer):
        toks = lex_str(lexer, "  99     CONTINUE\n", source_format="fixed")
        assert toks[0].value == 99

    def test_sem_label_nao_emite_label(self, lexer):
        toks = lex_str(lexer, "       INTEGER N\n", source_format="fixed")
        assert toks[0].type != "LABEL"

    def test_continuacao_de_linha(self, lexer):
        toks = tokenize(lexer, "continuation.f")
        tipos = token_types(toks)
        assert tipos.count("INT_LIT") >= 3
        assert tipos.count("PLUS")    >= 2

    def test_comentario_linha_C(self, lexer):
        src  = "C isto e um comentario\n       INTEGER N\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert "INTEGER" in token_types(toks)

    def test_linha_em_branco_ignorada(self, lexer):
        src  = "       INTEGER N\n\n       INTEGER M\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert token_types(toks).count("INTEGER") == 2


# ---------------------------------------------------------------------------
# 10. Free-form
# ---------------------------------------------------------------------------

class TestFreeForm:

    def test_continuacao_com_ampersand(self, lexer):
        src  = "INTEGER A, &\n        B, C\n"
        toks = lex_str(lexer, src, source_format="free")
        ids  = [t.value for t in toks if t.type == "ID"]
        assert ids == ["A", "B", "C"]

    def test_comentario_exclamacao(self, lexer):
        src  = "INTEGER N ! declara N\n"
        toks = lex_str(lexer, src, source_format="free")
        assert len(toks) == 2   # INTEGER + N


# ---------------------------------------------------------------------------
# 11. Números de linha
# ---------------------------------------------------------------------------

class TestLineNumbers:

    def test_lineno_hello(self, lexer):
        toks = tokenize(lexer, "hello.f")
        assert next(t for t in toks if t.type == "PROGRAM").lineno == 1
        assert next(t for t in toks if t.type == "PRINT").lineno   == 2
        assert next(t for t in toks if t.type == "END").lineno     == 3

    def test_lineno_fatorial_label(self, lexer):
        toks  = tokenize(lexer, "fatorial.f")
        label = next(t for t in toks if t.type == "LABEL")
        assert label.lineno == 8
