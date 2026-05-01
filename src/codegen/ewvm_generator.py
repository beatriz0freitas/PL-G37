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
from src.representacao_intermedia.operadores import IRArrayRef, IRStringLit, Temp

from .decls import ArrayTypes, ScalarTypes, SubprogramInfo, extract_program_decl_info
from .layout import FrameLayout, MemoryLayout


class EWVMGenerator:
    """Traduz IR para texto EWVM."""

    def __init__(
        self,
        scalar_types: ScalarTypes | None = None,
        array_types: ArrayTypes | None = None,
        subprograms: dict[str, SubprogramInfo] | None = None,
    ):
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
        info = extract_program_decl_info(program)
        return cls(
            scalar_types=info.scalar_types,
            array_types=info.array_types,
            subprograms=info.subprograms,
        )

    def generate(self, instructions: list[IRInstr]) -> str:
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

        self.emit("START")
        self._emit_global_initialization()
        self._emit_array_allocations()

        for instr in instructions:
            self._translate(instr)

        has_subprograms = any(isinstance(instr, IRProcBegin) for instr in instructions)
        if not has_subprograms and (not instructions or not isinstance(instructions[-1], IRStop)):
            self.emit("STOP")

        return "\n".join(self.lines)

    def emit(self, *tokens: Any) -> None:
        self.lines.append(" ".join(str(token) for token in tokens))

    def emit_label(self, label: Any) -> None:
        self.lines.append(f"{self._label_name(label)}:")

    def _new_backend_label(self, prefix: str) -> str:
        self._backend_label_count += 1
        return f"{prefix}_{self._backend_label_count}"

    def _label_name(self, label: Any) -> str:
        raw = str(label)
        sanitized = "".join(ch for ch in raw if ch.isalnum())
        return sanitized or raw

    def _allocate_declared_symbols(self) -> None:
        for name in sorted(self.scalar_types):
            self.layout.allocate_scalar(name)
        for name in sorted(self.array_types):
            self.layout.allocate_scalar(name)

    def _build_frame_layouts(self) -> None:
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
        needs_sqrt = any(
            isinstance(instr, IRCall) and instr.name.upper() == "SQRT"
            for instr in instructions
        )
        if not needs_sqrt:
            return

        self._reserve_helper_scalar("@SQRT_ARG", "REAL")
        self._reserve_helper_scalar("@SQRT_GUESS", "REAL")
        self._reserve_helper_scalar("@SQRT_ITER", "INTEGER")

    def _reserve_helper_scalar(self, name: str, typename: str) -> None:
        self._helper_scalars[name] = typename
        self.scalar_types.setdefault(name, typename)
        self.layout.allocate_scalar(name)

    def _emit_array_allocations(self) -> None:
        for name in sorted(self.array_types):
            _, dims = self.array_types[name]
            total = 1
            for dim in dims:
                total *= dim
            self.emit("ALLOC", total)
            self.emit("STOREG", self.layout.addr_of_scalar(name))

    def _emit_global_initialization(self) -> None:
        for _ in range(self.layout.total_cells):
            self.emit("PUSHI", 0)

    def _allocate_temporaries_and_implicit_scalars(self, instructions: list[IRInstr]) -> None:
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
        if isinstance(value, Temp):
            self._ensure_storage(value)
        elif isinstance(value, IRArrayRef):
            for idx in value.indices:
                self._scan_value(idx)
        elif isinstance(value, str) and self._looks_like_identifier(value) and not self._is_string_literal(value):
            if not self._is_declared_name(value):
                self._ensure_storage(value)

    def _ensure_storage(self, target: Any) -> None:
        if isinstance(target, Temp):
            self._ensure_named_storage(str(target))
            return
        if isinstance(target, str) and target not in self._active_array_types():
            self._ensure_named_storage(target)

    def _ensure_named_storage(self, name: str) -> None:
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
        if name in self.scalar_types or name in self.array_types:
            return True
        for info in self.subprograms.values():
            if name in info.scalar_types or name in info.array_types:
                return True
        return False

    def _set_current_subprogram(self, name: str | None) -> None:
        if name is None:
            self._current_subprogram = None
            self._current_frame = None
            return
        self._current_subprogram = self.subprograms[name]
        self._current_frame = self.frame_layouts[name]

    def _infer_temp_types(self, instructions: list[IRInstr]) -> None:
        changed = True
        while changed:
            changed = False
            for instr in instructions:
                if isinstance(instr, IRProcBegin):
                    self._set_current_subprogram(instr.name)
                    continue
                if isinstance(instr, IRProcEnd):
                    self._set_current_subprogram(None)
                    continue
                inferred = self._infer_instr_type(instr)
                if inferred is None:
                    continue
                name, typename = inferred
                if self.temp_types.get(name) != typename:
                    self.temp_types[name] = typename
                    changed = True
        self._set_current_subprogram(None)

    def _infer_instr_type(self, instr: IRInstr) -> tuple[str, str] | None:
        if isinstance(instr, IRAssign) and isinstance(instr.dest, Temp):
            return str(instr.dest), self._type_of(instr.src)

        if isinstance(instr, IRLoadArray):
            array_type, _ = self._active_array_types()[instr.name]
            return str(instr.dest), array_type

        if isinstance(instr, IRUnaryOp):
            if not isinstance(instr.dest, Temp):
                return None
            if instr.op == "NOT":
                return str(instr.dest), "LOGICAL"
            return str(instr.dest), self._type_of(instr.operand)

        if isinstance(instr, IROp):
            if not isinstance(instr.dest, Temp):
                return None
            if instr.op in {"<", "<=", ">", ">=", "==", "!=", "AND", "OR", "EQV", "NEQV"}:
                return str(instr.dest), "LOGICAL"
            if instr.op == "CONCAT":
                return str(instr.dest), "CHARACTER"
            left_type = self._type_of(instr.left)
            right_type = self._type_of(instr.right)
            if "REAL" in {left_type, right_type}:
                return str(instr.dest), "REAL"
            return str(instr.dest), "INTEGER"

        if isinstance(instr, IRCall) and isinstance(instr.dest, Temp):
            name = instr.name.upper()
            if name in {"SQRT", "REAL", "FLOAT"}:
                return str(instr.dest), "REAL"
            if name in {"MOD", "INT"}:
                return str(instr.dest), "INTEGER"
            if name in {"ABS", "MAX", "MIN"} and instr.args:
                return str(instr.dest), self._type_of(instr.args[0])
            if name in self.subprograms:
                info = self.subprograms[name]
                result_name = info.result_name or name
                return str(instr.dest), info.scalar_types.get(result_name, "INTEGER")
            return str(instr.dest), "INTEGER"

        return None

    def _translate(self, instr: IRInstr) -> None:
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
                self._push_value(src)
                self._pop_to(dest)
            case IROp(op=op, dest=dest, left=left, right=right):
                self._push_value(left)
                self._push_value(right)
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
                self._push_value(src)
                self.emit("STORE", 0)
            case IRStop():
                self.emit("STOP")
            case IRReturn():
                self._translate_return()
                self.emit("RETURN")
            case _:
                raise NotImplementedError(f"Instrução IR sem tradução: {type(instr).__name__}")

    def _translate_print(self, args: list[Any]) -> None:
        for arg in args:
            self._push_value(arg)
            typename = self._type_of(arg)
            if self._is_string_literal(arg) or typename == "CHARACTER":
                self.emit("WRITES")
            elif typename == "REAL":
                self.emit("WRITEF")
            else:
                self.emit("WRITEI")
        self.emit("WRITELN")

    def _translate_read(self, args: list[Any]) -> None:
        for target in args:
            typename = self._type_of(target)
            if isinstance(target, IRArrayRef):
                self._push_array_address(target.name, target.indices)
                self.emit("READ")
                if typename == "REAL":
                    self.emit("ATOF")
                elif typename != "CHARACTER":
                    self.emit("ATOI")
                self.emit("STORE", 0)
                continue

            self.emit("READ")
            if typename == "REAL":
                self.emit("ATOF")
            elif typename != "CHARACTER":
                self.emit("ATOI")
            self._pop_to(target)

    def _translate_call(self, name: str, args: list[Any], dest: Any | None) -> None:
        upper = name.upper()

        if upper == "MOD":
            self._push_value(args[0])
            self._push_value(args[1])
            self.emit("MOD")
        elif upper in {"REAL", "FLOAT", "INT"}:
            self._push_value(args[0])
            if upper in {"REAL", "FLOAT"} and self._type_of(args[0]) != "REAL":
                self.emit("ITOF")
            elif upper == "INT" and self._type_of(args[0]) == "REAL":
                self.emit("FTOI")
        elif upper in {"ABS", "SQRT", "MAX", "MIN"}:
            self._translate_intrinsic_call(upper, args)
        else:
            info = self.subprograms.get(upper)
            if info is None:
                raise NotImplementedError(f"Subprograma sem metadados: {upper}")
            for arg in args:
                self._push_value(arg)
            self.emit("PUSHI", 0)
            self.emit("PUSHA", upper)
            self.emit("CALL")

        if dest is not None:
            self._pop_to(dest)
            if upper in self.subprograms and args:
                self.emit("POP", len(args))
        elif upper in self.subprograms:
            self.emit("POP", len(args) + 1)

    def _translate_proc_begin(self, name: str) -> None:
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

    def _translate_intrinsic_call(self, name: str, args: list[Any]) -> None:
        if name == "ABS":
            self._emit_abs(args[0])
            return
        if name == "SQRT":
            self._emit_sqrt(args[0])
            return
        if name == "MAX":
            self._emit_max_min(args[0], args[1], want_max=True)
            return
        if name == "MIN":
            self._emit_max_min(args[0], args[1], want_max=False)
            return
        raise NotImplementedError(f"Intrínseca sem tradução: {name}")

    def _emit_abs(self, arg: Any) -> None:
        is_real = self._type_of(arg) == "REAL"
        keep_label = self._new_backend_label("ABS_KEEP")
        end_label = self._new_backend_label("ABS_END")

        self._push_value(arg)
        self.emit("PUSHF" if is_real else "PUSHI", 0.0 if is_real else 0)
        self.emit("FINF" if is_real else "INF")
        self.emit("JZ", self._label_name(keep_label))

        self._push_value(arg)
        self.emit("PUSHF" if is_real else "PUSHI", 0.0 if is_real else 0)
        self.emit("SWAP")
        self.emit("FSUB" if is_real else "SUB")
        self.emit("JUMP", self._label_name(end_label))

        self.emit_label(keep_label)
        self._push_value(arg)
        self.emit_label(end_label)

    def _emit_max_min(self, left: Any, right: Any, *, want_max: bool) -> None:
        is_real = "REAL" in {self._type_of(left), self._type_of(right)}
        take_left_label = self._new_backend_label("MM_LEFT")
        end_label = self._new_backend_label("MM_END")

        self._push_value(left)
        self._push_value(right)
        if want_max:
            self.emit("FSUPEQ" if is_real else "SUPEQ")
        else:
            self.emit("FINFEQ" if is_real else "INFEQ")
        self.emit("JZ", self._label_name(take_left_label))

        self._push_value(left)
        self.emit("JUMP", self._label_name(end_label))

        self.emit_label(take_left_label)
        self._push_value(right)
        self.emit_label(end_label)

    def _emit_sqrt(self, arg: Any) -> None:
        arg_name = "@SQRT_ARG"
        guess_name = "@SQRT_GUESS"
        iter_name = "@SQRT_ITER"
        negative_label = self._new_backend_label("SQRT_NEG")
        zero_label = self._new_backend_label("SQRT_ZERO")
        use_one_label = self._new_backend_label("SQRT_ONE")
        loop_label = self._new_backend_label("SQRT_LOOP")
        done_label = self._new_backend_label("SQRT_DONE")
        end_label = self._new_backend_label("SQRT_END")

        self._push_value(arg)
        if self._type_of(arg) != "REAL":
            self.emit("ITOF")
        self._pop_to(arg_name)

        self.emit("PUSHG", self.layout.addr_of_scalar(arg_name))
        self.emit("PUSHF", 0.0)
        self.emit("FINF")
        self.emit("JZ", self._label_name(zero_label))
        self.emit("PUSHF", 0.0)
        self.emit("JUMP", self._label_name(end_label))

        self.emit_label(zero_label)
        self.emit("PUSHG", self.layout.addr_of_scalar(arg_name))
        self.emit("PUSHF", 0.0)
        self.emit("EQUAL")
        self.emit("JZ", self._label_name(use_one_label))
        self.emit("PUSHF", 0.0)
        self.emit("JUMP", self._label_name(end_label))

        self.emit_label(use_one_label)
        self.emit("PUSHG", self.layout.addr_of_scalar(arg_name))
        self.emit("PUSHF", 1.0)
        self.emit("FINF")
        self.emit("JZ", self._label_name(negative_label))
        self.emit("PUSHF", 1.0)
        self._pop_to(guess_name)
        self.emit("JUMP", self._label_name(loop_label))

        self.emit_label(negative_label)
        self.emit("PUSHG", self.layout.addr_of_scalar(arg_name))
        self._pop_to(guess_name)

        self.emit_label(loop_label)
        self.emit("PUSHG", self.layout.addr_of_scalar(iter_name))
        self.emit("PUSHI", 8)
        self.emit("INF")
        self.emit("JZ", self._label_name(done_label))

        self.emit("PUSHG", self.layout.addr_of_scalar(guess_name))
        self.emit("PUSHG", self.layout.addr_of_scalar(arg_name))
        self.emit("PUSHG", self.layout.addr_of_scalar(guess_name))
        self.emit("FDIV")
        self.emit("FADD")
        self.emit("PUSHF", 2.0)
        self.emit("FDIV")
        self._pop_to(guess_name)

        self.emit("PUSHG", self.layout.addr_of_scalar(iter_name))
        self.emit("PUSHI", 1)
        self.emit("ADD")
        self._pop_to(iter_name)
        self.emit("JUMP", self._label_name(loop_label))

        self.emit_label(done_label)
        self.emit("PUSHG", self.layout.addr_of_scalar(guess_name))
        self.emit_label(end_label)

    def _binary_opcode(self, op: str, left: Any, right: Any) -> str:
        cmp_ops = {
            "<": "INF",
            "<=": "INFEQ",
            ">": "SUP",
            ">=": "SUPEQ",
        }
        real_cmp_ops = {
            "<": "FINF",
            "<=": "FINFEQ",
            ">": "FSUP",
            ">=": "FSUPEQ",
        }
        is_real = "REAL" in {self._type_of(left), self._type_of(right)}
        if op in cmp_ops:
            return real_cmp_ops[op] if is_real else cmp_ops[op]
        if op == "==":
            return "EQUAL"
        if op == "!=":
            return "EQUAL"
        if op == "AND":
            return "AND"
        if op == "OR":
            return "OR"
        if op == "EQV":
            return "EQUAL"
        if op == "NEQV":
            return "EQUAL"
        if op == "CONCAT":
            return "CONCAT"

        if op == "**":
            raise NotImplementedError(
                "Operador '**' ainda não tem mapeamento suportado pela EWVM documentada"
            )

        arithmetic = {
            "+": ("ADD", "FADD"),
            "-": ("SUB", "FSUB"),
            "*": ("MUL", "FMUL"),
            "/": ("DIV", "FDIV"),
        }
        int_op, real_op = arithmetic[op]
        return real_op if "REAL" in {self._type_of(left), self._type_of(right)} else int_op

    def _emit_unary(self, op: str, operand: Any) -> None:
        if op == "NOT":
            self.emit("NOT")
            return
        if op == "NEG":
            if self._type_of(operand) == "REAL":
                self.emit("PUSHF", 0.0)
                self.emit("SWAP")
                self.emit("FSUB")
            else:
                self.emit("PUSHI", 0)
                self.emit("SWAP")
                self.emit("SUB")
            return
        raise NotImplementedError(f"Operador unário sem tradução: {op}")

    def _push_value(self, value: Any) -> None:
        if isinstance(value, bool):
            self.emit("PUSHI", 1 if value else 0)
            return
        if isinstance(value, int):
            self.emit("PUSHI", value)
            return
        if isinstance(value, float):
            self.emit("PUSHF", value)
            return
        if isinstance(value, Temp):
            self._push_symbol(str(value))
            return
        if isinstance(value, IRArrayRef):
            self._push_array_address(value.name, value.indices)
            self.emit("LOAD", 0)
            return
        if isinstance(value, IRStringLit):
            escaped = value.value.replace("\\", "\\\\").replace('"', '\\"')
            self.emit(f'PUSHS "{escaped}"')
            return
        if isinstance(value, str):
            self._push_symbol(value)
            return
        raise NotImplementedError(f"Valor IR sem tradução para PUSH: {value!r}")

    def _pop_to(self, target: Any) -> None:
        if isinstance(target, Temp):
            self._store_symbol(str(target))
            return
        if isinstance(target, str):
            self._store_symbol(target)
            return
        raise NotImplementedError(f"Destino IR sem tradução para POP: {target!r}")

    def _push_array_address(self, name: str, indices: list[Any]) -> None:
        _, dims = self._active_array_types()[name]
        self._push_symbol(name)

        for idx_num, idx_expr in enumerate(indices):
            self._push_value(idx_expr)
            self.emit("PUSHI", 1)
            self.emit("SUB")

            stride = 1
            for dim in dims[:idx_num]:
                stride *= dim
            if stride != 1:
                self.emit("PUSHI", stride)
                self.emit("MUL")

            # O valor guardado na variável do array é um apontador devolvido por
            # ALLOC, por isso o deslocamento tem de usar aritmética de ponteiros.
            self.emit("PADD")

    def _type_of(self, value: Any) -> str:
        if isinstance(value, bool):
            return "LOGICAL"
        if isinstance(value, int):
            return "INTEGER"
        if isinstance(value, float):
            return "REAL"
        if isinstance(value, Temp):
            return self.temp_types.get(str(value), "INTEGER")
        if isinstance(value, IRArrayRef):
            return self._active_array_types().get(value.name, ("INTEGER", []))[0]
        if isinstance(value, IRStringLit):
            return "CHARACTER"
        if isinstance(value, str):
            if value in self._active_scalar_types():
                return self._active_scalar_types()[value]
            if value in self.temp_types:
                return self.temp_types[value]
            if value in self._active_array_types():
                return self._active_array_types()[value][0]
        return "INTEGER"

    def _active_scalar_types(self) -> ScalarTypes:
        if self._current_subprogram is not None:
            return self._current_subprogram.scalar_types
        return self.scalar_types

    def _active_array_types(self) -> ArrayTypes:
        if self._current_subprogram is not None:
            return self._current_subprogram.array_types
        return self.array_types

    def _push_symbol(self, name: str) -> None:
        if self._current_frame is not None:
            if name in self._current_frame.param_offsets:
                self.emit("PUSHL", self._current_frame.param_offsets[name])
                return
            if name in self._current_frame.local_offsets:
                self.emit("PUSHL", self._current_frame.local_offsets[name])
                return
        self.emit("PUSHG", self.layout.addr_of_scalar(name))

    def _store_symbol(self, name: str) -> None:
        if self._current_frame is not None:
            if name in self._current_frame.param_offsets:
                self.emit("STOREL", self._current_frame.param_offsets[name])
                return
            if name in self._current_frame.local_offsets:
                self.emit("STOREL", self._current_frame.local_offsets[name])
                return
        self.emit("STOREG", self.layout.addr_of_scalar(name))

    def _is_string_literal(self, value: Any) -> bool:
        return isinstance(value, IRStringLit)

    @staticmethod
    def _looks_like_identifier(value: str) -> bool:
        return bool(value) and (value[0].isalpha() or value[0] == "_") and all(ch.isalnum() or ch == "_" for ch in value)


EWVMBackend = EWVMGenerator
