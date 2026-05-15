"""Regras de subprogramas do parser Fortran 77 (PLY)."""

import src.analise_sintatica.ast_nodes as ast


class SubprogramRules:
    """Regras de definição de subprogramas."""

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
        """function_def : type_spec FUNCTION ID LPAREN param_list_opt RPAREN separators body END opt_separators"""
        decls, stmts = p[8]
        p[0] = ast.FunctionDef(
            name=p[3],
            return_type=p[1],
            params=p[5],
            decls=decls,
            stmts=stmts,
            lineno=p.lineno(2),
        )

    def p_subroutine_def(self, p):
        """subroutine_def : SUBROUTINE ID LPAREN param_list_opt RPAREN separators body END opt_separators
                          | SUBROUTINE ID separators body END opt_separators"""
        if len(p) == 7:
            decls, stmts = p[4]
            p[0] = ast.SubroutineDef(
                name=p[2],
                params=[],
                decls=decls,
                stmts=stmts,
                lineno=p.lineno(1),
            )
            return

        decls, stmts = p[7]
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
