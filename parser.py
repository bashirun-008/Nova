"""NOVA parser: tokens -> AST (recursive descent).

Grammar (lowest precedence at the top):

  program     -> statement* EOF
  statement   -> let | print | if | while | block | assignment
  let         -> "let" IDENT "=" expr ";"
  assignment  -> IDENT "=" expr ";"
  print       -> "print" "(" expr ")" ";"
  if          -> "if" "(" expr ")" block ( "else" (if | block) )?
  while       -> "while" "(" expr ")" block
  block       -> "{" statement* "}"
  fn          -> "fn" IDENT "(" params? ")" block
  return      -> "return" expr? ";"
  exprstmt    -> expr ";"

  expr        -> or
  or          -> and ( "||" and )*
  and         -> equality ( "&&" equality )*
  equality    -> comparison ( ("==" | "!=") comparison )*
  comparison  -> term ( ("<" | "<=" | ">" | ">=") term )*
  term        -> factor ( ("+" | "-") factor )*
  factor      -> unary ( ("*" | "/" | "%") unary )*
  unary       -> ("-" | "!") unary | primary
  primary     -> NUMBER | STRING | "true" | "false" | IDENT | "(" expr ")"
"""
from lexer import tokenize, Token
from ast_nodes import *


class ParseError(Exception):
    def __init__(self, message: str, line: int, col: int, source: str):
        self.message = message
        self.line = line
        self.col = col
        self.source = source
        super().__init__(message)


class Parser:
    def __init__(self, tokens: list[Token], source: str = ""):
        self.tokens = tokens
        self.pos = 0
        self.source = source

    # ---------- helpers ----------

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def check(self, type_, value=None) -> bool:
        tok = self.peek()
        return tok.type == type_ and (value is None or tok.value == value)

    def match(self, type_, *values) -> Token | None:
        """If the current token matches, consume and return it."""
        tok = self.peek()
        if tok.type == type_ and (not values or tok.value in values):
            return self.advance()
        return None

    def error(self, message: str, tok: Token | None = None) -> ParseError:
        tok = tok or self.peek()
        return ParseError(message, tok.line, tok.col, self.source)

    def expect(self, type_, value=None) -> Token:
        if self.check(type_, value):
            return self.advance()
        tok = self.peek()
        wanted = value if value else type_
        seen = "end of file" if tok.type == "EOF" else repr(tok.value)
        raise self.error(f"Expected {wanted!r}, but got {seen}.")

    # ---------- statements ----------

    def parse(self) -> Program:
        statements = []
        while not self.check("EOF"):
            statements.append(self.statement())
        return Program(statements)

    def statement(self):
        if self.match("KEYWORD", "let"):
            name = self.expect("IDENT").value
            self.expect("OP", "=")
            value = self.expression()
            self.expect("PUNCT", ";")
            return Let(name, value)

        if self.match("KEYWORD", "print"):
            self.expect("PUNCT", "(")
            value = self.expression()
            self.expect("PUNCT", ")")
            self.expect("PUNCT", ";")
            return Print(value)

        if self.match("KEYWORD", "fn"):
            return self.fn_declaration()

        if self.match("KEYWORD", "return"):
            value = None if self.check("PUNCT", ";") else self.expression()
            self.expect("PUNCT", ";")
            return Return(value)

        if self.match("KEYWORD", "if"):
            return self.if_statement()

        if self.match("KEYWORD", "while"):
            self.expect("PUNCT", "(")
            cond = self.expression()
            self.expect("PUNCT", ")")
            return While(cond, self.block())

        if self.check("PUNCT", "{"):
            return self.block()

        # assignment: IDENT "=" expr ";"
        if self.check("IDENT") and self.tokens[self.pos + 1].value == "=" \
                and self.tokens[self.pos + 1].type == "OP":
            name = self.advance().value
            self.advance()  # the "="
            value = self.expression()
            self.expect("PUNCT", ";")
            return Assign(name, value)

        # anything else must be an expression statement, e.g.  greet("hi");
        expr = self.expression()
        self.expect("PUNCT", ";")
        return ExprStmt(expr)

    def fn_declaration(self):
        name = self.expect("IDENT").value
        self.expect("PUNCT", "(")
        params = []
        if not self.check("PUNCT", ")"):
            params.append(self.expect("IDENT").value)
            while self.match("PUNCT", ","):
                params.append(self.expect("IDENT").value)
        self.expect("PUNCT", ")")
        return FnDecl(name, params, self.block())

    def if_statement(self):
        self.expect("PUNCT", "(")
        cond = self.expression()
        self.expect("PUNCT", ")")
        then_branch = self.block()
        else_branch = None
        if self.match("KEYWORD", "else"):
            if self.match("KEYWORD", "if"):
                # else-if: wrap the nested if in a block
                else_branch = Block([self.if_statement()])
            else:
                else_branch = self.block()
        return If(cond, then_branch, else_branch)

    def block(self) -> Block:
        self.expect("PUNCT", "{")
        statements = []
        while not self.check("PUNCT", "}") and not self.check("EOF"):
            statements.append(self.statement())
        self.expect("PUNCT", "}")
        return Block(statements)

    # ---------- expressions (one method per precedence level) ----------

    def expression(self):
        return self.or_expr()

    def _binary(self, next_level, *ops):
        """Shared loop for all left-associative binary operators."""
        left = next_level()
        while (tok := self.match("OP", *ops)):
            right = next_level()
            left = Binary(tok.value, left, right)
        return left

    def or_expr(self):
        return self._binary(self.and_expr, "||")

    def and_expr(self):
        return self._binary(self.equality, "&&")

    def equality(self):
        return self._binary(self.comparison, "==", "!=")

    def comparison(self):
        return self._binary(self.term, "<", "<=", ">", ">=")

    def term(self):
        return self._binary(self.factor, "+", "-")

    def factor(self):
        return self._binary(self.unary, "*", "/", "%")

    def unary(self):
        if (tok := self.match("OP", "-", "!")):
            return Unary(tok.value, self.unary())
        return self.primary()

    def primary(self):
        if (tok := self.match("NUMBER")):
            return Number(tok.value)
        if (tok := self.match("STRING")):
            return String(tok.value)
        if self.match("KEYWORD", "true"):
            return Bool(True)
        if self.match("KEYWORD", "false"):
            return Bool(False)
        if (tok := self.match("IDENT")):
            if self.match("PUNCT", "("):          # function call
                args = []
                if not self.check("PUNCT", ")"):
                    args.append(self.expression())
                    while self.match("PUNCT", ","):
                        args.append(self.expression())
                self.expect("PUNCT", ")")
                return Call(tok.value, args)
            return Variable(tok.value)
        if self.match("PUNCT", "("):
            expr = self.expression()
            self.expect("PUNCT", ")")
            return expr
        tok = self.peek()
        seen = "end of file" if tok.type == "EOF" else repr(tok.value)
        raise self.error(f"Expected an expression, but got {seen}.")


def parse(source: str) -> Program:
    return Parser(tokenize(source), source).parse()


if __name__ == "__main__":
    code = '''
    let x = 2 + 3 * 4;
    if (x > 10) { print("big"); } else { print("small"); }
    '''
    dump(parse(code))
