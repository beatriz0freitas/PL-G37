"""Especificacao das funcoes intrinsecas suportadas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntrinsicSpec:
    name: str
    arity: int | None
    return_type: str | None = None


INTRINSICS: dict[str, IntrinsicSpec] = {
    "MOD": IntrinsicSpec("MOD", 2, "INTEGER"),
    "INT": IntrinsicSpec("INT", 1, "INTEGER"),
    "REAL": IntrinsicSpec("REAL", 1, "REAL"),
    "FLOAT": IntrinsicSpec("FLOAT", 1, "REAL"),
    "ABS": IntrinsicSpec("ABS", 1, None),
    "SQRT": IntrinsicSpec("SQRT", 1, "REAL"),
    "MAX": IntrinsicSpec("MAX", 2, None),
    "MIN": IntrinsicSpec("MIN", 2, None),
}
