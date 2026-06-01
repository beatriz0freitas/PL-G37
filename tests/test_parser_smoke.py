# tests/test_parser_smoke.py
#
# Testes da análise sintática (Fortran77Parser) e integração com errors.py.

import pytest

import src.analise_sintatica.ast_nodes as ast
from conftest import FIXTURES, parse_fixture
from src.errors import ParseError, SourceLocation


# ---------------------------------------------------------------------------
# Utilitários locais
# ---------------------------------------------------------------------------

def parse_str(parser, code: str, source_format: str = "free", filename: str = "<test>"):
	"""Faz parsing de uma string inline (free-form por omissão)."""
	return parser.parse(code, filename=filename, source_format=source_format)


# ---------------------------------------------------------------------------
# 1. Programas completos dos fixtures
# ---------------------------------------------------------------------------

class TestFixturePrograms:
	"""Smoke tests: o parser deve aceitar os exemplos base do enunciado."""

	def test_hello_nao_lanca_excecao(self, parser):
		tree = parse_fixture(parser, "hello.f")
		assert isinstance(tree, ast.Program)

	def test_hello_nome_programa(self, parser):
		tree = parse_fixture(parser, "hello.f")
		assert tree.name == "HELLO"

	def test_hello_tem_um_print(self, parser):
		tree = parse_fixture(parser, "hello.f")
		prints = [s for s in tree.stmts if isinstance(s, ast.PrintStmt)]
		assert len(prints) == 1

	def test_fatorial_nao_lanca_excecao(self, parser):
		tree = parse_fixture(parser, "fatorial.f")
		assert isinstance(tree, ast.Program)

	def test_fatorial_tem_decl_integer(self, parser):
		tree = parse_fixture(parser, "fatorial.f")
		decl_types = [d.typename for d in tree.decls if isinstance(d, ast.TypeDecl)]
		assert "INTEGER" in decl_types

	def test_fatorial_tem_do_stmt(self, parser):
		tree = parse_fixture(parser, "fatorial.f")
		assert any(isinstance(s, ast.DoStmt) for s in tree.stmts)

	def test_primo_nao_lanca_excecao(self, parser):
		tree = parse_fixture(parser, "primo.f")
		assert isinstance(tree, ast.Program)

	def test_primo_tem_if_stmt(self, parser):
		tree = parse_fixture(parser, "primo.f")
		assert any(isinstance(s, ast.IfStmt) for s in tree.stmts)

	def test_primo_tem_assign_logico(self, parser):
		tree = parse_fixture(parser, "primo.f")
		assigns = [s for s in tree.stmts if isinstance(s, ast.AssignStmt)]
		assert len(assigns) >= 1

	def test_somaarr_nao_lanca_excecao(self, parser):
		tree = parse_fixture(parser, "somaarr.f")
		assert isinstance(tree, ast.Program)

	def test_somaarr_tem_read_e_assign(self, parser):
		tree = parse_fixture(parser, "somaarr.f")
		assert any(isinstance(s, ast.ReadStmt) for s in tree.stmts)
		assert any(isinstance(s, ast.AssignStmt) for s in tree.stmts)

	def test_conversor_agora_e_suportado(self, parser):
		tree = parse_fixture(parser, "conversor.f")
		assert isinstance(tree, ast.Program)
		assert len(tree.subprograms) == 1
		assert isinstance(tree.subprograms[0], ast.FunctionDef)
		assert tree.subprograms[0].name == "CONVRT"


# ---------------------------------------------------------------------------
# 2. Nós da AST e estrutura mínima
# ---------------------------------------------------------------------------

class TestAstShape:

	def test_program_devolve_decls_e_stmts_lista(self, parser):
		tree = parse_fixture(parser, "hello.f")
		assert isinstance(tree.decls, list)
		assert isinstance(tree.stmts, list)

	def test_assign_emite_assignstmt(self, parser):
		src = """PROGRAM P
				 INTEGER N
				 N = 1
				 END
			  """
		tree = parse_str(parser, src, source_format="free")
		assert any(isinstance(s, ast.AssignStmt) for s in tree.stmts)

	def test_expr_binaria_emite_binop(self, parser):
		src = """PROGRAM P
				 INTEGER A, B, C
				 A = B + C
				 END
			  """
		tree = parse_str(parser, src, source_format="free")
		assign = next(s for s in tree.stmts if isinstance(s, ast.AssignStmt))
		assert isinstance(assign.value, ast.BinOp)
		assert assign.value.op == "+"

	def test_do_stmt_guarda_label(self, parser):
		tree = parse_fixture(parser, "fatorial.f")
		do_stmt = next(s for s in tree.stmts if isinstance(s, ast.DoStmt))
		assert do_stmt.label == 10


# ---------------------------------------------------------------------------
# 3. Erros sintáticos (errors.py aplicado no parser)
# ---------------------------------------------------------------------------

class TestParserErrors:

	def test_erro_sintatico_lanca_parseerror(self, parser):
		src = """PROGRAM P
				 INTEGER N
				 N =
				 END
			  """
		with pytest.raises(ParseError):
			parse_str(parser, src, source_format="free", filename="bad_assign.f")

	def test_parseerror_tem_localizacao(self, parser):
		src = """PROGRAM P
				 INTEGER N
				 N =
				 END
			  """
		with pytest.raises(ParseError) as exc_info:
			parse_str(parser, src, source_format="free", filename="bad_assign.f")

		err = exc_info.value
		assert isinstance(err.location, SourceLocation)
		assert err.location.filename == "bad_assign.f"
		assert err.location.line >= 1

	def test_parseerror_str_formato_compiler(self, parser):
		src = """PROGRAM P
				 INTEGER N
				 N =
				 END
			  """
		with pytest.raises(ParseError) as exc_info:
			parse_str(parser, src, source_format="free", filename="bad_assign.f")

		msg = str(exc_info.value)
		assert "bad_assign.f:" in msg
		assert ": error: " in msg
		assert "N =" in msg
		assert "^" in msg

	def test_parser_reporta_multiplos_erros_no_mesmo_run(self, parser):
		src = """PROGRAM P
				 INTEGER N
				 N =
				 PRINT *,
				 END
			  """
		with pytest.raises(ParseError) as exc_info:
			parse_str(parser, src, source_format="free", filename="multi_bad.f")

		msg = str(exc_info.value)
		assert msg.count(": error:") >= 2
		assert "N =" in msg
		assert "PRINT *," in msg

	def test_erro_de_eof_inesperado(self, parser):
		src = "PROGRAM P\nINTEGER N\n"
		with pytest.raises(ParseError) as exc_info:
			parse_str(parser, src, source_format="free", filename="unexpected_eof.f")

		assert "fim de ficheiro inesperado" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Fixtures físicos (consistência)
# ---------------------------------------------------------------------------

class TestFixtureFiles:

	@pytest.mark.parametrize("fname", [
		"hello.f",
		"fatorial.f",
		"primo.f",
		"somaarr.f",
		"conversor.f",
		"intrinsics.f",
		"arith_if.f",
		"do_negativo.f",
		"subrotina.f",
		"logico_write.f",
	])
	def test_fixture_existe(self, fname):
		assert (FIXTURES / fname).exists()
