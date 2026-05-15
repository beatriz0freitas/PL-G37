"""Testes do optimizador peephole sobre texto EWVM.

Cobre:
  - identidades aritméticas inteiras  (PUSHI 0/1 + ADD/SUB/MUL/DIV)
  - identidades aritméticas reais     (PUSHF 0.0/1.0 + FADD/FSUB/FMUL/FDIV)
  - conversões redundantes            (ITOF+FTOI, FTOI+ITOF)
  - salto para label imediatamente seguinte (JUMP X; X:)
  - não-alteração de código correcto
  - ponto fixo (múltiplas passagens)
"""

import pytest
from src.codegen.peephole import peephole_optimize


def opt(code: str) -> str:
    """Aplica peephole e normaliza espaços de topo/fim."""
    return peephole_optimize(code.strip())


# ---------------------------------------------------------------------------
# 1. Identidades aritméticas — inteiros
# ---------------------------------------------------------------------------

class TestArithmeticIdentitiesInteger:

    def test_pushi0_add_eliminado(self):
        code = "PUSHG 0\nPUSHI 0\nADD\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushi0_sub_eliminado(self):
        code = "PUSHG 0\nPUSHI 0\nSUB\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushi1_mul_eliminado(self):
        code = "PUSHG 0\nPUSHI 1\nMUL\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushi1_div_eliminado(self):
        code = "PUSHG 0\nPUSHI 1\nDIV\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushi2_add_nao_eliminado(self):
        """Adicionar 2 não é identidade — não alterar."""
        code = "PUSHG 0\nPUSHI 2\nADD\nSTOREG 1"
        assert opt(code) == code

    def test_pushi0_mul_nao_eliminado(self):
        """Multiplicar por 0 zera — não é identidade, não alterar."""
        code = "PUSHG 0\nPUSHI 0\nMUL\nSTOREG 1"
        assert opt(code) == code


# ---------------------------------------------------------------------------
# 2. Identidades aritméticas — reais
# ---------------------------------------------------------------------------

class TestArithmeticIdentitiesReal:

    def test_pushf0_fadd_eliminado(self):
        code = "PUSHG 0\nPUSHF 0.0\nFADD\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushf0_fsub_eliminado(self):
        code = "PUSHG 0\nPUSHF 0.0\nFSUB\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushf1_fmul_eliminado(self):
        code = "PUSHG 0\nPUSHF 1.0\nFMUL\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_pushf1_fdiv_eliminado(self):
        code = "PUSHG 0\nPUSHF 1.0\nFDIV\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"


# ---------------------------------------------------------------------------
# 3. Conversões redundantes
# ---------------------------------------------------------------------------

class TestRedundantConversions:

    def test_itof_ftoi_eliminados(self):
        code = "PUSHG 0\nITOF\nFTOI\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_ftoi_itof_eliminados(self):
        code = "PUSHG 0\nFTOI\nITOF\nSTOREG 1"
        assert opt(code) == "PUSHG 0\nSTOREG 1"

    def test_itof_isolado_preservado(self):
        """ITOF sem par não deve ser eliminado."""
        code = "PUSHG 0\nITOF\nSTOREG 1"
        assert opt(code) == code

    def test_ftoi_isolado_preservado(self):
        code = "PUSHG 0\nFTOI\nSTOREG 1"
        assert opt(code) == code


# ---------------------------------------------------------------------------
# 4. Salto redundante (JUMP X; X:)
# ---------------------------------------------------------------------------

class TestRedundantJump:

    def test_jump_para_proxima_label_removido(self):
        code = "DOTEST1:\nJUMP DOPOS4\nDOPOS4:\nPUSHG 0"
        assert opt(code) == "DOTEST1:\nDOPOS4:\nPUSHG 0"

    def test_jump_then_apos_jz_removido(self):
        """Padrão típico de IF-THEN: JZ ENDIF; JUMP THEN; THEN:"""
        code = "JZ ENDIF2\nJUMP THEN1\nTHEN1:\nPUSHG 0"
        assert opt(code) == "JZ ENDIF2\nTHEN1:\nPUSHG 0"

    def test_jump_dobody_apos_jz_removido(self):
        """Padrão de corpo de DO loop: JZ DOEND; JUMP DOBODY; DOBODY:"""
        code = "JZ DOEND3\nJUMP DOBODY2\nDOBODY2:\nPUSHG 0"
        assert opt(code) == "JZ DOEND3\nDOBODY2:\nPUSHG 0"

    def test_jump_nao_imediato_preservado(self):
        """JUMP para label que não está na próxima linha — preservar."""
        code = "JUMP DOPOS4\nPUSHG 0\nDOPOS4:\nSTOP"
        assert opt(code) == code

    def test_jump_para_label_diferente_preservado(self):
        code = "JUMP LABEL_A\nLABEL_B:\nSTOP"
        assert opt(code) == code


# ---------------------------------------------------------------------------
# 5. Ponto fixo — múltiplas passagens
# ---------------------------------------------------------------------------

class TestFixedPoint:

    def test_dois_jumps_redundantes_consecutivos(self):
        """Dois saltos redundantes no mesmo bloco, removidos em passagens."""
        code = (
            "DOTEST1:\n"
            "JUMP DOPOS4\n"
            "DOPOS4:\n"
            "PUSHG 0\n"
            "JZ DOEND3\n"
            "JUMP DOBODY2\n"
            "DOBODY2:\n"
            "PUSHG 1"
        )
        result = opt(code)
        assert "JUMP DOPOS4" not in result
        assert "JUMP DOBODY2" not in result
        assert "DOPOS4:" in result
        assert "DOBODY2:" in result

    def test_itof_ftoi_em_cadeia_longa(self):
        """Elimina o par mesmo rodeado de outras instruções."""
        code = "PUSHG 0\nPUSHG 1\nFADD\nITOF\nFTOI\nSTOREG 2"
        assert opt(code) == "PUSHG 0\nPUSHG 1\nFADD\nSTOREG 2"


# ---------------------------------------------------------------------------
# 6. Preservação do código correcto
# ---------------------------------------------------------------------------

class TestNoFalsePositives:

    def test_start_stop_inalterados(self):
        code = "START\nPUSHS \"hello\"\nWRITES\nWRITELN\nSTOP"
        assert opt(code) == code

    def test_jump_condicional_preservado(self):
        """JZ não é JUMP — não deve ser afectado."""
        code = "PUSHG 0\nJZ LABEL1\nPUSHG 1\nLABEL1:\nSTOP"
        assert opt(code) == code

    def test_codigo_vazio(self):
        assert peephole_optimize("") == ""

    def test_so_labels(self):
        code = "L1:\nL2:\nL3:"
        assert opt(code) == code

    def test_jump_loop_back_preservado(self):
        """JUMP de volta ao início do loop não deve ser eliminado."""
        code = "LOOP:\nPUSHG 0\nJZ END\nJUMP LOOP\nEND:\nSTOP"
        assert opt(code) == code