# Estado do Projeto — Compilador Fortran 77

> **Grupo G37 · Processamento de Linguagens 2026**
> Última atualização: 2026-05-01

---

## Resumo

| Etapa                                   | Estado          |
| --------------------------------------- | --------------- |
| Análise Léxica                          | ✅ Completa     |
| Análise Sintática                       | ✅ Implementada |
| Análise Semântica                       | ✅ Implementada |
| Representação Intermédia (AST -> IR)    | ✅ Implementada |
| Tradução de Código (IR -> EWVM)         | ✅ Implementada |
| Otimização (valorização)                | 🔲 Em falta     |
| Testes                                  | ✅ 167/167      |

---

## ✅ Análise Léxica

**Ficheiros:** `src/analise_lexica/lexer.py`, `src/analise_lexica/processor.py`

**Implementado:**

- [X] Lexer com `ply.lex`
- [X] Keywords base do Fortran 77
- [X] Identificadores case-insensitive
- [X] Literais inteiros, reais, lógicos e strings
- [X] Operadores aritméticos, relacionais e lógicos
- [X] Suporte a fixed-form e free-form
- [X] Pré-processamento de labels e continuações

**Validação:**

- [X] `tests/test_lexer.py`

---

## ✅ Análise Sintática

**Ficheiros:** `src/analise_sintatica/parser.py`, `src/analise_sintatica/ast_nodes.py`

**Implementado:**

- [X] `PROGRAM ... END`
- [X] Declarações de tipo
- [X] Atribuições simples e com índice
- [X] Expressões com precedência
- [X] `IF-THEN-ELSE-ENDIF`
- [X] `IF` aritmético
- [X] `DO`, `GOTO`, `CONTINUE`
- [X] `READ`, `PRINT`, `WRITE`
- [X] `CALL`, `STOP`, `RETURN`
- [X] Definições externas `FUNCTION` e `SUBROUTINE`
- [X] AST com `lineno` e `source_label`
- [X] Separação entre programa principal e subprogramas externos

**Validação:**

- [X] `tests/test_parser_smoke.py`

---

## ✅ Análise Semântica

**Ficheiros:** `src/analise_semantica/analyzer.py`, `src/analise_semantica/symbols.py`

**Implementado:**

- [X] Tabela de símbolos para escalares e arrays
- [X] Deteção de declarações duplicadas
- [X] Validação de uso antes de declaração
- [X] Validação de uso antes de inicialização
- [X] Verificação de tipos em atribuições e expressões
- [X] Validação de labels em `GOTO` e `DO ... CONTINUE`
- [X] Anotação da AST com `sem_type` e símbolo associado
- [X] Resolução da ambiguidade `CallExpr` vs `ArrayRef`
- [X] Registo prévio de assinaturas de `FUNCTION` e `SUBROUTINE`
- [X] Validação de aridade e distinção função vs subrotina
- [X] Escopo semântico próprio por subprograma
- [X] Suporte ao retorno de função via atribuição ao nome da função
- [X] Stage `--stage sem` na CLI

**Notas:**

- [X] O pipeline `ir` e `codegen` passa obrigatoriamente pela análise semântica.
- [X] A heurística temporária no backend EWVM para distinguir arrays de chamadas deixou de ser necessária.
- [X] O `conversor.f` já faz parte do subconjunto aceite.

**Validação:**

- [X] `tests/test_semantic.py`

---

## ✅ Representação Intermédia (AST -> IR)

**Ficheiros:**

- `src/representacao_intermedia/gerador.py`
- `src/representacao_intermedia/instrucoes.py`
- `src/representacao_intermedia/operadores.py`

**Implementado:**

- [X] Temporários e labels
- [X] Instruções de três endereços
- [X] Saltos condicionais e incondicionais
- [X] `IF`, `IF` aritmético e `DO`
- [X] `READ`, `PRINT`, `WRITE`
- [X] `CALL`, `STOP`, `RETURN`
- [X] Leitura/escrita de arrays na IR
- [X] Marcadores explícitos de início/fim de subprograma
- [X] Lowering de funções e subrotinas definidas pelo utilizador

**Validação:**

- [X] `tests/test_ir.py`

---

## ✅ Tradução de Código (IR -> EWVM)

**Ficheiros:**

- `src/codegen/ewvm.py`
- `src/codegen/ewvm_generator.py`
- `src/codegen/layout.py`
- `src/codegen/decls.py`

**Implementado:**

- [X] Tradução de IR para EWVM
- [X] Integração CLI com `--stage codegen`
- [X] Alocação global
- [X] Operações aritméticas, relacionais e lógicas
- [X] `READ`, `PRINT`, `WRITE`
- [X] Suporte a arrays
- [X] Suporte a intrínsecas base como `MOD`, `INT`, `REAL` e `FLOAT`
- [X] Convenção de chamada para funções/subrotinas do utilizador
- [X] Slots reservados para argumentos e valor de retorno
- [X] Emissão de labels dedicadas para subprogramas

**Limitações conhecidas:**

- [ ] Ainda não há execução automática do `.vm` na VM do docente para validação end-to-end.
- [X] O backend extrai metadados de declarações exclusivamente da tabela de símbolos semântica e falha explicitamente sem `program.symbol_table`.
- [X] Intrínsecas `ABS`, `SQRT`, `MAX` e `MIN` têm agora tradução no backend EWVM.

**Validação:**

- [X] `tests/test_codegen.py`

---

## 🔲 Otimização

**Ficheiro:** `src/optimizer.py`

**Em falta:**

- [ ] Propagação de constantes
- [ ] Eliminação de código morto
- [ ] Peephole optimization

---

## ✅ Estado dos Testes

| Ficheiro                  | Resultado |
| ------------------------- | --------- |
| `tests/test_lexer.py`     | ✅ 98/98  |
| `tests/test_parser_smoke.py` | ✅ 20/20 |
| `tests/test_semantic.py`  | ✅ 13/13  |
| `tests/test_ir.py`        | ✅ 9/9    |
| `tests/test_codegen.py`   | ✅ 9/9    |
| `tests/test_cli.py`       | ✅ 3/3    |
| **Total**                 | ✅ 167/167 |

---

## Estado Atual

O pipeline funcional atual é:

`lexer -> parser -> semantic -> IR -> EWVM`

Neste momento, a única etapa estruturalmente em falta é a otimização. O pipeline já suporta definições externas `FUNCTION`/`SUBROUTINE`, incluindo análise semântica por escopo, lowering para IR e geração EWVM com convenção explícita de chamada. A fixture `conversor.f` já é aceite e testada de ponta a ponta.
