from dataclasses import dataclass
from typing import Any

from m2_pylox.tokens import Token
from m2_pylox.visitor import Visitable


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