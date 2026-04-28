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
from src.errors import CompileError, ParseError


def parse_args():
    p = argparse.ArgumentParser(prog="fortran77c",
                                description="Compilador Fortran 77 → EWVM")
    p.add_argument("input", metavar="FICHEIRO")
    p.add_argument("--stage",
                   choices=["lex", "parse", "sem", "ir", "codegen"],
                   default="codegen")
    p.add_argument("--format", dest="source_format",
                   choices=["fixed", "free", "auto"], default="auto")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def detect_source_format(source: str) -> str:
    """Deteta heurísticamente se o ficheiro parece fixed-form ou free-form."""

    fixed_score = 0
    free_score = 0

    for raw_line in source.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue

        stripped = line.lstrip()

        if stripped.startswith("!") or "&" in line:
            free_score += 2

        if len(line) >= 6:
            label_zone = line[:5]
            cont_col = line[5]
            if label_zone.strip().isdigit():
                fixed_score += 3
            if cont_col not in (" ", "0", "\t") and label_zone.strip() == "":
                fixed_score += 2

        if line and line[0] in ("C", "c", "*"):
            fixed_score += 1

    return "fixed" if fixed_score > free_score else "free"


def resolve_source_format(source: str, requested: str) -> str:
    return detect_source_format(source) if requested == "auto" else requested


def _alternate_format(source_format: str) -> str:
    return "free" if source_format == "fixed" else "fixed"


def _raise_with_format_hint(
    parser,
    source: str,
    filename: str,
    source_format: str,
    err: ParseError,
) -> None:
    alternate = _alternate_format(source_format)
    try:
        parser.parse(source, filename=filename, source_format=alternate)
    except CompileError:
        raise err

    raise ParseError(
        f"{err.message}. Dica: o ficheiro parece estar em formato {alternate!r}; tenta usar --format {alternate}",
        err.location,
    )


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

    try:
        tree = parser.parse(source, filename=filename, source_format=source_format)
    except ParseError as err:
        _raise_with_format_hint(parser, source, filename, source_format, err)

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
    tree = run_semantic(tree, filename, emit_output=False)

    if debug:
        print("[ir] AST semântica (debug):")
        print(tree)

    from src.representacao_intermedia.gerador import IRGenerator
    generator = IRGenerator()
    generator.generate(tree)

    print("[ir] Código Intermédio Gerado:")
    for instr in generator.instructions:
        print(f"  {instr}")

    return generator.instructions


def run_codegen(source: str, filename: str, source_format: str, debug: bool):
    _, parser = _build_pipeline(debug=debug)
    tree = run_parse(
        source,
        filename,
        source_format,
        debug=False,
        parser=parser,
        emit_output=False,
    )
    tree = run_semantic(tree, filename, emit_output=False)

    from src.codegen.ewvm import EWVMGenerator
    from src.representacao_intermedia.gerador import IRGenerator

    ir_generator = IRGenerator()
    ir_generator.generate(tree)

    if debug:
        print("[codegen] IR (debug):")
        for instr in ir_generator.instructions:
            print(f"  {instr}")

    backend = EWVMGenerator.from_program(tree)
    code = backend.generate(ir_generator.instructions)
    print(code)
    return code


def run_semantic(tree, filename: str, emit_output: bool = True):
    from src.semantic import analyze

    analyzed = analyze(tree, filename=filename)
    if emit_output:
        symbol_count = len(getattr(analyzed, "symbol_table", {}))
        print(f"[sem] análise semântica concluída para programa {analyzed.name!r}")
        print(f"[sem] símbolos registados: {symbol_count}")
    return analyzed


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
    resolved_format = resolve_source_format(source, args.source_format)

    try:
        if args.stage == "lex":
            run_lex(source, args.input, resolved_format, args.debug)
            return

        if args.stage == "parse":
            run_parse(source, args.input, resolved_format, args.debug)
            return

        if args.stage == "sem":
            _, parser = _build_pipeline(debug=args.debug)
            tree = run_parse(
                source,
                args.input,
                resolved_format,
                debug=False,
                parser=parser,
                emit_output=False,
            )
            run_semantic(tree, args.input, emit_output=True)
            return
        
        if args.stage == "ir":
            run_ir(source, args.input, resolved_format, args.debug)
            return

        if args.stage == "codegen":
            run_codegen(source, args.input, resolved_format, args.debug)
            return

    except CompileError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
