from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from m2_pylox.tokens import Token
from m2_pylox.visitor import Visitable

if TYPE_CHECKING:
    from m2_pylox import stmt as st


@dataclass(frozen=True)
class Expr(Visitable):
    ...

@dataclass(frozen=True)
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass(frozen=True)
class Grouping(Expr):
    expression: Expr

@dataclass(frozen=True)
class Literal(Expr):
    value: Any

@dataclass(frozen=True)
class Unary(Expr):
    operator: Token
    right: Expr

@dataclass(frozen=True)
class Conditional(Expr):
    condition: Expr
    on_true: Expr
    on_false: Expr

@dataclass(frozen=True)
class Variable(Expr):
    name: Token

@dataclass(frozen=True)
class Assign(Expr):
    name: Token
    value: Expr

@dataclass(frozen=True)
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass(frozen=True)
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: list[Expr]

@dataclass(frozen=True)
class Function(Expr):
    params: list[Token]
    body: list['st.Stmt']

@dataclass(frozen=True)
class Get(Expr):
    object: Expr
    name: Token

@dataclass(frozen=True)
class Set(Expr):
    object: Expr
    name: Token
    value: Expr

@dataclass(frozen=True)
class This(Expr):
    keyword: Token

@dataclass(frozen=True)
class Super(Expr):
    keyword: Token
    method: Token