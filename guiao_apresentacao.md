# Guião de Demonstração e Apresentação (PL-G37)

**Objetivo:** Demonstrar funcionamento do compilador e explicar escolhas técnicas de forma clara, mostrando domínio individual durante a defesa.

---

## 1) Abertura (30–45s)

- **Apresentar o objetivo do projeto:** compilador de um subconjunto de Fortran 77 para EWVM.
- **Mostrar a pipeline completa:** Lexer → Parser/AST → Semântica → IR → Otimização → EWVM.
- **Referir extras implementados:** IR + otimizações, peephole, subprogramas, intrínsecas, suporte fixed/free.

**Frase simples sugerida:**
“Vamos mostrar o pipeline completo do compilador e justificar as decisões técnicas mais importantes, com uma demonstração por fases.”

---

## 2) Demonstração funcional (5–7 min)

> Todos os comandos assumem execução na raiz do projeto. Se preferirem via Makefile, usar os atalhos equivalentes indicados.

### 2.1 Lexer (30–45s)

**Comando a executar:**

- `python -m src --stage lex tests/fixtures/hello.f`

**O que mostrar:**

- A lista de tokens, incluindo `PROGRAM`, identificadores, literais e operadores.

**O que dizer (frase curta):**
“Aqui vemos a tokenização. Antes do lexer existe um pré-processador que trata colunas, labels e continuações do Fortran 77, por isso o lexer foca-se só em reconhecer tokens.”

**Referência ao código:** “O pré-processamento está em [src/analise_lexica/processor.py](src/analise_lexica/processor.py) e o lexer em [src/analise_lexica/lexer.py](src/analise_lexica/lexer.py).”

**Se pedirem fixed-form:**

- `python -m src --stage lex --format fixed tests/fixtures/continuation.f`

### 2.2 Parser/AST (45–60s)

**Comando a executar:**

- `python -m src --stage parse tests/fixtures/fatorial.f`

**O que mostrar:**

- O resumo da AST (número de declarações e instruções).

**O que dizer:**
“O parser usa gramática LALR(1) com precedências explícitas. Mantemos labels associadas às instruções para suportar `GOTO` e `DO`.”

**Referência ao código:** “A gramática está em [src/analise_sintatica/parser.py](src/analise_sintatica/parser.py) e nos módulos por área, como [src/analise_sintatica/parser_expr.py](src/analise_sintatica/parser_expr.py) e [src/analise_sintatica/parser_stmts.py](src/analise_sintatica/parser_stmts.py). A AST está em [src/analise_sintatica/ast_nodes.py](src/analise_sintatica/ast_nodes.py).”

**Opcional (se quiserem mostrar AST em detalhe):**

- `python -m src --stage parse --debug tests/fixtures/fatorial.f`

### 2.3 Semântica (60–90s)

**Comando a executar:**

- `python -m src --stage sem tests/fixtures/fatorial.f`

**O que mostrar:**

- Ausência de erros semânticos e validação de tipos.

**O que dizer:**
“Nesta fase validamos tipos, declarações e labels. A ambiguidade `ID(args)` é resolvida aqui: se o identificador é array, é acesso; se é função/intrínseca, é chamada.”

**Mencionar controlo de tipagem:**

- “Com `IMPLICIT NONE` desativamos tipagem implícita; também existe a opção `--implicit-typing` via CLI.”

**Referência ao código:** “A análise semântica está em [src/analise_semantica/analyzer.py](src/analise_semantica/analyzer.py), as validações em [src/analise_semantica/checks.py](src/analise_semantica/checks.py), e a tabela de símbolos em [src/analise_semantica/symbols.py](src/analise_semantica/symbols.py).”

### 2.4 IR (45–60s)

**Comando a executar:**

- `python -m src --stage ir tests/fixtures/continuation.f`

**O que mostrar:**

- Instruções de três endereços (temporários, labels e saltos).

**O que dizer:**
“A IR é uniforme e fácil de otimizar. Cada instrução tem no máximo três operandos, o que simplifica análises e transformações.”

**Referência ao código:** “O gerador de IR está em [src/representacao_intermedia/gerador.py](src/representacao_intermedia/gerador.py) e as instruções em [src/representacao_intermedia/instrucoes.py](src/representacao_intermedia/instrucoes.py).”

**Detalhe para o Aluno C (o que referir e onde está no código):**

- “O gerador de IR está em [src/representacao_intermedia/gerador.py](src/representacao_intermedia/gerador.py) e as instruções são definidas em [src/representacao_intermedia/instrucoes.py](src/representacao_intermedia/instrucoes.py).”
- “Os operadores e tipos de operação estão em [src/representacao_intermedia/operadores.py](src/representacao_intermedia/operadores.py).”

### 2.5 Otimização (45–60s)

**Comando a executar:**

- `python -m src --stage opt tests/fixtures/continuation.f`

**O que mostrar:**

- Diferenças face à IR do passo anterior (menos temporários e saltos).

**O que dizer:**
“Aplicamos passes como constant folding e dead code elimination. O objetivo é reduzir trabalho em runtime sem alterar a semântica.”

**Referência ao código:** “A orquestração está em [src/optimizer.py](src/optimizer.py) e os passes principais em [src/otimizacao/folding.py](src/otimizacao/folding.py), [src/otimizacao/propagation.py](src/otimizacao/propagation.py) e [src/otimizacao/liveness.py](src/otimizacao/liveness.py).”

**Detalhe para o Aluno C (o que referir e onde está no código):**

- “A pipeline está em [src/optimizer.py](src/optimizer.py).”
- “Constant folding em [src/otimizacao/folding.py](src/otimizacao/folding.py).”
- “Propagação e CSE em [src/otimizacao/propagation.py](src/otimizacao/propagation.py) e [src/otimizacao/cse.py](src/otimizacao/cse.py).”
- “Liveness/DSE em [src/otimizacao/liveness.py](src/otimizacao/liveness.py).”

### 2.6 Codegen (60–90s)

**Comando a executar:**

- `python -m src --stage codegen tests/fixtures/hello.f > hello.vm`

**O que mostrar:**

- Ficheiro EWVM gerado, com padrões `PUSHG`, `STOREG`, `CALL`, `ALLOC`.

**O que dizer:**
“O backend só usa instruções reais da EWVM. Operações inexistentes são traduzidas em sequências equivalentes, garantindo compatibilidade total.”

**Referência ao código:** “A geração EWVM está em [src/codegen/ewvm_generator.py](src/codegen/ewvm_generator.py), e o peephole em [src/codegen/peephole.py](src/codegen/peephole.py).”

**Detalhe para o Aluno C (o que referir e onde está no código):**

- “O gerador EWVM principal está em [src/codegen/ewvm_generator.py](src/codegen/ewvm_generator.py).”
- “O conjunto de instruções está em [src/codegen/ewvm.py](src/codegen/ewvm.py).”
- “A emissão de stack e utilitários está em [src/codegen/stack_emitter.py](src/codegen/stack_emitter.py).”
- “Arrays e layout de memória: [src/codegen/layout.py](src/codegen/layout.py) e [src/codegen/decls.py](src/codegen/decls.py).”
- “Peephole: [src/codegen/peephole.py](src/codegen/peephole.py).”

**Opcional (mostrar execução na EWVM web):**

- Abrir a VM do docente, colar o conteúdo de `hello.vm` e correr.

**Explicação detalhada com fatorial.vm (recomendado para mostrar mais instruções):**

**Comando a executar:**

- `python -m src --stage codegen tests/fixtures/fatorial.f > fatorial.vm`

**O que dizer enquanto mostra [tests/expected_vm/fatorial.vm](tests/expected_vm/fatorial.vm):**

- “As primeiras `PUSHI 0` reservam espaço global; depois `START` inicia o programa.”
- “O input é feito com `READ` e convertido para inteiro com `ATOI`; o valor vai para memória global com `STOREG 2`.”
- “Inicializamos variáveis com `PUSHI 1` e `STOREG` (ex.: acumulador e contador).”
- “O ciclo é implementado com labels e saltos: `DOTEST1` calcula a condição, `JZ DOEND3` sai do ciclo se for falso.”
- “No corpo, o fatorial é calculado com `MUL` e guardado com `STOREG`.”
- “No fim, usamos `WRITES`/`WRITEI`/`WRITELN` para imprimir a mensagem e o resultado.”

**Se perguntarem onde isto é gerado:**

- “A lógica está em [src/codegen/ewvm_generator.py](src/codegen/ewvm_generator.py), e a alocação global é definida no layout em [src/codegen/layout.py](src/codegen/layout.py).”

> **Dica:** Se o tempo for curto, fazer demo completa com `hello.f` e usar `continuation.f` apenas para mostrar IR/otimização.

---

## 4) Extras implementados (2–3 min)

- **IR + otimizações avançadas** (constant folding, propagation, DCE, CSE, etc.).
- **Peephole no final** para limpar o EWVM gerado.
- **Subprogramas** com convenção de chamada bem definida.
- **Intrínsecas adicionais** (`MOD`, `INT`, `REAL`, `ABS`, `SQRT`, `MAX`, `MIN`).
- **Deteção automática de formato** (fixed/free).

**Explicação simples:** “Estes extras aproximam o compilador do Fortran real e tornam a saída mais eficiente.”

**Referência ao código:** “Os subprogramas estão em [src/analise_sintatica/parser_subprograms.py](src/analise_sintatica/parser_subprograms.py) e as intrínsecas em [src/analise_semantica/intrinsics.py](src/analise_semantica/intrinsics.py).”

---

## 5) Encerramento (30–45s)

- **Resumo rápido:** pipeline completo + validações + IR + backend compatível.
- **Reforçar domínio individual:** cada aluno explica 1–2 decisões que implementou diretamente.

**Frase de fecho sugerida:**
“Mostrámos o funcionamento por fases e justificámos as escolhas técnicas principais, assegurando compatibilidade com a EWVM e suporte realista a Fortran 77.”

---

## 6) Distribuição por alunos (sugestão)

- **Aluno A:** lexer + pré-processador + formatos.
- **Aluno B:** parser/AST + semântica.
- **Aluno C:** IR + otimização + backend EWVM.

> Ajustar conforme quem implementou cada parte.
