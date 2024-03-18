from typing import Any

from m2_pylox.lox import get_lox
from m2_pylox.tokens import Token, TokenType as TT


def is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def is_identifier(char: str) -> bool:
    return char.isascii() and char.isidentifier()


class Scanner:
    def __init__(self, source: str) -> None:
        self.source = source
        self.tokens: list[Token] = []

        self.start = 0
        self.current = 0
        self.line = 1

    def scan_tokens(self) -> list[Token]:
        while not self.at_end():
            self.start = self.current
            self.scan_token()

        self.tokens.append(Token(TT.EOF, "", self.line))
        return self.tokens

    def at_end(self) -> bool:
        return self.current >= len(self.source)

    def scan_token(self) -> None:
        ch = self.advance()

        if ch is None:
            return

        match ch:
            case "!" if self.match("="):
                self.add_token(TT.BANG_EQUAL)
            case "=" if self.match("="):
                self.add_token(TT.EQUAL_EQUAL)
            case "<" if self.match("="):
                self.add_token(TT.LESS_EQUAL)
            case ">" if self.match("="):
                self.add_token(TT.GREATER_EQUAL)
            case "/" if self.match("/"):
                while self.peek() != "\n" and not self.at_end():
                    self.advance()
            case "/" if self.match("*"):
                self.block_comment()
            case "*" if self.match("/"):
                get_lox().error(
                    self.line, "Unexpected end of comment outside block comment"
                )
            case (
                  "(" | ")" | "{" | "}" | ","
                | "." | "-" | "+" | ";" | "*"
                | "!" | "=" | "<" | ">" | "/"
                | ":" | "?"
            ):
                self.add_token(TT(ch))
            case "\n":
                self.line += 1
            case '"':
                self.string()
            case ch if is_ascii_digit(ch):
                self.number()
            case ch if is_identifier(ch) and not ch.isdigit():
                self.identifier()
            case ch if ch not in " \r\t":
                get_lox().error(self.line, f"Unexpected character `{ch}`")
                
    def advance(self) -> str:
        ch = self.source[self.current]
        self.current += 1
        return ch

    def add_token(self, type: TT, literal: Any = None) -> None:
        text = self.source[self.start : self.current]
        self.tokens.append(Token(type, text, self.line, literal))

    def match(self, expected: str) -> bool:
        if self.at_end() or self.source[self.current] != expected:
            return False

        self.current += 1
        return True

    def peek(self) -> str:
        return self.source[self.current] if not self.at_end() else "\0"

    def peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def string(self) -> None:
        while self.peek() != '"' and not self.at_end():
            if self.peek() == "\n":
                self.line += 1
            self.advance()

        if self.at_end():
            get_lox().error(self.line, "Unterminated string at end of file")
            return

        self.advance()

        value = self.source[self.start + 1 : self.current - 1]
        self.add_token(TT.STRING, value)

    def number(self) -> None:
        while is_ascii_digit(self.peek()):
            self.advance()

        if self.peek() == "." and is_ascii_digit(self.peek_next()):
            self.advance()

            while is_ascii_digit(self.peek()):
                self.advance()

        value_str = self.source[self.start : self.current]
        self.add_token(TT.NUMBER, float(value_str))

    def identifier(self) -> None:
        while is_identifier(self.peek()):
            self.advance()

        text = self.source[self.start : self.current]

        self.add_token(TT(text) if text in TT else TT.IDENTIFIER)

    def block_comment(self) -> None:
        while not self.at_end():
            ch = self.advance()
            if ch == "*" and self.match("/"):
                break
            elif ch == "/" and self.match("*"):
                self.block_comment()
                continue
            elif ch == "\n":
                self.line += 1
        else:
            get_lox().error(self.line, "Unterminated block comment at end of file")
