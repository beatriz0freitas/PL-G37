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
from src.representacao_intermedia.operadores import IRArrayRef, Temp

from .cfg import build_cfg
from .utils import (
    BLOCK_BOUNDARY_TYPES,
    is_copy_source,
    is_literal,
    rewrite_with_subst,
    temp_key,
)

ConstEnv = dict[str, Any]


def _lookup_const(env: ConstEnv, value: Any) -> Any:
    """Substitui temporário pelo literal conhecido, quando existir."""
    key = temp_key(value)
    return env.get(key, value) if key is not None else value


def _define_const(env: ConstEnv, dest: Any, value: Any) -> None:
    """Atualiza o ambiente de constantes para uma definição."""
    key = temp_key(dest)
    if key is None:
        return
    if is_literal(value):
        env[key] = value
    else:
        env.pop(key, None)


def _kill_const(env: ConstEnv, dest: Any) -> None:
    """Remove informação conhecida de um destino redefinido."""
    key = temp_key(dest)
    if key:
        env.pop(key, None)


def _kill_read_targets(env: ConstEnv, instr: IRRead) -> None:
    """Invalida temporários escritos por READ, se algum alvo for temporário."""
    for target in instr.args:
        if not isinstance(target, IRArrayRef):
            _kill_const(env, target)


def _transfer_const_env(instructions: list[IRInstr], in_env: ConstEnv) -> ConstEnv:
    """Executa a função de transferência de constantes para um bloco."""
    env = dict(in_env)

    for instr in instructions:
        rewritten = rewrite_with_subst(instr, lambda value: _lookup_const(env, value))
        if rewritten is not None:
            if isinstance(rewritten, IRAssign):
                _define_const(env, rewritten.dest, rewritten.src)
            elif isinstance(rewritten, (IROp, IRUnaryOp, IRLoadArray)):
                _kill_const(env, rewritten.dest)
            elif isinstance(rewritten, IRCall) and rewritten.dest is not None:
                _kill_const(env, rewritten.dest)
            elif isinstance(rewritten, IRRead):
                _kill_read_targets(env, rewritten)
            continue

        if isinstance(instr, IRRead):
            _kill_read_targets(env, instr)

    return env


def _meet_const_envs(envs: list[ConstEnv]) -> ConstEnv:
    """Intersecção de constantes iguais vindas de todos os predecessores."""
    if not envs:
        return {}

    common = dict(envs[0])
    for env in envs[1:]:
        for key in list(common):
            if key not in env or env[key] != common[key]:
                common.pop(key, None)
    return common


def constant_propagation(instructions: list[IRInstr]) -> list[IRInstr]:
    """Propaga constantes por data-flow sobre basic blocks e CFG."""
    cfg = build_cfg(instructions)
    if not cfg.blocks:
        return []

    in_envs: dict[int, ConstEnv | None] = {block.id: None for block in cfg.blocks}
    out_envs: dict[int, ConstEnv | None] = {block.id: None for block in cfg.blocks}

    changed = True
    while changed:
        changed = False
        for block in cfg.blocks:
            if block.predecessors:
                pred_envs = [
                    out_envs[pred]
                    for pred in sorted(block.predecessors)
                    if out_envs[pred] is not None
                ]
                if not pred_envs:
                    continue
                new_in = _meet_const_envs(pred_envs)
            else:
                new_in = {}
            new_out = _transfer_const_env(block.instructions, new_in)
            if new_in != in_envs[block.id] or new_out != out_envs[block.id]:
                in_envs[block.id] = new_in
                out_envs[block.id] = new_out
                changed = True

    result: list[IRInstr] = []
    for block in cfg.blocks:
        env = dict(in_envs[block.id] or {})
        for instr in block.instructions:
            rewritten = rewrite_with_subst(instr, lambda value: _lookup_const(env, value))
            if rewritten is None:
                rewritten = instr

            result.append(rewritten)

            if isinstance(rewritten, IRAssign):
                _define_const(env, rewritten.dest, rewritten.src)
            elif isinstance(rewritten, (IROp, IRUnaryOp, IRLoadArray)):
                _kill_const(env, rewritten.dest)
            elif isinstance(rewritten, IRCall) and rewritten.dest is not None:
                _kill_const(env, rewritten.dest)
            elif isinstance(rewritten, IRRead):
                _kill_read_targets(env, rewritten)

    return result


def copy_propagation(instructions: list[IRInstr]) -> list[IRInstr]:
    """Propaga temporários que são cópias diretas."""

    def resolve(value: Any) -> Any:
        """Segue cadeias de cópias para obter o valor mais direto."""
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
        """Regista uma cópia direta ou invalida a cópia anterior."""
        key = temp_key(dest)
        if key is None:
            return
        if is_copy_source(src):
            env[key] = src
        else:
            env.pop(key, None)

    def kill(dest: Any) -> None:
        """Remove uma cópia conhecida quando o destino é redefinido."""
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
            elif isinstance(instr, IRRead):
                for target in instr.args:
                    kill(target)
            continue

        if isinstance(instr, IRRead):
            for target in instr.args:
                kill(target)
            result.append(instr)
            continue

        result.append(instr)

    return result
