from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    COMMA = ","
    DOT = "."
    MINUS = "-"
    PLUS = "+"
    SEMICOLON = ";"
    SLASH = "/"
    STAR = "*"
    QUESTION = "?"
    COLON = ":"

    BANG = "!"
    BANG_EQUAL = "!="
    EQUAL = "="
    EQUAL_EQUAL = "=="
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="

    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    AND = "and"
    BREAK = "break"
    CLASS = "class"
    CONTINUE = "continue"
    ELSE = "else"
    FALSE = "false"
    FUN = "fun"
    FOR = "for"
    IF = "if"
    NIL = "nil"
    OR = "or"
    PRINT = "print"
    RETURN = "return"
    SUPER = "super"
    THIS = "this"
    TRUE = "true"
    VAR = "var"
    WHILE = "while"

    EOF = auto()

_TT = TokenType
class TokenGroup:
    Comparison = {_TT.GREATER, _TT.GREATER_EQUAL, _TT.LESS, _TT.LESS_EQUAL}
    Equality = {_TT.EQUAL_EQUAL, _TT.BANG_EQUAL}
    Factor = {_TT.STAR, _TT.SLASH}
    Term = {_TT.PLUS, _TT.MINUS}

class Token:
    def __init__(
        self, type: TokenType, lexeme: str, line: int, literal: Any = None
    ) -> None:
        self.type = type
        self.lexeme = lexeme
        self.literal = literal
        self.line = line

    def __str__(self) -> str:
        return f"{self.type} {self.lexeme} {self.literal}"
