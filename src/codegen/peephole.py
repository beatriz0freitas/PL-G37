"""Otimizações peephole sobre o texto EWVM gerado.

Trabalha directamente sobre as linhas de texto produzidas pelo backend,
eliminando sequências redundantes sem necessitar de análise de fluxo extra.

Padrões suportados (janela de 2 linhas):
  - Identidades aritméticas: x+0, x-0, x*1, x/1  (inteiros e reais)
  - Conversões redundantes:  ITOF;FTOI  e  FTOI;ITOF
  - Salto redundante:        JUMP X  quando X: é a linha imediatamente seguinte
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Tabela de padrões exactos (linha_a, linha_b) → substituição
# ---------------------------------------------------------------------------

_EXACT_PAIRS: dict[tuple[str, str], list[str]] = {
    # Identidades inteiras: empilha 0 ou 1 e opera — resultado é o próprio topo
    ("PUSHI 0", "ADD"):    [],   # x + 0  =  x
    ("PUSHI 0", "SUB"):    [],   # x - 0  =  x
    ("PUSHI 1", "MUL"):    [],   # x * 1  =  x
    ("PUSHI 1", "DIV"):    [],   # x / 1  =  x
    # Identidades reais equivalentes
    ("PUSHF 0.0", "FADD"): [],   # x + 0.0  =  x
    ("PUSHF 0.0", "FSUB"): [],   # x - 0.0  =  x
    ("PUSHF 1.0", "FMUL"): [],   # x * 1.0  =  x
    ("PUSHF 1.0", "FDIV"): [],   # x / 1.0  =  x
    # Conversões numéricas que se anulam mutuamente
    ("ITOF", "FTOI"):      [],   # inteiro → real → inteiro  =  inteiro
    ("FTOI", "ITOF"):      [],   # real → inteiro → real     =  real
}


# ---------------------------------------------------------------------------
# Helpers de reconhecimento de linhas
# ---------------------------------------------------------------------------

def _jump_target(line: str) -> str | None:
    """Devolve 'X' se a linha for 'JUMP X', caso contrário None."""
    if line.startswith("JUMP "):
        return line[5:].strip()
    return None


def _label_name(line: str) -> str | None:
    """Devolve 'X' se a linha for 'X:' (marcador de label), caso contrário None."""
    s = line.strip()
    if s.endswith(":") and " " not in s and len(s) > 1:
        return s[:-1]
    return None


# ---------------------------------------------------------------------------
# Passagem peephole
# ---------------------------------------------------------------------------

def _apply_pass(lines: list[str]) -> tuple[list[str], bool]:
    """Uma passagem de janela deslizante (2 linhas); devolve (novas_linhas, alterou)."""
    result: list[str] = []
    changed = False
    i = 0
    n = len(lines)

    while i < n:
        curr_raw = lines[i]
        curr = curr_raw.strip()

        if i + 1 < n:
            nxt_raw = lines[i + 1]
            nxt = nxt_raw.strip()

            # ── Padrão 1: par exacto na tabela ──────────────────────────
            if (curr, nxt) in _EXACT_PAIRS:
                result.extend(_EXACT_PAIRS[(curr, nxt)])
                changed = True
                i += 2
                continue

            # ── Padrão 2: JUMP X  quando X: está na próxima linha ───────
            target = _jump_target(curr)
            defined = _label_name(nxt)
            if target is not None and target == defined:
                # O salto é redundante; preserva apenas a label de destino
                result.append(nxt_raw)
                changed = True
                i += 2
                continue

        result.append(curr_raw)
        i += 1

    return result, changed


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def peephole_optimize(code: str) -> str:
    """Aplica passes peephole ao texto EWVM até estabilizar (ponto fixo)."""
    lines = code.splitlines()
    changed = True
    while changed:
        lines, changed = _apply_pass(lines)
    return "\n".join(lines)