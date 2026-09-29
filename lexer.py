"""NOVA lexer: source text -> list of tokens."""
from dataclasses import dataclass

KEYWORDS = {
    "let", "print", "if", "else", "while",
    "fn", "return", "true", "false",
}

# Longest operators first so "==" is matched before "="
OPERATORS = ["==", "!=", "<=", ">=", "&&", "||",
             "+", "-", "*", "/", "%", "<", ">", "=", "!"]
PUNCTUATION = "(){},;"


@dataclass
class Token:
    type: str      # NUMBER, STRING, IDENT, KEYWORD, OP, PUNCT, EOF
    value: object
    line: int
    col: int = 1

    def __repr__(self):
        return f"{self.type}({self.value!r})"


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int, source: str):
        self.message = message
        self.line = line
        self.col = col
        self.source = source
        super().__init__(message)


def tokenize(src: str) -> list[Token]:
    tokens = []
    i, line = 0, 1
    line_start = 0          # index in src where the current line begins
    n = len(src)

    def col(index: int) -> int:
        return index - line_start + 1

    while i < n:
        c = src[i]
        start_col = col(i)

        # whitespace
        if c == "\n":
            line += 1
            i += 1
            line_start = i
        elif c.isspace():
            i += 1

        # comments: // until end of line
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1

        # numbers (int or float)
        elif c.isdigit():
            start = i
            while i < n and src[i].isdigit():
                i += 1
            if i < n and src[i] == "." and i + 1 < n and src[i + 1].isdigit():
                i += 1
                while i < n and src[i].isdigit():
                    i += 1
                tokens.append(Token("NUMBER", float(src[start:i]), line, start_col))
            else:
                tokens.append(Token("NUMBER", int(src[start:i]), line, start_col))

        # identifiers and keywords
        elif c.isalpha() or c == "_":
            start = i
            while i < n and (src[i].isalnum() or src[i] == "_"):
                i += 1
            word = src[start:i]
            kind = "KEYWORD" if word in KEYWORDS else "IDENT"
            tokens.append(Token(kind, word, line, start_col))

        # strings
        elif c == '"':
            i += 1
            start = i
            while i < n and src[i] != '"':
                if src[i] == "\n":
                    raise LexError(f"line {line}: unterminated string", line, start_col, src)
                i += 1
            if i >= n:
                raise LexError(f"line {line}: unterminated string", line, start_col, src)
            tokens.append(Token("STRING", src[start:i], line, start_col))
            i += 1  # closing quote

        # operators
        else:
            for op in OPERATORS:
                if src.startswith(op, i):
                    tokens.append(Token("OP", op, line, start_col))
                    i += len(op)
                    break
            else:
                if c in PUNCTUATION:
                    tokens.append(Token("PUNCT", c, line, start_col))
                    i += 1
                else:
                    raise LexError(f"Unexpected character {c!r}.", line, start_col, src)

    tokens.append(Token("EOF", None, line, col(i)))
    return tokens


if __name__ == "__main__":
    program = '''
    // my first NOVA program
    let x = 10;
    let y = 3.5;
    print(x + y * 2);
    while (x > 0) { x = x - 1; }
    print("done");
    '''
    for tok in tokenize(program):
        print(tok)
