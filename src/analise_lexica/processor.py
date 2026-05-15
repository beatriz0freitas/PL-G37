"""Pré-processamento de linhas físicas Fortran → linhas lógicas.

Responsabilidade única: converter o texto fonte (fixe-form ou free-form)
numa lista de LogicalLine, resolvendo:
  - comentários
  - continuações de linha
  - extração de labels numéricos
"""
import re

from src.errors import LexError, SourceLocation

_FREE_LABEL_RE = re.compile(r"^\s*(\d+)\s+(.+)$")


class LogicalLine:
    """Uma linha lógica Fortran após resolução de continuações."""
    __slots__ = ("code", "lineno", "label")

    def __init__(self, code: str, lineno: int, label: int | None):
        """Guarda código normalizado, linha original e label opcional."""
        self.code   = code    # texto do código (pronto para o lexer PLY)
        self.lineno = lineno  # nº da 1ª linha física desta linha lógica
        self.label  = label   # int se houver label numérico, None caso contrário

    def __repr__(self):
        """Representação de depuração usada em testes e inspeção manual."""
        return f"LogicalLine(lineno={self.lineno}, label={self.label!r}, code={self.code!r})"


def preprocess_fixed(source: str, filename: str = "<stdin>") -> list[LogicalLine]:
    """Converte fonte fixed-form (ANSI F77) para lista de LogicalLine.

    Regras:
      col 1     : C, c, * ou ! → comentário (linha ignorada)
      cols 1-5  : zona de label (dígitos opcionais)
      col 6     : não-espaço/não-'0' com zona-de-label vazia → continuação
      cols 7-72 : código (standard ANSI)

    Tolerância: se não há label nem continuação, usa a linha inteira como
    código. Aceita programas escritos sem as restrições de coluna do standard,
    que é o caso comum em editores modernos.
    """
    result: list[LogicalLine] = []
    cur_code: str | None = None
    cur_lineno = 0
    cur_label: int | None = None

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        if not line.strip():
            continue

        # Comentário: primeiro caractere é C, c, * ou !
        if line[0] in ("C", "c", "*", "!"):
            continue

        # Zona de label: colunas 1-5 (índices 0-4)
        label_zone = (line[:5] if len(line) >= 5 else line).strip()
        label_val: int | None = int(label_zone) if label_zone.isdigit() else None

        # Coluna de continuação: índice 5 (coluna 6)
        # Só é continuação se a zona de label estiver vazia
        cont_char = line[5] if len(line) > 5 else " "
        is_cont = (label_zone == "") and (cont_char not in (" ", "0"))

        # Extração do código
        if label_val is not None or is_cont:
            # Standard ANSI: código nas colunas 7-72
            code = (line[6:72] if len(line) > 6 else "").rstrip()
        else:
            # Tolerância: código pode começar na coluna 1
            code = line.rstrip()

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

    Regras:
      - Comentários com ! (fora de strings)
      - Continuação com & no fim da linha
      - Sem restrições de colunas
    """
    result: list[LogicalLine] = []
    cur_code: str | None = None
    cur_lineno = 0
    cur_label: int | None = None

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        # Remover comentário inline !
        in_str = False
        clean: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "'":
                if in_str and i + 1 < len(line) and line[i + 1] == "'":
                    clean.append(ch)
                    clean.append(line[i + 1])
                    i += 2
                    continue
                in_str = not in_str
            if ch == "!" and not in_str:
                break
            clean.append(ch)
            i += 1
        line = "".join(clean).rstrip()

        if not line:
            continue

        cont = line.endswith("&")
        if cont:
            line = line[:-1].rstrip()

        if cur_code is None:
            label_match = _FREE_LABEL_RE.match(line)
            cur_label = None
            if label_match:
                cur_label = int(label_match.group(1))
                line = label_match.group(2).lstrip()

            cur_code   = line
            cur_lineno = lineno
        else:
            cur_code += " " + line

        if not cont:
            result.append(LogicalLine(cur_code, cur_lineno, cur_label))
            cur_code = None
            cur_label = None

    if cur_code is not None:
        result.append(LogicalLine(cur_code, cur_lineno, cur_label))

    return result
