"""NOVA runner.

Usage:
    python nova.py program.nova            run a program
    python nova.py program.nova --dis      show bytecode, then run
    python nova.py program.nova --trace    show every VM step while running
"""
import sys

from lexer import LexError
from parser import ParseError
from compiler import compile_source, disassemble, CompileError
from vm import VM, NovaRuntimeError
from errors import format_error


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    path = args[0]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"Cannot open {path}: {e}")
        return

    try:
        chunk = compile_source(source)
        if "--dis" in args:
            disassemble(chunk)
            print("--- output ---")
        VM(chunk, trace="--trace" in args).run()
    except (LexError, ParseError) as e:
        print(format_error("Syntax error", e.message, e.line, e.col, e.source))
    except CompileError as e:
        print(f"Compile error: {e}")
    except NovaRuntimeError as e:
        print(f"Runtime error: {e}")


if __name__ == "__main__":
    main()
