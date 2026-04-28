# Estado do Projeto — Compilador Fortran 77

> **Grupo G37 · Processamento de Linguagens 2026**
> Última atualização: 2026-04-28

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
| Testes                                  | ✅ 154/154      |

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
- [X] AST com `lineno` e `source_label`

**Validação:**

- [X] `tests/test_parser_smoke.py`

---

## ✅ Análise Semântica

**Ficheiros:** `src/semantic.py`, `src/symbols.py`

**Implementado:**

- [X] Tabela de símbolos para escalares e arrays
- [X] Deteção de declarações duplicadas
- [X] Validação de uso antes de declaração
- [X] Validação de uso antes de inicialização
- [X] Verificação de tipos em atribuições e expressões
- [X] Validação de labels em `GOTO` e `DO ... CONTINUE`
- [X] Anotação da AST com `sem_type` e símbolo associado
- [X] Resolução da ambiguidade `CallExpr` vs `ArrayRef`
- [X] Stage `--stage sem` na CLI

**Notas:**

- [X] O pipeline `ir` e `codegen` passa obrigatoriamente pela análise semântica.
- [X] A heurística temporária no backend EWVM para distinguir arrays de chamadas deixou de ser necessária.
- [ ] Ainda não há suporte completo a funções/subprogramas definidos pelo utilizador.

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

**Limitações conhecidas:**

- [ ] Ainda não há execução automática do `.vm` na VM do docente para validação end-to-end.
- [ ] O backend ainda extrai metadados de declarações diretamente da AST, apesar de a tabela de símbolos já existir.
- [ ] Intrínsecas como `ABS`, `SQRT`, `MAX` e `MIN` continuam com suporte parcial no backend EWVM.

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
| `tests/test_semantic.py`  | ✅ 10/10  |
| `tests/test_ir.py`        | ✅ 8/8    |
| `tests/test_codegen.py`   | ✅ 7/7    |
| `tests/test_cli.py`       | ✅ 3/3    |
| **Total**                 | ✅ 154/154 |

---

## Estado Atual

O pipeline funcional atual é:

`lexer -> parser -> semantic -> IR -> EWVM`

Neste momento, a única etapa estruturalmente em falta é a otimização. O parser ainda não suporta casos como `INTEGER FUNCTION ...`, por isso fixtures como `conversor.f` continuam fora do subconjunto aceite.
