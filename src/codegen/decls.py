"""Extração de metadados das declarações AST para o backend."""

from __future__ import annotations

from typing import Any

import src.analise_sintatica.ast_nodes as ast


ScalarTypes = dict[str, str]
ArrayTypes = dict[str, tuple[str, list[int]]]


def extract_decl_info(program: ast.Program) -> tuple[ScalarTypes, ArrayTypes]:
    """Extrai tipos e dimensões diretamente das declarações do programa."""

    scalar_types: ScalarTypes = {}
    array_types: ArrayTypes = {}

    for decl in program.decls:
        typename = decl.typename.upper()
        for var in decl.variables:
            if isinstance(var, str):
                scalar_types[var] = typename
                continue

            if isinstance(var, ast.ArrayDecl):
                dims = [_const_dimension(dim) for dim in var.dimensions]
                array_types[var.name] = (typename, dims)
                continue

            raise TypeError(f"Declaração não suportada no codegen: {type(var).__name__}")

    return scalar_types, array_types


def _const_dimension(node: Any) -> int:
    """Obtém o valor inteiro de uma dimensão de array declarada."""

    if isinstance(node, ast.IntLit):
        return node.value
    if isinstance(node, int):
        return node
    raise ValueError(f"Dimensão de array não constante no codegen: {node!r}")
