
# Estado do Projeto — Compilador Fortran 77

> **Grupo G37 · Processamento de Linguagens 2026**
> Última atualização: 2026-05-03

---

## Resumo

| Etapa                                   | Estado          |
| --------------------------------------- | --------------- |
| Análise Léxica                        | ✅ Completa     |
| Análise Sintática                     | ✅ Implementada |
| Análise Semântica                     | ✅ Implementada |
| Representação Intermédia (AST -> IR) | ✅ Implementada |
| Tradução de Código (IR -> EWVM)      | ✅ Implementada |
| Otimização (valorização)            | ✅ Implementada |
| Testes                                  | ✅ 181/181      |

---

## ✅ Análise Léxica

**Ficheiros:** `src/analise_lexica/lexer.py`, `src/analise_lexica/processor.py`

**Implementado:**

* [X] Lexer com `ply.lex`
* [X] Keywords base do Fortran 77
* [X] Identificadores case-insensitive
* [X] Literais inteiros, reais, lógicos e strings
* [X] Operadores aritméticos, relacionais e lógicos
* [X] Suporte a fixed-form e free-form
* [X] Pré-processamento de labels e continuações

**Validação:**

* [X] `tests/test_lexer.py`

---

## ✅ Análise Sintática

**Ficheiros:** `src/analise_sintatica/parser.py`, `src/analise_sintatica/ast_nodes.py`

**Implementado:**

* [X] `PROGRAM ... END`
* [X] Declarações de tipo
* [X] Atribuições simples e com índice
* [X] Expressões com precedência
* [X] `IF-THEN-ELSE-ENDIF`
* [X] `IF` aritmético
* [X] `DO`, `GOTO`, `CONTINUE`
* [X] `READ`, `PRINT`, `WRITE`
* [X] `CALL`, `STOP`, `RETURN`
* [X] Definições externas `FUNCTION` e `SUBROUTINE`
* [X] AST com `lineno` e `source_label`
* [X] Separação entre programa principal e subprogramas externos

**Validação:**

* [X] `tests/test_parser_smoke.py`

---

## ✅ Análise Semântica

**Ficheiros:** `src/analise_semantica/analyzer.py`, `src/analise_semantica/symbols.py`

**Implementado:**

* [X] Tabela de símbolos para escalares e arrays
* [X] Deteção de declarações duplicadas
* [X] Validação de uso antes de declaração
* [X] Validação de uso antes de inicialização
* [X] Verificação de tipos em atribuições e expressões
* [X] Validação de labels em `GOTO` e `DO ... CONTINUE`
* [X] Anotação da AST com `sem_type` e símbolo associado
* [X] Resolução da ambiguidade `CallExpr` vs `ArrayRef`
* [X] Registo prévio de assinaturas de `FUNCTION` e `SUBROUTINE`
* [X] Validação de aridade e distinção função vs subrotina
* [X] Escopo semântico próprio por subprograma
* [X] Suporte ao retorno de função via atribuição ao nome da função
* [X] Stage `--stage sem` na CLI

**Validação:**

* [X] `tests/test_semantic.py`

---

## ✅ Representação Intermédia (AST -> IR)

**Ficheiros:**

* `src/representacao_intermedia/gerador.py`
* `src/representacao_intermedia/instrucoes.py`
* `src/representacao_intermedia/operadores.py`

**Implementado:**

* [X] Temporários e labels
* [X] Instruções de três endereços
* [X] Saltos condicionais e incondicionais
* [X] `IF`, `IF` aritmético e `DO`
* [X] `READ`, `PRINT`, `WRITE`
* [X] `CALL`, `STOP`, `RETURN`
* [X] Leitura/escrita de arrays na IR
* [X] Marcadores explícitos de início/fim de subprograma
* [X] Lowering de funções e subrotinas definidas pelo utilizador

**Validação:**

* [X] `tests/test_ir.py`

---

## ✅ Tradução de Código (IR -> EWVM)

**Ficheiros:**

* `src/codegen/ewvm.py`
* `src/codegen/ewvm_generator.py`
* `src/codegen/layout.py`
* `src/codegen/decls.py`

**Implementado:**

* [X] Tradução de IR para EWVM
* [X] Integração CLI com `--stage codegen`
* [X] Alocação global
* [X] Operações aritméticas, relacionais e lógicas
* [X] `READ`, `PRINT`, `WRITE`
* [X] Suporte a arrays
* [X] Suporte a intrínsecas base como `MOD`, `INT`, `REAL`, `FLOAT`, `ABS`, `SQRT`, `MAX`, `MIN`
* [X] Convenção de chamada para funções/subrotinas do utilizador
* [X] Frames de ativação com `FP` para parâmetros, locais e retorno
* [X] Emissão de labels dedicadas para subprogramas

**Validação:**

* [X] `tests/test_codegen.py`

---

## ✅ Otimização (valorização)

**Ficheiro:** `src/optimizer.py`

**Implementado:**

* [X] **Constant Folding** — avalia IROp/IRUnaryOp com operandos literais em tempo de compilação (ex: `3 + 4 → 7`); protege contra divisão por zero
* [X] **Constant Propagation** — propaga literais atribuídos a temporários e variáveis simples para os usos seguintes; limpa o ambiente conservativamente em labels e fronteiras de subprograma
* [X] **Dead Code Elimination** — remove instruções após `JUMP`, `STOP` ou `RETURN` até ao próximo label; preserva marcadores estruturais `IRProcBegin`/`IRProcEnd`
* [X] Pipeline público `optimize(instructions)` com ordem: propagação → folding → propagação → DCE
* [X] Integrado na CLI: `--stage opt` mostra a IR otimizada; `--stage codegen` aplica otimização antes da geração EWVM

**Exemplo de efeito:**

```
; Antes
X = 3
t1 = X + 4
Y = t1
PRINT t1

; Depois
X = 3
t1 = 7
Y = 7
PRINT 7
```

**Validação:**

* [X] `tests/test_optimizer.py` (14 testes)

---

## ✅ Estado dos Testes

| Ficheiro                       | Resultado  |
| ------------------------------ | ---------- |
| `tests/test_lexer.py`        | ✅ 98/98   |
| `tests/test_parser_smoke.py` | ✅ 20/20   |
| `tests/test_semantic.py`     | ✅ 13/13   |
| `tests/test_ir.py`           | ✅ 9/9     |
| `tests/test_codegen.py`      | ✅ 27/27   |
| `tests/test_cli.py`          | ✅ 3/3     |
| `tests/test_optimizer.py`    | ✅ 14/14   |
| **Total**                | ✅ 184/184 |

> **Nota:** `test_codegen.py` usa o helper interno `gen_code()` que não passa pelo optimizer (IR bruta → backend), portanto os testes de codegen não são afetados pela otimização. A integração do optimizer no pipeline completo é testada em `test_optimizer.py`.

---

## Estado Atual

O pipeline completo é:

```
lexer → parser → semantic → IR → optimizer → EWVM
```

Todas as etapas estão implementadas. O optimizer aplica três passes clássicos (constant propagation, constant folding, dead code elimination) que reduzem o número de instruções em programas com expressões constantes e código inalcançável.

### Limites funcionais conhecidos

1. Sem `IMPLICIT NONE` efetivo (token reconhecido, regra semântica não aplicada).
2. Sem coerções implícitas gerais; compatibilidade de tipos é estrita.
3. Sem otimizações avançadas de IR (propagação de cópias, eliminação de subexpressões comuns, inlining).
4. Sem execução automática da VM do docente no pipeline de testes.
5. Sem procedimentos internos nem passagem de argumentos por referência completa.
