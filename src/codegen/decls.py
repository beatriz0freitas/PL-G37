"""Extração de metadados semânticos para o backend."""

from __future__ import annotations

from dataclasses import dataclass, field

import src.analise_sintatica.ast_nodes as ast
from src.analise_semantica.symbols import SymbolTable


ScalarTypes = dict[str, str]
ArrayTypes = dict[str, tuple[str, list[int]]]


@dataclass
class SubprogramInfo:
    name: str
    kind: str
    params: list[str]
    scalar_types: ScalarTypes = field(default_factory=dict)
    array_types: ArrayTypes = field(default_factory=dict)
    result_name: str | None = None


@dataclass
class ProgramDeclInfo:
    scalar_types: ScalarTypes
    array_types: ArrayTypes
    subprograms: dict[str, SubprogramInfo]


def extract_decl_info(program: ast.Program) -> tuple[ScalarTypes, ArrayTypes]:
    """Extrai tipos e dimensões a partir da tabela de símbolos semântica."""

    symbol_table = getattr(program, "symbol_table", None)
    if isinstance(symbol_table, SymbolTable):
        return _extract_from_symbol_table(symbol_table)

    raise RuntimeError(
        "Codegen requer um programa já anotado semanticamente com 'program.symbol_table'."
    )


def extract_program_decl_info(program: ast.Program) -> ProgramDeclInfo:
    symbol_table = getattr(program, "symbol_table", None)
    if not isinstance(symbol_table, SymbolTable):
        raise RuntimeError(
            "Codegen requer um programa já anotado semanticamente com 'program.symbol_table'."
        )

    scalar_types, array_types = _extract_from_symbol_table(symbol_table)
    subprograms: dict[str, SubprogramInfo] = {}
    for subprogram in program.subprograms:
        sub_symbol_table = getattr(subprogram, "symbol_table", None)
        if not isinstance(sub_symbol_table, SymbolTable):
            raise RuntimeError(
                f"Codegen requer symbol_table para o subprograma '{subprogram.name}'."
            )
        sub_scalars, sub_arrays = _extract_from_symbol_table(sub_symbol_table)
        info = SubprogramInfo(
            name=subprogram.name,
            kind="function" if isinstance(subprogram, ast.FunctionDef) else "subroutine",
            params=list(subprogram.params),
            scalar_types=sub_scalars,
            array_types=sub_arrays,
            result_name=getattr(subprogram, "result_name", None),
        )
        subprograms[subprogram.name] = info

    return ProgramDeclInfo(
        scalar_types=scalar_types,
        array_types=array_types,
        subprograms=subprograms,
    )


def _extract_from_symbol_table(symbol_table: SymbolTable) -> tuple[ScalarTypes, ArrayTypes]:
    """Extrai tipos e dimensões a partir da tabela de símbolos já validada."""

    scalar_types: ScalarTypes = {}
    array_types: ArrayTypes = {}

    for name, symbol in symbol_table.items():
        if symbol.kind == "scalar":
            scalar_types[name] = symbol.type_name
            continue
        if symbol.kind == "array":
            array_types[name] = (symbol.type_name, list(symbol.dimensions))

    return scalar_types, array_types
