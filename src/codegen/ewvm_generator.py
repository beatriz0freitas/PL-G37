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
    IRRead,
    IRReturn,
    IRStop,
    IRStoreArray,
    IRUnaryOp,
    IRWrite,
)
from src.representacao_intermedia.operadores import IRArrayRef, Temp

from .decls import ArrayTypes, ScalarTypes, extract_decl_info
from .layout import MemoryLayout


class EWVMGenerator:
    """Traduz IR para texto EWVM."""

    def __init__(
        self,
        scalar_types: ScalarTypes | None = None,
        array_types: ArrayTypes | None = None,
    ):
        self.scalar_types = dict(scalar_types or {})
        self.array_types = dict(array_types or {})
        self.layout = MemoryLayout()
        self.lines: list[str] = []
        self.temp_types: dict[str, str] = {}

    @classmethod
    def from_program(cls, program: ast.Program) -> "EWVMGenerator":
        scalar_types, array_types = extract_decl_info(program)
        return cls(scalar_types=scalar_types, array_types=array_types)

    def generate(self, instructions: list[IRInstr]) -> str:
        self.lines = []
        self.layout = MemoryLayout()
        self.temp_types = {}

        self._allocate_declared_symbols()
        self._infer_temp_types(instructions)
        self._allocate_temporaries_and_implicit_scalars(instructions)

        self.emit("START")
        self._emit_array_allocations()

        for instr in instructions:
            self._translate(instr)

        if not instructions or not isinstance(instructions[-1], IRStop):
            self.emit("STOP")

        return "\n".join(self.lines)

    def emit(self, *tokens: Any) -> None:
        self.lines.append(" ".join(str(token) for token in tokens))

    def emit_label(self, label: Any) -> None:
        self.lines.append(f"{self._label_name(label)}:")

    def _label_name(self, label: Any) -> str:
        raw = str(label)
        sanitized = "".join(ch for ch in raw if ch.isalnum())
        return sanitized or raw

    def _allocate_declared_symbols(self) -> None:
        for name in sorted(self.scalar_types):
            self.layout.allocate_scalar(name)
        for name in sorted(self.array_types):
            self.layout.allocate_scalar(name)

    def _emit_array_allocations(self) -> None:
        for name in sorted(self.array_types):
            _, dims = self.array_types[name]
            total = 1
            for dim in dims:
                total *= dim
            self.emit("ALLOC", total)
            self.emit("STOREG", self.layout.addr_of_scalar(name))

    def _allocate_temporaries_and_implicit_scalars(self, instructions: list[IRInstr]) -> None:
        for instr in instructions:
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

    def _scan_value(self, value: Any) -> None:
        if isinstance(value, Temp):
            self._ensure_storage(value)
        elif isinstance(value, IRArrayRef):
            for idx in value.indices:
                self._scan_value(idx)
        elif isinstance(value, str) and self._looks_like_identifier(value) and not self._is_string_literal(value):
            self._ensure_storage(value)

    def _ensure_storage(self, target: Any) -> None:
        if isinstance(target, Temp):
            self.layout.allocate_scalar(str(target))
            return
        if isinstance(target, str) and target not in self.array_types:
            self.layout.allocate_scalar(target)
            self.scalar_types.setdefault(target, self.temp_types.get(target, "INTEGER"))

    def _infer_temp_types(self, instructions: list[IRInstr]) -> None:
        changed = True
        while changed:
            changed = False
            for instr in instructions:
                inferred = self._infer_instr_type(instr)
                if inferred is None:
                    continue
                name, typename = inferred
                if self.temp_types.get(name) != typename:
                    self.temp_types[name] = typename
                    changed = True

    def _infer_instr_type(self, instr: IRInstr) -> tuple[str, str] | None:
        if isinstance(instr, IRAssign) and isinstance(instr.dest, Temp):
            return str(instr.dest), self._type_of(instr.src)

        if isinstance(instr, IRLoadArray):
            array_type, _ = self.array_types[instr.name]
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
                self.emit(self._unary_opcode(op, operand))
                self._pop_to(dest)
            case IRPrint(args=args):
                self._translate_print(args)
            case IRWrite(items=items):
                self._translate_print(items)
            case IRRead(args=args):
                self._translate_read(args)
            case IRCall(name=name, args=args, dest=dest):
                self._translate_call(name, args, dest)
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
            read_op = "READF" if typename == "REAL" else "READS" if typename == "CHARACTER" else "READ"
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
            raise NotImplementedError(
                f"Intrínseca '{upper}' ainda não mapeada para a EWVM documentada"
            )
        else:
            for arg in args:
                self._push_value(arg)
            self.emit("PUSHA", upper)
            self.emit("CALL")

        if dest is not None:
            self._pop_to(dest)

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
            return "NEQ"
        if op == "CONCAT":
            return "CONCAT"

        arithmetic = {
            "+": ("ADD", "FADD"),
            "-": ("SUB", "FSUB"),
            "*": ("MUL", "FMUL"),
            "/": ("DIV", "FDIV"),
            "**": ("POW", "FPOW"),
        }
        int_op, real_op = arithmetic[op]
        return real_op if "REAL" in {self._type_of(left), self._type_of(right)} else int_op

    def _unary_opcode(self, op: str, operand: Any) -> str:
        if op == "NOT":
            return "NOT"
        if op == "NEG":
            return "FNEG" if self._type_of(operand) == "REAL" else "NEG"
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
            self.emit("PUSHG", self.layout.addr_of_scalar(str(value)))
            return
        if isinstance(value, IRArrayRef):
            self._push_array_address(value.name, value.indices)
            self.emit("LOAD", 0)
            return
        if isinstance(value, str):
            if self._is_string_literal(value):
                escaped = value.replace('"', '\\"')
                self.emit(f'PUSHS "{escaped}"')
            else:
                self.emit("PUSHG", self.layout.addr_of_scalar(value))
            return
        raise NotImplementedError(f"Valor IR sem tradução para PUSH: {value!r}")

    def _pop_to(self, target: Any) -> None:
        if isinstance(target, Temp):
            self.emit("STOREG", self.layout.addr_of_scalar(str(target)))
            return
        if isinstance(target, str):
            self.emit("STOREG", self.layout.addr_of_scalar(target))
            return
        raise NotImplementedError(f"Destino IR sem tradução para POP: {target!r}")

    def _push_array_address(self, name: str, indices: list[Any]) -> None:
        _, dims = self.array_types[name]
        self.emit("PUSHG", self.layout.addr_of_scalar(name))

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

            self.emit("ADD")

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
            return self.array_types.get(value.name, ("INTEGER", []))[0]
        if isinstance(value, str):
            if self._is_string_literal(value):
                return "CHARACTER"
            if value in self.scalar_types:
                return self.scalar_types[value]
            if value in self.temp_types:
                return self.temp_types[value]
            if value in self.array_types:
                return self.array_types[value][0]
        return "INTEGER"

    def _is_string_literal(self, value: Any) -> bool:
        return isinstance(value, str) and value not in self.scalar_types and value not in self.array_types and value not in self.temp_types

    @staticmethod
    def _looks_like_identifier(value: str) -> bool:
        return bool(value) and (value[0].isalpha() or value[0] == "_") and all(ch.isalnum() or ch == "_" for ch in value)


EWVMBackend = EWVMGenerator
