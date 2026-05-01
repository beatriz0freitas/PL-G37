"""Extração de metadados semânticos para o backend."""

from __future__ import annotations

import src.analise_sintatica.ast_nodes as ast
from src.analise_semantica.symbols import SymbolTable


ScalarTypes = dict[str, str]
ArrayTypes = dict[str, tuple[str, list[int]]]


def extract_decl_info(program: ast.Program) -> tuple[ScalarTypes, ArrayTypes]:
    """Extrai tipos e dimensões a partir da tabela de símbolos semântica."""

    symbol_table = getattr(program, "symbol_table", None)
    if isinstance(symbol_table, SymbolTable):
        return _extract_from_symbol_table(symbol_table)

    raise RuntimeError(
        "Codegen requer um programa já anotado semanticamente com 'program.symbol_table'."
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
