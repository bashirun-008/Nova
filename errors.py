"""Shared formatting for NOVA error messages.

Turns (message, line, col, source) into something like:

    Syntax error at line 4:
        let x = ;
                ^
    Expected an expression.
"""


def format_error(kind: str, message: str, line: int, col: int, source: str) -> str:
    lines = source.split("\n")
    src_line = lines[line - 1] if 1 <= line <= len(lines) else ""
    stripped = src_line.strip()
    # column shifts left by however much leading whitespace we stripped
    leading_ws = len(src_line) - len(src_line.lstrip())
    pointer_col = max(col - leading_ws, 1)

    out = [f"{kind} at line {line}:"]
    out.append(f"    {stripped}")
    out.append("    " + " " * (pointer_col - 1) + "^")
    out.append(message)
    return "\n".join(out)
