# Guia de comandos da apresentação

Comandos a executar, na ordem sugerida pelo guião.

1) Lexer (free form)
- make lex FIXTURE=tests/fixtures/hello.f

2) Lexer (fixed form, se necessário)
- make lex FIXTURE=tests/fixtures/continuation.f FORMAT=fixed

3) Parser/AST
- make parse FIXTURE=tests/fixtures/fatorial.f

4) Parser/AST (com debug, opcional)
- make parse FIXTURE=tests/fixtures/fatorial.f DEBUG=1

5) Semântica
- make sem FIXTURE=tests/fixtures/fatorial.f

6) IR (exemplo com diferenças visíveis)
- make ir FIXTURE=tests/fixtures/continuation.f

7) Otimização (comparar com IR)
- make opt FIXTURE=tests/fixtures/continuation.f

8) Codegen mínimo (hello)
- make codegen FIXTURE=tests/fixtures/hello.f

9) Codegen completo (fatorial)
- make codegen FIXTURE=tests/fixtures/fatorial.f
