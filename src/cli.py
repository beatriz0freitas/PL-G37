"""Interface de linha de comando do compilador Fortran 77.

Uso:
    python cli.py --stage lex <ficheiro.f>
    python cli.py --stage lex --format free <ficheiro.f>
    python cli.py --debug --stage lex <ficheiro.f>
"""

import argparse
import sys
from pathlib import Path

from errors import CompileError


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


def run_lex(source: str, filename: str, source_format: str, debug: bool):
    from lexer import Fortran77Lexer
    lexer  = Fortran77Lexer().build(debug=debug)
    tokens = lexer.tokenize(source, filename=filename, source_format=source_format)
    for tok in tokens:
        print(f"  [{tok.lineno:>4}]  {tok.type:<20}  {tok.value!r}")
    return tokens


def main():
    args = parse_args()
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

        tokens = run_lex(source, args.input, args.source_format, args.debug)
        if args.stage in ("parse", "sem", "ir", "codegen"):
            print(f"[ stage '{args.stage}' ainda não implementado ]",
                  file=sys.stderr)

    except CompileError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()