# tests/test_lexer.py
#
# Testes da análise léxica (Fortran77Lexer).
#
# Organização:
#   - TestTokenTypes   : verifica os tipos dos tokens produzidos
#   - TestTokenValues  : verifica os valores (literais, strings, labels, ...)
#   - TestKeywords     : palavras-chave individuais
#   - TestOperators    : operadores aritméticos, relacionais e lógicos
#   - TestFixedForm    : regras do formato de colunas fixas (labels, continuação)
#   - TestErrors       : entradas inválidas que devem levantar LexError

import pytest
from conftest import tokenize, token_types, token_values, FIXTURES
from src.errors import LexError


# ---------------------------------------------------------------------------
# Utilitários locais
# ---------------------------------------------------------------------------

def lex_str(lexer, code: str, source_format: str = "free"):
    """Tokeniza uma string inline (free-form por omissão, mais cómodo)."""
    return lexer.tokenize(code, filename="<test>", source_format=source_format)


def types(lexer, code: str, fmt: str = "free") -> list[str]:
    return token_types(lex_str(lexer, code, fmt))


def values(lexer, code: str, fmt: str = "free") -> list:
    return token_values(lex_str(lexer, code, fmt))


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
        assert toks[0].type == "KW_PROGRAM"
        assert toks[0].value == "PROGRAM"

    def test_hello_token_types(self, lexer):
        toks = tokenize(lexer, "hello.f")
        tipos = token_types(toks)
        assert "KW_PROGRAM" in tipos
        assert "KW_PRINT"   in tipos
        assert "STRING_LITERAL" in tipos
        assert "KW_END"     in tipos

    def test_fatorial_nao_lanca_excecao(self, lexer):
        toks = tokenize(lexer, "fatorial.f")
        assert len(toks) > 0

    def test_fatorial_tem_label_10(self, lexer):
        toks = tokenize(lexer, "fatorial.f")
        labels = [t for t in toks if t.type == "LABEL"]
        assert len(labels) == 1
        assert labels[0].value == 10

    def test_fatorial_tem_do_e_continue(self, lexer):
        tipos = token_types(tokenize(lexer, "fatorial.f"))
        assert "KW_DO"       in tipos
        assert "KW_CONTINUE" in tipos

    def test_primo_nao_lanca_excecao(self, lexer):
        toks = tokenize(lexer, "primo.f")
        assert len(toks) > 0

    def test_primo_tem_label_20(self, lexer):
        toks = tokenize(lexer, "primo.f")
        labels = [t for t in toks if t.type == "LABEL"]
        assert any(lb.value == 20 for lb in labels)

    def test_primo_operadores_logicos(self, lexer):
        tipos = token_types(tokenize(lexer, "primo.f"))
        assert "OP_LE"  in tipos   # .LE.
        assert "OP_AND" in tipos   # .AND.
        assert "OP_EQ"  in tipos   # .EQ.

    def test_primo_literais_logicos(self, lexer):
        toks = tokenize(lexer, "primo.f")
        vals = token_values(toks)
        assert True  in vals   # .TRUE.
        assert False in vals   # .FALSE.


# ---------------------------------------------------------------------------
# 2. Palavras-chave
# ---------------------------------------------------------------------------

class TestKeywords:

    @pytest.mark.parametrize("kw,expected_type", [
        ("PROGRAM",   "KW_PROGRAM"),
        ("END",       "KW_END"),
        ("INTEGER",   "KW_INTEGER"),
        ("REAL",      "KW_REAL"),
        ("LOGICAL",   "KW_LOGICAL"),
        ("IF",        "KW_IF"),
        ("THEN",      "KW_THEN"),
        ("ELSE",      "KW_ELSE"),
        ("ENDIF",     "KW_ENDIF"),
        ("DO",        "KW_DO"),
        ("CONTINUE",  "KW_CONTINUE"),
        ("GOTO",      "KW_GOTO"),
        ("READ",      "KW_READ"),
        ("PRINT",     "KW_PRINT"),
        ("STOP",      "KW_STOP"),
        ("RETURN",    "KW_RETURN"),
        ("CALL",      "KW_CALL"),
    ])
    def test_keyword_maiusculas(self, lexer, kw, expected_type):
        toks = lex_str(lexer, kw)
        assert toks[0].type == expected_type

    @pytest.mark.parametrize("kw,expected_type", [
        ("program",  "KW_PROGRAM"),
        ("integer",  "KW_INTEGER"),
        ("logical",  "KW_LOGICAL"),
        ("if",       "KW_IF"),
        ("do",       "KW_DO"),
        ("goto",     "KW_GOTO"),
        ("print",    "KW_PRINT"),
    ])
    def test_keyword_minusculas(self, lexer, kw, expected_type):
        """F77 é case-insensitive: minúsculas devem ser reconhecidas."""
        toks = lex_str(lexer, kw)
        assert toks[0].type == expected_type

    @pytest.mark.parametrize("kw,expected_type", [
        ("Program",  "KW_PROGRAM"),
        ("Integer",  "KW_INTEGER"),
        ("GoTo",     "KW_GOTO"),
    ])
    def test_keyword_mixed_case(self, lexer, kw, expected_type):
        toks = lex_str(lexer, kw)
        assert toks[0].type == expected_type


# ---------------------------------------------------------------------------
# 3. Identificadores
# ---------------------------------------------------------------------------

class TestIdentifiers:

    def test_id_simples(self, lexer):
        toks = lex_str(lexer, "XPTO")
        assert toks[0].type  == "ID"
        assert toks[0].value == "XPTO"

    def test_id_normalizado_maiusculas(self, lexer):
        """O lexer normaliza IDs para maiúsculas."""
        toks = lex_str(lexer, "myVar")
        assert toks[0].value == "MYVAR"

    def test_id_com_digitos(self, lexer):
        toks = lex_str(lexer, "A1B2")
        assert toks[0].type == "ID"

    def test_id_nao_comeca_com_digito(self, lexer):
        """'1A' não pode ser um ID — deve gerar INT_LITERAL + ID."""
        toks = lex_str(lexer, "1A")
        assert toks[0].type == "INT_LITERAL"
        assert toks[1].type == "ID"


# ---------------------------------------------------------------------------
# 4. Literais numéricos
# ---------------------------------------------------------------------------

class TestNumericLiterals:

    @pytest.mark.parametrize("src,expected", [
        ("0",     0),
        ("1",     1),
        ("42",    42),
        ("1000",  1000),
    ])
    def test_int_literal(self, lexer, src, expected):
        toks = lex_str(lexer, src)
        assert toks[0].type  == "INT_LITERAL"
        assert toks[0].value == expected

    @pytest.mark.parametrize("src", [
        "1.0", "3.14", ".5", "1.", "1.0E3", "1.5E-2", "1.0D0",
    ])
    def test_real_literal_tipo(self, lexer, src):
        toks = lex_str(lexer, src)
        assert toks[0].type == "REAL_LITERAL"

    def test_real_valor(self, lexer):
        toks = lex_str(lexer, "3.14")
        assert abs(toks[0].value - 3.14) < 1e-9

    def test_real_notacao_cientifica(self, lexer):
        toks = lex_str(lexer, "1.5E2")
        assert abs(toks[0].value - 150.0) < 1e-9

    def test_real_notacao_d(self, lexer):
        """1.0D0 é DOUBLE PRECISION em F77; o lexer converte D→E."""
        toks = lex_str(lexer, "1.0D0")
        assert toks[0].type == "REAL_LITERAL"
        assert abs(toks[0].value - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# 5. Literais de string
# ---------------------------------------------------------------------------

class TestStringLiterals:

    def test_string_simples(self, lexer):
        toks = lex_str(lexer, "'hello'")
        assert toks[0].type  == "STRING_LITERAL"
        assert toks[0].value == "hello"

    def test_string_com_espacos(self, lexer):
        toks = lex_str(lexer, "'Ola, Mundo!'")
        assert toks[0].value == "Ola, Mundo!"

    def test_string_aspa_escapada(self, lexer):
        """Em F77, '' dentro de string representa um apóstrofe."""
        toks = lex_str(lexer, "'it''s'")   # 'it''s' → it's
        assert toks[0].value == "it's"

    def test_string_vazia(self, lexer):
        toks = lex_str(lexer, "''")
        assert toks[0].type  == "STRING_LITERAL"
        assert toks[0].value == ""


# ---------------------------------------------------------------------------
# 6. Operadores
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
        toks = lex_str(lexer, src)
        assert toks[0].type == expected_type

    @pytest.mark.parametrize("src,expected_type", [
        (".EQ.", "OP_EQ"),
        (".NE.", "OP_NE"),
        (".LT.", "OP_LT"),
        (".LE.", "OP_LE"),
        (".GT.", "OP_GT"),
        (".GE.", "OP_GE"),
    ])
    def test_operador_relacional(self, lexer, src, expected_type):
        toks = lex_str(lexer, src)
        assert toks[0].type == expected_type

    @pytest.mark.parametrize("src,expected_type", [
        (".AND.",  "OP_AND"),
        (".OR.",   "OP_OR"),
        (".NOT.",  "OP_NOT"),
        (".EQV.",  "OP_EQV"),
        (".NEQV.", "OP_NEQV"),
    ])
    def test_operador_logico(self, lexer, src, expected_type):
        toks = lex_str(lexer, src)
        assert toks[0].type == expected_type

    @pytest.mark.parametrize("src,expected_type", [
        (".le.", "OP_LE"),
        (".and.", "OP_AND"),
        (".true.", "LIT_TRUE"),
    ])
    def test_operadores_pontuados_minusculas(self, lexer, src, expected_type):
        """Operadores pontuados são case-insensitive."""
        toks = lex_str(lexer, src)
        assert toks[0].type == expected_type

    def test_true_valor(self, lexer):
        toks = lex_str(lexer, ".TRUE.")
        assert toks[0].type  == "LIT_TRUE"
        assert toks[0].value is True

    def test_false_valor(self, lexer):
        toks = lex_str(lexer, ".FALSE.")
        assert toks[0].type  == "LIT_FALSE"
        assert toks[0].value is False


# ---------------------------------------------------------------------------
# 7. Pontuação
# ---------------------------------------------------------------------------

class TestPunctuation:

    @pytest.mark.parametrize("src,expected_type", [
        ("(", "LPAREN"),
        (")", "RPAREN"),
        (",", "COMMA"),
        (":", "COLON"),
    ])
    def test_pontuacao(self, lexer, src, expected_type):
        toks = lex_str(lexer, src)
        assert toks[0].type == expected_type


# ---------------------------------------------------------------------------
# 8. Fixed-form: labels e continuação de linha
# ---------------------------------------------------------------------------

class TestFixedForm:

    def test_label_emitido(self, lexer):
        """Uma linha com label deve emitir token LABEL antes do código."""
        src = "  10     CONTINUE\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert toks[0].type  == "LABEL"
        assert toks[0].value == 10

    def test_label_seguido_de_continue(self, lexer):
        src = "  10     CONTINUE\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert toks[1].type == "KW_CONTINUE"

    def test_label_de_dois_digitos(self, lexer):
        src = "  99     CONTINUE\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert toks[0].value == 99

    def test_sem_label_nao_emite_label(self, lexer):
        src = "       INTEGER N\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert toks[0].type != "LABEL"

    def test_continuacao_de_linha(self, lexer):
        """Linhas com '*' na col 6 devem ser unidas à linha anterior."""
        toks = tokenize(lexer, "continuation.f")
        # A = 1 + 2 + 3  →  tokens: ID EQUALS INT PLUS INT PLUS INT
        tipos = token_types(toks)
        assert tipos.count("INT_LITERAL") >= 3
        assert tipos.count("PLUS") >= 2

    def test_comentario_linha_C(self, lexer):
        """Linhas que começam com C são comentários e não geram tokens."""
        src = "C isto e um comentario\n       INTEGER N\n"
        toks = lex_str(lexer, src, source_format="fixed")
        tipos = token_types(toks)
        assert "KW_INTEGER" in tipos
        # Nenhum token deve ter valor relacionado com o comentário
        assert all("COMENTARIO" not in str(t.value) for t in toks)

    def test_linha_em_branco_ignorada(self, lexer):
        src = "       INTEGER N\n\n       INTEGER M\n"
        toks = lex_str(lexer, src, source_format="fixed")
        assert token_types(toks).count("KW_INTEGER") == 2


# ---------------------------------------------------------------------------
# 9. Free-form
# ---------------------------------------------------------------------------

class TestFreeForm:

    def test_continuacao_com_ampersand(self, lexer):
        src = "INTEGER A, &\n        B, C\n"
        toks = lex_str(lexer, src, source_format="free")
        ids = [t.value for t in toks if t.type == "ID"]
        assert ids == ["A", "B", "C"]

    def test_comentario_exclamacao(self, lexer):
        src = "INTEGER N ! declara N\n"
        toks = lex_str(lexer, src, source_format="free")
        tipos = token_types(toks)
        assert "KW_INTEGER" in tipos
        assert "ID" in tipos
        # O comentário não deve gerar tokens
        assert len(toks) == 2   # INTEGER + N


# ---------------------------------------------------------------------------
# 10. Números de linha
# ---------------------------------------------------------------------------

class TestLineNumbers:

    def test_lineno_hello(self, lexer):
        toks = tokenize(lexer, "hello.f")
        program_tok = next(t for t in toks if t.type == "KW_PROGRAM")
        print_tok   = next(t for t in toks if t.type == "KW_PRINT")
        end_tok     = next(t for t in toks if t.type == "KW_END")
        assert program_tok.lineno == 1
        assert print_tok.lineno   == 2
        assert end_tok.lineno     == 3

    def test_lineno_fatorial_label(self, lexer):
        toks = tokenize(lexer, "fatorial.f")
        label = next(t for t in toks if t.type == "LABEL")
        assert label.lineno == 8   # linha 8 do ficheiro fatorial.f