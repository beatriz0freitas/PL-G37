"""Regras de expressões do parser Fortran 77 (PLY)."""

import src.analise_sintatica.ast_nodes as ast


class ExprRules:
    """Regras de expressões e listas de argumentos."""

    # Expressões — com precedência declarada no parser principal
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
