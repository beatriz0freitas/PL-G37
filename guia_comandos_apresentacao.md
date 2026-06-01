# Guia de comandos da apresentação

Comandos a executar, na ordem sugerida pelo guião.

1) Lexer (free form)

- make lex FIXTURE=tests/fixtures/hello.f

2) Lexer (fixed form, se necessário)

- make lex FIXTURE=tests/fixtures/continuation.f FORMAT=fixed

# Demo principal — tokenização de um programa simples

  python -m src --stage lex tests/fixtures/hello.f

# Mostrar continuação em fixed-form (o teu ponto forte)

  python -m src --stage lex --format fixed tests/fixtures/continuation.f

  O segundo é o mais importante para ti — mostra claramente o trabalho do
  pré-processador: três linhas físicas com * na coluna 6 que chegam ao lexer
  como uma instrução só.

  Se te pedirem para mostrar free-form explicitamente:

  python -m src --stage lex --format free tests/fixtures/hello.f

  E se perguntarem sobre deteção automática: sem --format, o compilador deteta sozinho

  python -m src --stage lex tests/fixtures/fatorial.f

---



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
