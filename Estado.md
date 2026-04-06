# Estado do Projeto — Compilador Fortran 77

> **Grupo G37 · Processamento de Linguagens 2026**  
> Última atualização: 2026-04-06

---

## Resumo

| Etapa | Estado |
|---|---|
| Análise Léxica | ✅ Completa |
| Análise Sintática | ✅ Implementada (base funcional) |
| Análise Semântica | 🔲 Por implementar |
| Tradução de Código (→ EWVM) | 🔲 Por implementar |
| Otimização *(valorização)* | 🔲 Por implementar |
| Testes | 🟡 Parcial (léxico + sintático base) |

---

## ✅ Análise Léxica — Completa

**Requisitos do enunciado:**
- [x] Analisador léxico com `ply.lex`
- [x] Identificação de palavras-chave: `PROGRAM`, `INTEGER`, `REAL`, `LOGICAL`, `IF`, `DO`, `GOTO`, `PRINT`, `READ`, `END`, e mais 40+ keywords F77
- [x] Identificadores (normalizados para maiúsculas — F77 é case-insensitive)
- [x] Números inteiros e reais (incluindo notação científica `E`/`D`)
- [x] Strings entre apóstrofes (com `''` como escape de `'`)
- [x] Operadores aritméticos: `+`, `-`, `*`, `/`, `**`
- [x] Operadores relacionais pontuados: `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.`
- [x] Operadores lógicos pontuados: `.AND.`, `.OR.`, `.NOT.`, `.EQV.`, `.NEQV.`
- [x] Literais lógicos: `.TRUE.`, `.FALSE.`
- [x] Concatenação de strings: `//`
- [x] Símbolos especiais: `(`, `)`, `,`, `:`, `=`, `&`

**Decisão de formato:**
- [x] Suporte a **fixed-form** (colunas fixas ANSI X3.9-1978)
    - Comentários com `C`, `c`, `*` ou `!` na coluna 1
    - Zona de label nas colunas 1-5
    - Coluna 6 como marcador de continuação
    - Código nas colunas 7-72 (com tolerância a código na coluna 1)
- [x] Suporte a **free-form** (extensão moderna)
    - Comentários com `!`
    - Continuação com `&`

**Testes do léxico: 97/97 a passar** (`pytest tests/test_lexer.py`)

---

## ✅ Análise Sintática — Implementada (base)

**Ficheiros:** `src/analise_sintatica/parser.py`, `src/analise_sintatica/ast_nodes.py`

**Requisitos do enunciado:**
- [x] Analisador sintático com `ply.yacc`
- [x] Gramática base para Fortran 77 cobrindo:
    - [x] Declaração de programa: `PROGRAM <nome>` ... `END`
    - [x] Declarações de tipo: `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE PRECISION`
    - [x] Expressões aritméticas com precedência correta (`**` > `*`/`/` > `+`/`-`)
    - [x] Expressões relacionais (`.EQ.`, `.LE.`, etc.)
    - [x] Expressões lógicas (`.AND.`, `.OR.`, `.NOT.`, `.EQV.`, `.NEQV.`)
    - [x] Atribuição: `VAR = EXPR` e `ARR(I,...) = EXPR`
    - [x] `IF-THEN-ELSE-ENDIF` (bloco)
    - [x] `IF` aritmético: `IF (EXPR) label1, label2, label3`
    - [x] Ciclo `DO`: `DO <label> VAR = inicio, fim [, passo]`
    - [x] `GOTO <label>`
    - [x] `CONTINUE`
    - [x] `READ *, varlist`, `PRINT *, exprlist`, `WRITE (...)`
    - [x] `STOP`, `RETURN`, `CALL`
- [x] Construção da AST (em `src/analise_sintatica/ast_nodes.py`)
- [x] Reporte de erros sintáticos com `ParseError` + `SourceLocation` (ficheiro/linha/coluna)

**Para valorização:**
- [ ] `SUBROUTINE` e `FUNCTION` (definição e chamada)
- [ ] Arrays: `DIMENSION`, acesso `A(I)`
- [ ] `COMMON`, `PARAMETER`, `SAVE`

**Notas atuais:**
- [x] `errors.py` está integrado no parser (`ParseError`) e no lexer (`LexError`)
- [x] Mensagens de erro seguem o formato `ficheiro:linha:coluna: error: mensagem`
- [ ] Melhorar recuperação de erro (atualmente falha rápida na primeira inconformidade)

---

## 🔲 Análise Semântica — Por implementar

**Ficheiro:** `src/semantic.py` (esqueleto presente)

**Requisitos do enunciado:**
- [ ] Verificação de tipos: `INTEGER`, `REAL`, `LOGICAL`
- [ ] Declaração de variáveis antes de uso
- [ ] Deteção de variáveis duplicadas
- [ ] Validação de labels: o label de `DO <label>` deve corresponder a um `CONTINUE`
- [ ] Tabela de símbolos (`src/symbols.py`): `declare()`, `lookup()`, scopes

**Decisão em aberto:** suportar ou não *implicit typing* do F77 (variáveis começadas por `I`-`N` são `INTEGER` por omissão). Recomendação: suportar mas avisar, para compatibilidade com os exemplos do enunciado.

---

## 🔲 Tradução de Código — Por implementar

**Ficheiros:** `src/ir.py`, `src/ewvm.py` (esqueletos presentes)

**Opção A — Direto para EWVM** (sem IR):
- [ ] Percorrer a AST e emitir instruções EWVM diretamente

**Opção B — Via IR** (recomendada para valorização):
- [ ] Definir IR (ex: código de 3 endereços ou stack-based)
- [ ] Converter AST → IR (`src/ir.py`)
- [ ] Converter IR → EWVM (`src/ewvm.py`)

**Construções mínimas a suportar na geração de código:**
- [ ] Expressões aritméticas e lógicas
- [ ] Atribuição de variáveis
- [ ] `IF-THEN-ELSE`
- [ ] Ciclos `DO` com label
- [ ] `GOTO`
- [ ] `READ` e `PRINT`

---

## 🔲 Otimização — Por implementar *(valorização)*

**Ficheiro:** `src/optimizer.py` (esqueleto presente)

- [ ] Propagação de constantes
- [ ] Eliminação de código morto
- [ ] Peephole optimizations no IR/EWVM

---

## 🟡 Testes — Parcial

**Estado atual:**

| Ficheiro | Cobertura | Resultado |
|---|---|---|
| `tests/test_lexer.py` | Léxico completo | ✅ 97/97 |
| `tests/test_parser_smoke.py` | Parser + integração de erros (smoke) | ✅ implementado |

**Fixtures disponíveis:**

| Ficheiro | Programa |
|---|---|
| `tests/fixtures/hello.f` | Olá Mundo |
| `tests/fixtures/fatorial.f` | Fatorial com `DO`/`CONTINUE` |
| `tests/fixtures/primo.f` | Teste de primalidade com `IF`/`GOTO` |
| `tests/fixtures/continuation.f` | Continuação de linha (fixed-form) |

**Por criar:**
- [ ] `tests/fixtures/somaarr.f` — Exemplo 4 do enunciado (arrays)
- [ ] `tests/fixtures/conversor.f` — Exemplo 5 do enunciado (função)
- [ ] `tests/test_semantic.py` — Testes semânticos
- [ ] Ficheiros `.vm` com output esperado para cada fixture

---

## Estrutura atual do repositório

```
fortran77c/
├── src/
│   ├── __init__.py
│   ├── analise_lexica/
│   │   ├── lexer.py        ✅ implementado
│   │   └── processor.py    ✅ implementado
│   ├── analise_sintatica/
│   │   ├── ast_nodes.py    ✅ implementado
│   │   └── parser.py       ✅ implementado
│   ├── errors.py       ✅ implementado
│   ├── config.py       ✅ implementado
│   ├── semantic.py     🔲 esqueleto
│   ├── symbols.py      🔲 esqueleto
│   ├── ir.py           🔲 esqueleto
│   ├── optimizer.py    🔲 esqueleto
│   └── codegen/
│       └── ewvm.py     🔲 esqueleto
├── bin/
│   ├── fortran77c      🔲 esqueleto
│   └── setup           🔲 esqueleto
├── src/cli.py          🟡 parcial (stages lex + parse funcionais)
├── tests/
│   ├── conftest.py     ✅ implementado
│   ├── fixtures/
│   │   ├── hello.f         ✅
│   │   ├── fatorial.f      ✅
│   │   ├── primo.f         ✅
│   │   └── continuation.f  ✅
│   ├── test_lexer.py        ✅ 97 testes
│   └── test_parser_smoke.py ✅ parser + erros
├── pyproject.toml      ✅
└── requirements*.txt   ✅
```

