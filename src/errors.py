"""Tipos de erro, localização e formatação de diagnósticos."""

from dataclasses import dataclass


@dataclass
class SourceLocation:
    """Localização textual de um erro no ficheiro de entrada."""

    filename: str
    line: int
    column: int

    def __str__(self):
        """Formata a localização como ficheiro:linha:coluna."""
        return f"{self.filename}:{self.line}:{self.column}"


def source_line_at(source: str, line: int) -> str | None:
    """Devolve a linha pedida de um texto fonte, usando numeração 1-based."""
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return None


def _format_source_excerpt(location: SourceLocation, source_line: str, length: int = 1) -> str:
    """Formata uma linha fonte com sublinhado no ponto do erro."""
    width = max(4, len(str(location.line)))
    column = max(1, location.column)
    underline_len = max(1, length)
    line_len = len(source_line)

    # Permite apontar para o fim da linha em erros como "expressão em falta".
    caret_column = min(column, line_len + 1)
    gutter = f"{location.line:>{width}} | "
    spacer = " " * (caret_column - 1)
    underline = "^" * underline_len
    return "\n".join([
        f"{gutter}{source_line}",
        f"{' ' * width} | {spacer}{underline}",
    ])


class CompileError(Exception):
    """Erro base do compilador com mensagem e localização opcional."""

    def __init__(
        self,
        message: str,
        location: SourceLocation | None = None,
        source_line: str | None = None,
        length: int = 1,
    ):
        """Guarda a mensagem original e a localização associada."""
        self.message = message
        self.location = location
        self.source_line = source_line
        self.length = length
        super().__init__(str(self))

    def attach_source(self, source: str) -> "CompileError":
        """Anexa a linha fonte ao diagnóstico, quando há localização."""
        if self.location and self.source_line is None:
            self.source_line = source_line_at(source, self.location.line)
        return self

    def __str__(self):
        """Formata o erro no estilo comum de compiladores."""
        if self.location:
            header = f"{self.location}: error: {self.message}"
            if self.source_line is not None:
                return "\n".join([
                    header,
                    _format_source_excerpt(self.location, self.source_line, self.length),
                ])
            return header
        return f"error: {self.message}"


class LexError(CompileError):
    pass


class ParseError(CompileError):
    """Erro sintático, podendo agregar vários diagnósticos do mesmo run."""

    def __init__(
        self,
        message: str | None = None,
        location: SourceLocation | None = None,
        source_line: str | None = None,
        length: int = 1,
        errors: list[CompileError] | None = None,
    ):
        self.errors = errors or []
        if self.errors:
            first = self.errors[0]
            message = message or f"{len(self.errors)} erros de sintaxe encontrados"
            location = first.location
            source_line = first.source_line
            length = first.length
        super().__init__(message or "Erro de sintaxe", location, source_line, length)

    def attach_source(self, source: str) -> "ParseError":
        """Anexa contexto de fonte ao erro agregado e aos seus filhos."""
        super().attach_source(source)
        for error in self.errors:
            error.attach_source(source)
        return self

    def __str__(self):
        """Mostra todos os erros recolhidos, um por bloco de diagnóstico."""
        if self.errors:
            return "\n".join(str(error) for error in self.errors)
        return super().__str__()


class SemanticError(CompileError):
    pass
