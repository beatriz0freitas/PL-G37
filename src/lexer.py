"""Lexer (análise léxica) para Fortran 77 com PLY (ply.lex).

Suporta dois formatos de fonte:
  - fixed-form (default): colunas fixas ANSI X3.9-1978
      col 1     : 'C', 'c', '*' ou '!' → comentário
      cols 1-5  : zona de label (dígitos opcionais)
      col 6     : não-espaço/não-'0' e zona de label vazia → continuação
      cols 7-72 : código
  - free-form: sem restrição de colunas; continuação com '&'; comentários com '!'

O lexer normaliza para maiúsculas (F77 é case-insensitive), excecto em strings.
"""

import ply.lex as lex

from src.errors import LexError, SourceLocation


# Pré-processamento de linhas físicas → linhas lógicas

class LogicalLine:
    """Uma linha lógica Fortran (após resolução de continuações)."""
    __slots__ = ("code", "lineno", "label")

    def __init__(self, code: str, lineno: int, label: int | None):
        self.code   = code    # texto do código (sem zona de label nem col de cont.)
        self.lineno = lineno  # nº da linha original onde esta linha lógica começa
        self.label  = label   # int se houver label, None caso contrário


def preprocess_fixed(source: str, filename: str = "<stdin>") -> list[LogicalLine]:
    """Converte fonte em fixed-form para lista de LogicalLine."""
    result: list[LogicalLine] = []
    cur_code: str | None = None
    cur_lineno = 0
    cur_label: int | None = None

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        if not line.strip():
            continue

        # col 1 (índice 0) = comentário
        if line[0] in ("C", "c", "*", "!"):
            continue

        # zona de label: índices 0-4 (colunas 1-5)
        label_zone = (line[:5] if len(line) >= 5 else line).strip()
        label_val: int | None = int(label_zone) if label_zone.isdigit() else None

        # col de continuação: índice 5 (coluna 6)
        cont_char = line[5] if len(line) > 5 else " "
        is_cont = (label_zone == "") and (cont_char not in (" ", "0"))

        # código: índices 6-71 (colunas 7-72)
        code = (line[6:72] if len(line) > 6 else "").rstrip()

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
    """Converte fonte em free-form para lista de LogicalLine."""
    result: list[LogicalLine] = []
    cur_code: str | None = None
    cur_lineno = 0

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        # remover comentário inline '!' (fora de strings)
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



# Implementação do Lexer 

def _upcase_outside_strings(code: str) -> str:
    """Normaliza para maiúsculas tudo fora de strings (apostrofes).
    Garante que operadores pontuados (.le., .and., ...) e keywords
    são sempre reconhecidos independentemente do case original.
    """
    result: list[str] = []
    in_str = False
    i = 0
    while i < len(code):
        ch = code[i]
        if ch == "'" and not in_str:
            in_str = True
            result.append(ch)
        elif ch == "'" and in_str:
            if i + 1 < len(code) and code[i + 1] == "'":
                result.append("''")
                i += 2
                continue
            else:
                in_str = False
                result.append(ch)
        elif in_str:
            result.append(ch)   # preserva case dentro da string
        else:
            result.append(ch.upper())
        i += 1
    return "".join(result)


class Fortran77Lexer:
    
    # Palavras-chave                                                       
    reserved: dict[str, str] = {
        "PROGRAM":    "KW_PROGRAM",
        "END":        "KW_END",
        "STOP":       "KW_STOP",
        "PAUSE":      "KW_PAUSE",
        "RETURN":     "KW_RETURN",
        "CALL":       "KW_CALL",
        "INTEGER":    "KW_INTEGER",
        "REAL":       "KW_REAL",
        "DOUBLE":     "KW_DOUBLE",
        "PRECISION":  "KW_PRECISION",
        "COMPLEX":    "KW_COMPLEX",
        "LOGICAL":    "KW_LOGICAL",
        "CHARACTER":  "KW_CHARACTER",
        "COMMON":     "KW_COMMON",
        "DIMENSION":  "KW_DIMENSION",
        "EQUIVALENCE":"KW_EQUIVALENCE",
        "EXTERNAL":   "KW_EXTERNAL",
        "INTRINSIC":  "KW_INTRINSIC",
        "PARAMETER":  "KW_PARAMETER",
        "SAVE":       "KW_SAVE",
        "IF":         "KW_IF",
        "THEN":       "KW_THEN",
        "ELSE":       "KW_ELSE",
        "ELSEIF":     "KW_ELSEIF",
        "ENDIF":      "KW_ENDIF",
        "DO":         "KW_DO",
        "CONTINUE":   "KW_CONTINUE",
        "GOTO":       "KW_GOTO",
        "READ":       "KW_READ",
        "WRITE":      "KW_WRITE",
        "PRINT":      "KW_PRINT",
        "OPEN":       "KW_OPEN",
        "CLOSE":      "KW_CLOSE",
        "REWIND":     "KW_REWIND",
        "BACKSPACE":  "KW_BACKSPACE",
        "ENDFILE":    "KW_ENDFILE",
        "INQUIRE":    "KW_INQUIRE",
        "FORMAT":     "KW_FORMAT",
        "FUNCTION":   "KW_FUNCTION",
        "SUBROUTINE": "KW_SUBROUTINE",
        "BLOCK":      "KW_BLOCK",
        "DATA":       "KW_DATA",
        "IMPLICIT":   "KW_IMPLICIT",
        "NONE":       "KW_NONE",
    }

    # Lista de tokens                                                      

    tokens: list[str] = [
        # Identificadores e literais
        "ID",
        "INT_LITERAL",
        "REAL_LITERAL",
        "STRING_LITERAL",
        "HOLLERITH",

        # Label de instrução (ex: 10 em "DO 10 I = ...")
        "LABEL",

        # Operadores relacionais pontuados
        "OP_EQ", "OP_NE", "OP_LT", "OP_LE", "OP_GT", "OP_GE",

        # Operadores lógicos pontuados
        "OP_AND", "OP_OR", "OP_NOT", "OP_EQV", "OP_NEQV",

        # Literais lógicos
        "LIT_TRUE", "LIT_FALSE",

        # Operadores aritméticos
        "PLUS", "MINUS", "STAR", "SLASH", "POWER",

        # Concatenação de strings
        "CONCAT",

        # Pontuação
        "LPAREN", "RPAREN",
        "COMMA", "COLON", "EQUALS",
        "AMPERSAND",

    ] + list(reserved.values())

    
    # Regras simples (strings)                                            

    t_PLUS      = r"\+"
    t_MINUS     = r"-"
    t_STAR      = r"\*"      # POWER (**) tem prioridade por ser função
    t_SLASH     = r"/"       # CONCAT (//) tem prioridade
    t_LPAREN    = r"\("
    t_RPAREN    = r"\)"
    t_COMMA     = r","
    t_COLON     = r":"
    t_EQUALS    = r"="
    t_AMPERSAND = r"&"
    t_ignore    = " \t"

    # Regras com função (ordem: mais específicas primeiro)                
    def t_POWER(self, t):
        r"\*\*"
        return t

    def t_CONCAT(self, t):
        r"\/\/"
        return t

    # Operadores pontuados: .LE. .AND. .TRUE. etc.
    # A alternância está ordenada do mais longo para o mais curto.
    def t_PUNCT_OP(self, t):
        r"\.(NEQV|EQV|AND|NOT|OR|TRUE|FALSE|LE|GE|LT|GT|EQ|NE)\."
        val = t.value.upper()
        mapping = {
            ".LE.":    ("OP_LE",    None),
            ".GE.":    ("OP_GE",    None),
            ".LT.":    ("OP_LT",    None),
            ".GT.":    ("OP_GT",    None),
            ".EQ.":    ("OP_EQ",    None),
            ".NE.":    ("OP_NE",    None),
            ".AND.":   ("OP_AND",   None),
            ".OR.":    ("OP_OR",    None),
            ".NOT.":   ("OP_NOT",   None),
            ".EQV.":   ("OP_EQV",   None),
            ".NEQV.":  ("OP_NEQV",  None),
            ".TRUE.":  ("LIT_TRUE",  True),
            ".FALSE.": ("LIT_FALSE", False),
        }
        t.type, new_val = mapping[val]
        if new_val is not None:
            t.value = new_val
        return t

    def t_HOLLERITH(self, t):
        r"[0-9]+[Hh][^\n]+"
        import re
        m = re.match(r"([0-9]+)[Hh](.+)", t.value)
        if m:
            n = int(m.group(1))
            # devolve apenas os n caracteres; o resto é re-tokenizado
            t.value  = m.group(2)[:n]
            # ajusta o lexer para não consumir além dos n chars
            t.lexer.lexpos -= len(m.group(2)) - n
        return t

    def t_STRING_LITERAL(self, t):
        r"'([^']|'')*'"
        t.value = t.value[1:-1].replace("''", "'")
        return t

    def t_REAL_LITERAL(self, t):
        r"[0-9]+\.[0-9]*([EeDd][+-]?[0-9]+)?|[0-9]*\.[0-9]+([EeDd][+-]?[0-9]+)?|[0-9]+[EeDd][+-]?[0-9]+"
        t.value = float(t.value.upper().replace("D", "E"))
        return t

    def t_INT_LITERAL(self, t):
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
        raise LexError(
            f"Carácter ilegal {t.value[0]!r}",
            SourceLocation(self._filename, self._current_lineno, t.lexpos + 1),
        )


    # Construção e interface pública                                       
    def __init__(self):
        self._filename      = "<stdin>"
        self._current_lineno = 1
        self.lexer          = None

    def build(self, **kwargs):
        """Constrói o lexer PLY. Chamar antes de tokenize()."""
        self.lexer = lex.lex(module=self, **kwargs)
        return self

    def tokenize(self, source: str, filename: str = "<stdin>",
                 source_format: str = "fixed") -> list:
        """
        Analisa o texto Fortran e devolve a lista de tokens.
 
        Parâmetros
        ----------
        source        : texto completo do ficheiro
        filename      : nome do ficheiro (para mensagens de erro)
        source_format : "fixed" ou "free"
 
        Devolve
        -------
        Lista de LexToken com atributos: type, value, lineno
        """
        self._filename = filename
 
        if source_format == "fixed":
            logical_lines = preprocess_fixed(source, filename)
        else:
            logical_lines = preprocess_free(source, filename)
 
        all_tokens: list = []
 
        for ll in logical_lines:
            self._current_lineno = ll.lineno
 
            # Se a linha lógica tem label, emite token LABEL sintético
            if ll.label is not None:
                tok         = lex.LexToken()
                tok.type    = "LABEL"
                tok.value   = ll.label
                tok.lineno  = ll.lineno
                tok.lexpos  = 0
                all_tokens.append(tok)
 
            # Tokeniza o código da linha lógica
            lx = self.lexer.clone()
            lx.lineno = 1
            lx.input(_upcase_outside_strings(ll.code))
 
            for tok in lx:
                tok.lineno = ll.lineno   # linha original, não linha PLY
                all_tokens.append(tok)
 
        return all_tokens
 