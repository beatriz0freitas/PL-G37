# Documentação Técnica — Compilador Fortran 77

## PL-G37 · Processamento de Linguagens 2026

---

## 1. Visão Geral do Projeto

O projeto consiste na implementação de um compilador para um subconjunto significativo de **Fortran 77** (ANSI X3.9-1978) que traduz programas Fortran para código executável na **EWVM** (máquina virtual fornecida pelo docente).

### Objetivo final do pipeline

```
Fortran 77 source (.f)
        │
        ▼  Análise Léxica (ply.lex)
   Token stream
        │
        ▼  Análise Sintática (ply.yacc)
      AST
        │
        ▼  Análise Semântica
   AST anotada
        │
        ▼  Geração de IR (three-address code)
      IR
        │
        ▼  Geração de Código
   EWVM bytecode / texto
```

### Linguagem alvo

Fortran 77 é uma linguagem **case-insensitive**, com formato de linha fixo (colunas 1–72), sem inferência de tipos (via *implicit typing* — decidiu-se não suportar implicitly-typed variables por simplicidade), e com construções de controlo de fluxo baseadas em labels numéricos (`DO <label>`, `GOTO <label>`, IF aritmético).

---

## 2. Arquitetura e Pipeline de Compilação

### Estrutura de módulos

```
src/
├── analise_lexica/
│   ├── lexer.py         # Fortran77Lexer — tokenização com PLY lex
│   └── processor.py     # Pré-processamento de linhas físicas → lógicas
├── analise_sintatica/
│   ├── parser.py        # Fortran77Parser — gramática PLY yacc
│   └── ast_nodes.py     # Hierarquia de nós da AST (dataclasses)
├── representacao_intermedia/
│   ├── gerador.py       # IRGenerator — visitor AST → IR
│   ├── instrucoes.py    # Instrucoes IR (IRAssign, IROp, IRCJump, ...)
│   └── operadores.py    # Tipos auxiliares (Temp, Label, LoopContext, ...)
├── codegen/
│   ├── ewvm.py          # API pública do backend EWVM
│   ├── ewvm_generator.py# Backend principal IR -> EWVM
│   ├── decls.py         # Extração de metadados semânticos
│   └── layout.py        # Layout de memória global
├── errors.py            # CompileError, LexError, ParseError, SourceLocation
├── analise_semantica/
│   ├── analyzer.py      # Análise semântica
│   ├── symbols.py       # Tabela de símbolos
│   ├── intrinsics.py    # Assinaturas de intrínsecas
│   └── types.py         # Conjuntos auxiliares de tipos
├── optimizer.py         # Optimizações IR [esqueleto]
├── cli.py               # Interface de linha de comando
├── config.py            # Configuração global
└── __main__.py          # Entry point `python -m src`

tests/
├── conftest.py          # Fixtures pytest partilhadas
├── test_lexer.py        # 98 testes ao lexer
├── test_parser_smoke.py # 20 testes ao parser
├── test_ir.py           # Testes à geração de IR
├── test_semantic.py     # Testes de análise semântica
├── test_codegen.py      # Testes do backend EWVM
└── fixtures/            # Programas Fortran de referência
    ├── hello.f
    ├── fatorial.f
    ├── primo.f
    ├── somaarr.f
    ├── conversor.f
    └── continuation.f
```

### Decisão de arquitectura: pipeline sequencial com separação estrita de fases

O compilador segue a separação clássica em fases independentes, tal como ensinado nos notebooks da UC (NB03, NB04, NB05). Cada fase comunica apenas com a fase seguinte via uma estrutura de dados bem definida:

- **Lexer → Parser**: lista de `LexToken` (tokens PLY)
- **Parser → IR Generator**: árvore `ast.Program` (AST)
- **IR Generator → Codegen**: lista de `IRInstr`

**Por quê esta separação?** Facilita o teste isolado de cada fase, permite substituir um módulo sem reescrever os outros, e segue o modelo canónico da teoria dos compiladores (Aho et al., "Dragon Book").

**Alternativa não adoptada**: compilação em *single-pass* (tokenização + parsing + geração de código ao mesmo tempo). Seria mais eficiente em memória mas torna o código muito mais difícil de testar, depurar e estender — especialmente para Fortran 77 onde os labels numéricos exigem um segundo passe (ou backpatching) para resolver `GOTO` e `DO`.

---

## 3. Etapa 1 — Análise Léxica

**Ficheiros:** `src/analise_lexica/lexer.py`, `src/analise_lexica/processor.py`

### 3.1 Pré-processamento de linhas físicas (processor.py)

O Fortran 77 em formato *fixed-form* tem regras de colunas estritas que não são adequadas para processar directamente com `ply.lex`:

| Coluna(s) | Significado                                                                            |
| --------- | -------------------------------------------------------------------------------------- |
| 1         | `C`, `c`, `*` ou `!` → linha de comentário                                   |
| 1–5      | Zona de label numérico (dígitos)                                                     |
| 6         | Não-espaço e não-`0` (com zona de label vazia) → continuação da linha anterior |
| 7–72     | Código Fortran                                                                        |

**Solução implementada**: o módulo `processor.py` converte o texto fonte num `list[LogicalLine]`, onde cada `LogicalLine` agrega:

- o código limpo (colunas 7–72 ou linha completa em tolerância)
- o número de linha da primeira linha física
- o label numérico, se presente

Esta separação resolve três problemas antes de o lexer PLY sequer ver o código:

1. Comentários eliminados
2. Linhas de continuação concatenadas
3. Labels numéricos emitidos como tokens `LABEL` especiais

**Tolerância ao formato**: se a linha não tem label nem caracter de continuação, o código é retirado da linha inteira (sem restrição de colunas). Isto suporta programas escritos em editores modernos sem respeitar estritamente as colunas ANSI.

**Free-form**: suportado também via `preprocess_free`, que usa `&` no fim da linha como continuação e `!` como início de comentário inline (compatível com Fortran 90/95 free-form, mas exposto também para Fortran 77 por conveniência nos testes).

**Alternativa não adoptada**: implementar o pré-processamento dentro do próprio lexer PLY (usando estados de lexer, `lexer.begin('state')`). Seria mais compacto mas misturaria a lógica de pré-processamento com a tokenização, dificultando o teste isolado e a leitura do código.

### 3.2 Tokenização (lexer.py)

O lexer é implementado como classe `Fortran77Lexer` usando `ply.lex`. A abordagem orientada a objetos (em vez de usar funções e variáveis globais) permite ter múltiplas instâncias independentes e passar o lexer como argumento ao parser.

**Tokens implementados:**

| Categoria               | Exemplos                                                                                                                                                                                                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Keywords                | `PROGRAM`, `END`, `IF`, `THEN`, `ELSE`, `ENDIF`, `DO`, `CONTINUE`, `GOTO`, `READ`, `PRINT`, `WRITE`, `CALL`, `STOP`, `RETURN`, `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE`, `PRECISION`, ... |
| Identificadores         | `ID` (normalizado para maiúsculas)                                                                                                                                                                                                          |
| Literais inteiros       | `INT_LIT` → `int` Python                                                                                                                                                                                                                  |
| Literais reais          | `REAL_LIT` → `float` Python (suporta `E`, `e`, `D`, `d` em notação científica)                                                                                                                                                 |
| Literais lógicos       | `BOOL_LIT` — `.TRUE.` → `True`, `.FALSE.` → `False`                                                                                                                                                                               |
| Strings                 | `STRING_LIT` — apóstrofe duplo `''` como escape para `'`                                                                                                                                                                               |
| Operadores relacionais  | `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` (forma `.OP.`)                                                                                                                                                                                |
| Operadores lógicos     | `AND`, `OR`, `NOT`, `EQV`, `NEQV` (forma `.OP.`)                                                                                                                                                                                   |
| Operadores aritméticos | `PLUS`, `MINUS`, `STAR`, `SLASH`, `POWER` (`**`), `CONCAT` (`//`)                                                                                                                                                              |
| Pontuação             | `LPAREN`, `RPAREN`, `COMMA`, `COLON`, `EQUALS`                                                                                                                                                                                       |
| Labels                  | `LABEL` (emitido pelo pré-processador, não pelo PLY)                                                                                                                                                                                       |

**Case-insensitivity**: Fortran 77 é explicitamente case-insensitive. A normalização é feita na regra `t_ID`, que converte para maiúsculas antes de consultar o dicionário `reserved`. Os operadores pontuados (`.EQ.`, etc.) são capturados pela regra `t_PUNCT_OP` com `re.IGNORECASE`. O lexer é construído com `reflags=re.IGNORECASE`.

**Ambiguidade STAR / POWER**: a regra `t_POWER` para `**` tem prioridade sobre `t_STAR` para `*` porque PLY dá prioridade às funções com docstring de expressão regular mais longa. Isto garante que `A**B` é tokenizado como `[ID, POWER, ID]` e não `[ID, STAR, STAR, ID]`.

**Ambiguidade operadores lógicos / literais lógicos**: `.TRUE.` e `.FALSE.` são capturados por `t_BOOL_LIT` antes que `.AND.` etc. sejam tentados, porque `t_BOOL_LIT` tem docstring mais específica e PLY processa as funções por ordem de definição (e comprimento do padrão).

**Hollerith**: suportado (`t_HOLLERITH`), embora não seja gerado nenhum nó AST específico — é tratado como string.

**Adaptador de token para o parser**: o método `tokenize()` devolve uma `list[LexToken]` (não um iterador). O parser recebe um objecto `TokenAdapter` que adapta esta lista à interface `token()`/`input()` esperada pelo PLY yacc. Esta separação permite que o pré-processamento (labels, continuações) seja feito antes de o parser começar, sem interferências.

**Alternativa não adoptada**: usar um lexer PLY em modo *streaming* (sem pré-tokenizar tudo). Seria mais eficiente para ficheiros muito grandes mas impossibilitaria a injecção de tokens sintéticos (`LABEL`) produzidos pelo pré-processador fora do PLY.

---

## 4. Etapa 2 — Análise Sintática e AST

**Ficheiros:** `src/analise_sintatica/parser.py`, `src/analise_sintatica/ast_nodes.py`

### 4.1 Escolha do método de parsing: LALR(1) com PLY yacc

O Fortran 77 tem uma gramática com ambiguidades contextuais que tornam a análise LL(1) impraticável sem transformações extensas (remoção de recursividade esquerda, factorização esquerda). Em particular:

- Expressões aritméticas com precedência e associatividade requerem recursividade esquerda na gramática natural
- A distinção entre `A(I)` como acesso a array e `A(I)` como chamada de função é semântica, não sintática

**PLY yacc** implementa um parser **LALR(1)** — *Left-to-right scanning, Rightmost derivation, 1 token lookahead*. É o método canónico para compiladores de linguagens de programação:

- Resolve as ambiguidades de expressões usando a tabela de **precedências e associatividades** declarada em `precedence`
- Suporta gramáticas com recursividade esquerda naturalmente
- Gera a tabela de parsing automaticamente a partir das regras BNF nas docstrings

**Alternativa não adoptada — parsing recursivo descendente manual (LL)**: seria mais simples de implementar para um subconjunto pequeno de Fortran, mas exigiria reescrita de todas as regras de expressão para eliminar recursividade esquerda e conflitos FIRST/FIRST — o que resulta numa gramática menos legível e mais difícil de manter.

**Alternativa não adoptada — ANTLR4**: gerador de parsers mais moderno, com suporte nativo a gramáticas com ambiguidades e melhor recuperação de erros. No entanto, exigiria uma dependência pesada externa e afastaria o projecto da plataforma PLY já usada para o lexer.

### 4.2 Gramática implementada

A gramática cobre o subconjunto de Fortran 77 definido no enunciado:

```
program      : PROGRAM ID body END subprogram_list

body         : decl_list stmt_list

decl_list    : ε | decl_list decl
decl         : INTEGER var_decl_list
             | REAL var_decl_list
             | LOGICAL var_decl_list
             | CHARACTER var_decl_list
             | DOUBLE PRECISION var_decl_list

var_decl     : ID | ID LPAREN dim_list RPAREN

stmt_list    : ε | stmt_list stmt
stmt         : LABEL unlabeled_stmt | unlabeled_stmt

unlabeled_stmt : assign_stmt | if_stmt | do_stmt | goto_stmt
               | continue_stmt | print_stmt | read_stmt
               | write_stmt | stop_stmt | return_stmt | call_stmt

assign_stmt  : ID EQUALS expr
             | ID LPAREN arg_list RPAREN EQUALS expr

if_stmt      : IF LPAREN expr RPAREN THEN stmt_list ENDIF
             | IF LPAREN expr RPAREN THEN stmt_list ELSE stmt_list ENDIF
             | IF LPAREN expr RPAREN INT_LIT COMMA INT_LIT COMMA INT_LIT  (IF aritmético)

do_stmt      : DO INT_LIT ID EQUALS expr COMMA expr [COMMA expr]

goto_stmt    : GOTO INT_LIT
continue_stmt: CONTINUE
stop_stmt    : STOP
return_stmt  : RETURN
call_stmt    : CALL ID | CALL ID LPAREN arg_list RPAREN
print_stmt   : PRINT STAR COMMA print_list
read_stmt    : READ STAR COMMA var_list
write_stmt   : WRITE LPAREN expr COMMA STAR RPAREN print_list

subprogram_list : ε | subprogram_list subprogram
subprogram      : function_def | subroutine_def
function_def    : type_spec FUNCTION ID LPAREN param_list_opt RPAREN body END
subroutine_def  : SUBROUTINE ID LPAREN param_list_opt RPAREN body END
                | SUBROUTINE ID body END
param_list_opt  : ε | param_list
param_list      : ID | param_list COMMA ID

expr         : expr op expr | MINUS expr | PLUS expr | NOT expr
             | LPAREN expr RPAREN | INT_LIT | REAL_LIT | BOOL_LIT
             | STRING_LIT | ID | ID LPAREN arg_list RPAREN
```

**Separação `decl_list` / `stmt_list`**: o parser distingue uma secção de declarações (sempre primeiro) de uma secção de instruções. Isto reflecte a regra ANSI F77 de que declarações de tipo precedem executáveis — e simplifica a construção da tabela de símbolos na análise semântica.

### 4.3 Precedência de operadores

A tabela de precedências segue exactamente a especificação ANSI F77, do menor para o maior:

```python
precedence = (
    ("left",  "EQV", "NEQV"),       # 1. lógicos de equivalência
    ("left",  "OR"),                # 2. disjunção
    ("left",  "AND"),               # 3. conjunção
    ("right", "NOT"),               # 4. negação lógica (unária)
    ("left",  "EQ", "NE", "LT", "LE", "GT", "GE"),  # 5. relacionais
    ("left",  "CONCAT"),            # 6. concatenação de strings
    ("left",  "PLUS", "MINUS"),     # 7. adição/subtracção
    ("left",  "STAR", "SLASH"),     # 8. multiplicação/divisão
    ("right", "UMINUS", "UPLUS"),   # 9. unários (sentinelas)
    ("right", "POWER"),             # 10. exponenciação (associa à direita)
)
```

Os sentinelas `UMINUS` e `UPLUS` são necessários porque PLY yacc não permite que uma regra `expr : MINUS expr` use a precedência de `MINUS` (que é binário) — a directiva `%prec UMINUS` na docstring instrui o parser a usar a linha de precedência de `UMINUS` em vez disso.

**A associatividade de `POWER` à direita** é obrigatória em Fortran: `2**3**4` deve ser interpretado como `2**(3**4)` = 2^81, não como `(2**3)**4` = 8^4.

### 4.4 Distinção array / chamada de função

Em Fortran 77, `A(I)` pode significar:

- Acesso ao array `A` na posição `I`
- Chamada à função `A` com argumento `I`

Esta distinção é **semântica**, não sintática (depende da declaração de `A`). O parser produz um nó `CallExpr` para ambos os casos nas expressões — a análise semântica (fase futura) resolve a ambiguidade consultando a tabela de símbolos.

Para lvalues (lado esquerdo de atribuições), o parser produz directamente `ArrayRef`.

### 4.5 Labels e o mecanismo source_label

O Fortran 77 usa labels numéricos em duas vertentes:

1. **Destino de salto**: `GOTO 10`, `DO 10 I = 1, N`
2. **Marcador de instrução**: `10 CONTINUE`

O token `LABEL` é emitido pelo pré-processador e injectado na stream de tokens. No parser, qualquer instrução pode ter um `LABEL` prefixado:

```python
def p_stmt_labeled(self, p):
    """stmt : LABEL unlabeled_stmt"""
    s = p[2]
    setattr(s, "source_label", p[1])  # guardado para o IR resolver GOTOs
    if isinstance(s, ast.ContinueStmt):
        s.label = p[1]
    p[0] = s
```

O atributo `source_label` é guardado em **qualquer** instrução labelada — não apenas `CONTINUE`. Isto permite ao gerador de IR emitir o `IRLabelInstr` correspondente antes de qualquer instrução que possa ser destino de um `GOTO`, sem necessitar de uma fase separada de resolução de labels.

### 4.6 AST — Nós e hierarquia (ast_nodes.py)

Todos os nós da AST são `@dataclass` Python, herdando de `Node`:

```
Node
├── Program          — PROGRAM nome decls stmts subprograms END
├── FunctionDef      — tipo FUNCTION nome(params) ... END
├── SubroutineDef    — SUBROUTINE nome(params) ... END
├── TypeDecl         — tipo varlist
├── ArrayDecl        — ID(dims)
├── Expr
│   ├── IntLit, RealLit, BoolLit, StringLit
│   ├── VarRef          — ID
│   ├── ArrayRef        — ID(indices)
│   ├── CallExpr        — ID(args)  [função ou array — ambíguo até semântica]
│   ├── UnaryOp         — op operand
│   └── BinOp           — left op right
└── Stmt
    ├── AssignStmt   — target = value
    ├── IfStmt       — cond then_stmts else_stmts
    ├── ArithIfStmt  — expr label_neg label_zero label_pos
    ├── DoStmt       — label var start end step body
    ├── GotoStmt     — label
    ├── ContinueStmt — label
    ├── PrintStmt    — items
    ├── ReadStmt     — variables
    ├── WriteStmt    — unit fmt items
    ├── StopStmt
    ├── ReturnStmt
    └── CallStmt     — name args
```

**Uso de `dataclass`**: os nós são imutáveis por valor (não frozen, para permitir que a análise semântica os anote com atributos adicionais como `source_label`). O campo `lineno` em todos os nós preserva a rastreabilidade para mensagens de erro.

**Alternativa não adoptada**: usar dicionários ou namedtuples. Perder-se-ia a tipagem estática, o `__repr__` automático, e a distinção por `isinstance` necessária no gerador de IR.

---

## 5. Etapa 3 — Representação Intermédia (IR)

**Ficheiros:** `src/representacao_intermedia/gerador.py`, `instrucoes.py`, `operadores.py`

### 5.1 Estilo da IR: Three-Address Code (TAC)

A IR adoptada é **Three-Address Code** (código de três endereços), o estilo mais comum em compiladores modernos (usado por GCC, LLVM, etc.) e ensinado nos materiais da UC. Cada instrução tem no máximo um operador e três operandos:

```
t1 = A + B       (IROp)
t2 = t1 < 0      (IROp)
IF t2 GOTO L1 ELSE GOTO L2   (IRCJump)
L1:              (IRLabelInstr)
...
GOTO L3          (IRJump)
```

**Por quê TAC em vez de stack-based IR?**: A EWVM é stack-based, mas produzir directamente código de stack durante o parsing tornaria impossível optimizações futuras. O TAC é uma IR de nível mais alto que permite propagação de constantes, eliminação de subexpressões comuns, etc. A tradução TAC → EWVM é feita (futuramente) no backend `codegen/ewvm.py`.

**Alternativa não adoptada**: produzir directamente código EWVM durante a travessia da AST (sem IR intermédia). Seria a abordagem mais simples, mas impossibilitaria qualquer optimização e dificultaria o teste isolado do gerador de código.

### 5.2 Tipos de instrução IR

| Instrução      | Semântica                            | Exemplo             |
| ---------------- | ------------------------------------- | ------------------- |
| `IRAssign`     | `dest = src`                        | `A = t1`          |
| `IROp`         | `dest = left op right`              | `t1 = B + C`      |
| `IRUnaryOp`    | `dest = op operand`                 | `t1 = NEG A`      |
| `IRCJump`      | `IF cond GOTO true ELSE GOTO false` | Salto condicional   |
| `IRJump`       | `GOTO label`                        | Salto incondicional |
| `IRLabelInstr` | `label:`                            | Marcador de destino |
| `IRCall`       | `[dest =] CALL name(args)`          | Função/subrotina  |
| `IRProcBegin`  | `FUNCTION/SUBROUTINE name(params)`  | Início de subprograma |
| `IRProcEnd`    | `ENDPROC name`                      | Fim de subprograma |
| `IRLoadArray`  | `dest = A[indices]`                 | Leitura de array    |
| `IRStoreArray` | `A[indices] = src`                  | Escrita em array    |
| `IRPrint`      | `PRINT args`                        | Saída              |
| `IRRead`       | `READ args`                         | Entrada             |
| `IRWrite`      | `WRITE(unit, fmt) items`            | Escrita formatada   |
| `IRStop`       | `STOP`                              | Fim de programa     |
| `IRReturn`     | `RETURN`                            | Retorno             |

### 5.3 Temporários e Labels

- **`Temp(id)`**: variável temporária gerada pelo compilador, impressa como `t1`, `t2`, etc.
- **`Label(name)`**: destino de salto, com prefixos convencionais:
  - `Lx` — labels internos gerados pelo compilador (IFs, DOs)
  - `Fx` — labels Fortran numéricos (ex: `F10` para `10 CONTINUE`, `F20` para `GOTO 20`)

### 5.4 Gerador de IR — padrão Visitor

O `IRGenerator` usa o padrão **Visitor** via despacho dinâmico por nome de método:

```python
def generate(self, node):
    method_name = f"visit_{type(node).__name__}"
    visitor = getattr(self, method_name, self.generic_visit)
    return visitor(node)
```

Cada nó AST tem um `visit_NomeDoNó` correspondente. Isto é o padrão canónico para travessias de AST em compiladores — torna trivial adicionar novos tipos de nó sem modificar o gerador.

**Por quê despacho dinâmico em vez de `match`/`isinstance`?**: O `match` de Python 3.10+ seria uma alternativa válida e ligeiramente mais segura em termos de tipagem, mas o despacho por nome de método é mais extensível (qualquer módulo pode registar um `visit_Foo` sem modificar `IRGenerator`) e é o idioma consagrado em compiladores Python (usado também pelo PLY internamente).

### 5.5 Subprogramas definidos pelo utilizador

O suporte a `FUNCTION` e `SUBROUTINE` foi implementado mantendo a divisão por fases:

- o parser constrói nós próprios (`FunctionDef`, `SubroutineDef`) e mantém-nos fora do corpo do programa principal;
- a análise semântica regista primeiro as assinaturas globais e só depois analisa cada corpo com uma tabela de símbolos própria;
- o gerador de IR emite marcadores explícitos `IRProcBegin`/`IRProcEnd`, além de `IRCall` e `IRReturn`;
- o backend EWVM traduz cada unit para um label dedicado e usa `FP` para separar parâmetros, locais e valor de retorno por ativação.

Esta opção evita concentrar convenções implícitas num único módulo e permite que parser, semântica, IR e backend evoluam de forma relativamente independente.

### 5.5 Geração de DO loops

O DO clássico do Fortran 77 (`DO 10 I = 1, N ... 10 CONTINUE`) não é estruturado: o corpo do DO vai até ao `CONTINUE` com o label correspondente, podendo ter `GOTO` no meio.

**Solução implementada**: uso de uma *pilha de contexto de loops* (`_loop_stack`). Quando o parser encontra `DO 10 I = 1, N`, cria um `DoStmt` com `body=[]` e o gerador de IR:

1. Emite o código de inicialização e o teste de condição
2. Empurha um `LoopContext` na pilha com o label terminal (`10`), a variável de controlo, o passo, e os labels IR de teste e fim
3. Continua a processar as instruções seguintes normalmente
4. Quando encontra `10 CONTINUE`, o método `_close_do_loops_for_label` desempilha os contextos cujo `target_label == 10`, emite o incremento da variável de controlo e o salto de volta ao teste

Este mecanismo suporta DO loops aninhados com o mesmo label terminal (válido em F77 — vários DO podem terminar no mesmo CONTINUE).

**Geração do teste de condição**: o padrão ANSI F77 especifica que um DO loop com passo negativo deve verificar `var >= end` e com passo positivo `var <= end`. Como o passo pode ser uma expressão em tempo de execução, o gerador emite código que verifica o sinal do passo em runtime:

```
step_nonneg = step >= 0
IF step_nonneg GOTO DO_POS ELSE GOTO DO_NEG
DO_POS: pos_cond = var <= end; IF pos_cond GOTO DO_BODY ELSE GOTO DO_END
DO_NEG: neg_cond = var >= end; IF neg_cond GOTO DO_BODY ELSE GOTO DO_END
DO_BODY: ...
```

**Alternativa não adoptada**: assumir que o passo é sempre positivo (o caso mais comum em F77). Simplificaria muito o código gerado, mas violaria o standard e falharia para loops com passo negativo.

### 5.6 Geração de IF aritmético

O IF aritmético `IF (expr) label_neg, label_zero, label_pos` é uma construção F77 arcaica que desvia para um de três labels conforme o sinal da expressão. O gerador emite duas decisões em cascata:

```
t1 = expr
t2 = t1 < 0
IF t2 GOTO F_neg ELSE GOTO ARZ1
ARZ1:
t3 = t1 == 0
IF t3 GOTO F_zero ELSE GOTO F_pos
```

### 5.7 Normalização de operadores

O Fortran usa operadores pontuados (`.EQ.`, `.AND.`, etc.) enquanto a IR usa símbolos normais (`==`, `AND`). A normalização é feita nos métodos `_normalize_binop` e `_normalize_unary`, centralizando a conversão num único sítio.

---

## 6. Infraestrutura de Suporte

### 6.1 Tratamento de erros (errors.py)

Hierarquia simples de excepções:

```
CompileError(Exception)
├── LexError
├── ParseError
└── SemanticError   [reservado para fase futura]
```

Cada erro carrega um `SourceLocation(filename, line, column)` que permite produzir mensagens no formato canónico dos compiladores:

```
bad_assign.f:3:5: error: Erro de sintaxe em 'END'
```

O parser PLY invoca `p_error(p)` quando encontra um token inesperado. A implementação extrai a linha e posição do token e lança `ParseError` com `SourceLocation`. Para EOF inesperado (quando `p` é `None`), usa `self._source_line_count + 1` como linha de erro.

### 6.2 Interface de linha de comando (cli.py)

O CLI aceita as seguintes fases via `--stage`:

| Flag                | Acção                                                 |
| ------------------- | ------------------------------------------------------- |
| `--stage lex`     | Corre só o lexer e imprime os tokens                   |
| `--stage parse`   | Corre lexer + parser e imprime resumo da AST            |
| `--stage ir`      | Corre até à geração de IR e imprime as instruções |
| `--stage sem`     | Análise semântica e validação da AST anotada         |
| `--stage codegen` | Pipeline completo até EWVM                           |

O formato fixo/livre é controlado por `--format fixed|free|auto` (default: `auto`).

### 6.3 Configuração global (config.py)

O módulo `config.py` expõe uma instância global `Config` com valores por omissão. Actualmente pouco usada (as fases recebem os parâmetros directamente), mas serve como ponto central para configurações futuras (largura de linha, modo debug, etc.).

### 6.4 Testes (pytest)

A suite de testes usa `pytest` com `scope="session"` para o lexer e o parser — as instâncias PLY são construídas uma vez por sessão de testes (construir o parser PLY implica gerar as tabelas LALR, o que tem custo).

As fixtures de programas Fortran em `tests/fixtures/` servem de casos de teste de integração reais — não programas artificialmente simples.

---

## 7. Testes e Validação

### Estado actual: 167/167 testes a passar

| Ficheiro                 | Testes | Cobertura                                                               |
| ------------------------ | ------ | ----------------------------------------------------------------------- |
| `test_lexer.py`        | 98     | Tokens, keywords, literais, operadores, fixed/free form, linenos, erros |
| `test_parser_smoke.py` | 20     | AST shape, declarações, instruções, subprogramas, erros sintáticos |
| `test_semantic.py`     | 13     | Declarações, tipos, labels, arrays, assinaturas e aridade de subprogramas |
| `test_ir.py`           | 9      | Atribuições, IFs, DOs, GOTOs, arrays, I/O, calls e lowering de subprogramas |
| `test_codegen.py`      | 9      | Backend EWVM, arrays, intrínsecas e convenção de chamada |
| `test_cli.py`          | 3      | Execução por estágios via CLI |

### Fixtures de referência

| Ficheiro           | O que testa                                                           |
| ------------------ | --------------------------------------------------------------------- |
| `hello.f`        | Programa mínimo — PRINT de string literal                           |
| `fatorial.f`     | DO loop clássico com label, CONTINUE, READ, PRINT                    |
| `primo.f`        | GOTO, LOGICAL, AND, IF-THEN-ELSE aninhado, MOD (função intrínseca) |
| `continuation.f` | Continuação de linha em fixed-form (`*` na coluna 6)              |
| `somaarr.f`      | Arrays, READ/WRITE e indexação                                    |
| `conversor.f`    | `INTEGER FUNCTION`, retorno por nome e chamada definida pelo utilizador |

---

## 8. Estado Atual e Trabalho Futuro

### Implementado — Análise Semântica (`src/analise_semantica/analyzer.py`, `src/analise_semantica/symbols.py`)

A análise semântica já percorre a AST e:

1. regista declarações de escalares e arrays;
2. valida tipos em atribuições e expressões;
3. resolve `CallExpr` vs `ArrayRef`;
4. valida labels de `GOTO` e `DO`;
5. anota expressões com `sem_type`;
6. regista assinaturas de `FUNCTION`/`SUBROUTINE` antes da análise dos corpos;
7. analisa cada subprograma com escopo próprio e valida aridade das chamadas.

### Implementado — Geração de Código EWVM (`src/codegen/ewvm_generator.py`)

O backend já mapeia a IR para EWVM, incluindo:

- gestão da stack de operandos;
- modelo de memória global para escalares, arrays, temporários e auxiliares;
- intrínsecas suportadas (`MOD`, `INT`, `REAL`, `FLOAT`, `ABS`, `SQRT`, `MAX`, `MIN`);
- convenção explícita de chamada para subprogramas definidos pelo utilizador;
- emissão de labels, `CALL` e `RETURN`.

### Pendente — Optimizações (`src/optimizer.py`)

Optimizações clássicas sobre a IR (valorização):

- **Propagação de constantes**: substituir `t1 = 3; t2 = t1 + 4` por `t2 = 7`
- **Eliminação de código morto**: remover instruções cujo resultado nunca é usado
- **Peephole optimization**: simplificações locais na IR antes da tradução para EWVM

---

## 9. Resumo das Escolhas Técnicas

| Decisão              | Escolha                                       | Principal Alternativa Rejeitada             | Justificação                                                    |
| --------------------- | --------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------- |
| Gerador de lexer      | `ply.lex`                                   | `re` manual / ANTLR4                      | Integração directa com `ply.yacc`; obrigatório pela UC       |
| Gerador de parser     | `ply.yacc` (LALR(1))                        | Recursivo descendente manual (LL)           | Suporta recursividade esquerda; gramática de expressões natural |
| Pré-processamento    | Módulo separado `processor.py`             | Dentro do lexer PLY (estados)               | Testabilidade isolada; separação de responsabilidades           |
| Tokenização prévia | `list[LexToken]` completa                   | Streaming token-a-token                     | Permite injecção de tokens sintéticos (`LABEL`)              |
| Representação AST   | `@dataclass` Python                         | `dict` / `namedtuple` / classes manuais | `isinstance`, `__repr__`, tipagem estática, extensibilidade  |
| IR                    | Three-Address Code (TAC)                      | Stack-based directo                         | Permite optimizações; separa lógica de geração do backend VM |
| Travessia AST         | Visitor por despacho dinâmico                | `match` / `isinstance` em cadeia        | Extensibilidade sem modificar o gerador; idioma canónico PLY     |
| DO loops              | Pilha de contextos (`_loop_stack`)          | DO estruturado com body na AST              | Suporta o estilo label-based original do F77                      |
| Labels                | Atributo `source_label` em qualquer nó     | Apenas em `ContinueStmt`                  | Qualquer instrução pode ser alvo de GOTO em F77                 |
| Gestão de erros      | Hierarquia de excepções +`SourceLocation` | Print e `sys.exit`                        | Testabilidade; formato de mensagem canónico de compiladores      |
| Testes                | pytest + fixtures `.f` reais                | Só unit tests com strings inline           | Valida o pipeline de ponta a ponta com código Fortran real       |

---

## 12. Limites Funcionais Atuais (subconjunto efetivo)

Para evitar sobredeclaração de suporte, ficam explícitos os limites observados no código atual:

1. **Sem `IMPLICIT NONE` efetivo** (token reconhecido, mas sem regra semântica aplicada).
2. **Sem coerções implícitas gerais** na fase semântica; a validação atual privilegia compatibilidade estrita entre tipos.
3. **Sem otimização IR/EWVM**: o código gerado ainda reserva e inicializa mais slots do que o necessário.
4. **Sem execução automática da VM do docente** no pipeline de testes.
5. **Sem procedimentos internos nem argumentos por referência completos**; o suporte atual cobre subprogramas externos do subconjunto usado no projeto.
6. **Sem otimização específica de frames**: o backend já usa `FP`, mas ainda não minimiza slots locais/temporários nem faz compactação de ativação.

---

## 13. Critérios Objetivos para Fechar o Projeto

Definição prática de “done” para a versão de entrega:

1. `src/analise_semantica/analyzer.py` + `src/analise_semantica/symbols.py` com:

- deteção de variável não declarada;
- deteção de declaração duplicada;
- validação de tipos em `AssignStmt`, `BinOp`, `UnaryOp`;
- validação estrutural de labels de `DO`.

2. `src/codegen/ewvm_generator.py` a traduzir **todo o conjunto de instruções IR já emitidas**.
3. Testes novos:

- `tests/test_semantic.py`;
- testes de codegen com comparação de output EWVM esperado.

4. Inclusão no repositório de exemplos `.f` + respetivos `.vm` (requisito explícito do enunciado).

---

## 14. Reprodutibilidade (execução rápida)

Sequência mínima para reproduzir o estado atual:

1. Instalar dependências (`requirements.txt` e `requirements-dev.txt`).
2. Correr testes (`pytest`) — esperado: suite completa verde.
3. Validar pipeline por estágio:

- `--stage lex` em `hello.f` / `primo.f`;
- `--stage parse` em `fatorial.f`;
- `--stage ir` em `primo.f`.

Esta rotina garante verificação funcional sem depender de componentes ainda pendentes (semântica/codegen).

---

*Documento gerado automaticamente a partir da análise do código-fonte do projecto — PL-G37, Abril 2026.*
