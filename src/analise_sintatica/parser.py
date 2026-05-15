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

from src.errors import ParseError, SourceLocation, source_line_at
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
        """Liga o parser ao lexer e prepara estado de erro por ficheiro."""
        self.lexer = lexer
        self.tokens = lexer.tokens          # PLY exige este atributo
        self._filename = "<stdin>"
        self._source = ""
        self._source_lines: list[str] = []
        self._parse_errors: list[ParseError] = []
        self._parse_error_keys: set[tuple[int, int, str]] = set()
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

    # Separadores lógicos de linha: produzidos só no caminho parser.parse().
    def p_separators_single(self, p):
        """separators : NEWLINE"""
        p[0] = None

    def p_separators_multi(self, p):
        """separators : separators NEWLINE"""
        p[0] = None

    def p_opt_separators_empty(self, p):
        """opt_separators :"""
        p[0] = None

    def p_opt_separators_some(self, p):
        """opt_separators : separators"""
        p[0] = None

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
    def _record_parse_error(self, message: str, location: SourceLocation, length: int = 1) -> None:
        """Acumula um erro sintático, evitando duplicados da recuperação PLY."""
        key = (location.line, location.column, message)
        if key in self._parse_error_keys:
            return
        self._parse_error_keys.add(key)
        self._parse_errors.append(ParseError(
            message,
            location,
            source_line=source_line_at(self._source, location.line),
            length=length,
        ))

    def p_error(self, p):
        """Regista erros PLY e deixa a recuperação tentar continuar."""
        if p:
            column = getattr(p, "lexpos", -1)
            column = column + 1 if column >= 0 else 1
            length = getattr(p, "length", len(str(getattr(p, "value", ""))) or 1)
            if getattr(p, "type", None) == "NEWLINE":
                message = "Erro de sintaxe no fim da linha"
            else:
                message = f"Erro de sintaxe em {p.value!r}"
            self._record_parse_error(
                message,
                SourceLocation(self._filename, p.lineno, column),
                length=length,
            )
        else:
            eof_line = max(1, self._source_line_count)
            if self._source_lines:
                eof_column = len(self._source_lines[-1]) + 1
            else:
                eof_column = 1
            self._record_parse_error(
                "Erro de sintaxe: fim de ficheiro inesperado",
                SourceLocation(self._filename, eof_line, eof_column),
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
        self._source = source
        self._source_lines = source.splitlines()
        self._source_line_count = len(self._source_lines) or 1
        self._parse_errors = []
        self._parse_error_keys = set()
        tokens = self.lexer.tokenize(
            source,
            filename=filename,
            source_format=source_format,
            include_newlines=True,
        )
        # PLY yacc.parse espera um lexer com input()/token() — criamos um
        # adaptador simples a partir da lista de tokens já produzida.
        token_iter = iter(tokens)

        class TokenAdapter:
            """Adapta uma lista de LexToken para a interface que o PLY yacc espera."""

            def __init__(self, it):
                """Recebe o iterador de tokens já produzido pelo lexer."""
                self._it = it
                self.lineno = 1
                self.lexpos = 0

            def token(self):
                """Devolve o próximo token no formato esperado pelo PLY yacc."""
                try:
                    tok = next(self._it)
                    self.lineno = tok.lineno
                    self.lexpos = getattr(tok, "lexpos", 0)
                    return tok
                except StopIteration:
                    return None

            def input(self, _):
                """Satisfaz a interface de lexer do PLY; os tokens já existem."""
                pass

        adapter = TokenAdapter(token_iter)
        tree = self.parser.parse(lexer=adapter, tracking=True)
        if self._parse_errors:
            if len(self._parse_errors) == 1:
                raise self._parse_errors[0]
            raise ParseError(errors=self._parse_errors)
        if tree is None:
            raise ParseError(
                "Erro de sintaxe",
                SourceLocation(self._filename, self._source_line_count, 1),
                source_line=source_line_at(self._source, self._source_line_count),
            )
        setattr(tree, "_source", source)
        setattr(tree, "_source_lines", self._source_lines)
        return tree
