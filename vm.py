"""NOVA VM: executes bytecode on a stack."""
from compiler import Chunk, Op, Function


class NovaRuntimeError(Exception):
    pass


def is_truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return len(v) > 0
    return v is not None


def is_number(v) -> bool:
    # bool is a subclass of int in Python, so exclude it explicitly
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def to_text(v) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "nil"
    return str(v)


class VM:
    def __init__(self, chunk: Chunk, trace: bool = False):
        self.chunk = chunk
        self.stack: list = []
        self.globals: dict = {}
        self.trace = trace

    def pop(self):
        return self.stack.pop()

    def push(self, v):
        self.stack.append(v)

    def run(self):
        code = self.chunk.code
        consts = self.chunk.constants
        pc = 0
        locals_ = None          # local slots of the running function (None at top level)
        frames = []             # saved (code, consts, pc, locals_) of every caller

        while True:
            op, arg = code[pc]
            if self.trace:
                print(f"{'  ' * len(frames)}{pc:04d}  {op.name:<22}{'' if arg is None else repr(arg):<8} stack={self.stack}")
            pc += 1

            if op == Op.CONST:
                self.push(consts[arg])

            elif op == Op.LOAD_GLOBAL:
                if arg not in self.globals:
                    raise NovaRuntimeError(f"undefined variable '{arg}'")
                self.push(self.globals[arg])

            elif op == Op.STORE_GLOBAL:
                self.globals[arg] = self.pop()

            elif op in (Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD):
                b, a = self.pop(), self.pop()
                self.push(self.arithmetic(op, a, b))

            elif op in (Op.LT, Op.LE, Op.GT, Op.GE):
                b, a = self.pop(), self.pop()
                self.push(self.compare(op, a, b))

            elif op == Op.EQ:
                b, a = self.pop(), self.pop()
                self.push(self.equal(a, b))

            elif op == Op.NE:
                b, a = self.pop(), self.pop()
                self.push(not self.equal(a, b))

            elif op == Op.NEG:
                a = self.pop()
                if not is_number(a):
                    raise NovaRuntimeError("can only negate numbers")
                self.push(-a)

            elif op == Op.NOT:
                self.push(not is_truthy(self.pop()))

            elif op == Op.PRINT:
                print(to_text(self.pop()))

            elif op == Op.JUMP:
                pc = arg

            elif op == Op.JUMP_IF_FALSE:
                if not is_truthy(self.pop()):
                    pc = arg

            elif op == Op.JUMP_IF_FALSE_OR_POP:
                if not is_truthy(self.stack[-1]):
                    pc = arg
                else:
                    self.pop()

            elif op == Op.JUMP_IF_TRUE_OR_POP:
                if is_truthy(self.stack[-1]):
                    pc = arg
                else:
                    self.pop()

            elif op == Op.LOAD_LOCAL:
                self.push(locals_[arg])

            elif op == Op.STORE_LOCAL:
                locals_[arg] = self.pop()

            elif op == Op.POP:
                self.pop()

            elif op == Op.CALL:
                callee = self.stack[-arg - 1]
                if not isinstance(callee, Function):
                    raise NovaRuntimeError(f"{to_text(callee)!r} is not a function")
                if callee.arity != arg:
                    raise NovaRuntimeError(
                        f"{callee.name}() expects {callee.arity} argument(s) but got {arg}")
                if len(frames) >= 1000:
                    raise NovaRuntimeError("stack overflow (too much recursion)")
                base = len(self.stack) - arg
                args = self.stack[base:]
                del self.stack[base - 1:]                   # remove function + args
                frames.append((code, consts, pc, locals_))  # remember where to return
                code = callee.chunk.code
                consts = callee.chunk.constants
                locals_ = args + [None] * (callee.num_locals - arg)
                pc = 0

            elif op == Op.RETURN:
                result = self.pop()
                code, consts, pc, locals_ = frames.pop()     # back to the caller
                self.push(result)

            elif op == Op.HALT:
                return

            else:
                raise NovaRuntimeError(f"unknown opcode {op}")

    # ---------- operation helpers ----------

    def arithmetic(self, op, a, b):
        if op == Op.ADD and isinstance(a, str) and isinstance(b, str):
            return a + b                      # string concatenation
        if not (is_number(a) and is_number(b)):
            raise NovaRuntimeError(f"cannot apply {op.name} to {to_text(a)!r} and {to_text(b)!r}")
        if op == Op.ADD: return a + b
        if op == Op.SUB: return a - b
        if op == Op.MUL: return a * b
        if b == 0:
            raise NovaRuntimeError("division by zero")
        if op == Op.MOD:
            return a % b
        # DIV: keep ints when the result is whole (6 / 3 -> 2), else float
        if isinstance(a, int) and isinstance(b, int) and a % b == 0:
            return a // b
        return a / b

    def compare(self, op, a, b):
        both_numbers = is_number(a) and is_number(b)
        both_strings = isinstance(a, str) and isinstance(b, str)
        if not (both_numbers or both_strings):
            raise NovaRuntimeError(f"cannot compare {to_text(a)!r} and {to_text(b)!r}")
        if op == Op.LT: return a < b
        if op == Op.LE: return a <= b
        if op == Op.GT: return a > b
        return a >= b

    def equal(self, a, b):
        if isinstance(a, bool) != isinstance(b, bool):
            return False                      # 1 == true should be false
        return a == b
