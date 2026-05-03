"""Otimizações sobre IR (valorização).

Três passes, aplicados em sequência por ``optimize()``:

  1. constant_propagation  — substitui Temp/variáveis por literais conhecidos
  2. constant_folding      — avalia IROp/IRUnaryOp com operandos literais
  3. dead_code_elimination — remove instruções após saltos incondicionais

A ordem propagação → folding → propagação cobre o caso típico em que uma
variável constante é usada numa expressão que, após substituição, fica
totalmente constante e pode ser dobrada num único literal.
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
from src.representacao_intermedia.operadores import Temp


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
    if isinstance(v, str):
        return v
    return None


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
    """Propaga literais atribuídos a Temp/variáveis para os seus usos seguintes.

    O ambiente é limpo conservativamente em IRLabelInstr (ponto de junção
    de fluxo), IRProcBegin e IRProcEnd (fronteiras de escopo).
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
    """Aplica os três passes de otimização em sequência.

    Ordem:
      propagação → folding → propagação → eliminação de código morto

    A segunda passagem de propagação garante que os literais produzidos pelo
    folding sejam também substituídos nos usos seguintes.
    """
    instructions = constant_propagation(instructions)
    instructions = constant_folding(instructions)
    instructions = constant_propagation(instructions)
    instructions = dead_code_elimination(instructions)
    return instructions