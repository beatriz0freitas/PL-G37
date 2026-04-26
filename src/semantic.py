"""Análise semântica.

Ponto crítico a não esquecer quando esta fase for implementada:

- O parser produz `CallExpr` para formas ambíguas como `A(I)` em expressões.
- Nesta fase semântica é obrigatório resolver essa ambiguidade:
  se `A` estiver declarada como array, o nó deve passar a `ArrayRef`;
  se `A` for função/intrínseca, mantém-se `CallExpr`.

Neste momento o backend EWVM tem uma heurística temporária para compensar a
ausência desta resolução semântica, usando as declarações do programa para
tentar perceber se uma `IRCall` afinal representa um acesso a array. Quando a
análise semântica existir, essa responsabilidade deve passar a estar aqui.

Quando implementar:
- validar declarações (duplicados, uso antes de declarar, etc.)
- validar tipos (INTEGER/REAL/LOGICAL)
- validar labels: DO <label> ... <label> CONTINUE
- regras Fortran 77 (ex: implicit typing, se decidir-mos suportar)
- anotar AST com tipos/informação de símbolos
- resolver `CallExpr` vs `ArrayRef` antes da geração de IR/codegen
"""
