"""Gerador principal de código EWVM."""

from __future__ import annotations

from typing import Any

import src.analise_sintatica.ast_nodes as ast
from src.representacao_intermedia.instrucoes import (
    IRAssign,
    IRCJump,
    IRCall,
    IRInstr,
    IRJump,
    IRLabelInstr,
    IRLoadArray,
    IROp,
    IRPrint,
    IRProcBegin,
    IRProcEnd,
    IRRead,
    IRReturn,
    IRStop,
    IRStoreArray,
    IRUnaryOp,
    IRWrite,
)
from src.representacao_intermedia.operadores import IRArrayRef, Temp

from .decls import ArrayTypes, ScalarTypes, SubprogramInfo, extract_program_decl_info
from .intrinsics_codegen import IntrinsicsCodegenMixin
from .layout import FrameLayout, MemoryLayout
from .stack_emitter import StackEmitterMixin
from .type_inference import TypeInferenceMixin


class EWVMGenerator(TypeInferenceMixin, IntrinsicsCodegenMixin, StackEmitterMixin):
    """Traduz IR para texto EWVM."""

    def __init__(
        self,
        scalar_types: ScalarTypes | None = None,
        array_types: ArrayTypes | None = None,
        subprograms: dict[str, SubprogramInfo] | None = None,
    ):
        """Recebe metadados semânticos e prepara estado interno do backend."""
        self.scalar_types = dict(scalar_types or {})
        self.array_types = dict(array_types or {})
        self.subprograms = dict(subprograms or {})
        self.layout = MemoryLayout()
        self.lines: list[str] = []
        self.temp_types: dict[str, str] = {}
        self._backend_label_count = 0
        self._helper_scalars: dict[str, str] = {}
        self.frame_layouts: dict[str, FrameLayout] = {}
        self._current_subprogram: SubprogramInfo | None = None
        self._current_frame: FrameLayout | None = None

    @classmethod
    def from_program(cls, program: ast.Program) -> "EWVMGenerator":
        """Constrói o backend a partir de uma AST semanticamente anotada."""
        info = extract_program_decl_info(program)
        return cls(
            scalar_types=info.scalar_types,
            array_types=info.array_types,
            subprograms=info.subprograms,
        )

    def generate(self, instructions: list[IRInstr]) -> str:
        """Traduz uma lista de IR para texto EWVM completo."""
        self.lines = []
        self.layout = MemoryLayout()
        self.temp_types = {}
        self._backend_label_count = 0
        self._helper_scalars = {}
        self.frame_layouts = {}
        self._current_subprogram = None
        self._current_frame = None

        self._allocate_declared_symbols()
        self._build_frame_layouts()
        self._infer_temp_types(instructions)
        self._reserve_intrinsic_helpers(instructions)
        self._allocate_temporaries_and_implicit_scalars(instructions)

        self._emit_global_initialization()
        self._emit_array_allocations()
        self.emit("START")

        for instr in instructions:
            self._translate(instr)

        has_subprograms = any(isinstance(instr, IRProcBegin) for instr in instructions)
        if not has_subprograms and (not instructions or not isinstance(instructions[-1], IRStop)):
            self.emit("STOP")

        return "\n".join(self.lines)

    def emit(self, *tokens: Any) -> None:
        """Acrescenta uma instrução EWVM já serializada por tokens."""
        self.lines.append(" ".join(str(token) for token in tokens))

    def emit_label(self, label: Any) -> None:
        """Emite uma label EWVM normalizada."""
        self.lines.append(f"{self._label_name(label)}:")

    def _new_backend_label(self, prefix: str) -> str:
        """Cria uma label interna única para sequências auxiliares do backend."""
        self._backend_label_count += 1
        return f"{prefix}_{self._backend_label_count}"

    def _label_name(self, label: Any) -> str:
        """Remove caracteres inválidos de labels antes de emitir EWVM."""
        raw = str(label)
        sanitized = "".join(ch for ch in raw if ch.isalnum())
        return sanitized or raw

    def _allocate_declared_symbols(self) -> None:
        """Reserva slots globais para escalares e ponteiros de arrays declarados."""
        for name in sorted(self.scalar_types):
            self.layout.allocate_scalar(name)
        for name in sorted(self.array_types):
            self.layout.allocate_scalar(name)

    def _build_frame_layouts(self) -> None:
        """Calcula offsets relativos ao FP para cada subprograma."""
        self.frame_layouts = {}
        for info in self.subprograms.values():
            param_offsets = {
                param: idx - len(info.params)
                for idx, param in enumerate(info.params)
            }
            local_offsets: dict[str, int] = {}
            local_array_offsets: dict[str, int] = {}
            next_offset = 1

            for name in sorted(info.scalar_types):
                if name in param_offsets:
                    continue
                local_offsets[name] = next_offset
                next_offset += 1

            for name in sorted(info.array_types):
                local_offsets[name] = next_offset
                local_array_offsets[name] = next_offset
                next_offset += 1

            self.frame_layouts[info.name] = FrameLayout(
                name=info.name,
                kind=info.kind,
                param_offsets=param_offsets,
                local_offsets=local_offsets,
                local_array_offsets=local_array_offsets,
                result_slot=0,
            )

    def _reserve_intrinsic_helpers(self, instructions: list[IRInstr]) -> None:
        """Reserva variáveis auxiliares necessárias para intrínsecas complexas."""
        needs_sqrt = any(
            isinstance(instr, IRCall) and instr.name.upper() == "SQRT"
            for instr in instructions
        )
        needs_pow = any(
            isinstance(instr, IROp) and instr.op == "**"
            for instr in instructions
        )

        if needs_sqrt:
            self._reserve_helper_scalar("@SQRT_ARG", "REAL")
            self._reserve_helper_scalar("@SQRT_GUESS", "REAL")
            self._reserve_helper_scalar("@SQRT_ITER", "INTEGER")

        if needs_pow:
            self._reserve_helper_scalar("@POW_BASE", "INTEGER")
            self._reserve_helper_scalar("@POW_EXP", "INTEGER")
            self._reserve_helper_scalar("@POW_RESULT", "INTEGER")

    def _reserve_helper_scalar(self, name: str, typename: str) -> None:
        """Regista um escalar interno usado pelo backend."""
        self._helper_scalars[name] = typename
        self.scalar_types.setdefault(name, typename)
        self.layout.allocate_scalar(name)

    def _emit_array_allocations(self) -> None:
        """Emite ALLOC para arrays globais e guarda os ponteiros."""
        for name in sorted(self.array_types):
            _, dims = self.array_types[name]
            total = 1
            for dim in dims:
                total *= dim
            self.emit("ALLOC", total)
            self.emit("STOREG", self.layout.addr_of_scalar(name))

    def _emit_global_initialization(self) -> None:
        """Inicializa a zona global da EWVM com zeros."""
        for _ in range(self.layout.total_cells):
            self.emit("PUSHI", 0)

    def _allocate_temporaries_and_implicit_scalars(self, instructions: list[IRInstr]) -> None:
        """Percorre a IR para reservar armazenamento a temporários e nomes implícitos."""
        for instr in instructions:
            if isinstance(instr, IRProcBegin):
                self._set_current_subprogram(instr.name)
                continue
            if isinstance(instr, IRProcEnd):
                self._set_current_subprogram(None)
                continue
            match instr:
                case IRAssign(dest=dest, src=src):
                    self._ensure_storage(dest)
                    self._scan_value(src)
                case IROp(dest=dest, left=left, right=right):
                    self._ensure_storage(dest)
                    self._scan_value(left)
                    self._scan_value(right)
                case IRUnaryOp(dest=dest, operand=operand):
                    self._ensure_storage(dest)
                    self._scan_value(operand)
                case IRCJump(cond=cond):
                    self._scan_value(cond)
                case IRCall(dest=dest, args=args):
                    if dest is not None:
                        self._ensure_storage(dest)
                    for arg in args:
                        self._scan_value(arg)
                case IRRead(args=args):
                    for arg in args:
                        if isinstance(arg, IRArrayRef):
                            for idx in arg.indices:
                                self._scan_value(idx)
                        else:
                            self._ensure_storage(arg)
                case IRPrint(args=args):
                    for arg in args:
                        self._scan_value(arg)
                case IRWrite(items=items):
                    for item in items:
                        self._scan_value(item)
                case IRLoadArray(dest=dest, indices=indices):
                    self._ensure_storage(dest)
                    for idx in indices:
                        self._scan_value(idx)
                case IRStoreArray(src=src, indices=indices):
                    self._scan_value(src)
                    for idx in indices:
                        self._scan_value(idx)
        self._set_current_subprogram(None)

    def _scan_value(self, value: Any) -> None:
        """Inspeciona um valor IR e reserva armazenamento se necessário."""
        if isinstance(value, Temp):
            self._ensure_storage(value)
        elif isinstance(value, IRArrayRef):
            for idx in value.indices:
                self._scan_value(idx)
        elif isinstance(value, str) and self._looks_like_identifier(value) and not self._is_string_literal(value):
            if not self._is_declared_name(value):
                self._ensure_storage(value)

    def _ensure_storage(self, target: Any) -> None:
        """Garante que um destino IR tem slot global ou local."""
        if isinstance(target, Temp):
            self._ensure_named_storage(str(target))
            return
        if isinstance(target, str) and target not in self._active_array_types():
            self._ensure_named_storage(target)

    def _ensure_named_storage(self, name: str) -> None:
        """Reserva um nome concreto no escopo ativo."""
        if self._current_frame is not None:
            if name in self._current_frame.param_offsets or name in self._current_frame.local_offsets:
                return
            next_offset = self._current_frame.local_slot_count + 1
            self._current_frame.local_offsets[name] = next_offset
            self._active_scalar_types().setdefault(name, self.temp_types.get(name, "INTEGER"))
            return

        self.layout.allocate_scalar(name)
        self.scalar_types.setdefault(name, self.temp_types.get(name, "INTEGER"))

    def _is_declared_name(self, name: str) -> bool:
        """Indica se um nome já existe nos metadados globais ou de subprogramas."""
        if name in self.scalar_types or name in self.array_types:
            return True
        for info in self.subprograms.values():
            if name in info.scalar_types or name in info.array_types:
                return True
        return False

    def _set_current_subprogram(self, name: str | None) -> None:
        """Ativa ou limpa o contexto de subprograma durante tradução/alocação."""
        if name is None:
            self._current_subprogram = None
            self._current_frame = None
            return
        self._current_subprogram = self.subprograms[name]
        self._current_frame = self.frame_layouts[name]

    def _translate(self, instr: IRInstr) -> None:
        """Despacha uma instrução IR para a sequência EWVM correspondente."""
        match instr:
            case IRLabelInstr(label=label):
                self.emit_label(label)
            case IRJump(label=label):
                self.emit("JUMP", self._label_name(label))
            case IRCJump(cond=cond, true_label=true_label, false_label=false_label):
                self._push_value(cond)
                self.emit("JZ", self._label_name(false_label))
                self.emit("JUMP", self._label_name(true_label))
            case IRAssign(dest=dest, src=src):
                self._push_value_for_target(src, dest)
                self._pop_to(dest)
            case IROp(op=op, dest=dest, left=left, right=right):
                if op == "**":
                    self._emit_integer_power(left, right, dest)
                    return

                if op == "CONCAT":
                    # A EWVM documenta CONCAT como n + m, ao contrário da
                    # família aritmética m op n. Para Fortran A // B empilhamos
                    # B e depois A.
                    self._push_value(right)
                    self._push_value(left)
                    self.emit("CONCAT")
                    self._pop_to(dest)
                    return

                real_stack = self._op_uses_real_stack(op, left, right)
                self._push_numeric_value(left, as_real=real_stack)
                self._push_numeric_value(right, as_real=real_stack)
                self.emit(self._binary_opcode(op, left, right))
                if op in {"!=", "NEQV"}:
                    self.emit("NOT")
                self._pop_to(dest)
            case IRUnaryOp(op=op, dest=dest, operand=operand):
                self._push_value(operand)
                self._emit_unary(op, operand)
                self._pop_to(dest)
            case IRPrint(args=args):
                self._translate_print(args)
            case IRWrite(items=items):
                self._translate_print(items)
            case IRRead(args=args):
                self._translate_read(args)
            case IRCall(name=name, args=args, dest=dest):
                self._translate_call(name, args, dest)
            case IRProcBegin(name=name):
                self._translate_proc_begin(name)
            case IRProcEnd():
                self._set_current_subprogram(None)
            case IRLoadArray(dest=dest, name=name, indices=indices):
                self._push_array_address(name, indices)
                self.emit("LOAD", 0)
                self._pop_to(dest)
            case IRStoreArray(name=name, indices=indices, src=src):
                self._push_array_address(name, indices)
                self._push_value_for_type(src, self._active_array_types()[name][0])
                self.emit("STORE", 0)
            case IRStop():
                self.emit("STOP")
            case IRReturn():
                self._translate_return()
                self.emit("RETURN")
            case _:
                raise NotImplementedError(f"Instrução IR sem tradução: {type(instr).__name__}")

    def _translate_print(self, args: list[Any]) -> None:
        """Traduz PRINT/WRITE textual para instruções WRITE* da EWVM."""
        for arg in args:
            self._push_value(arg)
            typename = self._type_of(arg)
            if self._is_string_literal(arg) or typename == "CHARACTER":
                self.emit("WRITES")
            elif self._is_real_type(typename):
                self.emit("WRITEF")
            else:
                self.emit("WRITEI")
        self.emit("WRITELN")

    def _translate_read(self, args: list[Any]) -> None:
        """Traduz READ para leitura, conversão e armazenamento no alvo."""
        for target in args:
            typename = self._type_of(target)
            if isinstance(target, IRArrayRef):
                self._push_array_address(target.name, target.indices)
                self.emit("READ")
                if self._is_real_type(typename):
                    self.emit("ATOF")
                elif typename != "CHARACTER":
                    self.emit("ATOI")
                self.emit("STORE", 0)
                continue

            self.emit("READ")
            if self._is_real_type(typename):
                self.emit("ATOF")
            elif typename != "CHARACTER":
                self.emit("ATOI")
            self._pop_to(target)

    def _translate_call(self, name: str, args: list[Any], dest: Any | None) -> None:
        """Traduz intrínsecas e chamadas a subprogramas definidos pelo utilizador."""
        upper = name.upper()

        if upper == "MOD":
            self._push_value(args[0])
            self._push_value(args[1])
            self.emit("MOD")
        elif upper in {"REAL", "FLOAT", "INT"}:
            self._push_value(args[0])
            if upper in {"REAL", "FLOAT"} and not self._is_real_type(self._type_of(args[0])):
                self.emit("ITOF")
            elif upper == "INT" and self._is_real_type(self._type_of(args[0])):
                self.emit("FTOI")
        elif upper in {"ABS", "SQRT", "MAX", "MIN"}:
            self._translate_intrinsic_call(upper, args)
        else:
            info = self.subprograms.get(upper)
            if info is None:
                raise NotImplementedError(f"Subprograma sem metadados: {upper}")
            for idx, arg in enumerate(args):
                param_type = None
                if idx < len(info.params):
                    param_type = info.scalar_types.get(info.params[idx])
                if param_type is None:
                    self._push_value(arg)
                else:
                    self._push_value_for_type(arg, param_type)
            if info.kind == "function":
                self.emit("PUSHI", 0)
            self.emit("PUSHA", upper)
            self.emit("CALL")

        if dest is not None:
            self._pop_to(dest)
            if upper in self.subprograms and args:
                self.emit("POP", len(args))
        elif upper in self.subprograms:
            info = self.subprograms[upper]
            cleanup_count = len(args) + (1 if info.kind == "function" else 0)
            if cleanup_count:
                self.emit("POP", cleanup_count)

    def _translate_proc_begin(self, name: str) -> None:
        """Emite prólogo de função/subrotina e aloca arrays locais."""
        info = self.subprograms.get(name)
        if info is None:
            raise NotImplementedError(f"Subprograma sem metadados: {name}")
        self._set_current_subprogram(name)
        frame = self._current_frame
        self.emit_label(name)
        if frame is not None and frame.local_slot_count:
            self.emit("PUSHN", frame.local_slot_count)
        if frame is None:
            return
        for array_name, offset in sorted(frame.local_array_offsets.items(), key=lambda item: item[1]):
            _, dims = info.array_types[array_name]
            total = 1
            for dim in dims:
                total *= dim
            self.emit("ALLOC", total)
            self.emit("STOREL", offset)

    def _translate_return(self) -> None:
        """Emite epílogo de retorno, incluindo resultado de função e FREE locais."""
        info = self._current_subprogram
        frame = self._current_frame
        if info is None or frame is None:
            return
        if info.kind == "function":
            result_name = info.result_name or info.name
            self._push_symbol(result_name)
            self.emit("STOREL", frame.result_slot)
        for _, offset in sorted(frame.local_array_offsets.items(), key=lambda item: item[1], reverse=True):
            self.emit("PUSHL", offset)
            self.emit("FREE")

    def _active_scalar_types(self) -> ScalarTypes:
        """Devolve os tipos escalares do escopo atualmente ativo."""
        if self._current_subprogram is not None:
            return self._current_subprogram.scalar_types
        return self.scalar_types

    def _active_array_types(self) -> ArrayTypes:
        """Devolve os tipos de arrays do escopo atualmente ativo."""
        if self._current_subprogram is not None:
            return self._current_subprogram.array_types
        return self.array_types

EWVMBackend = EWVMGenerator
