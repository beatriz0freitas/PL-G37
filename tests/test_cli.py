"""Testes da CLI e deteção de formato."""

import subprocess
import sys
from pathlib import Path

import pytest

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

    def test_cli_aceita_labels_numericos_tambem_em_free_form(self):
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

        assert result.returncode == 0
        assert "F10:" in result.stdout
        assert "STOP" in result.stdout


class TestExpectedVmArtifacts:

    @pytest.mark.parametrize("fixture,source_format", [
        ("hello", "free"),
        ("fatorial", "fixed"),
        ("primo", "fixed"),
        ("somaarr", "fixed"),
        ("conversor", "fixed"),
        ("continuation", "fixed"),
    ])
    def test_fixture_vm_esperado_esta_sincronizado(self, fixture, source_format):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src",
                "--stage",
                "codegen",
                "--format",
                source_format,
                f"tests/fixtures/{fixture}.f",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        expected = Path(f"tests/expected_vm/{fixture}.vm").read_text(encoding="utf-8")
        assert result.returncode == 0
        assert result.stdout.strip() == expected.strip()
