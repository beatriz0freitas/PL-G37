# Estado do Projeto — Compilador Fortran 77

> **Grupo G37 · Processamento de Linguagens 2026**  
> Última atualização: 2026-04-17

---

## Resumo

| Etapa | Estado |
|---|---|
| Análise Léxica | ✅ Completa |
| Análise Sintática | ✅ Implementada (base funcional) |
| Representação Intermédia (AST -> IR) | ✅ Implementada |
| Análise Semântica | 🔲 Por implementar |
| Tradução de Código (IR -> EWVM) | 🔲 Por implementar |
| Otimização (valorização) | 🔲 Por implementar |
| Testes | ✅ 125/125 a passar |

---

## ✅ Análise Léxica — Completa

**Ficheiros:** `src/analise_lexica/lexer.py`, `src/analise_lexica/processor.py`

**Implementado:**
- [x] Lexer com `ply.lex`
- [x] Keywords base do Fortran 77
- [x] Identificadores case-insensitive (normalização para maiúsculas)
- [x] Literais inteiros, reais e lógicos
- [x] Strings com escape de apóstrofo (`''`)
- [x] Operadores aritméticos, relacionais e lógicos pontuados
- [x] Suporte a fixed-form e free-form
- [x] Pré-processamento de labels e continuações de linha

**Validação:**
- [x] `tests/test_lexer.py` — **98/98**

---

## ✅ Análise Sintática — Implementada (base)

**Ficheiros:** `src/analise_sintatica/parser.py`, `src/analise_sintatica/ast_nodes.py`

**Implementado:**
- [x] Parser com `ply.yacc`
- [x] `PROGRAM ... END`
- [x] Declarações de tipo (`INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE PRECISION`)
- [x] Atribuições simples e com índice
- [x] Expressões aritméticas, relacionais e lógicas com precedência
- [x] `IF-THEN-ELSE-ENDIF`
- [x] `IF` aritmético
- [x] `DO` clássico com label
- [x] `GOTO`, `CONTINUE`, `STOP`, `RETURN`, `CALL`
- [x] `READ`, `PRINT`, `WRITE`
- [x] AST consistente para as etapas seguintes
- [x] Integração com `errors.py` (`ParseError` + `SourceLocation`)
- [x] Preservação do `source_label` em instruções com label (útil para IR/codegen)

**Validação:**
- [x] `tests/test_parser_smoke.py` — **20/20**

---

## ✅ Representação Intermédia (AST -> IR) — Implementada

**Ficheiros:**
- `src/representacao_intermedia/gerador.py`
- `src/representacao_intermedia/instrucoes.py`
- `src/representacao_intermedia/operadores.py`

**Integração CLI:**
- [x] Stage `--stage ir` funcional em `src/cli.py`

**Implementado na IR:**
- [x] Temporários e labels
- [x] Instruções de três endereços (atribuição, unário, binário)
- [x] Saltos condicionais e incondicionais
- [x] `IF-THEN-ELSE`
- [x] `IF` aritmético
- [x] `DO` clássico com fecho em label `CONTINUE`
- [x] `GOTO`
- [x] `READ`, `PRINT`, `WRITE`
- [x] `CALL`, `STOP`, `RETURN`
- [x] Leitura/escrita de arrays na IR

**Validação:**
- [x] `tests/test_ir.py` — **7/7**

---

## 🔲 Análise Semântica — Por implementar

**Ficheiro:** `src/semantic.py`

**Pendente:**
- [ ] Verificação de tipos (`INTEGER`, `REAL`, `LOGICAL`)
- [ ] Uso de variável antes de declaração
- [ ] Deteção de declarações duplicadas
- [ ] Regras de labels (`DO <label>` com `CONTINUE` válido)
- [ ] Anotação semântica da AST

**Tabela de símbolos:**
- `src/symbols.py` permanece em esqueleto

---

## 🔲 Tradução de Código (IR -> EWVM) — Por implementar

**Ficheiro:** `src/codegen/ewvm.py`

**Pendente:**
- [ ] Mapeamento das instruções IR para EWVM
- [ ] Convenções de stack/frame/memória
- [ ] Geração de artefacto final executável na VM

---

## 🔲 Otimização — Por implementar (valorização)

**Ficheiro:** `src/optimizer.py`

**Pendente:**
- [ ] Propagação de constantes
- [ ] Eliminação de código morto
- [ ] Peephole optimization

---

## ✅ Estado dos Testes

| Ficheiro | Resultado |
|---|---|
| `tests/test_lexer.py` | ✅ 98/98 |
| `tests/test_parser_smoke.py` | ✅ 20/20 |
| `tests/test_ir.py` | ✅ 7/7 |
| **Total** | ✅ **125/125** |

**Fixtures atuais:**
- `tests/fixtures/hello.f`
- `tests/fixtures/fatorial.f`
- `tests/fixtures/primo.f`
- `tests/fixtures/continuation.f`

**Ainda por criar (planeado):**
- [ ] `tests/test_semantic.py`
- [ ] Casos de teste para `codegen/ewvm.py`
- [ ] Ficheiros `.vm` esperados para comparação automática de output
