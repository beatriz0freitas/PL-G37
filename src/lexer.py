# Lexer (análise léxica) com PLY (ply.lex).
#
# Responsabilidades:
# - ler texto Fortran e produzir tokens (keywords, IDs, números, strings, operadores)
# - suportar ou não fixed-format vs free-form
# - tratar operadores pontuados (.LE., .AND., .TRUE., ...)
# - preservar localização (linha/coluna) para erros

