"""NOVA AST: the node types the parser builds."""
from dataclasses import dataclass


# ---------- Expressions (produce a value) ----------

@dataclass
class Number:
    value: float | int

@dataclass
class String:
    value: str

@dataclass
class Bool:
    value: bool

@dataclass
class Variable:
    name: str

@dataclass
class Unary:
    op: str            # "-" or "!"
    operand: object

@dataclass
class Binary:
    op: str            # + - * / % == != < <= > >= && ||
    left: object
    right: object


# ---------- Statements (do something) ----------

@dataclass
class Let:
    name: str
    value: object

@dataclass
class Assign:
    name: str
    value: object

@dataclass
class Print:
    value: object

@dataclass
class Block:
    statements: list

@dataclass
class If:
    condition: object
    then_branch: Block
    else_branch: Block | None

@dataclass
class While:
    condition: object
    body: Block

@dataclass
class Program:
    statements: list


@dataclass
class ExprStmt:
    expr: object       # an expression used as a statement, e.g.  greet("hi");

@dataclass
class Return:
    value: object | None

@dataclass
class FnDecl:
    name: str
    params: list
    body: Block

@dataclass
class Call:
    name: str
    args: list


def dump(node, indent=0):
    """Pretty-print an AST as an indented tree."""
    pad = "  " * indent
    if isinstance(node, list):
        for item in node:
            dump(item, indent)
    elif hasattr(node, "__dataclass_fields__"):
        print(f"{pad}{type(node).__name__}")
        for field in node.__dataclass_fields__:
            value = getattr(node, field)
            if hasattr(value, "__dataclass_fields__") or isinstance(value, list):
                print(f"{pad}  {field}:")
                dump(value, indent + 2)
            else:
                print(f"{pad}  {field}: {value!r}")
    elif node is None:
        print(f"{pad}None")
    else:
        print(f"{pad}{node!r}")
