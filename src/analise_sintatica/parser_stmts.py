"""Regras de instruções do parser Fortran 77 (PLY)."""

import src.analise_sintatica.ast_nodes as ast


class StmtRules:
    """Regras de instruções e controlo de fluxo."""

    # Lista de instruções
    def p_stmt_list_empty(self, p):
        """stmt_list :"""
        p[0] = []

    def p_stmt_list(self, p):
        """stmt_list : stmt_list stmt separators"""
        p[0] = p[1] + ([] if p[2] is None else [p[2]])

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

    def p_stmt_error(self, p):
        """stmt : error"""
        self.parser.errok()
        p[0] = None

    # Instruções sem label
    def p_unlabeled_stmt(self, p):
        """unlabeled_stmt : assign_stmt
                          | if_stmt
                          | do_stmt
                          | goto_stmt
                          | continue_stmt
                          | print_stmt
                          | read_stmt
                          | write_stmt
                          | stop_stmt
                          | return_stmt
                          | call_stmt"""
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
        """if_stmt : IF LPAREN expr RPAREN THEN separators stmt_list elseif_chain ENDIF"""
        p[0] = ast.IfStmt(
            condition=p[3],
            then_stmts=p[7],
            else_stmts=self._build_elseif_branch(p[8]),
            lineno=p.lineno(1),
        )

    def p_elseif_chain_elseif(self, p):
        """elseif_chain : ELSEIF LPAREN expr RPAREN THEN separators stmt_list elseif_chain"""
        p[0] = [(p[3], p[7], p.lineno(1))] + p[8]

    def p_elseif_chain_else(self, p):
        """elseif_chain : ELSE separators stmt_list"""
        p[0] = [("ELSE", p[3])]

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
