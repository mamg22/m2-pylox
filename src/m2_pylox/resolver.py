from contextlib import contextmanager
from enum import Enum, auto
from functools import singledispatchmethod
from typing import override, Any

from m2_pylox import lox
from m2_pylox.tokens import Token
from m2_pylox.visitor import Visitable, Visitor
from m2_pylox import interpreter as interp, stmt as st, expr as ex

class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()

class Resolver(Visitor):
    interpreter: interp.Interpreter
    scopes: list[dict[str, bool]]
    current_function: FunctionType

    def __init__(self, interpreter: interp.Interpreter) -> None:
        self.interpreter = interpreter
        self.scopes = []
        self.current_function = FunctionType.NONE

    @singledispatchmethod
    def resolve(self, obj: Any) -> None:
        raise NotImplementedError(f"'{obj.__class__.__name__}' could not be dispatched by resolve()")

    @resolve.register(list)
    def _(self, statements: list[st.Stmt]) -> None:
        for statement in statements:
            self.resolve(statement)
    
    @resolve.register
    def _(self, stmt: st.Stmt) -> None:
        stmt.accept(self)
    
    @resolve.register
    def _(self, expr: ex.Expr) -> None:
        expr.accept(self)
    
    def begin_scope(self) -> None:
        self.scopes.append({})

    def end_scope(self) -> None:
        self.scopes.pop()
    
    @contextmanager
    def scope(self):
        try:
            self.begin_scope()
            yield
        finally:
            self.end_scope()
    
    def declare(self, name: Token) -> None:
        if self.scopes:
            scope = self.scopes[-1]
            if name.lexeme in scope:
                lox.get_lox().error(name, "Already a variable with this name in this scope")

            scope[name.lexeme] = False
    
    def define(self, name: Token) -> None:
        if self.scopes:
            self.scopes[-1][name.lexeme] = True
    
    def resolve_local(self, expr: ex.Expr, name: Token) -> None:
        for i, scope in enumerate(reversed(self.scopes)):
            if name.lexeme in scope:
                self.interpreter.resolve(expr, i)
    
    def resolve_function(self, function: ex.Function, type: FunctionType) -> None:
        enclosing_function = self.current_function
        self.current_function = type

        with self.scope():
            for param in function.params:
                self.declare(param)
                self.define(param)
            self.resolve(function.body)
        
        self.current_function = enclosing_function
    
    @singledispatchmethod
    @override
    def visit(self, obj: Visitable) -> None:
        raise NotImplementedError(f"'{obj.__class__.__name__}' could not be dispatched by visit()")
    
    @visit.register
    def _(self, stmt: st.Block) -> None:
        with self.scope():
            self.resolve(stmt.statements)
    
    @visit.register
    def _(self, stmt: st.Break) -> None:
        pass

    @visit.register
    def _(self, stmt: st.Expression) -> None:
        self.resolve(stmt.expression)
    
    @visit.register
    def _(self, stmt: st.Function) -> None:
        self.declare(stmt.name)
        self.define(stmt.name)

        self.resolve_function(stmt.function, FunctionType.FUNCTION)
    
    @visit.register
    def _(self, stmt: st.If) -> None:
        self.resolve(stmt.condition)
        self.resolve(stmt.then_branch)

        if stmt.else_branch is not None:
            self.resolve(stmt.else_branch)
    
    @visit.register
    def _(self, stmt: st.Print) -> None:
        self.resolve(stmt.expression)
    
    @visit.register
    def _(self, stmt: st.Return) -> None:
        if self.current_function is FunctionType.NONE:
            lox.get_lox().error(stmt.keyword, "Can't return from top-level code")

        if stmt.value is not None:
            self.resolve(stmt.value)
    
    @visit.register
    def _(self, stmt: st.Var) -> None:
        self.declare(stmt.name)
        if stmt.initializer is not None:
            self.resolve(stmt.initializer)
        self.define(stmt.name)
    
    @visit.register
    def _(self, stmt: st.While) -> None:
        self.resolve(stmt.condition)
        self.resolve(stmt.body)
    
    @visit.register
    def _(self, expr: ex.Assign) -> None:
        self.resolve(expr.value)
        self.resolve_local(expr, expr.name)
    
    @visit.register
    def _(self, expr: ex.Binary) -> None:
        self.resolve(expr.left)
        self.resolve(expr.right)
    
    @visit.register
    def _(self, expr: ex.Call) -> None:
        self.resolve(expr.callee)

        for argument in expr.arguments:
            self.resolve(argument)
    
    @visit.register
    def _(self, expr: ex.Conditional) -> None:
        self.resolve(expr.condition)
        self.resolve(expr.on_true)
        self.resolve(expr.on_false)
    
    @visit.register
    def _(self, expr: ex.Function) -> None:
        self.resolve_function(expr, FunctionType.FUNCTION)
        
    @visit.register
    def _(self, expr: ex.Grouping) -> None:
        self.resolve(expr.expression)
    
    @visit.register
    def _(self, expr: ex.Literal) -> None:
        pass

    @visit.register
    def _(self, expr: ex.Logical) -> None:
        self.resolve(expr.left)
        self.resolve(expr.right)
    
    @visit.register
    def _(self, expr: ex.Unary) -> None:
        self.resolve(expr.right)
    
    @visit.register
    def _(self, expr: ex.Variable) -> None:
        if self.scopes and not self.scopes[-1].get(expr.name.lexeme, True):
            lox.get_lox().error(expr.name,
                                "Can't read local variable in its own initializer")
        
        self.resolve_local(expr, expr.name)