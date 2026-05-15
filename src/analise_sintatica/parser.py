"""Parser (análise sintática) para Fortran 77 com PLY (ply.yacc).

Gramática coberta:
  program      : PROGRAM ID body END subprogram_list
  body         : decl_list stmt_list
  stmt_list    : stmt_list stmt | ε
  stmt         : decl | assign | if_stmt | do_stmt | goto |
                 continue | print | read | stop | call | return
  expr         : expressões aritméticas, relacionais, lógicas
                 com precedência correta
"""

import ply.yacc as yacc

from src.errors import ParseError, SourceLocation
from src.analise_lexica.lexer import Fortran77Lexer
import src.analise_sintatica.ast_nodes as ast
from src.analise_sintatica.parser_decls import DeclRules
from src.analise_sintatica.parser_expr import ExprRules
from src.analise_sintatica.parser_stmts import StmtRules
from src.analise_sintatica.parser_subprograms import SubprogramRules


class Fortran77Parser(DeclRules, StmtRules, ExprRules, SubprogramRules):
    """Parser PLY para Fortran 77.

    Uso:
        lexer  = Fortran77Lexer().build()
        parser = Fortran77Parser(lexer).build()
        tree   = parser.parse(source, filename="prog.f")
    """

    start = "program"

    def __init__(self, lexer: Fortran77Lexer):
        self.lexer = lexer
        self.tokens = lexer.tokens          # PLY exige este atributo
        self._filename = "<stdin>"
        self.parser = None

    def _build_elseif_branch(self, chain: list):
        """Converte cadeia ELSEIF/ELSE numa lista de stmts para else_stmts."""
        if not chain:
            return []

        head = chain[0]
        if head[0] == "ELSE":
            return head[1]

        condition, then_stmts, lineno = head
        nested_else = self._build_elseif_branch(chain[1:])
        nested_if = ast.IfStmt(
            condition=condition,
            then_stmts=then_stmts,
            else_stmts=nested_else,
            lineno=lineno,
        )
        return [nested_if]

    # ------------------------------------------------------------------
    # Precedência (do menor para o maior)
    # Baseado na especificação ANSI F77:
    #   1. .EQV. .NEQV.   (menor)
    #   2. .OR.
    #   3. .AND.
    #   4. .NOT.
    #   5. .EQ. .NE. .LT. .LE. .GT. .GE.
    #   6. // (concatenação)
    #   7. + -  (binário)
    #   8. * /
    #   9. + -  (unário)
    #  10. **              (maior, associa à direita)
    # ------------------------------------------------------------------
    precedence = (
        ("left", "EQV", "NEQV"),
        ("left", "OR"),
        ("left", "AND"),
        ("right", "NOT"),
        ("left", "EQ", "NE", "LT", "LE", "GT", "GE"),
        ("left", "CONCAT"),
        ("left", "PLUS", "MINUS"),
        ("left", "STAR", "SLASH"),
        ("right", "UMINUS", "UPLUS"),
        ("right", "POWER"),
    )

    # Tratamento de erros
    def p_error(self, p):
        if p:
            column = getattr(p, "lexpos", -1)
            column = column + 1 if column >= 0 else 0
            raise ParseError(
                f"Erro de sintaxe em {p.value!r}",
                SourceLocation(self._filename, p.lineno, column),
            )
        else:
            # EOF inesperado: indica a linha seguinte ao último caracter lido.
            eof_line = self._source_line_count + 1
            raise ParseError(
                "Erro de sintaxe: fim de ficheiro inesperado",
                SourceLocation(self._filename, eof_line, 1),
            )

    # Construção e interface pública
    def build(self, **kwargs):
        """Constrói o parser PLY."""
        self.parser = yacc.yacc(module=self, **kwargs)
        return self

    def parse(self, source: str, filename: str = "<stdin>", source_format: str = "fixed") -> ast.Program:
        """Analisa o texto Fortran e devolve a AST.

        Internamente usa o lexer para produzir os tokens,
        depois alimenta o parser PLY.
        """
        self._filename = filename
        self._source_line_count = source.count("\n")
        tokens = self.lexer.tokenize(source, filename=filename, source_format=source_format)
        # PLY yacc.parse espera um lexer com input()/token() — criamos um
        # adaptador simples a partir da lista de tokens já produzida.
        token_iter = iter(tokens)

        class TokenAdapter:
            """Adapta uma lista de LexToken para a interface que o PLY yacc espera."""

            def __init__(self, it):
                self._it = it
                self.lineno = 1
                self.lexpos = 0

            def token(self):
                try:
                    tok = next(self._it)
                    self.lineno = tok.lineno
                    self.lexpos = getattr(tok, "lexpos", 0)
                    return tok
                except StopIteration:
                    return None

            def input(self, _):
                pass

        adapter = TokenAdapter(token_iter)
        return self.parser.parse(lexer=adapter, tracking=True)
