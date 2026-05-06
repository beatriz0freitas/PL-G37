"""Helpers de emissão para a stack da EWVM."""

from __future__ import annotations

from typing import Any

from src.representacao_intermedia.operadores import IRArrayRef, IRStringLit, Temp


class StackEmitterMixin:
    """Responsável por empilhar valores, guardar destinos e mapear operações."""

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
        is_real = self._op_uses_real_stack(op, left, right)
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
        return real_op if is_real else int_op

    def _emit_unary(self, op: str, operand: Any) -> None:
        if op == "NOT":
            self.emit("NOT")
            return
        if op == "NEG":
            if self._is_real_type(self._type_of(operand)):
                self.emit("PUSHF", 0.0)
                self.emit("SWAP")
                self.emit("FSUB")
            else:
                self.emit("PUSHI", 0)
                self.emit("SWAP")
                self.emit("SUB")
            return
        raise NotImplementedError(f"Operador unário sem tradução: {op}")

    def _push_value_for_target(self, value: Any, target: Any) -> None:
        self._push_value_for_type(value, self._type_of(target))

    def _push_value_for_type(self, value: Any, target_type: str) -> None:
        self._push_value(value)
        value_type = self._type_of(value)
        if self._is_real_type(target_type) and value_type == "INTEGER":
            self.emit("ITOF")
            return
        if target_type == "INTEGER" and self._is_real_type(value_type):
            self.emit("FTOI")

    def _push_numeric_value(self, value: Any, *, as_real: bool) -> None:
        self._push_value(value)
        if as_real and self._type_of(value) == "INTEGER":
            self.emit("ITOF")

    def _op_uses_real_stack(self, op: str, left: Any, right: Any) -> bool:
        numeric_ops = {"+", "-", "*", "/", "<", "<=", ">", ">=", "==", "!="}
        if op not in numeric_ops:
            return False
        return self._is_real_type(self._type_of(left)) or self._is_real_type(self._type_of(right))

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
