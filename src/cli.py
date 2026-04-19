"""Interface de linha de comando do compilador Fortran 77.

Uso:
    python cli.py --stage lex <ficheiro.f>
    python cli.py --stage parse <ficheiro.f>
    python cli.py --stage lex --format free <ficheiro.f>
    python cli.py --debug --stage lex <ficheiro.f>
"""

import argparse
import sys
from pathlib import Path

from src.config import config
from src.errors import CompileError


def parse_args():
    p = argparse.ArgumentParser(prog="fortran77c",
                                description="Compilador Fortran 77 → EWVM")
    p.add_argument("input", metavar="FICHEIRO")
    p.add_argument("--stage",
                   choices=["lex", "parse", "sem", "ir", "codegen"],
                   default="codegen")
    p.add_argument("--format", dest="source_format",
                   choices=["fixed", "free"], default="fixed")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def _build_pipeline(debug: bool = False):
    from src.analise_lexica.lexer import Fortran77Lexer
    from src.analise_sintatica.parser import Fortran77Parser

    lexer = Fortran77Lexer().build(debug=debug)
    parser = Fortran77Parser(lexer).build(debug=debug)
    return lexer, parser


def run_lex(source: str, filename: str, source_format: str, debug: bool):
    from src.analise_lexica.lexer import Fortran77Lexer
    lexer = Fortran77Lexer().build(debug=debug)
    tokens = lexer.tokenize(source, filename=filename, source_format=source_format)
    for tok in tokens:
        print(f"  [{tok.lineno:>4}]  {tok.type:<20}  {tok.value!r}")
    return tokens


def run_parse(
    source: str,
    filename: str,
    source_format: str,
    debug: bool,
    parser=None,
    emit_output: bool = True,
):
    if parser is None:
        _, parser = _build_pipeline(debug=debug)

    tree = parser.parse(source, filename=filename, source_format=source_format)

    if emit_output:
        print(f"[parse] AST criada para programa {tree.name!r}")
        print(f"[parse] declarações: {len(tree.decls)} | instruções: {len(tree.stmts)}")
    if debug and emit_output:
        print(tree)
    return tree


def run_ir(source: str, filename: str, source_format: str, debug: bool):
    _, parser = _build_pipeline(debug=debug)
    tree = run_parse(
        source,
        filename,
        source_format,
        debug=False,
        parser=parser,
        emit_output=False,
    )

    if debug:
        print("[ir] AST (debug):")
        print(tree)

    from src.representacao_intermedia.gerador import IRGenerator
    generator = IRGenerator()
    generator.generate(tree)

    print("[ir] Código Intermédio Gerado:")
    for instr in generator.instructions:
        print(f"  {instr}")

    return generator.instructions


def main():
    args = parse_args()

    config.source_format = args.source_format
    config.debug = args.debug
    config.input_file = args.input
    config.validate()

    path = Path(args.input)
    if not path.exists():
        print(f"fortran77c: erro: ficheiro não encontrado: {args.input}",
              file=sys.stderr)
        sys.exit(1)

    source = path.read_text(encoding="utf-8", errors="replace")

    try:
        if args.stage == "lex":
            run_lex(source, args.input, args.source_format, args.debug)
            return

        if args.stage == "parse":
            run_parse(source, args.input, args.source_format, args.debug)
            return
        
        if args.stage == "ir":
            run_ir(source, args.input, args.source_format, args.debug)
            return

        if args.stage in ("sem", "codegen"):
            print(f"[ stage '{args.stage}' ainda não implementado ]",
                  file=sys.stderr)

    except CompileError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()