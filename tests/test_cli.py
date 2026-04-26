"""Testes da CLI e deteção de formato."""

import subprocess
import sys

from src.cli import detect_source_format


class TestFormatDetection:

    def test_detecta_hello_como_free(self):
        src = "PROGRAM HELLO\nPRINT *, 'Ola, Mundo!'\nEND\n"
        assert detect_source_format(src) == "free"

    def test_detecta_fatorial_como_fixed(self):
        src = (
            "PROGRAM FATORIAL\n"
            "       INTEGER N, I, FAT\n"
            "       DO 10 I = 1, N\n"
            "  10     CONTINUE\n"
            "       END\n"
        )
        assert detect_source_format(src) == "fixed"


class TestCliHints:

    def test_cli_sugere_fixed_quando_free_falha_em_fixture_fixed(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src",
                "--stage",
                "codegen",
                "--format",
                "free",
                "tests/fixtures/fatorial.f",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "parece estar em formato 'fixed'" in result.stderr
        assert "--format fixed" in result.stderr
