"""NOVA compiler: AST -> bytecode.

Bytecode is a flat list of (opcode, argument) tuples, plus a constant pool.
The VM (step 4) will run these on a stack.
"""
from enum import Enum, auto
from ast_nodes import *
from parser import parse


class Op(Enum):
    CONST = auto()             # push constants[arg]
    LOAD_GLOBAL = auto()       # push variable named arg
    STORE_GLOBAL = auto()      # pop value, store in variable named arg
    ADD = auto(); SUB = auto(); MUL = auto(); DIV = auto(); MOD = auto()
    EQ = auto(); NE = auto(); LT = auto(); LE = auto(); GT = auto(); GE = auto()
    NEG = auto()               # unary minus
    NOT = auto()               # logical not
    PRINT = auto()             # pop and print
    JUMP = auto()              # pc = arg
    JUMP_IF_FALSE = auto()     # pop; if falsy, pc = arg
    JUMP_IF_FALSE_OR_POP = auto()  # if top is falsy: jump (keep it), else pop
    JUMP_IF_TRUE_OR_POP = auto()   # if top is truthy: jump (keep it), else pop
    LOAD_LOCAL = auto()        # push local slot arg of the current function
    STORE_LOCAL = auto()       # pop value into local slot arg
    POP = auto()               # discard top of stack
    CALL = auto()              # call the function under the last `arg` values
    RETURN = auto()            # pop result, go back to the caller
    HALT = auto()


BINARY_OPS = {
    "+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV, "%": Op.MOD,
    "==": Op.EQ, "!=": Op.NE, "<": Op.LT, "<=": Op.LE, ">": Op.GT, ">=": Op.GE,
}


class Chunk:
    """A compiled program: instructions + constants."""
    def __init__(self):
        self.code: list[tuple] = []
        self.constants: list = []


class CompileError(Exception):
    pass


class Function:
    """A compiled NOVA function: its own bytecode plus metadata."""
    def __init__(self, name: str, arity: int, chunk: Chunk, num_locals: int):
        self.name = name
        self.arity = arity
        self.chunk = chunk
        self.num_locals = num_locals

    def __repr__(self):
        return f"<fn {self.name}>"


class Compiler:
    def __init__(self, params: list | None = None):
        self.chunk = Chunk()
        # None  -> top-level code (variables are globals)
        # dict  -> inside a function (name -> local slot number)
        self.locals: dict | None = None
        if params is not None:
            self.locals = {name: i for i, name in enumerate(params)}

    # ---------- helpers ----------

    def emit(self, op: Op, arg=None) -> int:
        self.chunk.code.append((op, arg))
        return len(self.chunk.code) - 1      # index, handy for patching jumps

    def add_constant(self, value) -> int:
        self.chunk.constants.append(value)
        return len(self.chunk.constants) - 1

    def emit_jump(self, op: Op) -> int:
        """Emit a jump with a placeholder target; patch it later."""
        return self.emit(op, None)

    def patch(self, jump_index: int):
        """Make the jump at jump_index land on the NEXT instruction to be emitted."""
        op, _ = self.chunk.code[jump_index]
        self.chunk.code[jump_index] = (op, len(self.chunk.code))

    def here(self) -> int:
        return len(self.chunk.code)

    # ---------- entry point ----------

    def compile(self, program: Program) -> Chunk:
        for stmt in program.statements:
            self.visit(stmt)
        self.emit(Op.HALT)
        return self.chunk

    def visit(self, node):
        getattr(self, "visit_" + type(node).__name__)(node)

    # ---------- statements ----------

    def visit_Let(self, node: Let):
        self.visit(node.value)            # compile value BEFORE declaring the name
        if self.locals is not None:
            if node.name not in self.locals:
                self.locals[node.name] = len(self.locals)
            self.emit(Op.STORE_LOCAL, self.locals[node.name])
        else:
            self.emit(Op.STORE_GLOBAL, node.name)

    def visit_Assign(self, node: Assign):
        self.visit(node.value)
        if self.locals is not None and node.name in self.locals:
            self.emit(Op.STORE_LOCAL, self.locals[node.name])
        else:
            self.emit(Op.STORE_GLOBAL, node.name)

    def visit_ExprStmt(self, node: ExprStmt):
        self.visit(node.expr)
        self.emit(Op.POP)                 # throw away the unused result

    def visit_Return(self, node: Return):
        if self.locals is None:
            raise CompileError("'return' outside of a function")
        if node.value is None:
            self.emit(Op.CONST, self.add_constant(None))
        else:
            self.visit(node.value)
        self.emit(Op.RETURN)

    def visit_FnDecl(self, node: FnDecl):
        if self.locals is not None:
            raise CompileError(f"nested function '{node.name}' is not supported")
        sub = Compiler(params=node.params)     # a fresh compiler for the body
        sub.visit(node.body)
        sub.emit(Op.CONST, sub.add_constant(None))   # implicit "return nil"
        sub.emit(Op.RETURN)
        fn = Function(node.name, len(node.params), sub.chunk, len(sub.locals))
        self.emit(Op.CONST, self.add_constant(fn))
        self.emit(Op.STORE_GLOBAL, node.name)

    def visit_Print(self, node: Print):
        self.visit(node.value)
        self.emit(Op.PRINT)

    def visit_Block(self, node: Block):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_If(self, node: If):
        self.visit(node.condition)
        to_else = self.emit_jump(Op.JUMP_IF_FALSE)
        self.visit(node.then_branch)
        if node.else_branch:
            to_end = self.emit_jump(Op.JUMP)
            self.patch(to_else)              # else-part starts here
            self.visit(node.else_branch)
            self.patch(to_end)
        else:
            self.patch(to_else)

    def visit_While(self, node: While):
        loop_start = self.here()
        self.visit(node.condition)
        to_end = self.emit_jump(Op.JUMP_IF_FALSE)
        self.visit(node.body)
        self.emit(Op.JUMP, loop_start)       # jump backwards
        self.patch(to_end)

    # ---------- expressions ----------

    def visit_Number(self, node: Number):
        self.emit(Op.CONST, self.add_constant(node.value))

    def visit_String(self, node: String):
        self.emit(Op.CONST, self.add_constant(node.value))

    def visit_Bool(self, node: Bool):
        self.emit(Op.CONST, self.add_constant(node.value))

    def visit_Variable(self, node: Variable):
        if self.locals is not None and node.name in self.locals:
            self.emit(Op.LOAD_LOCAL, self.locals[node.name])
        else:
            self.emit(Op.LOAD_GLOBAL, node.name)

    def visit_Call(self, node: Call):
        self.emit(Op.LOAD_GLOBAL, node.name)     # the function itself
        for arg in node.args:
            self.visit(arg)                      # then its arguments, in order
        self.emit(Op.CALL, len(node.args))

    def visit_Unary(self, node: Unary):
        self.visit(node.operand)
        self.emit(Op.NEG if node.op == "-" else Op.NOT)

    def visit_Binary(self, node: Binary):
        if node.op in ("&&", "||"):
            # short-circuit: skip the right side if the left decides the answer
            self.visit(node.left)
            jump_op = Op.JUMP_IF_FALSE_OR_POP if node.op == "&&" else Op.JUMP_IF_TRUE_OR_POP
            j = self.emit_jump(jump_op)
            self.visit(node.right)
            self.patch(j)
        else:
            self.visit(node.left)
            self.visit(node.right)
            self.emit(BINARY_OPS[node.op])


def compile_source(source: str) -> Chunk:
    return Compiler().compile(parse(source))


def disassemble(chunk: Chunk, name: str = "main"):
    """Print bytecode in a human-readable form (functions included)."""
    print(f"== {name} ==")
    for i, (op, arg) in enumerate(chunk.code):
        line = f"{i:04d}  {op.name:<22}"
        if op == Op.CONST:
            line += f"{arg}   ({chunk.constants[arg]!r})"
        elif arg is not None:
            line += f"{arg!r}"
        print(line)
    for const in chunk.constants:
        if isinstance(const, Function):
            print()
            disassemble(const.chunk, f"fn {const.name}")


if __name__ == "__main__":
    print("--- program 1 ---")
    disassemble(compile_source("let x = 2 + 3 * 4; print(x);"))

    print("\n--- program 2 (loop) ---")
    disassemble(compile_source('''
        let i = 0;
        while (i < 3) {
            print(i);
            i = i + 1;
        }
    '''))
