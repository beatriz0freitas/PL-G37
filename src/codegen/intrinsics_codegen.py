"""Emissão de intrínsecas suportadas pelo backend EWVM."""

from __future__ import annotations

from typing import Any


class IntrinsicsCodegenMixin:
    """Responsável por traduzir intrínsecas Fortran para EWVM."""

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
        is_real = self._is_real_type(self._type_of(arg))
        keep_label = self._new_backend_label("ABS_KEEP")
        end_label = self._new_backend_label("ABS_END")

        self._push_numeric_value(arg, as_real=is_real)
        self.emit("PUSHF" if is_real else "PUSHI", 0.0 if is_real else 0)
        self.emit("FINF" if is_real else "INF")
        self.emit("JZ", self._label_name(keep_label))

        self._push_numeric_value(arg, as_real=is_real)
        self.emit("PUSHF" if is_real else "PUSHI", 0.0 if is_real else 0)
        self.emit("SWAP")
        self.emit("FSUB" if is_real else "SUB")
        self.emit("JUMP", self._label_name(end_label))

        self.emit_label(keep_label)
        self._push_numeric_value(arg, as_real=is_real)
        self.emit_label(end_label)

    def _emit_max_min(self, left: Any, right: Any, *, want_max: bool) -> None:
        is_real = self._is_real_type(self._type_of(left)) or self._is_real_type(self._type_of(right))
        take_left_label = self._new_backend_label("MM_LEFT")
        end_label = self._new_backend_label("MM_END")

        self._push_numeric_value(left, as_real=is_real)
        self._push_numeric_value(right, as_real=is_real)
        if want_max:
            self.emit("FSUPEQ" if is_real else "SUPEQ")
        else:
            self.emit("FINFEQ" if is_real else "INFEQ")
        self.emit("JZ", self._label_name(take_left_label))

        self._push_numeric_value(left, as_real=is_real)
        self.emit("JUMP", self._label_name(end_label))

        self.emit_label(take_left_label)
        self._push_numeric_value(right, as_real=is_real)
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
        if not self._is_real_type(self._type_of(arg)):
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
