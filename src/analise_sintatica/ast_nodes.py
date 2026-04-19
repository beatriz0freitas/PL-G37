"""Nós da AST para Fortran 77.

Hierarquia:
  Node                  — base de todos os nós
  ├── Program           — PROGRAM nome ... END
  ├── Decl              — declarações de tipo
  │   └── TypeDecl      — INTEGER/REAL/LOGICAL/CHARACTER varlist
  └── Stmt              — instruções
      ├── AssignStmt    — var = expr
      ├── IfStmt        — IF (cond) THEN ... [ELSE ...] ENDIF
      ├── ArithIfStmt   — IF (expr) label, label, label
      ├── DoStmt        — DO label var = start, end [, step]
      ├── GotoStmt      — GOTO label
      ├── ContinueStmt  — [label] CONTINUE
      ├── PrintStmt     — PRINT *, exprlist
      ├── ReadStmt      — READ *, varlist
      ├── StopStmt      — STOP
      └── Expr          — expressões (aritméticas, relacionais, lógicas)
          ├── IntLit
          ├── RealLit
          ├── BoolLit
          ├── StringLit
          ├── VarRef
          ├── ArrayRef
          ├── CallExpr
          ├── UnaryOp
          └── BinOp
"""

from dataclasses import dataclass
from typing import Optional



# Base
class Node:
    """Base de todos os nós da AST."""
    pass



# Programa
@dataclass
class Program(Node):
    """PROGRAM nome\n  decls\n  stmts\nEND"""
    name: str
    decls: list         # list[TypeDecl]
    stmts: list         # list[Stmt]
    lineno: int = 0



# Declarações
@dataclass
class TypeDecl(Node):
    """INTEGER / REAL / LOGICAL / CHARACTER varlist"""
    typename: str       # "INTEGER", "REAL", "LOGICAL", "CHARACTER"
    variables: list     # list[str | ArrayDecl]
    lineno: int = 0


@dataclass
class ArrayDecl(Node):
    """INTEGER A(10) ou DIMENSION A(10)"""
    name: str
    dimensions: list    # list[Expr]  — tamanhos de cada dimensão
    lineno: int = 0



# Expressões
@dataclass
class IntLit(Node):
    value: int
    lineno: int = 0


@dataclass
class RealLit(Node):
    value: float
    lineno: int = 0


@dataclass
class BoolLit(Node):
    value: bool         # True = .TRUE., False = .FALSE.
    lineno: int = 0


@dataclass
class StringLit(Node):
    value: str
    lineno: int = 0


@dataclass
class VarRef(Node):
    """Referência a variável simples."""
    name: str
    lineno: int = 0


@dataclass
class ArrayRef(Node):
    """Acesso a array: A(I) ou A(I,J)"""
    name: str
    indices: list       # list[Expr]
    lineno: int = 0


@dataclass
class CallExpr(Node):
    """Chamada de função intrínseca ou definida: MOD(N,I), CONVRT(N,B)"""
    name: str
    args: list          # list[Expr]
    lineno: int = 0


@dataclass
class UnaryOp(Node):
    """Operador unário: -expr, .NOT. expr"""
    op: str             # "-" | ".NOT."
    operand: object     # Expr
    lineno: int = 0


@dataclass
class BinOp(Node):
    """Operador binário: expr op expr"""
    op: str         
    left: object        
    right: object      
    lineno: int = 0



# Instruções
@dataclass
class AssignStmt(Node):
    """var = expr   (ou   var(indices) = expr)"""
    target: object      # VarRef | ArrayRef
    value: object       # Expr
    lineno: int = 0


@dataclass
class IfStmt(Node):
    """IF (cond) THEN\n  stmts\n[ELSE\n  stmts]\nENDIF"""
    condition: object   # Expr
    then_stmts: list    # list[Stmt]
    else_stmts: list    # list[Stmt]  — vazio se não há ELSE
    lineno: int = 0


@dataclass
class ArithIfStmt(Node):
    """IF (expr) label_neg, label_zero, label_pos"""
    expr: object        # Expr
    label_neg: int
    label_zero: int
    label_pos: int
    lineno: int = 0


@dataclass
class DoStmt(Node):
    """DO label var = start, end [, step]"""
    label: int          # label do CONTINUE terminal
    var: str            # variável de controlo
    start: object       # Expr
    end: object         # Expr
    step: object        # Expr | None
    body: list          # list[Stmt] 
    lineno: int = 0


@dataclass
class GotoStmt(Node):
    """GOTO label"""
    label: int
    lineno: int = 0


@dataclass
class ContinueStmt(Node):
    """[label] CONTINUE"""
    label: Optional[int]   # None se não tiver label explícito
    lineno: int = 0


@dataclass
class PrintStmt(Node):
    """PRINT *, exprlist"""
    items: list         # list[Expr]
    lineno: int = 0


@dataclass
class ReadStmt(Node):
    """READ *, varlist"""
    variables: list     # list[VarRef | ArrayRef]
    lineno: int = 0


@dataclass
class WriteStmt(Node):
    """WRITE (unit, fmt) exprlist"""
    unit: object        # Expr | None
    fmt: object         # Expr | str | None
    items: list         # list[Expr]
    lineno: int = 0


@dataclass
class StopStmt(Node):
    lineno: int = 0


@dataclass
class ReturnStmt(Node):
    lineno: int = 0


@dataclass
class CallStmt(Node):
    """CALL subname(args)"""
    name: str
    args: list          # list[Expr]
    lineno: int = 0