🔗 **[Try NOVA in your browser](https://bashirun-008.github.io/Nova/)** — no install needed
# NOVA

NOVA is a small programming language with its own lexer, parser, bytecode compiler, and stack-based virtual machine — all written from scratch in Python.

```
NOVA program
     |
     v
   Lexer
     |
     v
   Parser
     |
     v
    AST
     |
     v
  Compiler
     |
     v
  Bytecode
     |
     v
NOVA Virtual Machine
     |
     v
   Output
```

## Why

Most intro projects stop at "write an interpreter that walks the syntax tree directly." NOVA instead compiles down to bytecode — small numeric instructions like `CONST`, `ADD`, `JUMP_IF_FALSE` — and runs them on a stack machine, which is the same basic architecture used by CPython, Lua, and the JVM.

## Features

- Variables, arithmetic, comparisons, and string concatenation
- `if` / `else if` / `else`, `while` loops
- Functions, including recursion, with proper call frames and local variable slots
- Short-circuiting `&&` and `||`
- Compiler errors that point at the exact character in your source code

## Example

```
fn fib(n) {
    if (n < 2) { return n; }
    return fib(n - 1) + fib(n - 2);
}

let i = 0;
while (i < 10) {
    print(fib(i));
    i = i + 1;
}
```

```
fn factorial(n) {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}

print(factorial(10));   // 3628800
```

More examples are in [`fizzbuzz.nova`](fizzbuzz.nova) and [`functions.nova`](functions.nova).

## Running it

Requires Python 3.10+.

```
python nova.py yourprogram.nova            # run a program
python nova.py yourprogram.nova --dis      # show the compiled bytecode
python nova.py yourprogram.nova --trace    # print every VM step and stack state
```

## Error messages

Errors point at the exact line and column that caused them:

```
Syntax error at line 1:
    let y = ;
            ^
Expected an expression, but got ';'.
```

## Architecture

| File | Role |
|---|---|
| `lexer.py` | Turns source text into a stream of tokens |
| `parser.py` | Recursive-descent parser: tokens → AST |
| `ast_nodes.py` | AST node type definitions |
| `compiler.py` | Walks the AST and emits bytecode; defines the instruction set |
| `vm.py` | Executes bytecode on a stack, including function call frames |
| `errors.py` | Shared formatting for source-pointer error messages |
| `nova.py` | Command-line entry point |

## How a program runs, end to end

`2 + 3 * 4` compiles to:

```
CONST 0   (2)
CONST 1   (3)
CONST 2   (4)
MUL
ADD
```

The VM pushes `2`, `3`, `4` onto its stack, then `MUL` pops `3` and `4` and pushes `12`, then `ADD` pops `2` and `12` and pushes `14`. Control flow (`if`, `while`) works by jumping the program counter to a different instruction index, and function calls push a new "frame" onto a call stack so the VM knows where to resume once the function returns.

## What's not implemented (yet)

- Arrays/lists
- Closures and nested functions
- Block-level scoping (variables inside `{ }` are function/global scoped, not block scoped)

## What I learned

Built incrementally: lexer → parser/AST → bytecode compiler → VM → functions & recursion → error diagnostics. Each stage was tested independently before moving to the next, which made debugging the trickiest part — call frames and per-function constant pools — much more manageable.
