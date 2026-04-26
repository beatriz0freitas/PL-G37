# Estado do Projeto — Compilador Fortran 77

> **Grupo G37 · Processamento de Linguagens 2026**
> Última atualização: 2026-04-26

---

## Resumo

| Etapa                                   | Estado                           |
| --------------------------------------- | -------------------------------- |
| Análise Léxica                        | ✅ Completa                      |
| Análise Sintática                     | ✅ Implementada (base funcional) |
| Representação Intermédia (AST -> IR) | ✅ Implementada                  |
| Análise Semântica                     | 🔲 Por implementar               |
| Tradução de Código (IR -> EWVM)      | ✅ Implementada                  |
| Otimização (valorização)            | 🔲 Por implementar               |
| Testes                                  | ✅ 130/130 a passar              |

---

## ✅ Análise Léxica — Completa

**Ficheiros:** `src/analise_lexica/lexer.py`, `src/analise_lexica/processor.py`

**Implementado:**

- [X] Lexer com `ply.lex`
- [X] Keywords base do Fortran 77
- [X] Identificadores case-insensitive (normalização para maiúsculas)
- [X] Literais inteiros, reais e lógicos
- [X] Strings com escape de apóstrofo (`''`)
- [X] Operadores aritméticos, relacionais e lógicos pontuados
- [X] Suporte a fixed-form e free-form
- [X] Pré-processamento de labels e continuações de linha

**Validação:**

- [X] `tests/test_lexer.py` — **98/98**

---

## ✅ Análise Sintática — Implementada (base)

**Ficheiros:** `src/analise_sintatica/parser.py`, `src/analise_sintatica/ast_nodes.py`

**Implementado:**

- [X] Parser com `ply.yacc`
- [X] `PROGRAM ... END`
- [X] Declarações de tipo (`INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE PRECISION`)
- [X] Atribuições simples e com índice
- [X] Expressões aritméticas, relacionais e lógicas com precedência
- [X] `IF-THEN-ELSE-ENDIF`
- [X] `IF` aritmético
- [X] `DO` clássico com label
- [X] `GOTO`, `CONTINUE`, `STOP`, `RETURN`, `CALL`
- [X] `READ`, `PRINT`, `WRITE`
- [X] AST consistente para as etapas seguintes
- [X] Integração com `errors.py` (`ParseError` + `SourceLocation`)
- [X] Preservação do `source_label` em instruções com label (útil para IR/codegen)

**Validação:**

- [X] `tests/test_parser_smoke.py` — **20/20**

---

## ✅ Representação Intermédia (AST -> IR) — Implementada

**Ficheiros:**

- `src/representacao_intermedia/gerador.py`
- `src/representacao_intermedia/instrucoes.py`
- `src/representacao_intermedia/operadores.py`

**Integração CLI:**

- [X] Stage `--stage ir` funcional em `src/cli.py`

**Implementado na IR:**

- [X] Temporários e labels
- [X] Instruções de três endereços (atribuição, unário, binário)
- [X] Saltos condicionais e incondicionais
- [X] `IF-THEN-ELSE`
- [X] `IF` aritmético
- [X] `DO` clássico com fecho em label `CONTINUE`
- [X] `GOTO`
- [X] `READ`, `PRINT`, `WRITE`
- [X] `CALL`, `STOP`, `RETURN`
- [X] Leitura/escrita de arrays na IR

**Validação:**

- [X] `tests/test_ir.py` — **7/7**

---

## 🔲 Análise Semântica — Por implementar

**Ficheiro:** `src/semantic.py`

**Pendente:**

- [ ] Verificação de tipos (`INTEGER`, `REAL`, `LOGICAL`)
- [ ] Uso de variável antes de declaração
- [ ] Deteção de declarações duplicadas
- [ ] Regras de labels (`DO <label>` com `CONTINUE` válido)
- [ ] Anotação semântica da AST

**Atenção importante para a implementação:**

- [ ] Resolver obrigatoriamente a ambiguidade `CallExpr` vs `ArrayRef` em expressões como `A(I)`.
- [ ] Se `A` estiver declarada como array, a análise semântica deve normalizar esse nó antes da geração de IR/backend.
- [ ] O backend atual tem uma heurística temporária para este caso; quando a semântica existir, esta decisão deve passar a ser feita aqui.

**Tabela de símbolos:**

- `src/symbols.py` permanece em esqueleto

---

## ✅ Tradução de Código (IR -> EWVM) — Implementada

**Ficheiros:**

- `src/codegen/ewvm.py`
- `src/codegen/ewvm_generator.py`
- `src/codegen/layout.py`
- `src/codegen/decls.py`

**Implementado:**

- [X] Tradução de IR para código texto EWVM
- [X] Integração CLI com `--stage codegen`
- [X] Alocação global com `ALLOC`
- [X] Suporte a escalares com `PUSHG` / `POPG`
- [X] Literais inteiros, reais e strings com `PUSHI` / `PUSHF` / `PUSHS`
- [X] Operações aritméticas, relacionais e lógicas
- [X] Saltos `JUMP` e `JZ`
- [X] `READ`, `PRINT`, `WRITE` com seleção de instrução por tipo
- [X] Arrays com `LOADN` / `STOREN` e indexação Fortran base 1
- [X] Chamadas intrínsecas base (`MOD`, `ABS`, `SQRT`, `MAX`, `MIN`)

**Limitações conhecidas:**

- [ ] A análise semântica ainda não existe, por isso a distinção `CallExpr` vs `ArrayRef` em expressões é parcialmente resolvida no backend com base nas declarações.
- [ ] Ainda não há execução automática do `.vm` na VM do docente para validação end-to-end.
- [ ] Ainda não há symbol table semântica a alimentar o backend; o codegen extrai metadados diretamente da AST.

---

## 🔲 Otimização — Por implementar (valorização)

**Ficheiro:** `src/optimizer.py`

**Pendente:**

- [ ] Propagação de constantes
- [ ] Eliminação de código morto
- [ ] Peephole optimization

---

## ✅ Estado dos Testes

| Ficheiro                       | Resultado           |
| ------------------------------ | ------------------- |
| `tests/test_lexer.py`        | ✅ 98/98            |
| `tests/test_parser_smoke.py` | ✅ 20/20            |
| `tests/test_ir.py`           | ✅ 7/7              |
| `tests/test_codegen.py`      | ✅ 5/5              |
| **Total**                | ✅**130/130** |

**Fixtures atuais:**

- `tests/fixtures/hello.f`
- `tests/fixtures/fatorial.f`
- `tests/fixtures/primo.f`
- `tests/fixtures/continuation.f`

**Ainda por criar (planeado):**

- [ ] `tests/test_semantic.py`
- [ ] Ficheiros `.vm` esperados para comparação automática de output

---

## 🔲 Análise Semântica — Por implementar

**Ficheiros a criar/completar:** `src/semantic.py`, `src/symbols.py`

### O que é e para que serve

A análise semântica percorre a AST e realiza verificações que dependem de contexto acumulado — o que as gramáticas livres de contexto não conseguem expressar. Em Fortran 77 as verificações centrais são: construção da tabela de símbolos, resolução da ambiguidade `CallExpr` vs `ArrayRef`, verificação de tipos, e validação de labels DO.

A saída desta fase é a **tabela de símbolos** que o gerador de código EWVM precisa para saber o tipo e endereço de cada variável.

---

### Passo S1 — Tabela de Símbolos (`src/symbols.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
from src.errors import SemanticError, SourceLocation

@dataclass
class Symbol:
    name: str
    kind: str        # "scalar" | "array" | "function" | "subroutine"
    type: str        # "INTEGER" | "REAL" | "LOGICAL" | "CHARACTER" | "DOUBLE PRECISION"
    dimensions: list # [] se escalar; [dim1, dim2, ...] se array (valores inteiros)
    lineno: int = 0

class SymbolTable:
    def __init__(self):
        self._table: dict[str, Symbol] = {}

    def declare(self, sym: Symbol) -> None:
        """Regista um símbolo. Lança SemanticError se já declarado."""
        if sym.name in self._table:
            raise SemanticError(
                f"Variável '{sym.name}' já declarada",
                SourceLocation("<unknown>", sym.lineno, 0),
            )
        self._table[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        return self._table.get(name)

    def require(self, name: str, lineno: int) -> Symbol:
        sym = self.lookup(name)
        if sym is None:
            raise SemanticError(
                f"Variável '{name}' usada sem declaração",
                SourceLocation("<unknown>", lineno, 0),
            )
        return sym

    def all_symbols(self):
        return self._table.values()

    def __len__(self):
        return len(self._table)
```

**Implicit typing (opcional mas recomendado):** Fortran 77 define que variáveis não declaradas começadas por `I`, `J`, `K`, `L`, `M` ou `N` são `INTEGER`; as restantes são `REAL`. Implementar como fallback em `lookup`:

```python
IMPLICIT_INTEGER = frozenset("IJKLMN")

def lookup(self, name: str) -> Symbol:
    if name in self._table:
        return self._table[name]
    # Implicit typing F77
    t = "INTEGER" if name[0].upper() in IMPLICIT_INTEGER else "REAL"
    sym = Symbol(name=name, kind="scalar", type=t, dimensions=[])
    self._table[name] = sym   # regista para uso futuro consistente
    return sym
```

---

### Passo S2 — Visitor Semântico (`src/semantic.py`)

Usar o mesmo padrão Visitor do `IRGenerator`:

```python
class SemanticAnalyser:
    def __init__(self):
        self.symbols = SymbolTable()
        self._errors: list[SemanticError] = []
        self._active_do_labels: set[int] = set()

    def analyse(self, node: ast.Program) -> SymbolTable:
        # Primeira passagem: registar todas as declarações
        for decl in node.decls:
            self.visit(decl)
        # Segunda passagem: verificar instruções
        for stmt in node.stmts:
            self.visit(stmt)
        if self._errors:
            raise self._errors[0]
        return self.symbols

    def visit(self, node):
        method = f"visit_{type(node).__name__}"
        return getattr(self, method, self.generic_visit)(node)

    def generic_visit(self, node):
        return None   # nós sem verificação semântica específica

    def _error(self, msg: str, lineno: int):
        self._errors.append(SemanticError(msg, SourceLocation("<unknown>", lineno, 0)))
```

#### S2a — Percurso das declarações

```python
def visit_TypeDecl(self, node: ast.TypeDecl):
    for var in node.variables:
        if isinstance(var, str):
            self.symbols.declare(Symbol(
                name=var, kind="scalar", type=node.typename, dimensions=[], lineno=node.lineno
            ))
        elif isinstance(var, ast.ArrayDecl):
            dims = []
            for d in var.dimensions:
                val = self.visit(d)
                if not isinstance(val, int):
                    self._error(f"Dimensão de array deve ser constante inteira", var.lineno)
                else:
                    dims.append(val)
            self.symbols.declare(Symbol(
                name=var.name, kind="array", type=node.typename, dimensions=dims, lineno=var.lineno
            ))
```

#### S2b — Resolução `CallExpr` vs `ArrayRef` **(obrigatório)**

O parser produz `CallExpr` para `A(I)` em expressões. A semântica resolve:

```python
def visit_CallExpr(self, node: ast.CallExpr) -> str:
    sym = self.symbols.lookup(node.name)
    if sym and sym.kind == "array":
        # Reescrever o nó in-place para ArrayRef
        # (alternativamente: devolver um novo nó e o chamador substitui)
        node.__class__ = ast.ArrayRef
        node.indices = node.args
        del node.args
        return sym.type
    # É chamada de função — verificar número de argumentos se for intrínseca
    for arg in node.args:
        self.visit(arg)
    return self._intrinsic_return_type(node.name)

def _intrinsic_return_type(self, name: str) -> str:
    INTRINSIC_TYPES = {
        "MOD": "INTEGER", "ABS": "INTEGER", "IABS": "INTEGER",
        "SQRT": "REAL",   "SIN": "REAL",    "COS": "REAL",
        "FLOAT": "REAL",  "INT": "INTEGER", "REAL": "REAL",
        "MAX": "INTEGER", "MIN": "INTEGER", "MAX0": "INTEGER",
    }
    return INTRINSIC_TYPES.get(name, "INTEGER")   # default conservador
```

> Nota: este passo não é opcional no estado atual do projeto. O backend EWVM já contém uma compensação temporária para este problema, mas ela só existe enquanto a análise semântica não estiver implementada.

#### S2c — Verificação de tipos em expressões

```python
def visit_BinOp(self, node: ast.BinOp) -> str:
    lt = self.visit(node.left)  or "INTEGER"
    rt = self.visit(node.right) or "INTEGER"
    logical_ops = {".AND.", ".OR.", ".EQV.", ".NEQV.", "AND", "OR", "EQV", "NEQV"}
    relational_ops = {".EQ.", ".NE.", ".LT.", ".LE.", ".GT.", ".GE.",
                      "==", "!=", "<", "<=", ">", ">="}
    if node.op in logical_ops:
        if lt != "LOGICAL" or rt != "LOGICAL":
            self._error(f"Operador lógico '{node.op}' requer operandos LOGICAL", node.lineno)
        return "LOGICAL"
    if node.op in relational_ops:
        return "LOGICAL"   # comparações produzem LOGICAL
    # Operadores aritméticos
    if "LOGICAL" in (lt, rt):
        self._error(f"Operador aritmético '{node.op}' não aplicável a LOGICAL", node.lineno)
    if "DOUBLE PRECISION" in (lt, rt):
        return "DOUBLE PRECISION"
    if "REAL" in (lt, rt):
        return "REAL"
    return "INTEGER"

def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
    t = self.visit(node.operand) or "INTEGER"
    if node.op in (".NOT.", "NOT") and t != "LOGICAL":
        self._error(".NOT. requer operando LOGICAL", node.lineno)
    if node.op in ("-", "NEG") and t == "LOGICAL":
        self._error("Negação aritmética não aplicável a LOGICAL", node.lineno)
    return t
```

#### S2d — Verificação de atribuições

```python
def visit_AssignStmt(self, node: ast.AssignStmt):
    target_type = self.visit(node.target)
    value_type  = self.visit(node.value) or "INTEGER"
    # LOGICAL só pode receber LOGICAL
    if target_type == "LOGICAL" and value_type != "LOGICAL":
        self._error(
            f"Atribuição de tipo '{value_type}' a variável LOGICAL", node.lineno
        )
    # Valor LOGICAL não pode ser atribuído a variável numérica
    if value_type == "LOGICAL" and target_type != "LOGICAL":
        self._error(
            f"Atribuição de LOGICAL a variável '{target_type}'", node.lineno
        )
    # Coerção INTEGER → REAL é implícita e permitida (sem aviso)
```

#### S2e — Validação de labels DO

```python
def visit_DoStmt(self, node: ast.DoStmt):
    sym = self.symbols.lookup(node.var)
    if sym and sym.type not in ("INTEGER",):
        self._error(
            f"Variável de controlo DO '{node.var}' deve ser INTEGER", node.lineno
        )
    self._active_do_labels.add(node.label)
    self.visit(node.start)
    self.visit(node.end)
    if node.step:
        self.visit(node.step)

def visit_ContinueStmt(self, node: ast.ContinueStmt):
    if node.label is not None and node.label not in self._active_do_labels:
        # CONTINUE com label que não corresponde a nenhum DO activo é válido
        # mas pode ser aviso; label sem DO correspondente é inofensivo
        pass
    if node.label in self._active_do_labels:
        self._active_do_labels.discard(node.label)
```

#### S2f — Tipos de literais e variáveis (folhas da AST)

```python
def visit_IntLit(self, node: ast.IntLit) -> str:    return "INTEGER"
def visit_RealLit(self, node: ast.RealLit) -> str:  return "REAL"
def visit_BoolLit(self, node: ast.BoolLit) -> str:  return "LOGICAL"
def visit_StringLit(self, node: ast.StringLit) -> str: return "CHARACTER"

def visit_VarRef(self, node: ast.VarRef) -> str:
    sym = self.symbols.lookup(node.name)
    if sym is None:
        self._error(f"Variável '{node.name}' usada sem declaração", node.lineno)
        return "INTEGER"
    return sym.type

def visit_ArrayRef(self, node: ast.ArrayRef) -> str:
    sym = self.symbols.require(node.name, node.lineno)
    if sym.kind != "array":
        self._error(f"'{node.name}' não é um array", node.lineno)
    if len(node.indices) != len(sym.dimensions):
        self._error(
            f"Array '{node.name}' tem {len(sym.dimensions)} dimensões, "
            f"usado com {len(node.indices)}", node.lineno
        )
    for idx in node.indices:
        self.visit(idx)
    return sym.type
```

---

### Passo S3 — Integração no CLI (`src/cli.py`)

```python
def run_sem(source: str, filename: str, source_format: str, debug: bool):
    tree = run_parse(source, filename, source_format, debug=False)
    from src.semantic import SemanticAnalyser
    analyser = SemanticAnalyser()
    symtable = analyser.analyse(tree)
    print(f"[sem] {len(symtable)} símbolos declarados e validados")
    if debug:
        for sym in symtable.all_symbols():
            dims = f"({', '.join(str(d) for d in sym.dimensions)})" if sym.dimensions else ""
            print(f"  {sym.type:<18} {sym.name}{dims}")
    return tree, symtable
```

Adicionar `"sem"` ao `--stage` choices e ao dispatcher em `main()`.

---

### Passo S4 — Testes (`tests/test_semantic.py`)

```python
class TestSymbolTable:
    def test_declare_e_lookup(self): ...           # registo básico
    def test_duplicado_lanca_erro(self): ...       # SemanticError em declaração dupla
    def test_implicit_typing_i_e_integer(self): ...
    def test_implicit_typing_a_e_real(self): ...

class TestTipos:
    def test_int_plus_int_e_integer(self): ...
    def test_int_plus_real_e_real(self): ...
    def test_logical_op_logico_ok(self): ...
    def test_logical_op_aritmetico_e_erro(self): ...
    def test_assign_logical_a_integer_e_erro(self): ...

class TestArrays:
    def test_call_expr_sobre_array_resolve_para_arrayref(self): ...
    def test_array_com_indices_errados_e_erro(self): ...

class TestDo:
    def test_do_com_variavel_real_e_erro(self): ...

class TestFixtures:
    def test_hello_sem_erros(self): ...
    def test_fatorial_sem_erros(self): ...
    def test_primo_sem_erros(self): ...
```

---

## ✅ Tradução de Código (IR → EWVM) — Implementada

**Ficheiros:**

- `src/codegen/ewvm.py` — fachada pública do backend
- `src/codegen/ewvm_generator.py` — tradução IR → EWVM
- `src/codegen/layout.py` — layout de memória global
- `src/codegen/decls.py` — extração de tipos/dimensões a partir da AST

### Instruções EWVM relevantes

| Instrução                                           | Efeito na stack                                 |
| ----------------------------------------------------- | ----------------------------------------------- |
| `PUSHI n`                                           | push inteiro n                                  |
| `PUSHF f`                                           | push real f                                     |
| `PUSHS "str"`                                       | push string                                     |
| `PUSHG addr`                                        | push valor da posição global addr             |
| `POPG addr`                                         | pop → posição global addr                    |
| `ADD`,`SUB`,`MUL`,`DIV`                       | op aritmética inteira (pop 2, push 1)          |
| `FADD`,`FSUB`,`FMUL`,`FDIV`                   | op aritmética real                             |
| `INF`,`INFEQ`,`SUP`,`SUPEQ`,`EQUAL`,`NEQ` | comparação (push 0 ou 1)                      |
| `NOT`,`AND`,`OR`                                | lógica booleana                                |
| `JUMP label`                                        | salto incondicional                             |
| `JZ label`                                          | salto se topo == 0 (pop)                        |
| `JNZ label`                                         | salto se topo != 0 (pop)                        |
| `LABEL label`                                       | marca de destino                                |
| `ALLOC n`                                           | aloca n posições no heap; push endereço base |
| `LOADN`                                             | pop addr; push heap[addr]                       |
| `STOREN`                                            | pop val; pop addr; heap[addr] = val             |
| `READ`/`READF`/`READS`                          | lê da stdin, push valor                        |
| `WRITEI`/`WRITEF`/`WRITES`                      | pop, escreve na stdout                          |
| `WRITELN`                                           | escreve newline                                 |
| `STOP`                                              | termina o programa                              |

---

### Estrutura atual do backend

O backend foi desacoplado em componentes pequenos para reduzir acoplamento e tornar a manutenção mais simples:

- `MemoryLayout`: gere endereços de escalares e arrays
- `extract_decl_info`: recolhe tipos e dimensões diretamente das declarações do `Program`
- `EWVMGenerator`: concentra apenas a tradução efetiva das instruções IR
- `ewvm.py`: reexporta a API pública e preserva compatibilidade de imports

### C1 — Modelo de Memória (`MemoryLayout`)

Para a primeira versão, todas as variáveis são globais (sem subprogramas). Cada variável recebe um endereço inteiro sequencial no heap EWVM:

```python
class MemoryLayout:
    def __init__(self):
        self._next_addr = 0
        self._scalars: dict[str, int] = {}           # nome → addr
        self._arrays:  dict[str, tuple[int, list]] = {}  # nome → (base, dims)

    def allocate_scalar(self, name: str) -> int:
        addr = self._next_addr
        self._scalars[name] = addr
        self._next_addr += 1
        return addr

    def allocate_array(self, name: str, dims: list[int]) -> int:
        """Alocação linear. Total de células = produto das dimensões."""
        total = 1
        for d in dims:
            total *= d
        base = self._next_addr
        self._arrays[name] = (base, dims)
        self._next_addr += total
        return base

    def addr_of(self, name: str) -> int:
        if name in self._scalars:
            return self._scalars[name]
        base, _ = self._arrays[name]
        return base

    @property
    def total_cells(self) -> int:
        return self._next_addr
```

---

### C2 — Estrutura do Gerador (`EWVMGenerator`)

```python
class EWVMGenerator:
    def __init__(self, symbol_table: SymbolTable):
        self.symtab  = symbol_table
        self.layout  = MemoryLayout()
        self._lines: list[str] = []
        self._temp_addrs: dict[str, int] = {}

    def emit(self, *tokens) -> None:
        self._lines.append("\t" + " ".join(str(t) for t in tokens))

    def emit_label(self, name: str) -> None:
        self._lines.append(f"{name}:")

    def generate(self, instructions: list[IRInstr]) -> str:
        self._allocate_symbols()
        self.emit("START")
        for instr in instructions:
            self._translate(instr)
        return "\n".join(self._lines)

    def _allocate_symbols(self) -> None:
        for sym in self.symtab.all_symbols():
            if sym.kind == "scalar":
                self.layout.allocate_scalar(sym.name)
            elif sym.kind == "array":
                self.layout.allocate_array(sym.name, sym.dimensions)
        if self.layout.total_cells > 0:
            self.emit("ALLOC", self.layout.total_cells)
```

---

### C3 — Tradução instrução a instrução

Método `_translate` com `match` Python 3.10+:

```python
def _translate(self, instr: IRInstr) -> None:
    match instr:
        case IRLabelInstr(label=lbl):
            self.emit_label(str(lbl))
        case IRJump(label=lbl):
            self.emit("JUMP", lbl)
        case IRStop():
            self.emit("STOP")
        case IRReturn():
            self.emit("RETURN")
        case IRAssign():
            self._push_value(instr.src)
            self._pop_to(instr.dest)
        case IROp():
            self._translate_op(instr)
        case IRUnaryOp():
            self._translate_unary(instr)
        case IRCJump():
            self._translate_cjump(instr)
        case IRPrint():
            self._translate_print(instr)
        case IRRead():
            self._translate_read(instr)
        case IRCall():
            self._translate_call(instr)
        case IRLoadArray():
            self._translate_load_array(instr)
        case IRStoreArray():
            self._translate_store_array(instr)
        case _:
            raise NotImplementedError(f"Instrução IR sem tradução: {type(instr).__name__}")
```

#### C3a — Push e Pop de valores

```python
def _push_value(self, val) -> None:
    if isinstance(val, bool):          # bool antes de int (bool é subclasse de int)
        self.emit("PUSHI", 1 if val else 0)
    elif isinstance(val, int):
        self.emit("PUSHI", val)
    elif isinstance(val, float):
        self.emit("PUSHF", val)
    elif isinstance(val, str) and val.startswith("'"):
        self.emit("PUSHS", val)
    elif isinstance(val, str):         # nome de variável
        self.emit("PUSHG", self.layout.addr_of(val))
    elif isinstance(val, Temp):
        self.emit("PUSHG", self._temp_addr(val))

def _pop_to(self, dest) -> None:
    if isinstance(dest, str):
        self.emit("POPG", self.layout.addr_of(dest))
    elif isinstance(dest, Temp):
        self.emit("POPG", self._temp_addr(dest))

def _temp_addr(self, temp: Temp) -> int:
    key = str(temp)
    if key not in self._temp_addrs:
        self._temp_addrs[key] = self.layout.allocate_scalar(key)
    return self._temp_addrs[key]
```

#### C3b — Operações binárias

```python
# Mapeamento IR → EWVM
_INT_OPS  = {"+": "ADD",  "-": "SUB",  "*": "MUL",  "/": "DIV"}
_REAL_OPS = {"+": "FADD", "-": "FSUB", "*": "FMUL", "/": "FDIV"}
_CMP_OPS  = {"<": "INF", "<=": "INFEQ", ">": "SUP", ">=": "SUPEQ",
              "==": "EQUAL", "!=": "NEQ"}

def _translate_op(self, instr: IROp) -> None:
    self._push_value(instr.left)
    self._push_value(instr.right)
    op = instr.op
    if op in _CMP_OPS:
        self.emit(_CMP_OPS[op])
    elif op in ("AND",):  self.emit("AND")
    elif op in ("OR",):   self.emit("OR")
    else:
        # Escolher versão real ou inteira conforme os tipos na tabela de símbolos
        left_type  = self._type_of(instr.left)
        if left_type == "REAL":
            self.emit(_REAL_OPS.get(op, op))
        else:
            self.emit(_INT_OPS.get(op, op))
    self._pop_to(instr.dest)

def _type_of(self, val) -> str:
    """Devolve o tipo IR de um valor (variável, temporário ou literal)."""
    if isinstance(val, float):  return "REAL"
    if isinstance(val, bool):   return "LOGICAL"
    if isinstance(val, int):    return "INTEGER"
    if isinstance(val, str):
        sym = self.symtab.lookup(val)
        return sym.type if sym else "INTEGER"
    return "INTEGER"
```

#### C3c — Salto condicional

```python
def _translate_cjump(self, instr: IRCJump) -> None:
    self._push_value(instr.cond)
    self.emit("JZ", instr.false_label)
    self.emit("JUMP", instr.true_label)
```

#### C3d — PRINT e READ

```python
def _translate_print(self, instr: IRPrint) -> None:
    for arg in instr.args:
        self._push_value(arg)
        t = self._type_of(arg)
        if t == "REAL":             self.emit("WRITEF")
        elif t == "CHARACTER":      self.emit("WRITES")
        else:                       self.emit("WRITEI")
    self.emit("WRITELN")

def _translate_read(self, instr: IRRead) -> None:
    for target in instr.args:
        if isinstance(target, str):
            t = self._type_of(target)
            if t == "REAL":     self.emit("READF")
            elif t == "CHARACTER": self.emit("READS")
            else:               self.emit("READ")
            self._pop_to(target)
        elif isinstance(target, IRArrayRef):
            self._push_array_base_and_offset(target.name, target.indices)
            self.emit("ADD")
            self.emit("READ")      # ou READF conforme tipo
            self.emit("STOREN")
```

#### C3e — Arrays (indexação column-major, base 1)

```python
# Fortran 77: arrays indexados a partir de 1, armazenamento column-major
def _push_array_base_and_offset(self, name: str, indices: list) -> None:
    """Coloca na stack: endereço_base, offset (separados para LOADN/STOREN)."""
    base, dims = self.layout._arrays[name]
    self.emit("PUSHI", base)   # base address
    self._compute_offset(dims, indices)

def _compute_offset(self, dims: list[int], indices: list) -> None:
    """Calcula offset linear column-major (base 1) e coloca na stack."""
    if len(dims) == 1:
        self._push_value(indices[0])
        self.emit("PUSHI", 1)
        self.emit("SUB")                       # i - 1
    elif len(dims) == 2:
        # offset = (i-1) + d1*(j-1)
        self._push_value(indices[0])
        self.emit("PUSHI", 1)
        self.emit("SUB")                       # (i-1)
        self.emit("PUSHI", dims[0])
        self._push_value(indices[1])
        self.emit("PUSHI", 1)
        self.emit("SUB")                       # (j-1)
        self.emit("MUL")                       # d1*(j-1)
        self.emit("ADD")                       # (i-1) + d1*(j-1)

def _translate_load_array(self, instr: IRLoadArray) -> None:
    self._push_array_base_and_offset(instr.name, instr.indices)
    self.emit("ADD")
    self.emit("LOADN")
    self._pop_to(instr.dest)

def _translate_store_array(self, instr: IRStoreArray) -> None:
    self._push_array_base_and_offset(instr.name, instr.indices)
    self.emit("ADD")                  # endereço final na stack
    self._push_value(instr.src)       # valor a armazenar
    self.emit("STOREN")
```

#### C3f — Funções intrínsecas

```python
_INTRINSICS: dict[str, str | None] = {
    # nome → instrução EWVM directa (None = expansão manual)
    "SQRT": "SQRT", "SIN": "SIN", "COS": "COS", "EXP": "EXP", "LN": "LN",
    "ABS":  None,   "MOD": None,  "INT": "FTOI", "FLOAT": "ITOF",
    "MAX":  None,   "MIN": None,
}

def _translate_call(self, instr: IRCall) -> None:
    if instr.name in _INTRINSICS:
        instr_ewvm = _INTRINSICS[instr.name]
        if instr_ewvm:                         # tradução directa
            for arg in instr.args:
                self._push_value(arg)
            self.emit(instr_ewvm)
        else:                                  # expansão manual
            self._expand_intrinsic(instr.name, instr.args)
        if instr.dest is not None:
            self._pop_to(instr.dest)
    else:
        # Subprograma definido pelo utilizador
        for arg in instr.args:
            self._push_value(arg)
        self.emit("CALL", instr.name)
        if instr.dest is not None:
            self._pop_to(instr.dest)

def _expand_intrinsic(self, name: str, args: list) -> None:
    if name == "MOD":
        # MOD(A, B) = A - (A / B) * B  (divisão inteira)
        self._push_value(args[0])        # A
        self._push_value(args[0])        # A
        self._push_value(args[1])        # B
        self.emit("DIV")                 # A / B
        self._push_value(args[1])        # B
        self.emit("MUL")                 # (A/B) * B
        self.emit("SUB")                 # A - (A/B)*B
    elif name == "ABS":
        # ABS(X) = X < 0 ? -X : X  (via jump)
        lbl_neg = f"ABS_NEG_{self._fresh_id()}"
        lbl_end = f"ABS_END_{self._fresh_id()}"
        self._push_value(args[0])
        self.emit("PUSHI", 0)
        self.emit("INF")                 # X < 0 ?
        self.emit("JZ", lbl_neg)
        self._push_value(args[0])
        self.emit("PUSHI", -1)
        self.emit("MUL")
        self.emit("JUMP", lbl_end)
        self.emit_label(lbl_neg)
        self._push_value(args[0])
        self.emit_label(lbl_end)
    # MAX e MIN: expandir com comparações encadeadas
```

---

### C4 — Integração no CLI

```python
def run_codegen(source: str, filename: str, source_format: str, debug: bool):
    tree, symtable = run_sem(source, filename, source_format, debug=False)
    from src.representacao_intermedia.gerador import IRGenerator
    from src.codegen.ewvm import EWVMGenerator
    ir_gen = IRGenerator()
    ir_gen.generate(tree)
    ewvm_gen = EWVMGenerator(symtable)
    code = ewvm_gen.generate(ir_gen.instructions)
    print(code)
    return code
```

---

### C5 — Testes (`tests/test_codegen.py`)

```python
class TestCodigoHello:
    def test_tem_stop(self, codegen):         ...  # "STOP" in code
    def test_tem_writes(self, codegen):       ...  # "WRITES" in code
    def test_tem_writeln(self, codegen):      ...  # "WRITELN" in code
    def test_comeca_com_start(self, codegen): ...  # code.strip().startswith("START")

class TestCodigoFatorial:
    def test_tem_mul(self, codegen):          ...  # "MUL" in code
    def test_tem_read(self, codegen):         ...  # "READ" in code
    def test_tem_loop(self, codegen):         ...  # JUMP + LABEL (ciclo)
    def test_tem_alloc(self, codegen):        ...  # "ALLOC" para variáveis

class TestCodigoPrimo:
    def test_tem_jz_ou_jnz(self, codegen):    ...  # salto condicional
    def test_tem_writei_para_num(self, codegen): ...

class TestEndToEnd:
    """Executar na EWVM e comparar stdout com esperado."""
    def test_hello_output(self):              ...  # "Ola, Mundo!\n"
    def test_fatorial_5(self):                ...  # input=5 → output="120"
```

---

## 🔲 Otimização — Por implementar (valorização)

**Ficheiro:** `src/optimizer.py`

### O1 — Propagação de Constantes

```python
def constant_folding(instructions: list[IRInstr]) -> list[IRInstr]:
    """
    Elimina operações cujos operandos são todos constantes conhecidas.
    Algoritmo em uma passagem:
      1. Manter dict {nome_ou_temp → valor_literal}
      2. IRAssign(dest, literal):  consts[dest] = literal
      3. IROp(op, dest, left, right):
         - Se left in consts: substituir por consts[left]
         - Se right in consts: substituir por consts[right]
         - Se ambos são literais: calcular resultado em compile-time,
           emitir IRAssign(dest, resultado), não emitir IROp
      4. IRCJump com cond constante: substituir por IRJump para o branch correcto
      5. Qualquer IRAssign que nao seja literal: remover dest de consts
    """
```

### O2 — Eliminação de Código Morto

```python
def dead_code_elimination(instructions: list[IRInstr]) -> list[IRInstr]:
    """
    Remove instruções inalcançáveis (após GOTO/STOP sem label a seguir).
    Algoritmo:
      dead = False
      Para cada instrução:
        - Se IRLabelInstr: dead = False (pode ser alvo de salto)
        - Se dead: descartar instrução
        - Se IRJump ou IRStop: dead = True
    """
```

### O3 — Eliminação de Temporários de Uso Único (Peephole)

```python
def eliminate_single_use_temps(instructions: list[IRInstr]) -> list[IRInstr]:
    """
    Padrão:  t1 = A op B  ;  X = t1   (t1 só usado uma vez)
    Optimização: X = A op B  (eliminar t1)
    Algoritmo:
      1. Contar usos de cada Temp em toda a lista
      2. Para cada IROp(dest=Temp) seguido de IRAssign(dest=X, src=Temp)
         com use_count[Temp] == 1: fundir em IROp(dest=X)
    """
```

---

## ✅ Estado dos Testes

| Ficheiro                       | Resultado                       |
| ------------------------------ | ------------------------------- |
| `tests/test_lexer.py`        | ✅ 98/98                        |
| `tests/test_parser_smoke.py` | ✅ 20/20                        |
| `tests/test_ir.py`           | ✅ 7/7                          |
| `tests/test_semantic.py`     | 🔲 Por criar                 |
| `tests/test_codegen.py`      | ✅ 5/5                       |
| **Total implementados**  | ✅**130/130**             |

**Fixtures actuais:**

* `tests/fixtures/hello.f` — programa mínimo
* `tests/fixtures/fatorial.f` — DO loop, READ, multiplicação
* `tests/fixtures/primo.f` — GOTO, LOGICAL, MOD, IF-THEN-ELSE aninhado
* `tests/fixtures/continuation.f` — continuação de linha fixed-form

**Fixtures a criar:**

* [ ] `tests/fixtures/arrays.f` — declaração e acesso a arrays 1D e 2D
* [ ] `tests/fixtures/arith_if.f` — IF aritmético com três labels distintos
* [ ] `tests/fixtures/tipos.f` — mistura INTEGER/REAL para testar coerção
* [ ] `tests/fixtures/expected/hello.vm` — output EWVM esperado (end-to-end)
* [ ] `tests/fixtures/expected/fatorial.vm` — output EWVM esperado

---

## Ordem de Implementação Recomendada

```
1.  Melhorias ao código existente
    ├── M1: Remover _emit_structured_do (código morto)
    ├── M4/M5: Refactorizar CLI (separar construção de apresentação)
    └── M6/M9: Limpar Node base class

2.  Análise Semântica
    ├── S1: SymbolTable (symbols.py) + testes unitários
    ├── S2a: visit_TypeDecl e visit_ArrayDecl
    ├── S2b: Resolução CallExpr vs ArrayRef
    ├── S2c/d: Verificação de tipos e atribuições
    ├── S3: Integração CLI --stage sem
    └── S4: tests/test_semantic.py (mínimo 15 casos)

3.  Validação end-to-end
    └── Executar .vm na EWVM; comparar stdout com esperado

4.  Otimizações (valorização)
    ├── O1: Propagação de constantes
    ├── O2: Eliminação de código morto
    └── O3: Eliminação de temporários de uso único
```
