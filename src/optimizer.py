"""Otimizações sobre IR (valorização).

Passes principais aplicados em ``optimize()``:

    1. constant_propagation  — substitui temporários por literais conhecidos
    2. constant_folding      — avalia IROp/IRUnaryOp com operandos literais
    3. copy_propagation      — propaga temporários que são cópias diretas
    4. common_subexpr_elim   — elimina subexpressões comuns simples (por bloco)
    5. dead_store_elim       — remove stores para temporários não usados
    6. jump_simplification   — remove saltos redundantes/constantes
    7. dead_code_elimination — remove instruções após saltos incondicionais

As passagens de propagação e folding são repetidas para capturar cadeias curtas
de temporários e tornar expressões constantes dobráveis.
"""

from __future__ import annotations

from typing import Any

from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCJump,
    IRCall,
    IRInstr,
    IRJump,
    IRLabelInstr,
    IRLoadArray,
    IRStoreArray,
    IROp,
    IRPrint,
    IRProcBegin,
    IRProcEnd,
    IRRead,
    IRReturn,
    IRStop,
    IRUnaryOp,
    IRWrite,
)
from src.representacao_intermedia.operadores import IRArrayRef, Temp


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------

def _is_literal(v: Any) -> bool:
    """Verdadeiro se v é um literal Python (int, float ou bool)."""
    return isinstance(v, (int, float, bool))


def _env_key(v: Any) -> str | None:
    """Chave de pesquisa no ambiente de constantes; None se não aplicável."""
    if isinstance(v, Temp):
        return str(v)
    return None


def _is_temp(v: Any) -> bool:
    return isinstance(v, Temp)


def _temp_key(v: Any) -> str | None:
    return str(v) if isinstance(v, Temp) else None


def _is_copy_source(v: Any) -> bool:
    return isinstance(v, (Temp, str))


def _is_false_literal(v: Any) -> bool:
    if isinstance(v, bool):
        return not v
    if isinstance(v, (int, float)):
        return v == 0
    return False


def _is_true_literal(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return False


def _uses_temp(value: Any) -> set[str]:
    if isinstance(value, Temp):
        return {str(value)}
    if isinstance(value, IRArrayRef):
        used: set[str] = set()
        for idx in value.indices:
            used |= _uses_temp(idx)
        return used
    return set()


# ---------------------------------------------------------------------------
# 1. Constant Folding
# ---------------------------------------------------------------------------

def _eval_binop(op: str, left: Any, right: Any) -> Any:
    """Avalia op(left, right) em tempo de compilação.

    Lança ArithmeticError em divisão por zero,
    ValueError se o operador não tem avaliação estática definida.
    """
    match op:
        case "+":    return left + right
        case "-":    return left - right
        case "*":    return left * right
        case "/":
            if right == 0:
                raise ArithmeticError("divisão por zero")
            # Fortran 77: divisão de dois inteiros é inteira (trunca para zero)
            if isinstance(left, int) and isinstance(right, int):
                return int(left / right)
            return left / right
        case "==":   return int(left == right)
        case "!=":   return int(left != right)
        case "<":    return int(left < right)
        case "<=":   return int(left <= right)
        case ">":    return int(left > right)
        case ">=":   return int(left >= right)
        case "AND":  return int(bool(left) and bool(right))
        case "OR":   return int(bool(left) or bool(right))
        case "EQV":  return int(bool(left) == bool(right))
        case "NEQV": return int(bool(left) != bool(right))
    raise ValueError(f"Operador sem avaliação estática: {op!r}")


def _eval_unary(op: str, operand: Any) -> Any:
    match op:
        case "NEG": return -operand
        case "NOT": return int(not bool(operand))
    raise ValueError(f"Operador unário sem avaliação estática: {op!r}")


def constant_folding(instructions: list[IRInstr]) -> list[IRInstr]:
    """Substitui IROp/IRUnaryOp com ambos os operandos literais pelo resultado."""
    result: list[IRInstr] = []

    for instr in instructions:
        if isinstance(instr, IROp) and _is_literal(instr.left) and _is_literal(instr.right):
            try:
                value = _eval_binop(instr.op, instr.left, instr.right)
                result.append(IRAssign(dest=instr.dest, src=value))
                continue
            except (ArithmeticError, ValueError):
                pass  # Não dobrável — mantém a instrução original

        if isinstance(instr, IRUnaryOp) and _is_literal(instr.operand):
            try:
                value = _eval_unary(instr.op, instr.operand)
                result.append(IRAssign(dest=instr.dest, src=value))
                continue
            except ValueError:
                pass

        result.append(instr)

    return result


# ---------------------------------------------------------------------------
# 2. Constant Propagation
# ---------------------------------------------------------------------------

def constant_propagation(instructions: list[IRInstr]) -> list[IRInstr]:
    """Propaga literais atribuídos a temporários para os seus usos seguintes.

    O ambiente é limpo conservativamente em IRLabelInstr (ponto de junção
    de fluxo), IRProcBegin e IRProcEnd (fronteiras de escopo).
    Variáveis de utilizador não são propagadas para não perder informação de
    tipo necessária ao backend EWVM.
    """

    def subst(v: Any) -> Any:
        """Substitui v pelo literal correspondente, se conhecido."""
        k = _env_key(v)
        return env.get(k, v) if k is not None else v

    def define(dest: Any, value: Any) -> None:
        """Regista dest=value se value é literal; caso contrário invalida dest."""
        k = _env_key(dest)
        if k is None:
            return
        if _is_literal(value):
            env[k] = value
        else:
            env.pop(k, None)

    def kill(dest: Any) -> None:
        """Invalida o valor de dest no ambiente."""
        k = _env_key(dest)
        if k:
            env.pop(k, None)

    result: list[IRInstr] = []
    env: dict[str, Any] = {}

    for instr in instructions:

        # Fronteiras de escopo / pontos de junção: limpa todo o ambiente
        if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
            env.clear()
            result.append(instr)
            continue

        if isinstance(instr, IRAssign):
            new_src = subst(instr.src)
            result.append(IRAssign(dest=instr.dest, src=new_src))
            define(instr.dest, new_src)
            continue

        if isinstance(instr, IROp):
            result.append(IROp(
                op=instr.op, dest=instr.dest,
                left=subst(instr.left), right=subst(instr.right),
            ))
            kill(instr.dest)
            continue

        if isinstance(instr, IRUnaryOp):
            result.append(IRUnaryOp(
                op=instr.op, dest=instr.dest,
                operand=subst(instr.operand),
            ))
            kill(instr.dest)
            continue

        if isinstance(instr, IRCJump):
            result.append(IRCJump(
                cond=subst(instr.cond),
                true_label=instr.true_label,
                false_label=instr.false_label,
            ))
            continue

        if isinstance(instr, IRPrint):
            result.append(IRPrint(args=[subst(a) for a in instr.args]))
            continue

        if isinstance(instr, IRWrite):
            result.append(IRWrite(
                unit=instr.unit, fmt=instr.fmt,
                items=[subst(a) for a in instr.items],
            ))
            continue

        if isinstance(instr, IRRead):
            # READ escreve nos alvos — invalida os valores conhecidos
            for target in instr.args:
                kill(target)
            result.append(instr)
            continue

        if isinstance(instr, IRCall):
            # O resultado da chamada não é um literal estático
            if instr.dest is not None:
                kill(instr.dest)
            result.append(instr)
            continue

        result.append(instr)

    return result


# ---------------------------------------------------------------------------
# 2.5 Copy Propagation
# ---------------------------------------------------------------------------

def copy_propagation(instructions: list[IRInstr]) -> list[IRInstr]:
    """Propaga temporários que são cópias diretas (t1 = t2)."""

    def resolve(v: Any) -> Any:
        if not isinstance(v, Temp):
            return v
        key = str(v)
        seen = set()
        while key in env and key not in seen:
            seen.add(key)
            mapped = env[key]
            if isinstance(mapped, Temp):
                next_key = str(mapped)
                if next_key in env:
                    key = next_key
                    continue
                return mapped
            return mapped
        return v

    def define(dest: Any, src: Any) -> None:
        key = _temp_key(dest)
        if key is None:
            return
        if _is_copy_source(src):
            env[key] = src
        else:
            env.pop(key, None)

    def kill(dest: Any) -> None:
        key = _temp_key(dest)
        if key:
            env.pop(key, None)

    result: list[IRInstr] = []
    env: dict[str, Any] = {}

    for instr in instructions:
        if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
            env.clear()
            result.append(instr)
            continue

        if isinstance(instr, IRAssign):
            new_src = resolve(instr.src)
            result.append(IRAssign(dest=instr.dest, src=new_src))
            define(instr.dest, new_src)
            continue

        if isinstance(instr, IROp):
            result.append(IROp(
                op=instr.op,
                dest=instr.dest,
                left=resolve(instr.left),
                right=resolve(instr.right),
            ))
            kill(instr.dest)
            continue

        if isinstance(instr, IRUnaryOp):
            result.append(IRUnaryOp(
                op=instr.op,
                dest=instr.dest,
                operand=resolve(instr.operand),
            ))
            kill(instr.dest)
            continue

        if isinstance(instr, IRCJump):
            result.append(IRCJump(
                cond=resolve(instr.cond),
                true_label=instr.true_label,
                false_label=instr.false_label,
            ))
            continue

        if isinstance(instr, IRPrint):
            result.append(IRPrint(args=[resolve(a) for a in instr.args]))
            continue

        if isinstance(instr, IRWrite):
            result.append(IRWrite(
                unit=resolve(instr.unit) if instr.unit is not None else None,
                fmt=resolve(instr.fmt) if instr.fmt is not None else None,
                items=[resolve(a) for a in instr.items],
            ))
            continue

        if isinstance(instr, IRRead):
            for target in instr.args:
                kill(target)
            result.append(instr)
            continue

        if isinstance(instr, IRCall):
            result.append(IRCall(
                name=instr.name,
                args=[resolve(a) for a in instr.args],
                dest=instr.dest,
            ))
            if instr.dest is not None:
                kill(instr.dest)
            continue

        if isinstance(instr, IRLoadArray):
            result.append(IRLoadArray(
                dest=instr.dest,
                name=instr.name,
                indices=[resolve(idx) for idx in instr.indices],
            ))
            kill(instr.dest)
            continue

        if isinstance(instr, IRStoreArray):
            result.append(IRStoreArray(
                name=instr.name,
                indices=[resolve(idx) for idx in instr.indices],
                src=resolve(instr.src),
            ))
            continue

        result.append(instr)

    return result


# ---------------------------------------------------------------------------
# 3. Common Subexpression Elimination (por bloco)
# ---------------------------------------------------------------------------

def common_subexpression_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Elimina subexpressões comuns simples (apenas com temporários/literais)."""

    def is_cse_value(v: Any) -> bool:
        return _is_literal(v) or isinstance(v, Temp)

    def norm_value(v: Any) -> Any:
        if isinstance(v, Temp):
            return ("t", str(v))
        if _is_literal(v):
            return ("l", v)
        return ("o", v)

    def key_for_binop(op: str, left: Any, right: Any) -> tuple | None:
        if not is_cse_value(left) or not is_cse_value(right):
            return None
        commutative = {"+", "*", "==", "!=", "AND", "OR", "EQV", "NEQV"}
        l = norm_value(left)
        r = norm_value(right)
        if op in commutative and l > r:
            l, r = r, l
        return ("bin", op, l, r)

    def key_for_unary(op: str, operand: Any) -> tuple | None:
        if not is_cse_value(operand):
            return None
        return ("un", op, norm_value(operand))

    def invalidate_for_temp(temp_name: str) -> None:
        to_remove = [k for k, v in expr_map.items() if temp_name in k_repr[k]]
        for k in to_remove:
            expr_map.pop(k, None)
            k_repr.pop(k, None)

    result: list[IRInstr] = []
    expr_map: dict[tuple, Temp] = {}
    k_repr: dict[tuple, set[str]] = {}

    for instr in instructions:
        if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
            expr_map.clear()
            k_repr.clear()
            result.append(instr)
            continue

        if isinstance(instr, IROp):
            key = key_for_binop(instr.op, instr.left, instr.right)
            if key is not None and key in expr_map:
                result.append(IRAssign(dest=instr.dest, src=expr_map[key]))
            else:
                result.append(instr)
                if isinstance(instr.dest, Temp) and key is not None:
                    expr_map[key] = instr.dest
                    deps = set()
                    deps |= _uses_temp(instr.left)
                    deps |= _uses_temp(instr.right)
                    k_repr[key] = deps
            if isinstance(instr.dest, Temp):
                invalidate_for_temp(str(instr.dest))
            continue

        if isinstance(instr, IRUnaryOp):
            key = key_for_unary(instr.op, instr.operand)
            if key is not None and key in expr_map:
                result.append(IRAssign(dest=instr.dest, src=expr_map[key]))
            else:
                result.append(instr)
                if isinstance(instr.dest, Temp) and key is not None:
                    expr_map[key] = instr.dest
                    deps = set()
                    deps |= _uses_temp(instr.operand)
                    k_repr[key] = deps
            if isinstance(instr.dest, Temp):
                invalidate_for_temp(str(instr.dest))
            continue

        result.append(instr)

    return result


# ---------------------------------------------------------------------------
# 4. Dead Store Elimination (por bloco)
# ---------------------------------------------------------------------------

def dead_store_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Remove stores para temporários que não são usados no bloco."""

    def split_blocks(instrs: list[IRInstr]) -> list[list[IRInstr]]:
        blocks: list[list[IRInstr]] = []
        current: list[IRInstr] = []
        for instr in instrs:
            if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
                if current:
                    blocks.append(current)
                    current = []
                blocks.append([instr])
                continue
            current.append(instr)
        if current:
            blocks.append(current)
        return blocks

    def uses_in_value(value: Any) -> set[str]:
        return _uses_temp(value)

    def uses_in_instr(instr: IRInstr) -> set[str]:
        used: set[str] = set()
        if isinstance(instr, IRAssign):
            used |= uses_in_value(instr.src)
        elif isinstance(instr, IROp):
            used |= uses_in_value(instr.left)
            used |= uses_in_value(instr.right)
        elif isinstance(instr, IRUnaryOp):
            used |= uses_in_value(instr.operand)
        elif isinstance(instr, IRLoadArray):
            for idx in instr.indices:
                used |= uses_in_value(idx)
        elif isinstance(instr, IRCJump):
            used |= uses_in_value(instr.cond)
        elif isinstance(instr, IRPrint):
            for arg in instr.args:
                used |= uses_in_value(arg)
        elif isinstance(instr, IRWrite):
            if instr.unit is not None:
                used |= uses_in_value(instr.unit)
            if instr.fmt is not None:
                used |= uses_in_value(instr.fmt)
            for item in instr.items:
                used |= uses_in_value(item)
        elif isinstance(instr, IRRead):
            for arg in instr.args:
                used |= uses_in_value(arg)
        elif isinstance(instr, IRStoreArray):
            used |= uses_in_value(instr.src)
            for idx in instr.indices:
                used |= uses_in_value(idx)
        elif isinstance(instr, IRCall):
            for arg in instr.args:
                used |= uses_in_value(arg)
        return used

    def defs_in_instr(instr: IRInstr) -> str | None:
        if isinstance(instr, IRAssign) and isinstance(instr.dest, Temp):
            return str(instr.dest)
        if isinstance(instr, IROp) and isinstance(instr.dest, Temp):
            return str(instr.dest)
        if isinstance(instr, IRUnaryOp) and isinstance(instr.dest, Temp):
            return str(instr.dest)
        if isinstance(instr, IRLoadArray) and isinstance(instr.dest, Temp):
            return str(instr.dest)
        return None

    result: list[IRInstr] = []
    for block in split_blocks(instructions):
        if len(block) == 1 and isinstance(block[0], (IRLabelInstr, IRProcBegin, IRProcEnd)):
            result.extend(block)
            continue
        live: set[str] = set()
        kept: list[IRInstr] = []
        for instr in reversed(block):
            defs = defs_in_instr(instr)
            uses = uses_in_instr(instr)
            if defs is not None and defs not in live:
                continue
            kept.append(instr)
            if defs is not None and defs in live:
                live.remove(defs)
            live |= uses
        result.extend(reversed(kept))
    return result


# ---------------------------------------------------------------------------
# 5. Jump Simplification
# ---------------------------------------------------------------------------

def jump_simplification(instructions: list[IRInstr]) -> list[IRInstr]:
    """Simplifica saltos redundantes e condicionais com constantes."""
    result: list[IRInstr] = []
    i = 0
    while i < len(instructions):
        instr = instructions[i]
        next_instr = instructions[i + 1] if i + 1 < len(instructions) else None

        if isinstance(instr, IRJump) and isinstance(next_instr, IRLabelInstr):
            if instr.label == next_instr.label:
                i += 1
                continue

        if isinstance(instr, IRCJump):
            if instr.true_label == instr.false_label:
                result.append(IRJump(instr.true_label))
                i += 1
                continue
            if _is_false_literal(instr.cond):
                result.append(IRJump(instr.false_label))
                i += 1
                continue
            if _is_true_literal(instr.cond):
                result.append(IRJump(instr.true_label))
                i += 1
                continue

        result.append(instr)
        i += 1

    return result


# ---------------------------------------------------------------------------
# 3. Dead Code Elimination
# ---------------------------------------------------------------------------

def dead_code_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """Remove instruções inalcançáveis após IRJump, IRStop ou IRReturn.

    IRLabelInstr, IRProcBegin e IRProcEnd restauram sempre a alcançabilidade:
      - labels são destinos potenciais de saltos;
      - IRProcBegin/End são marcadores estruturais que o backend precisa ver.
    """
    result: list[IRInstr] = []
    unreachable = False

    for instr in instructions:
        if isinstance(instr, (IRLabelInstr, IRProcBegin, IRProcEnd)):
            unreachable = False  # Restaura alcançabilidade

        if not unreachable:
            result.append(instr)

        if isinstance(instr, (IRJump, IRStop, IRReturn)):
            unreachable = True  # O que se segue é inalcançável

    return result


# ---------------------------------------------------------------------------
# Pipeline público
# ---------------------------------------------------------------------------

def optimize(instructions: list[IRInstr]) -> list[IRInstr]:
        """Aplica passes de otimização em sequência.

        Ordem:
            propagação → folding → copy → CSE → propagação → folding → copy
            → propagação → dead-store → jump-simplify → DCE
        """
        instructions = constant_propagation(instructions)
        instructions = constant_folding(instructions)
        instructions = copy_propagation(instructions)
        instructions = common_subexpression_elimination(instructions)
        instructions = constant_propagation(instructions)
        instructions = constant_folding(instructions)
        instructions = copy_propagation(instructions)
        instructions = constant_propagation(instructions)
        instructions = dead_store_elimination(instructions)
        instructions = jump_simplification(instructions)
        instructions = dead_code_elimination(instructions)
        return instructions
