"""Parser (análise sintática) para Fortran 77 com PLY (ply.yacc).

Gramática coberta:
  program      : PROGRAM ID stmts END
  stmts        : stmt stmts | ε
  stmt         : decl | assign | if_stmt | do_stmt | goto |
                 continue | print | read | stop | call | return
  expr         : expressões aritméticas, relacionais, lógicas
                 com precedência correta
"""

import ply.yacc as yacc

from src.errors import ParseError, SourceLocation
from src.analise_lexica.lexer import Fortran77Lexer
import src.analise_sintatica.ast_nodes as ast


class Fortran77Parser:
    """Parser PLY para Fortran 77.

    Uso:
        lexer  = Fortran77Lexer().build()
        parser = Fortran77Parser(lexer).build()
        tree   = parser.parse(source, filename="prog.f")
    """

    def __init__(self, lexer: Fortran77Lexer):
        self.lexer  = lexer
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
        ("left",  "EQV", "NEQV"),
        ("left",  "OR"),
        ("left",  "AND"),
        ("right", "NOT"),
        ("left",  "EQ", "NE", "LT", "LE", "GT", "GE"),
        ("left",  "CONCAT"),
        ("left",  "PLUS", "MINUS"),
        ("left",  "STAR", "SLASH"),
        ("right", "UMINUS", "UPLUS"),
        ("right", "POWER"),
    )

    # Ponto de entrada
    def p_program(self, p):
        """program : PROGRAM ID body END subprogram_list"""
        decls, stmts = p[3]
        p[0] = ast.Program(
            name=p[2],
            decls=decls,
            stmts=stmts,
            subprograms=p[5],
            lineno=p.lineno(1),
        )

    # body agrupa declarações (antes) e instruções (depois)
    def p_body(self, p):
        """body : decl_list stmt_list"""
        p[0] = (p[1], p[2])

    # Declarações de tipo
    def p_decl_list_empty(self, p):
        """decl_list :"""
        p[0] = []

    def p_decl_list(self, p):
        """decl_list : decl_list decl"""
        p[0] = p[1] + [p[2]]

    def p_decl_type(self, p):
        """decl : type_spec var_decl_list"""
        p[0] = ast.TypeDecl(typename=p[1], variables=p[2], lineno=p.lineno(1))

    def p_decl_implicit_none(self, p):
        """decl : IMPLICIT NONE"""
        p[0] = ast.ImplicitNone(lineno=p.lineno(1))

    def p_type_spec(self, p):
        """type_spec : INTEGER
                     | REAL
                     | LOGICAL
                     | CHARACTER"""
        p[0] = p[1]

    def p_type_spec_double(self, p):
        """type_spec : DOUBLE PRECISION"""
        p[0] = "DOUBLE PRECISION"

    def p_var_decl_list_single(self, p):
        """var_decl_list : var_decl"""
        p[0] = [p[1]]

    def p_var_decl_list_multi(self, p):
        """var_decl_list : var_decl_list COMMA var_decl"""
        p[0] = p[1] + [p[3]]

    def p_var_decl_simple(self, p):
        """var_decl : ID"""
        p[0] = p[1]

    def p_var_decl_array(self, p):
        """var_decl : ID LPAREN dim_list RPAREN"""
        p[0] = ast.ArrayDecl(name=p[1], dimensions=p[3], lineno=p.lineno(1))

    def p_dim_list_single(self, p):
        """dim_list : expr"""
        p[0] = [p[1]]

    def p_dim_list_multi(self, p):
        """dim_list : dim_list COMMA expr"""
        p[0] = p[1] + [p[3]]


    # Lista de instruções
    def p_stmt_list_empty(self, p):
        """stmt_list :"""
        p[0] = []

    def p_stmt_list(self, p):
        """stmt_list : stmt_list stmt"""
        p[0] = p[1] + [p[2]]

    # Instrução com label opcional
    def p_stmt_labeled(self, p):
        """stmt : LABEL unlabeled_stmt"""
        s = p[2]
        # Preserva o label em qualquer instrucao para fases seguintes
        # (IR/codegen) conseguirem resolver GOTO corretamente.
        setattr(s, "source_label", p[1])

        # Mantemos o campo especifico de ContinueStmt por compatibilidade.
        if isinstance(s, ast.ContinueStmt):
            s.label = p[1]
        p[0] = s

    def p_stmt_unlabeled(self, p):
        """stmt : unlabeled_stmt"""
        p[0] = p[1]


    # Instruções sem label
    def p_unlabeled_assign(self, p):
        """unlabeled_stmt : assign_stmt"""
        p[0] = p[1]

    def p_unlabeled_if(self, p):
        """unlabeled_stmt : if_stmt"""
        p[0] = p[1]

    def p_unlabeled_do(self, p):
        """unlabeled_stmt : do_stmt"""
        p[0] = p[1]

    def p_unlabeled_goto(self, p):
        """unlabeled_stmt : goto_stmt"""
        p[0] = p[1]

    def p_unlabeled_continue(self, p):
        """unlabeled_stmt : continue_stmt"""
        p[0] = p[1]

    def p_unlabeled_print(self, p):
        """unlabeled_stmt : print_stmt"""
        p[0] = p[1]

    def p_unlabeled_read(self, p):
        """unlabeled_stmt : read_stmt"""
        p[0] = p[1]

    def p_unlabeled_write(self, p):
        """unlabeled_stmt : write_stmt"""
        p[0] = p[1]

    def p_unlabeled_stop(self, p):
        """unlabeled_stmt : stop_stmt"""
        p[0] = p[1]

    def p_unlabeled_return(self, p):
        """unlabeled_stmt : return_stmt"""
        p[0] = p[1]

    def p_unlabeled_call(self, p):
        """unlabeled_stmt : call_stmt"""
        p[0] = p[1]


    # Atribuição:  var = expr   ou   arr(i) = expr
    def p_assign_simple(self, p):
        """assign_stmt : ID EQUALS expr"""
        p[0] = ast.AssignStmt(
            target=ast.VarRef(name=p[1], lineno=p.lineno(1)),
            value=p[3], lineno=p.lineno(1))

    def p_assign_array(self, p):
        """assign_stmt : ID LPAREN arg_list RPAREN EQUALS expr"""
        p[0] = ast.AssignStmt(
            target=ast.ArrayRef(name=p[1], indices=p[3], lineno=p.lineno(1)),
            value=p[6], lineno=p.lineno(1))


    # IF-THEN-ELSE-ENDIF
    def p_if_stmt(self, p):
        """if_stmt : IF LPAREN expr RPAREN THEN stmt_list elseif_chain ENDIF"""
        p[0] = ast.IfStmt(
            condition=p[3],
            then_stmts=p[6],
            else_stmts=self._build_elseif_branch(p[7]),
            lineno=p.lineno(1),
        )

    def p_elseif_chain_elseif(self, p):
        """elseif_chain : ELSEIF LPAREN expr RPAREN THEN stmt_list elseif_chain"""
        p[0] = [(p[3], p[6], p.lineno(1))] + p[7]

    def p_elseif_chain_else(self, p):
        """elseif_chain : ELSE stmt_list"""
        p[0] = [("ELSE", p[2])]

    def p_elseif_chain_empty(self, p):
        """elseif_chain :"""
        p[0] = []

    # IF aritmético:  IF (expr) label, label, label
    def p_arith_if(self, p):
        """if_stmt : IF LPAREN expr RPAREN INT_LIT COMMA INT_LIT COMMA INT_LIT"""
        p[0] = ast.ArithIfStmt(expr=p[3],
                               label_neg=p[5], label_zero=p[7], label_pos=p[9],
                               lineno=p.lineno(1))



    # DO loop:  DO label var = start, end [, step]
    def p_do_stmt(self, p):
        """do_stmt : DO INT_LIT ID EQUALS expr COMMA expr"""
        p[0] = ast.DoStmt(label=p[2], var=p[3],
                          start=p[5], end=p[7], step=None,
                          body=[], lineno=p.lineno(1))

    def p_do_stmt_step(self, p):
        """do_stmt : DO INT_LIT ID EQUALS expr COMMA expr COMMA expr"""
        p[0] = ast.DoStmt(label=p[2], var=p[3],
                          start=p[5], end=p[7], step=p[9],
                          body=[], lineno=p.lineno(1))


    # GOTO, CONTINUE, STOP, RETURN
    def p_goto(self, p):
        """goto_stmt : GOTO INT_LIT"""
        p[0] = ast.GotoStmt(label=p[2], lineno=p.lineno(1))

    def p_continue(self, p):
        """continue_stmt : CONTINUE"""
        p[0] = ast.ContinueStmt(label=None, lineno=p.lineno(1))

    def p_stop(self, p):
        """stop_stmt : STOP"""
        p[0] = ast.StopStmt(lineno=p.lineno(1))

    def p_return(self, p):
        """return_stmt : RETURN"""
        p[0] = ast.ReturnStmt(lineno=p.lineno(1))


    # PRINT, READ, WRITE
    def p_print_star(self, p):
        """print_stmt : PRINT STAR COMMA print_list"""
        p[0] = ast.PrintStmt(items=p[4], lineno=p.lineno(1))

    def p_print_list_single(self, p):
        """print_list : expr"""
        p[0] = [p[1]]

    def p_print_list_multi(self, p):
        """print_list : print_list COMMA expr"""
        p[0] = p[1] + [p[3]]

    def p_read_star(self, p):
        """read_stmt : READ STAR COMMA var_list"""
        p[0] = ast.ReadStmt(variables=p[4], lineno=p.lineno(1))

    def p_read_paren_fmt(self, p):
        """read_stmt : READ LPAREN expr COMMA expr RPAREN var_list"""
        p[0] = ast.ReadStmt(variables=p[7], lineno=p.lineno(1))

    def p_read_paren_star(self, p):
        """read_stmt : READ LPAREN expr COMMA STAR RPAREN var_list"""
        p[0] = ast.ReadStmt(variables=p[7], lineno=p.lineno(1))

    def p_var_list_single(self, p):
        """var_list : lvalue"""
        p[0] = [p[1]]

    def p_var_list_multi(self, p):
        """var_list : var_list COMMA lvalue"""
        p[0] = p[1] + [p[3]]

    def p_lvalue_var(self, p):
        """lvalue : ID"""
        p[0] = ast.VarRef(name=p[1], lineno=p.lineno(1))

    def p_lvalue_array(self, p):
        """lvalue : ID LPAREN arg_list RPAREN"""
        p[0] = ast.ArrayRef(name=p[1], indices=p[3], lineno=p.lineno(1))

    def p_write_stmt(self, p):
        """write_stmt : WRITE LPAREN expr COMMA STAR RPAREN print_list"""
        p[0] = ast.WriteStmt(unit=p[3], fmt=None, items=p[7], lineno=p.lineno(1))

    def p_write_stmt_fmt(self, p):
        """write_stmt : WRITE LPAREN expr COMMA expr RPAREN print_list"""
        p[0] = ast.WriteStmt(unit=p[3], fmt=p[5], items=p[7], lineno=p.lineno(1))



    # CALL
    def p_call_no_args(self, p):
        """call_stmt : CALL ID"""
        p[0] = ast.CallStmt(name=p[2], args=[], lineno=p.lineno(1))

    def p_call_with_args(self, p):
        """call_stmt : CALL ID LPAREN arg_list RPAREN"""
        p[0] = ast.CallStmt(name=p[2], args=p[4], lineno=p.lineno(1))



    # Expressões — com precedência declarada acima
    # Operadores binários
    def p_expr_binop(self, p):
        """expr : expr PLUS expr
            | expr MINUS expr
            | expr STAR expr
            | expr SLASH expr
            | expr POWER expr
            | expr CONCAT expr
            | expr EQ expr
            | expr NE expr
            | expr LT expr
            | expr LE expr
            | expr GT expr
            | expr GE expr
            | expr AND expr
            | expr OR expr
            | expr EQV expr
            | expr NEQV expr"""
        p[0] = ast.BinOp(op=p[2], left=p[1], right=p[3], lineno=p.lineno(2))

    # Operadores unários
    def p_expr_uminus(self, p):
        """expr : MINUS expr %prec UMINUS"""
        p[0] = ast.UnaryOp(op="-", operand=p[2], lineno=p.lineno(1))

    def p_expr_uplus(self, p):
        """expr : PLUS expr %prec UPLUS"""
        p[0] = p[2]   # +expr == expr

    def p_expr_not(self, p):
        """expr : NOT expr"""
        p[0] = ast.UnaryOp(op=".NOT.", operand=p[2], lineno=p.lineno(1))

    # Parênteses
    def p_expr_paren(self, p):
        """expr : LPAREN expr RPAREN"""
        p[0] = p[2]

    # Literais
    def p_expr_int(self, p):
        """expr : INT_LIT"""
        p[0] = ast.IntLit(value=p[1], lineno=p.lineno(1))

    def p_expr_real(self, p):
        """expr : REAL_LIT"""
        p[0] = ast.RealLit(value=p[1], lineno=p.lineno(1))

    def p_expr_bool(self, p):
        """expr : BOOL_LIT"""
        p[0] = ast.BoolLit(value=p[1], lineno=p.lineno(1))

    def p_expr_string(self, p):
        """expr : STRING_LIT"""
        p[0] = ast.StringLit(value=p[1], lineno=p.lineno(1))

    # Variável ou chamada de função
    def p_expr_id(self, p):
        """expr : ID"""
        p[0] = ast.VarRef(name=p[1], lineno=p.lineno(1))

    def p_expr_call_or_array(self, p):
        """expr : ID LPAREN arg_list RPAREN"""
        # No Fortran 77 a distinção função/array é semântica.
        # O parser produz CallExpr; a análise semântica decide.
        p[0] = ast.CallExpr(name=p[1], args=p[3], lineno=p.lineno(1))

    # Lista de argumentos
    def p_arg_list_single(self, p):
        """arg_list : expr"""
        p[0] = [p[1]]

    def p_arg_list_multi(self, p):
        """arg_list : arg_list COMMA expr"""
        p[0] = p[1] + [p[3]]

    def p_subprogram_list_empty(self, p):
        """subprogram_list :"""
        p[0] = []

    def p_subprogram_list(self, p):
        """subprogram_list : subprogram_list subprogram"""
        p[0] = p[1] + [p[2]]

    def p_subprogram(self, p):
        """subprogram : function_def
                      | subroutine_def"""
        p[0] = p[1]

    def p_function_def(self, p):
        """function_def : type_spec FUNCTION ID LPAREN param_list_opt RPAREN body END"""
        decls, stmts = p[7]
        p[0] = ast.FunctionDef(
            name=p[3],
            return_type=p[1],
            params=p[5],
            decls=decls,
            stmts=stmts,
            lineno=p.lineno(2),
        )

    def p_subroutine_def(self, p):
        """subroutine_def : SUBROUTINE ID LPAREN param_list_opt RPAREN body END
                          | SUBROUTINE ID body END"""
        if len(p) == 5:
            decls, stmts = p[3]
            p[0] = ast.SubroutineDef(
                name=p[2],
                params=[],
                decls=decls,
                stmts=stmts,
                lineno=p.lineno(1),
            )
            return

        decls, stmts = p[6]
        p[0] = ast.SubroutineDef(
            name=p[2],
            params=p[4],
            decls=decls,
            stmts=stmts,
            lineno=p.lineno(1),
        )

    def p_param_list_opt_empty(self, p):
        """param_list_opt :"""
        p[0] = []

    def p_param_list_opt(self, p):
        """param_list_opt : param_list"""
        p[0] = p[1]

    def p_param_list_single(self, p):
        """param_list : ID"""
        p[0] = [p[1]]

    def p_param_list_multi(self, p):
        """param_list : param_list COMMA ID"""
        p[0] = p[1] + [p[3]]

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

    def parse(self, source: str, filename: str = "<stdin>",
              source_format: str = "fixed") -> ast.Program:
        """Analisa o texto Fortran e devolve a AST.

        Internamente usa o lexer para produzir os tokens,
        depois alimenta o parser PLY.
        """
        self._filename = filename
        self._source_line_count = source.count("\n")
        tokens = self.lexer.tokenize(source, filename=filename,
                                     source_format=source_format)
        # PLY yacc.parse espera um lexer com input()/token() — criamos um
        # adaptador simples a partir da lista de tokens já produzida.
        token_iter = iter(tokens)

        class TokenAdapter:
            """Adapta uma lista de LexToken para a interface que o PLY yacc espera."""
            def __init__(self, it):
                self._it    = it
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
