"""Tipos de erro e localização no ficheiro fonte."""

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


class CompileError(Exception):
    """Erro base do compilador com mensagem e localização opcional."""

    def __init__(self, message: str, location: SourceLocation | None = None):
        """Guarda a mensagem original e a localização associada."""
        self.message = message
        self.location = location
        super().__init__(str(self))

    def __str__(self):
        """Formata o erro no estilo comum de compiladores."""
        if self.location:
            return f"{self.location}: error: {self.message}"
        return f"error: {self.message}"


class LexError(CompileError):
    pass


class ParseError(CompileError):
    pass


class SemanticError(CompileError):
    pass
