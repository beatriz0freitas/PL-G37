"""Lexer (análise léxica) para Fortran 77 com PLY (ply.lex).

Pré-processamento (fixe-form / free-form) fora da classe PLY,
produz LogicalLine com label já extraído.
"""

import re
import ply.lex as lex

from src.errors import LexError, SourceLocation


# Pré-processamento: linhas físicas → linhas lógicas
class LogicalLine:
    """Uma linha lógica Fortran (continuações já resolvidas)."""
    __slots__ = ("code", "lineno", "label")

    def __init__(self, code: str, lineno: int, label: int | None):
        self.code   = code    # texto do código
        self.lineno = lineno  # nº da 1ª linha física desta linha lógica
        self.label  = label   # int se houver label numérico, None caso contrário


def preprocess_fixed(source: str, filename: str = "<stdin>") -> list[LogicalLine]:
    """Converte fonte fixed-form para lista de LogicalLine.

    Regras ANSI F77:
      col 1     : C, c, * ou ! → comentário (linha ignorada)
      cols 1-5  : zona de label (dígitos)
      col 6     : não-espaço/não-'0' com zona-de-label vazia → continuação
      cols 7-72 : código
    Tolerância: se não há label nem continuação, usa a linha inteira como
    código (aceita programas que não respeitam o formato de colunas estrito).
    """
    result: list[LogicalLine] = []
    cur_code: str | None = None
    cur_lineno = 0
    cur_label: int | None = None

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        if not line.strip():
            continue

        if line[0] in ("C", "c", "*", "!"):
            continue

        label_zone = (line[:5] if len(line) >= 5 else line).strip()
        label_val: int | None = int(label_zone) if label_zone.isdigit() else None

        cont_char = line[5] if len(line) > 5 else " "
        is_cont = (label_zone == "") and (cont_char not in (" ", "0"))

        if label_val is not None:
            code = (line[6:72] if len(line) > 6 else "").rstrip()
        elif is_cont:
            code = (line[6:72] if len(line) > 6 else "").rstrip()
        else:
            code = line.rstrip()   # tolerância a código na coluna 1

        if is_cont:
            if cur_code is None:
                raise LexError(
                    "Linha de continuação sem linha anterior",
                    SourceLocation(filename, lineno, 6),
                )
            cur_code += " " + code
        else:
            if cur_code is not None:
                result.append(LogicalLine(cur_code, cur_lineno, cur_label))
            cur_code   = code
            cur_lineno = lineno
            cur_label  = label_val

    if cur_code is not None:
        result.append(LogicalLine(cur_code, cur_lineno, cur_label))

    return result


def preprocess_free(source: str, filename: str = "<stdin>") -> list[LogicalLine]:
    """Converte fonte free-form para lista de LogicalLine.

    Comentários com !, continuação com & no fim da linha.
    """
    result: list[LogicalLine] = []
    cur_code: str | None = None
    cur_lineno = 0

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        # remover comentário inline ! (fora de strings)
        in_str = False
        clean: list[str] = []
        for ch in line:
            if ch == "'":
                in_str = not in_str
            if ch == "!" and not in_str:
                break
            clean.append(ch)
        line = "".join(clean).rstrip()

        if not line:
            continue

        cont = line.endswith("&")
        if cont:
            line = line[:-1].rstrip()

        if cur_code is None:
            cur_code   = line
            cur_lineno = lineno
        else:
            cur_code += " " + line

        if not cont:
            result.append(LogicalLine(cur_code, cur_lineno, None))
            cur_code = None

    if cur_code is not None:
        result.append(LogicalLine(cur_code, cur_lineno, None))

    return result


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
        "HOLLERITH",
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
        "AMPERSAND",
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
    t_AMPERSAND = r"&"
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
        # reflags=re.IGNORECASE já garante matching; upper() normaliza o valor
        t.value = t.value.upper() == ".TRUE."
        return t

    def t_PUNCT_OP(self, t):
        r"\.(NEQV|EQV|AND|NOT|OR|LE|GE|LT|GT|EQ|NE)\."
        # Mapeia para o tipo correspondente (sem prefixo OP_)
        mapping = {
            ".LE.": "LE", ".GE.": "GE", ".LT.": "LT", ".GT.": "GT",
            ".EQ.": "EQ", ".NE.": "NE",
            ".AND.": "AND", ".OR.": "OR", ".NOT.": "NOT",
            ".EQV.": "EQV", ".NEQV.": "NEQV",
        }
        t.type = mapping[t.value.upper()]
        return t

    def t_HOLLERITH(self, t):
        r"[0-9]+[Hh][^\n]+"
        m = re.match(r"([0-9]+)[Hh](.+)", t.value, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            t.value = m.group(2)[:n]
            t.lexer.lexpos -= len(m.group(2)) - n
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
        #normaliza para maiúsculas, depois verifica reserved
        upper  = t.value.upper()
        t.type = self.reserved.get(upper, "ID")
        t.value = upper
        return t

    def t_newline(self, t):
        r"\n+"
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        raise LexError(
            f"Carácter ilegal {t.value[0]!r}",
            SourceLocation(self._filename, self._current_lineno, t.lexpos + 1),
        )


    # Construção e interface pública
    def __init__(self):
        self._filename       = "<stdin>"
        self._current_lineno = 1
        self.lexer           = None

    def build(self, **kwargs):
        """Constrói o lexer PLY. Deve ser chamado antes de tokenize()."""
        # reflags=re.IGNORECASE: matching case-insensitive sem alterar t.value
        self.lexer = lex.lex(module=self, reflags=re.IGNORECASE, **kwargs)
        return self

    def tokenize(self, source: str, filename: str = "<stdin>",
                 source_format: str = "fixed") -> list:
        """Tokeniza o texto Fortran e devolve lista de LexToken.

        Cada token tem: type, value, lineno.
        Labels são emitidos como token LABEL antes do código da linha.
        """
        self._filename = filename

        if source_format == "fixed":
            logical_lines = preprocess_fixed(source, filename)
        else:
            logical_lines = preprocess_free(source, filename)

        all_tokens: list = []

        for ll in logical_lines:
            self._current_lineno = ll.lineno

            # Label → token sintético emitido antes do código
            if ll.label is not None:
                tok        = lex.LexToken()
                tok.type   = "LABEL"
                tok.value  = ll.label
                tok.lineno = ll.lineno
                tok.lexpos = 0
                all_tokens.append(tok)

            # Tokeniza o código da linha lógica
            lx = self.lexer.clone()
            lx.lineno = 1
            lx.input(ll.code)

            for tok in lx:
                tok.lineno = ll.lineno
                all_tokens.append(tok)

        return all_tokens