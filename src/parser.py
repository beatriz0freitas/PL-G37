# Parser (análise sintática) com PLY (ply.yacc).
#
# Responsabilidades:
# - definir gramática (regras p_*) para Fortran 77
# - construir AST usando nós definidos em ast_nodes.py
# - reportar erros de sintaxe com localização
#
# Notas:
# - controlar precedência/associatividade (operadores aritméticos e lógicos)
# - suportar labels (ex: DO 10 ... / 10 CONTINUE) e GOTO

