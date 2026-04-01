# PL-G37 — Compilador Fortran 77 (PL 2026)

Este repositório contém uma estrutura/base (arquitetura) para o projeto.

Nota: a pedido, os ficheiros de implementação foram deixados apenas com comentários
(documentação do que cada ficheiro deve fazer), sem código executável.

## Estrutura (alto nível)

- `src/fortran77c/lexer.py`: deverá conter o lexer (ply.lex)
- `src/fortran77c/parser.py`: deverá conter o parser (ply.yacc) e produzir AST
- `src/fortran77c/semantic.py`: deverá conter análise semântica (tabela de símbolos)
- `src/fortran77c/ir.py`: deverá conter a representação intermédia
- `src/fortran77c/codegen/`: deverá conter o backend (VM)
- `tests/`: deverá conter testes do compilador

## Setup / Execução

Quando voltarem a introduzir implementação, podem reativar:
- `bin/setup` para preparar ambiente
- `bin/fortran77c` para correr o compilador
