"""Testes do backend EWVM."""

from conftest import parse_fixture
from src.codegen.ewvm import EWVMGenerator
from src.representacao_intermedia.gerador import IRGenerator
from src.analise_semantica import analyze


def gen_code(tree):
    tree = analyze(tree, filename="<codegen-test>")
    ir_generator = IRGenerator()
    ir_generator.generate(tree)
    backend = EWVMGenerator.from_program(tree)
    return backend.generate(ir_generator.instructions)


def parse_str(parser, code: str, source_format: str = "free", filename: str = "<codegen-test>"):
    tree = parser.parse(code, filename=filename, source_format=source_format)
    return analyze(tree, filename=filename)


class TestCodegenHello:

    def test_hello_emite_strings_e_termina(self, parser):
        tree = parse_fixture(parser, "hello.f", source_format="free")
        code = gen_code(tree)

        assert code.startswith("START")
        assert 'PUSHS "Ola, Mundo!"' in code
        assert "WRITES" in code
        assert code.strip().endswith("STOP")


class TestCodegenFatorial:

    def test_fatorial_tem_read_atoi_storeg_mul_e_labels_de_loop(self, parser):
        tree = parse_fixture(parser, "fatorial.f", source_format="fixed")
        code = gen_code(tree)

        assert "READ" in code
        assert "ATOI" in code
        assert "STOREG" in code
        assert "MUL" in code
        assert "DOTEST" in code
        assert "JUMP DOTEST" in code

    def test_labels_ewvm_nao_tem_underscores(self, parser):
        tree = parse_fixture(parser, "fatorial.f", source_format="fixed")
        code = gen_code(tree)

        assert "DO_TEST" not in code
        assert "DO_BODY" not in code
        assert "DO_END" not in code

    def test_fatorial_distingue_strings_de_variaveis_no_print(self, parser):
        tree = parse_fixture(parser, "fatorial.f", source_format="fixed")
        code = gen_code(tree)

        assert 'PUSHS "Fatorial de "' in code
        assert 'PUSHS ": "' in code
        assert "PUSHG" in code
        assert "WRITEI" in code

    def test_variaveis_e_temporarios_reservam_slots_globais(self, parser):
        src = """PROGRAM P
                 INTEGER X, Y
                 X = 1
                 Y = X + 2
                 PRINT *, Y
                 END
              """
        code = gen_code(parse_str(parser, src))
        lines = code.splitlines()

        assert lines[0] == "START"
        assert lines[1:4] == ["PUSHI 0", "PUSHI 0", "PUSHI 0"]
        assert lines[4] == "PUSHI 1"


class TestCodegenPrimo:

    def test_primo_usa_logica_mod_e_saltos_condicionais(self, parser):
        tree = parse_fixture(parser, "primo.f", source_format="fixed")
        code = gen_code(tree)

        assert "AND" in code
        assert "MOD" in code
        assert "JZ" in code
        assert "JUMP THEN" in code or "JUMP ELSE" in code


class TestCodegenArrays:

    def test_array_store_e_load_geram_storen_e_loadn(self, parser):
        src = """PROGRAM P
                 INTEGER A(10), X
                 A(1) = 3
                 X = A(1)
                 PRINT *, X
                 END
              """
        tree = parse_str(parser, src, source_format="free", filename="arr_codegen.f")
        code = gen_code(tree)

        assert "ALLOC" in code
        assert "STOREG" in code
        assert "STORE 0" in code
        assert "LOAD 0" in code
        assert "PUSHG" in code

    def test_somaarr_tem_alloc_read_store_e_load_de_array(self, parser):
        tree = parse_fixture(parser, "somaarr.f", source_format="fixed")
        code = gen_code(tree)

        assert "ALLOC" in code
        assert "PADD" in code
        assert "READ" in code
        assert "STORE 0" in code
        assert "LOAD 0" in code
        assert "WRITEI" in code


class TestCodegenVmCompatibility:

    def test_neqv_nao_emite_instrucao_neq_inexistente(self, parser):
        src = """PROGRAM P
                 LOGICAL A, B
                 A = .TRUE.
                 B = .FALSE.
                 A = A .NEQV. B
                 END
              """
        code = gen_code(parse_str(parser, src))

        assert "NEQ" not in code
        assert "EQUAL" in code
        assert "NOT" in code

    def test_unary_minus_nao_depende_de_neg_ou_fneg(self, parser):
        src = """PROGRAM P
                 INTEGER X
                 X = -1
                 END
              """
        code = gen_code(parse_str(parser, src))

        assert " NEG" not in code
        assert "FNEG" not in code
        assert "SWAP" in code
        assert "SUB" in code

    def test_literal_character_nao_e_confundido_com_variavel_homonima(self, parser):
        src = """PROGRAM P
                 CHARACTER X
                 X = 'valor'
                 PRINT *, 'X'
                 END
              """
        code = gen_code(parse_str(parser, src))

        assert 'PUSHS "X"' in code
        assert 'PUSHG 0\nWRITES' not in code
