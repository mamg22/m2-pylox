from dataclasses import dataclass

from m2_pylox import expr as ex
from m2_pylox.tokens import Token
from m2_pylox.visitor import Visitable

@dataclass(frozen=True)
class Stmt(Visitable[None]):
    ...

@dataclass(frozen=True)
class Expression(Stmt):
    expression: ex.Expr

@dataclass(frozen=True)
class Print(Stmt):
    expression: ex.Expr

@dataclass(frozen=True)
class Var(Stmt):
    name: Token
    initializer: ex.Expr | None = None

@dataclass(frozen=True)
class Block(Stmt):
    statements: list[Stmt]

@dataclass(frozen=True)
class If(Stmt):
    condition: ex.Expr
    then_branch: Stmt
    else_branch: Stmt | None = None

@dataclass(frozen=True)
class While(Stmt):
    condition: ex.Expr
    body: Stmt