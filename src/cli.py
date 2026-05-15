"""Interface de linha de comando do compilador Fortran 77.

Uso:
    python cli.py --stage lex <ficheiro.f>
    python cli.py --stage parse <ficheiro.f>
    python cli.py --stage sem <ficheiro.f>
    python cli.py --stage ir <ficheiro.f>
    python cli.py --stage opt <ficheiro.f>      # IR após otimização
    python cli.py --stage codegen <ficheiro.f>  # EWVM (com otimização)
"""

import argparse
import sys
from pathlib import Path

from src.config import config
from src.errors import CompileError, ParseError


def parse_args():
    """Lê argumentos da linha de comando e devolve o namespace argparse."""
    p = argparse.ArgumentParser(prog="fortran77c",
                                description="Compilador Fortran 77 → EWVM")
    p.add_argument("input", metavar="FICHEIRO")
    p.add_argument("--stage",
                   choices=["lex", "parse", "sem", "ir", "opt", "codegen"],
                   default="codegen")
    p.add_argument("--format", dest="source_format",
                   choices=["fixed", "free", "auto"], default="auto")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--implicit-typing", action="store_true",
                   help="Ativa tipagem implícita Fortran 77 (I-N -> INTEGER)")
    return p.parse_args()


def detect_source_format(source: str) -> str:
    """Deteta heurísticamente se o ficheiro parece fixed-form ou free-form.

    Nota: ignora símbolos dentro de strings e comentários para evitar falsos
    positivos com '&' e '!'.
    """

    def _strip_comments_and_strings(line: str) -> str:
        """Remove zonas irrelevantes para a heurística de formato."""
        in_str = False
        cleaned: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "!" and not in_str:
                break
            if ch == "'":
                if in_str:
                    if i + 1 < len(line) and line[i + 1] == "'":
                        cleaned.append(" ")
                        cleaned.append(" ")
                        i += 2
                        continue
                    in_str = False
                    cleaned.append(" ")
                    i += 1
                    continue
                in_str = True
                cleaned.append(" ")
                i += 1
                continue
            if in_str:
                cleaned.append(" ")
            else:
                cleaned.append(ch)
            i += 1
        return "".join(cleaned)

    fixed_score = 0
    free_score = 0

    for raw_line in source.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue

        if line and line[0] in ("C", "c", "*", "!"):
            fixed_score += 1
            continue

        clean_line = _strip_comments_and_strings(line)
        if not clean_line.strip():
            continue

        stripped = clean_line.lstrip()

        if "&" in clean_line or stripped.startswith("!"):
            free_score += 2

        if len(line) >= 6:
            label_zone = line[:5]
            cont_col = line[5]
            if label_zone.strip().isdigit():
                fixed_score += 3
            if cont_col not in (" ", "0", "\t") and label_zone.strip() == "":
                fixed_score += 2

    return "fixed" if fixed_score > free_score else "free"


def resolve_source_format(source: str, requested: str) -> str:
    """Resolve 'auto' para fixed/free ou respeita o formato pedido."""
    return detect_source_format(source) if requested == "auto" else requested


def _alternate_format(source_format: str) -> str:
    """Devolve o formato alternativo usado para sugerir correções."""
    return "free" if source_format == "fixed" else "fixed"


def _raise_with_format_hint(
    parser,
    source: str,
    filename: str,
    source_format: str,
    err: ParseError,
) -> None:
    """Tenta parsear no formato alternativo para produzir uma dica útil."""
    alternate = _alternate_format(source_format)
    try:
        parser.parse(source, filename=filename, source_format=alternate)
    except CompileError:
        raise err

    raise ParseError(
        f"{err.message}. Dica: o ficheiro parece estar em formato {alternate!r}; tenta usar --format {alternate}",
        err.location,
        source_line=err.source_line,
        length=err.length,
    )


def _build_pipeline(debug: bool = False):
    """Constrói lexer e parser PLY prontos para executar um estágio."""
    from src.analise_lexica.lexer import Fortran77Lexer
    from src.analise_sintatica.parser import Fortran77Parser

    lexer = Fortran77Lexer().build(debug=debug)
    parser = Fortran77Parser(lexer).build(debug=debug)
    return lexer, parser


def run_lex(source: str, filename: str, source_format: str, debug: bool):
    """Executa apenas a análise léxica e imprime os tokens."""
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
    """Executa lexer+parser e devolve a AST."""
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


def run_semantic(tree, filename: str, emit_output: bool = True):
    """Executa a análise semântica sobre uma AST já construída."""
    from src.analise_semantica import analyze

    analyzed = analyze(tree, filename=filename)
    if emit_output:
        symbol_count = len(getattr(analyzed, "symbol_table", {}))
        print(f"[sem] análise semântica concluída para programa {analyzed.name!r}")
        print(f"[sem] símbolos registados: {symbol_count}")
    return analyzed


def _run_ir_generator(tree):
    """Gera IR não otimizado e devolve as instruções."""
    from src.representacao_intermedia.gerador import IRGenerator
    generator = IRGenerator()
    generator.generate(tree)
    return generator.instructions


def run_ir(source: str, filename: str, source_format: str, debug: bool):
    """Executa o pipeline até à IR não otimizada e imprime o resultado."""
    _, parser = _build_pipeline(debug=debug)
    tree = run_parse(source, filename, source_format, debug=False,
                     parser=parser, emit_output=False)
    tree = run_semantic(tree, filename, emit_output=False)

    if debug:
        print("[ir] AST semântica (debug):")
        print(tree)

    instructions = _run_ir_generator(tree)

    print("[ir] Código Intermédio (sem otimização):")
    for instr in instructions:
        print(f"  {instr}")

    return instructions


def run_opt(source: str, filename: str, source_format: str, debug: bool):
    """Mostra a IR após otimização."""
    _, parser = _build_pipeline(debug=debug)
    tree = run_parse(source, filename, source_format, debug=False,
                     parser=parser, emit_output=False)
    tree = run_semantic(tree, filename, emit_output=False)

    instructions = _run_ir_generator(tree)

    from src.optimizer import optimize
    optimized = optimize(instructions)

    removed = len(instructions) - len(optimized)
    print(f"[opt] {len(instructions)} instruções → {len(optimized)} ({removed} eliminadas)")
    for instr in optimized:
        print(f"  {instr}")

    return optimized


def run_codegen(source: str, filename: str, source_format: str, debug: bool):
    """Executa o pipeline completo e imprime código EWVM."""
    _, parser = _build_pipeline(debug=debug)
    tree = run_parse(source, filename, source_format, debug=False,
                     parser=parser, emit_output=False)
    tree = run_semantic(tree, filename, emit_output=False)

    instructions = _run_ir_generator(tree)

    # Aplica otimizações antes da geração de código
    from src.optimizer import optimize
    optimized = optimize(instructions)

    if debug:
        print("[codegen] IR otimizado (debug):")
        for instr in optimized:
            print(f"  {instr}")

    from src.codegen.ewvm import EWVMGenerator
    backend = EWVMGenerator.from_program(tree)
    code = backend.generate(optimized)
    print(code)
    return code


def main():
    """Ponto de entrada da CLI; escolhe e executa o estágio pedido."""
    args = parse_args()

    config.source_format = args.source_format
    config.debug = args.debug
    config.input_file = args.input
    config.implicit_typing = args.implicit_typing
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
            tree = run_parse(source, args.input, resolved_format,
                             debug=False, parser=parser, emit_output=False)
            run_semantic(tree, args.input, emit_output=True)
            return

        if args.stage == "ir":
            run_ir(source, args.input, resolved_format, args.debug)
            return

        if args.stage == "opt":
            run_opt(source, args.input, resolved_format, args.debug)
            return

        if args.stage == "codegen":
            run_codegen(source, args.input, resolved_format, args.debug)
            return

    except CompileError as e:
        e.attach_source(source)
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
