from contextlib import contextmanager, nullcontext
from enum import Enum, auto
from functools import singledispatchmethod
from typing import Final, override

from m2_pylox import lox
from m2_pylox.tokens import Token
from m2_pylox.visitor import Visitable, Visitor
from m2_pylox import interpreter as interp, stmt as st, expr as ex

class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()
    INITIALIZER = auto()
    METHOD = auto()

class ClassType(Enum):
    NONE = auto()
    CLASS = auto()
    SUBCLASS = auto()

class VariableState(Enum):
    UNDECLARED = auto()
    DECLARED = auto()
    DEFINED = auto()
    ACCESSED = auto()

class Variable:
    name: Final[Token]
    state: VariableState

    def __init__(self, name: Token, state: VariableState) -> None:
        self.name = name
        self.state = state

class Resolver(Visitor):
    interpreter: interp.Interpreter
    scopes: list[dict[str, Variable]]
    current_function: FunctionType
    current_class: ClassType

    def __init__(self, interpreter: interp.Interpreter) -> None:
        self.interpreter = interpreter
        self.scopes = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE

    def resolve(self, node: list[st.Stmt] | st.Stmt | ex.Expr) -> None:
        match node:
            case list(statements):
                for statement in statements:
                    self.resolve(statement)
            case st.Stmt() | ex.Expr():
                node.accept(self)
            case _:
                raise NotImplementedError(f"'{node.__class__.__name__}' could not be handled by resolve()")

    def begin_scope(self, content: dict[str, Variable] | None = None) -> None:
        if content is None:
            content = {}
        self.scopes.append(content)

    def end_scope(self) -> None:
        top = self.scopes[-1]
        for var in top.values():
            if var.state is not VariableState.ACCESSED:
                lox.get_lox().error(var.name, "Unused variable")
        self.scopes.pop()
    
    @contextmanager
    def scope(self, content: dict[str, Variable] | None = None):
        try:
            self.begin_scope(content)
            yield self.scopes[-1]
        finally:
            self.end_scope()
    
    def declare(self, name: Token) -> None:
        if self.scopes:
            scope = self.scopes[-1]
            if name.lexeme in scope:
                lox.get_lox().error(name, "Already a variable with this name in this scope")

            scope[name.lexeme] = Variable(name, VariableState.DECLARED)
    
    def define(self, name: Token) -> None:
        if self.scopes:
            self.scopes[-1][name.lexeme].state = VariableState.DEFINED
    
    def resolve_local(self, expr: ex.Expr, name: Token, is_access: bool = True) -> None:
        for i, scope in enumerate(reversed(self.scopes)):
            if name.lexeme in scope:
                self.interpreter.resolve(expr, i)

                if is_access:
                    scope[name.lexeme].state = VariableState.ACCESSED
                return
    
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
    def _(self, stmt: st.Class) -> None:
        enclosing_class = self.current_class
        self.current_class = ClassType.CLASS

        self.declare(stmt.name)
        self.define(stmt.name)

        if stmt.superclass is not None:
            if stmt.name.lexeme == stmt.superclass.name.lexeme:
                lox.get_lox().error(stmt.superclass.name, "A class can't inherit from itself")

            self.current_class = ClassType.SUBCLASS
            self.resolve(stmt.superclass)

            super_scope = self.scope({
                "super": Variable(stmt.name, VariableState.ACCESSED)
            })
        else:
            super_scope = nullcontext()

        with super_scope as super_scope, self.scope() as top:
            top["this"] = Variable(stmt.name, VariableState.ACCESSED)
            for method in stmt.methods:
                declaration = FunctionType.METHOD
                self.resolve_function(method.function, declaration)
        
        self.current_class = enclosing_class

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
            if self.current_function is FunctionType.INITIALIZER:
                lox.get_lox().error(stmt.keyword, "Can't return from initializer function")
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
        self.resolve_local(expr, expr.name, is_access=False)
    
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
    def _(self, expr: ex.Get) -> None:
        self.resolve(expr.object)
    
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
    def _(self, expr: ex.Set) -> None:
        self.resolve(expr.value)
        self.resolve(expr.object)
    
    @visit.register
    def _(self, expr: ex.Super) -> None:
        if self.current_class is ClassType.NONE:
            lox.get_lox().error(expr.keyword, "Can't use 'super' outside a class")
        elif self.current_class is not ClassType.SUBCLASS:
            lox.get_lox().error(expr.keyword, "Can't use 'super' in a class with no superclass")

        self.resolve_local(expr, expr.keyword)
    
    @visit.register
    def _(self, expr: ex.This) -> None:
        if self.current_class is ClassType.NONE:
            lox.get_lox().error(expr.keyword, "Can't use 'this' outside of class")
            return

        self.resolve_local(expr, expr.keyword)

    @visit.register
    def _(self, expr: ex.Unary) -> None:
        self.resolve(expr.right)
    
    @visit.register
    def _(self, expr: ex.Variable) -> None:
        if self.scopes:
            top = self.scopes[-1]
            var = top.get(expr.name.lexeme)
            if var is not None and var.state is VariableState.DECLARED:
                lox.get_lox().error(expr.name,
                                "Can't read local variable in its own initializer")
        
        self.resolve_local(expr, expr.name)