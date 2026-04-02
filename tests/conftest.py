# tests/conftest.py
#
# Fixtures partilhadas por todos os testes.

import sys
from pathlib import Path

import pytest

# Garante que o módulo raiz do compilador está no PYTHONPATH,
# independentemente de onde o pytest é invocado.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.lexer import Fortran77Lexer 

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def lexer():
    """Instância do lexer já construída (reutilizada em toda a sessão)."""
    return Fortran77Lexer().build()


def tokenize(lexer, filename: str, source_format: str = "fixed"):
    """Helper: lê um fixture e devolve a lista de tokens."""
    src = (FIXTURES / filename).read_text(encoding="utf-8")
    return lexer.tokenize(src, filename=filename, source_format=source_format)


def token_types(tokens) -> list[str]:
    """Extrai só os tipos da lista de tokens."""
    return [t.type for t in tokens]


def token_values(tokens) -> list:
    """Extrai só os valores da lista de tokens."""
    return [t.value for t in tokens]