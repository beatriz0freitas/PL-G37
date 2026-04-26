"""Testes do backend EWVM."""

from conftest import parse_fixture
from src.codegen.ewvm import EWVMGenerator
from src.representacao_intermedia.gerador import IRGenerator


def gen_code(tree):
    ir_generator = IRGenerator()
    ir_generator.generate(tree)
    backend = EWVMGenerator.from_program(tree)
    return backend.generate(ir_generator.instructions)


def parse_str(parser, code: str, source_format: str = "free", filename: str = "<codegen-test>"):
    return parser.parse(code, filename=filename, source_format=source_format)


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
        assert "DO_TEST" in code
        assert "JUMP DO_TEST" in code

    def test_fatorial_distingue_strings_de_variaveis_no_print(self, parser):
        tree = parse_fixture(parser, "fatorial.f", source_format="fixed")
        code = gen_code(tree)

        assert 'PUSHS "Fatorial de "' in code
        assert 'PUSHS ": "' in code
        assert "PUSHG" in code
        assert "WRITEI" in code


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
