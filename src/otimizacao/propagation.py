"""Propagação de constantes e cópias sobre IR."""

from __future__ import annotations

from typing import Any

from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCall,
    IRInstr,
    IRLoadArray,
    IROp,
    IRRead,
    IRUnaryOp,
)
from src.representacao_intermedia.operadores import Temp

from .utils import (
    BLOCK_BOUNDARY_TYPES,
    is_copy_source,
    is_literal,
    rewrite_with_subst,
    temp_key,
)


def constant_propagation(instructions: list[IRInstr]) -> list[IRInstr]:
    """Propaga literais atribuídos a temporários para os seus usos seguintes."""

    def subst(value: Any) -> Any:
        key = temp_key(value)
        return env.get(key, value) if key is not None else value

    def define(dest: Any, value: Any) -> None:
        key = temp_key(dest)
        if key is None:
            return
        if is_literal(value):
            env[key] = value
        else:
            env.pop(key, None)

    def kill(dest: Any) -> None:
        key = temp_key(dest)
        if key:
            env.pop(key, None)

    result: list[IRInstr] = []
    env: dict[str, Any] = {}

    for instr in instructions:
        if isinstance(instr, BLOCK_BOUNDARY_TYPES):
            env.clear()
            result.append(instr)
            continue

        rewritten = rewrite_with_subst(instr, subst)
        if rewritten is not None:
            result.append(rewritten)
            if isinstance(instr, IRAssign):
                define(instr.dest, rewritten.src)
            elif isinstance(instr, (IROp, IRUnaryOp, IRLoadArray)):
                kill(instr.dest)
            elif isinstance(instr, IRCall) and instr.dest is not None:
                kill(instr.dest)
            continue

        if isinstance(instr, IRRead):
            for target in instr.args:
                kill(target)
            result.append(instr)
            continue

        result.append(instr)

    return result


def copy_propagation(instructions: list[IRInstr]) -> list[IRInstr]:
    """Propaga temporários que são cópias diretas."""

    def resolve(value: Any) -> Any:
        if not isinstance(value, Temp):
            return value
        key = str(value)
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
        return value

    def define(dest: Any, src: Any) -> None:
        key = temp_key(dest)
        if key is None:
            return
        if is_copy_source(src):
            env[key] = src
        else:
            env.pop(key, None)

    def kill(dest: Any) -> None:
        key = temp_key(dest)
        if key:
            env.pop(key, None)

    result: list[IRInstr] = []
    env: dict[str, Any] = {}

    for instr in instructions:
        if isinstance(instr, BLOCK_BOUNDARY_TYPES):
            env.clear()
            result.append(instr)
            continue

        rewritten = rewrite_with_subst(instr, resolve)
        if rewritten is not None:
            result.append(rewritten)
            if isinstance(instr, IRAssign):
                define(instr.dest, rewritten.src)
            elif isinstance(instr, (IROp, IRUnaryOp, IRLoadArray)):
                kill(instr.dest)
            elif isinstance(instr, IRCall) and instr.dest is not None:
                kill(instr.dest)
            continue

        if isinstance(instr, IRRead):
            for target in instr.args:
                kill(target)
            result.append(instr)
            continue

        result.append(instr)

    return result
