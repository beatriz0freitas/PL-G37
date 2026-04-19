# PL-G37 — Compilador Fortran 77

Projeto da UC **Processamento de Linguagens**: implementação de um compilador para um subconjunto de **Fortran 77** usando **Python + PLY**.

---

## Requisitos

- Python **3.11+**
- `ply>=3.11`
- `pytest>=8` (desenvolvimento/testes)
- `make` (recomendado para simplificar comandos)

## Instalação

### A) Opção recomendada:

```bash
make setup
```

Este comando:

- cria `.venv` (se necessário);
- atualiza `pip`;
- instala `requirements.txt` e `requirements-dev.txt`.

Para recriar do zero:

```bash
make setup-recreate
```

Comandos de instalação atualmente mantidos no `Makefile`:

- `make setup`
- `make setup-recreate`

### B) Opção manual:

##### 1) Confirmar a versão de Python

```bash
python --version
```

Deve devolver `3.11.x` (ou superior).
Se o teu sistema usar `python3` em vez de `python`, usa `python3` nos comandos seguintes.

##### 2) Criar ambiente virtual

```bash
python -m venv .venv
```

Este comando cria uma pasta `.venv/` com um Python isolado só para este projeto.

##### 3) Ativar ambiente virtual

**Linux/macOS (bash/zsh):**

```bash
source .venv/bin/activate
```

Quando está ativo, o terminal normalmente mostra `(.venv)` no início da linha.

##### 4) Atualizar `pip` 

```bash
python -m pip install --upgrade pip
```

##### 5) Instalar dependências

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

- `requirements.txt`: dependências de execução do compilador (ex.: `ply`).
- `requirements-dev.txt`: ferramentas de desenvolvimento/testes (ex.: `pytest`).

##### 6) Verificação rápida da instalação

```bash
python -m src --stage lex tests/fixtures/hello.f
```

Se imprimir tokens, a instalação está funcional.

---

## Execução

### A) Forma recomendada (via `Makefile`)

```bash
make lex FIXTURE=tests/fixtures/hello.f
make parse FIXTURE=tests/fixtures/fatorial.f
make ir FIXTURE=tests/fixtures/primo.f
```

Com formato explícito:

```bash
make lex FIXTURE=tests/fixtures/continuation.f FORMAT=fixed
make lex FIXTURE=tests/fixtures/hello.f FORMAT=free
```

Ver todos os atalhos disponíveis:

```bash
make help
```

Comandos de execução atualmente mantidos no `Makefile`:

- `make lex FIXTURE=... [FORMAT=fixed|free]`
- `make parse FIXTURE=... [FORMAT=fixed|free]`
- `make ir FIXTURE=... [FORMAT=fixed|free]`
- `make clean`

### B) Forma direta (sem Makefile)

O compilador é executado por fases com:

```bash
python -m src --stage <fase> [--format fixed|free] [--debug] <ficheiro>
```

### Sintaxe dos argumentos

- `--stage`: fase do pipeline (`lex`, `parse`, `ir`, `sem`, `codegen`)
- `--format`: formato do fonte (`fixed` por omissão, ou `free`)
- `--debug`: saída detalhada para depuração
- `<ficheiro>`: caminho para o `.f`

> Nota: `sem` e `codegen` existem na interface, mas ainda não estão implementados.

##### 1) Análise léxica (`--stage lex`)

Faz tokenização e imprime a lista de tokens com linha, tipo e valor.

Exemplo:

```bash
python -m src --stage lex tests/fixtures/hello.f
```

Uso típico:

- validar rapidamente se o ficheiro é reconhecido pelo lexer;
- confirmar labels, literais e operadores;
- depurar problemas de fixed/free form.

##### 2) Análise sintática (`--stage parse`)

Executa lexer + parser e constrói a AST.
Imprime um resumo (nome do programa, nº de declarações e instruções).

Exemplo:

```bash
python -m src --stage parse tests/fixtures/fatorial.f
```

Com debug:

```bash
python -m src --stage parse --debug tests/fixtures/fatorial.f
```

No modo `--debug`, imprime também a AST para inspeção.

##### 3) Geração de IR (`--stage ir`)

Executa lexer + parser + gerador de IR e imprime as instruções intermédias.

Exemplo:

```bash
python -m src --stage ir tests/fixtures/primo.f
```

Uso típico:

- verificar tradução de `IF`, `DO`, `GOTO`;
- validar labels e saltos;
- preparar futura integração com backend EWVM.

##### 4) Formato de fonte (`--format`)

Por omissão o compilador usa `fixed` (Fortran 77 clássico por colunas).
Quando o ficheiro está em estilo livre, usa `--format free`.

Exemplo (`fixed`, explícito):

```bash
python -m src --stage lex --format fixed tests/fixtures/continuation.f
```

Exemplo (`free`):

```bash
python -m src --stage lex --format free <ficheiro.f>
```

---

## Testes

Executar todos os testes:

```bash
make test
```

Testes por componente:

```bash
make test-lexer
make test-parser
make test-ir
```

Alternativa direta:

```bash
python -m pytest
python -m pytest tests/test_lexer.py
python -m pytest tests/test_parser_smoke.py
python -m pytest tests/test_ir.py
```

---

**Universidade do Minho 2026 | Escola de Engenharia**
