"""Configuração global do compilador."""

from dataclasses import dataclass, field


@dataclass
class Config:
    # "fixed" = colunas fixas Fortran 77 
    # "free"  = free-form 
    source_format: str = "fixed"

    # Fortran 77 é case-insensitive por definição
    case_insensitive: bool = True

    # Largura máxima de linha no modo fixed 
    fixed_line_width: int = 72

    # Modo debug: imprime tokens, AST, IR ao longo do pipeline
    debug: bool = False

    # Ficheiro de entrada 
    input_file: str = ""

    def validate(self):
        if self.source_format not in ("fixed", "free"):
            raise ValueError(f"source_format inválido: {self.source_format!r}")


# Instância global partilhada pelo pipeline
config = Config()
