"""Lexer (análise léxica) para Fortran 77 com PLY (ply.lex).

Pré-processamento (fixe-form / free-form) fora da classe PLY,
produz LogicalLine com label já extraído.
"""

import re
import ply.lex as lex

from src.errors import LexError, SourceLocation
from src.analise_lexica.processor import preprocess_fixed, preprocess_free

# Lexer PLY 
class Fortran77Lexer:
    """Analisador léxico para Fortran 77.

    Uso:
        lexer = Fortran77Lexer().build()
        tokens = lexer.tokenize(source, filename="prog.f", source_format="fixed")
    """

    # Palavras-chave: chave = lexema em maiúsculas, valor = tipo do token
    reserved: dict[str, str] = {
        "PROGRAM":    "PROGRAM",
        "END":        "END",
        "STOP":       "STOP",
        "PAUSE":      "PAUSE",
        "RETURN":     "RETURN",
        "CALL":       "CALL",
        "INTEGER":    "INTEGER",
        "REAL":       "REAL",
        "DOUBLE":     "DOUBLE",
        "PRECISION":  "PRECISION",
        "COMPLEX":    "COMPLEX",
        "LOGICAL":    "LOGICAL",
        "CHARACTER":  "CHARACTER",
        "COMMON":     "COMMON",
        "DIMENSION":  "DIMENSION",
        "EQUIVALENCE":"EQUIVALENCE",
        "EXTERNAL":   "EXTERNAL",
        "INTRINSIC":  "INTRINSIC",
        "PARAMETER":  "PARAMETER",
        "SAVE":       "SAVE",
        "IF":         "IF",
        "THEN":       "THEN",
        "ELSE":       "ELSE",
        "ELSEIF":     "ELSEIF",
        "ENDIF":      "ENDIF",
        "DO":         "DO",
        "CONTINUE":   "CONTINUE",
        "GOTO":       "GOTO",
        "READ":       "READ",
        "WRITE":      "WRITE",
        "PRINT":      "PRINT",
        "OPEN":       "OPEN",
        "CLOSE":      "CLOSE",
        "REWIND":     "REWIND",
        "BACKSPACE":  "BACKSPACE",
        "ENDFILE":    "ENDFILE",
        "INQUIRE":    "INQUIRE",
        "FORMAT":     "FORMAT",
        "FUNCTION":   "FUNCTION",
        "SUBROUTINE": "SUBROUTINE",
        "BLOCK":      "BLOCK",
        "DATA":       "DATA",
        "IMPLICIT":   "IMPLICIT",
        "NONE":       "NONE",
    }

    # Lista de tokens 
    tokens: list[str] = [
        "ID",
        "INT_LIT",
        "REAL_LIT",
        "BOOL_LIT",        # .TRUE. / .FALSE.
        "STRING_LIT",
        "LABEL",
        # Operadores relacionais pontuados
        "EQ", "NE", "LT", "LE", "GT", "GE",
        # Operadores lógicos pontuados
        "AND", "OR", "NOT", "EQV", "NEQV",
        # Operadores aritméticos
        "PLUS", "MINUS", "STAR", "SLASH", "POWER",
        # Concatenação de strings
        "CONCAT",
        # Pontuação
        "LPAREN", "RPAREN",
        "COMMA", "COLON", "EQUALS",
    ] + list(reserved.values())

    # Regras simples
    t_PLUS      = r"\+"
    t_MINUS     = r"-"
    t_STAR      = r"\*"
    t_SLASH     = r"/"
    t_LPAREN    = r"\("
    t_RPAREN    = r"\)"
    t_COMMA     = r","
    t_COLON     = r":"
    t_EQUALS    = r"="
    t_ignore    = " \t"


    # Regras com função (têm prioridade sobre as de string; ordem importa)
    def t_POWER(self, t):
        r"\*\*"
        return t
 
    def t_CONCAT(self, t):
        r"\/\/"
        return t
 
    def t_BOOL_LIT(self, t):
        r"\.(TRUE|FALSE)\."
        t.value = t.value.upper() == ".TRUE."
        return t
 
    def t_PUNCT_OP(self, t):
        r"\.(NEQV|EQV|AND|NOT|OR|LE|GE|LT|GT|EQ|NE)\."
        mapping = {
            ".LE.": "LE", ".GE.": "GE", ".LT.": "LT", ".GT.": "GT",
            ".EQ.": "EQ", ".NE.": "NE",
            ".AND.": "AND", ".OR.": "OR", ".NOT.": "NOT",
            ".EQV.": "EQV", ".NEQV.": "NEQV",
        }
        t.type = mapping[t.value.upper()]
        return t
 
    def t_STRING_LIT(self, t):
        r"'([^']|'')*'"
        t.value = t.value[1:-1].replace("''", "'")
        return t
 
    def t_REAL_LIT(self, t):
        r"[0-9]+\.[0-9]*([EeDd][+-]?[0-9]+)?|[0-9]*\.[0-9]+([EeDd][+-]?[0-9]+)?|[0-9]+[EeDd][+-]?[0-9]+"
        t.value = float(t.value.upper().replace("D", "E"))
        return t
 
    def t_INT_LIT(self, t):
        r"[0-9]+"
        t.value = int(t.value)
        return t
 
    def t_ID(self, t):
        r"[A-Za-z][A-Za-z0-9_]*"
        upper   = t.value.upper()
        t.type  = self.reserved.get(upper, "ID")
        t.value = upper
        return t
 
    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)
 
    def t_error(self, t):
        """Reporta caracteres que nenhuma regra léxica reconheceu."""
        raise LexError(
            f"Carácter ilegal {t.value[0]!r}",
            SourceLocation(self._filename, self._current_lineno, t.lexpos + 1),
        )
 
    def __init__(self):
        """Inicializa metadados usados em mensagens de erro e instância PLY."""
        self._filename       = "<stdin>"
        self._current_lineno = 1
        self.lexer           = None
 
    def build(self, **kwargs):
        """Constrói o lexer PLY e devolve a própria instância."""
        self.lexer = lex.lex(module=self, reflags=re.IGNORECASE, **kwargs)
        return self
 
    def tokenize(self, source: str, filename: str = "<stdin>",
                 source_format: str = "fixed") -> list:
        """Tokeniza o texto Fortran e devolve lista de LexToken."""
        self._filename = filename
        logical_lines = (preprocess_fixed if source_format == "fixed"
                         else preprocess_free)(source, filename)
        all_tokens: list = []
        for ll in logical_lines:
            self._current_lineno = ll.lineno
            if ll.label is not None:
                tok = lex.LexToken()
                tok.type, tok.value, tok.lineno, tok.lexpos = "LABEL", ll.label, ll.lineno, 0
                all_tokens.append(tok)
            lx = self.lexer.clone()
            lx.lineno = 1
            lx.input(ll.code)
            for tok in lx:
                tok.lineno = ll.lineno
                all_tokens.append(tok)
        return all_tokens
