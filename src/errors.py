"""Tipos de erro e localização no ficheiro fonte."""

from dataclasses import dataclass


@dataclass
class SourceLocation:
    filename: str
    line: int
    column: int

    def __str__(self):
        return f"{self.filename}:{self.line}:{self.column}"


class CompileError(Exception):
    def __init__(self, message: str, location: SourceLocation | None = None):
        self.message = message
        self.location = location
        super().__init__(str(self))

    def __str__(self):
        if self.location:
            return f"{self.location}: error: {self.message}"
        return f"error: {self.message}"


class LexError(CompileError):
    pass


class ParseError(CompileError):
    pass


class SemanticError(CompileError):
    pass