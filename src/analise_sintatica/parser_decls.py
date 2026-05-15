"""Regras de declarações do parser Fortran 77 (PLY)."""

import src.analise_sintatica.ast_nodes as ast


class DeclRules:
    """Regras de declarações e corpo do programa."""

    # Ponto de entrada
    def p_program(self, p):
        """program : opt_separators PROGRAM ID separators body END opt_separators subprogram_list opt_separators"""
        decls, stmts = p[5]
        p[0] = ast.Program(
            name=p[3],
            decls=decls,
            stmts=stmts,
            subprograms=p[8],
            lineno=p.lineno(2),
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
        """decl_list : decl_list decl separators"""
        p[0] = p[1] + ([] if p[2] is None else [p[2]])

    def p_decl_type(self, p):
        """decl : type_spec var_decl_list"""
        p[0] = ast.TypeDecl(typename=p[1], variables=p[2], lineno=p.lineno(1))

    def p_decl_implicit_none(self, p):
        """decl : IMPLICIT NONE"""
        p[0] = ast.ImplicitNone(lineno=p.lineno(1))

    def p_decl_error(self, p):
        """decl : error"""
        self.parser.errok()
        p[0] = None

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
