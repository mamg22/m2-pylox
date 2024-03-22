from functools import singledispatchmethod
from typing import Any, override, Final

from m2_pylox.environment import Environment
import m2_pylox.expr as ex
from m2_pylox import lox
from m2_pylox import stmt as st
from m2_pylox.tokens import Token, TokenType as TT, TokenGroup as TG
from m2_pylox.visitor import Visitor, Visitable


class LoxRuntimeError(Exception):
    token: Final[Token]

    def __init__(self, token: Token, message: str) -> None:
        super().__init__(message)
        self.token = token

class Interpreter(Visitor[Any]):
    environment: Environment
    _uninitialized = object()

    def __init__(self) -> None:
        self.environment = Environment()

    def interpret(self, statements: list[st.Stmt]) -> None:
        try:
            for statement in statements:
                self.execute(statement)
        except LoxRuntimeError as error:
            lox.get_lox().runtime_error(error)

    @singledispatchmethod
    @override
    def visit(self, _: Visitable) -> Any:
        raise NotImplementedError()

    @visit.register
    def _(self, expr: ex.Literal) -> Any:
        return expr.value
    
    @visit.register
    def _(self, expr: ex.Unary) -> Any:
        right = self.evaluate(expr.right)

        match expr.operator.type:
            case TT.BANG:
                return not self.is_truthy(right)
            case TT.MINUS:
                self.check_number_operands(expr.operator, right)
                return -float(right)

            case _:
                return None
    
    @visit.register
    def _(self, expr: ex.Binary) -> Any:
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)

        if expr.operator.type in TG.Factor | {TT.MINUS}:
            self.check_number_operands(expr.operator, left, right)
        elif expr.operator.type in TG.Comparison:
            if not type(left) == type(right):
                raise LoxRuntimeError(expr.operator,
                "Cannot compare, expressions are of different types")
            elif not isinstance(left, float | str | bool):
                raise LoxRuntimeError(expr.operator,
                "Cannot compare, type is not orderable")
                

        match expr.operator.type:
            case TT.BANG_EQUAL:
                return left != right
            case TT.EQUAL_EQUAL:
                return left == right
            case TT.GREATER:
                return left > right
            case TT.GREATER_EQUAL:
                return left >= right
            case TT.LESS:
                return left < right
            case TT.LESS_EQUAL:
                return left <= right
            case TT.MINUS:
                return left - right
            case TT.SLASH:
                if right == 0:
                    raise LoxRuntimeError(expr.operator,
                                          "Division by zero")
                return left / right
            case TT.STAR:
                return left * right
            case TT.PLUS:
                if (
                    isinstance(left, (float, str)) and
                    type(left) == type(right)
                ):
                    return left + right
                elif isinstance(left, str) or isinstance(right, str):
                    return self.stringify(left) + self.stringify(right)
                else:
                    raise LoxRuntimeError(expr.operator,
                                          "Operands must be two numbers or two strings")
            case TT.COMMA:
                return right
            case _:
                return None

    @visit.register
    def _(self, expr: ex.Grouping) -> Any:
        return self.evaluate(expr.expression)
    
    @visit.register
    def _(self, expr: ex.Conditional) -> Any:
        cond = self.evaluate(expr.condition)

        if self.is_truthy(cond):
            return self.evaluate(expr.on_true)
        else:
            return self.evaluate(expr.on_false)
    
    @visit.register
    def _(self, expr: ex.Variable) -> Any:
        var = self.environment.get(expr.name)
        if var is self._uninitialized:
            raise LoxRuntimeError(expr.name, f"Access of uninitialized variable '{expr.name.lexeme}'")

        return var
    
    @visit.register
    def _(self, expr: ex.Assign) -> Any:
        value = self.evaluate(expr.value)
        self.environment.assign(expr.name, value)
        return value

    @visit.register
    def _(self, stmt: st.Expression) -> None:
        self.evaluate(stmt.expression)
    
    @visit.register
    def _(self, stmt: st.If) -> None:
        if self.is_truthy(self.evaluate(stmt.condition)):
            self.execute(stmt.then_branch)
        elif stmt.else_branch is not None:
            self.execute(stmt.else_branch)
    
    @visit.register
    def _(self, stmt: st.Print) -> None:
        value = self.evaluate(stmt.expression)
        print(self.stringify(value))
    
    @visit.register
    def _(self, stmt: st.Var) -> None:
        value = self._uninitialized
        if stmt.initializer:
            value = self.evaluate(stmt.initializer)
        
        self.environment.define(stmt.name.lexeme, value)

    @visit.register
    def _(self, stmt: st.Block) -> None:
        self.execute_block(stmt.statements, Environment(self.environment))
    
    def is_truthy(self, obj: Any) -> bool:
        return obj not in {None, False}
    
    def evaluate(self, expr: ex.Expr) -> Any:
        return expr.accept(self)
    
    def execute(self, stmt: st.Stmt) -> None:
        stmt.accept(self)
    
    def execute_block(self, statements: list[st.Stmt], environment: Environment) -> None:
        previous = self.environment

        try:
            self.environment = environment

            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous
    
    @staticmethod
    def is_number(num: Any) -> bool:
        return isinstance(num, float)

    def check_number_operands(self, operator: Token, *operands: Any) -> None:
        if not all(map(self.is_number, operands)):
            plural = "s" if len(operands) > 1 else ""

            raise LoxRuntimeError(operator, f"Operand{plural} must be a number.")
    
    def stringify(self, obj: Any) -> str:
        match obj:
            case None:
                return "nil"
            case bool(b):
                return str(b).lower()
            case float(num) if num.is_integer():
                return str(int(num))
            case _:
                return str(obj)
