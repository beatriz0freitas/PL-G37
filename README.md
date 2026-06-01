# PL-G37 - Compilador Fortran 77

Projeto da UC **Processamento de Linguagens**: compilador para um subconjunto de **Fortran 77**, desenvolvido em **Python** com **PLY**.

## Requisitos

- Python 3.11+
- `make`

## Instalação

```bash
make setup
```

Este comando cria a `.venv` e instala as dependências do projeto.

Para recriar o ambiente do zero:

```bash
make setup-recreate
```

## Execução

O compilador pode ser executado por fases:

```bash
make lex FIXTURE=tests/fixtures/hello.f FORMAT=free
make parse FIXTURE=tests/fixtures/fatorial.f FORMAT=fixed
make sem FIXTURE=tests/fixtures/fatorial.f FORMAT=fixed
make ir FIXTURE=tests/fixtures/primo.f FORMAT=fixed
make opt FIXTURE=tests/fixtures/continuation.f FORMAT=fixed
make codegen FIXTURE=tests/fixtures/hello.f FORMAT=free
```

O formato do ficheiro pode ser indicado com `FORMAT=fixed`, `FORMAT=free` ou omitido quando a deteção automática for suficiente.

Também é possível executar diretamente:

```bash
.venv/bin/python -m src --stage codegen --format fixed tests/fixtures/fatorial.f
```

## Testes

Para correr todos os testes:

```bash
make test
```

Testes por componente:

```bash
make test-lexer
make test-parser
make test-ir
make test-codegen
```

## Validação na EWVM

Para gerar código EWVM e testar manualmente na VM do docente:

```bash
make codegen FIXTURE=tests/fixtures/hello.f FORMAT=free
```

Depois copia o código gerado para:

```text
https://ewvm.epl.di.uminho.pt/run
```

## Exemplos

Alguns programas de teste estão em:

```text
tests/fixtures/
```

Os respetivos códigos EWVM esperados estão em:

```text
tests/expected_vm/
```

---

Universidade do Minho 2026 | Escola de Engenharia
