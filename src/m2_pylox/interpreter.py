from functools import singledispatchmethod
from typing import Any, Never, override, Final

from m2_pylox.environment import Environment
import m2_pylox.expr as ex
from m2_pylox import lox
from m2_pylox import function as fn
from m2_pylox import loxclass as cl
from m2_pylox import stmt as st
from m2_pylox.tokens import Token, TokenType as TT, TokenGroup as TG
from m2_pylox.visitor import Visitor, Visitable


class LoxRuntimeError(Exception):
    token: Final[Token | None]

    def __init__(self, token: Token | None, message: str) -> None:
        super().__init__(message)
        self.token = token

class LoxBreak(Exception):
    pass

class LoxContinue(Exception):
    pass

class Interpreter(Visitor[Any]):
    globals: Environment
    environment: Environment
    locals: dict[ex.Expr, int]
    _uninitialized = object()

    def __init__(self) -> None:
        self.globals = Environment()
        self.environment = self.globals
        self.locals = {}

        self.register_native(fn.clock)
        self.register_native(fn.randint)
        self.register_native(fn.lox_input)
    
    def register_native(self, function: fn.NativeFunction, name: str | None = None):
        if name is None:
            name = function.name
        
        self.globals.define(name, function)

    def interpret(self, statements: list[st.Stmt]) -> None:
        try:
            for statement in statements:
                self.execute(statement)
        except LoxRuntimeError as error:
            lox.get_lox().runtime_error(error)

    @singledispatchmethod
    @override
    def visit(self, obj: Visitable) -> Any:
        raise NotImplementedError(f"'{obj.__class__.__name__}' could not be dispatched by visit()")

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
        var = self.lookup_variable(expr.name, expr)
        var = self.environment.get(expr.name)
        if var is self._uninitialized:
            raise LoxRuntimeError(expr.name, f"Access of uninitialized variable '{expr.name.lexeme}'")

        return var
    
    @visit.register
    def _(self, expr: ex.Assign) -> Any:
        value = self.evaluate(expr.value)

        distance = self.locals.get(expr)
        if distance is not None:
            self.environment.assign_at(distance, expr.name, value)
        else:
            self.globals.assign(expr.name, value)
        return value

    @visit.register
    def _(self, expr: ex.Logical) -> Any:
        left = self.evaluate(expr.left)

        if expr.operator.type == TT.OR:
            if self.is_truthy(left):
                return left
        else:
            if not self.is_truthy(left):
                return left
        
        return self.evaluate(expr.right)
    
    @visit.register
    def _(self, expr: ex.Call) -> Any:
        callee = self.evaluate(expr.callee)

        arguments = []
        for argument in expr.arguments:
            arguments.append(self.evaluate(argument))
        
        if not isinstance(callee, fn.LoxCallable):
            raise LoxRuntimeError(expr.paren, "Can only call functions and classes")

        function = callee

        if len(arguments) != function.arity():
            raise LoxRuntimeError(expr.paren,
            f"Expected {function.arity()} arguments but got {len(arguments)}")

        return function.call(self, arguments)
    
    @visit.register
    def _(self, expr: ex.Function) -> Any:
        return fn.LoxFunction(None, expr, self.environment)
    
    @visit.register
    def _(self, expr: ex.Get) -> Any:
        obj = self.evaluate(expr.object)
        if isinstance(obj, cl.LoxInstance):
            result = obj.get(expr.name)
            
            if isinstance(result, fn.LoxFunction) and fn.Flags.Getter in result.flags:
                result = result.call(self, [])
            
            return result
        
        raise LoxRuntimeError(expr.name, "Cannot get property, not an instance")
    
    @visit.register
    def _(self, expr: ex.Set) -> Any:
        obj = self.evaluate(expr.object)
        
        if not isinstance(obj, cl.LoxInstance):
            raise LoxRuntimeError(expr.name, "Cannot set property, not an instance")
        
        value = self.evaluate(expr.value)
        obj.set(expr.name, value)
        return value
    
    @visit.register
    def _(self, expr: ex.Super) -> Any:
        distance = self.locals.get(expr)
        
        if distance is not None:
            superclass: cl.LoxClass = self.environment.get_at(distance, "super")
            obj: cl.LoxInstance = self.environment.get_at(distance - 1, "this")
            method = superclass.find_method(expr.method.lexeme)

            if method is None:
                raise LoxRuntimeError(expr.method, f"Undefined property '{expr.method.lexeme}'")

            return method.bind(obj)
        else:
            raise Exception("Mismatch between resolved and runtime scopes")


    
    @visit.register
    def _(self, expr: ex.This) -> Any:
        return self.lookup_variable(expr.keyword, expr)
    
    @visit.register
    def _(self, stmt: st.ControlFlow) -> Never:
        match stmt.keyword.type:
            case TT.BREAK:
                raise LoxBreak()
            case TT.CONTINUE:
                raise LoxContinue()
            case _:
                raise NotImplementedError(f"Cannot handle '{stmt.keyword.lexeme}'")
    
    @visit.register
    def _(self, stmt: st.Class) -> None:
        superclass = None
        if stmt.superclass is not None:
            superclass = self.evaluate(stmt.superclass)
            if not isinstance(superclass, cl.LoxClass):
                raise LoxRuntimeError(stmt.superclass.name, "Superclass must be a class")

        self.environment.define(stmt.name.lexeme, None)

        if stmt.superclass is not None:
            self.environment = Environment(self.environment)
            self.environment.define("super", superclass)

        methods, class_methods = self.use_traits(stmt.traits)

        for cmethod in stmt.class_methods:
            function = fn.LoxFunction(cmethod.name.lexeme, cmethod.function, self.environment)
            class_methods[cmethod.name.lexeme] = function
        
        metaclass = cl.LoxClass(
            f'{stmt.name.lexeme} meta',
            None,
            superclass and superclass.klass,
            class_methods
            )

        for method in stmt.methods:
            flags = fn.Flags(0)
            if method.name.lexeme == 'init':
                flags |= fn.Flags.Initializer
            if isinstance(method, st.Getter):
                flags |= fn.Flags.Getter

            function = fn.LoxFunction(method.name.lexeme, method.function, self.environment, flags)
            methods[method.name.lexeme] = function

        klass = cl.LoxClass(stmt.name.lexeme, metaclass, superclass, methods)

        if superclass is not None:
            if self.environment.enclosing is None:
                raise Exception("Invalid super environment")

            self.environment = self.environment.enclosing
    
        self.environment.assign(stmt.name, klass)

    @visit.register
    def _(self, stmt: st.Expression) -> None:
        self.evaluate(stmt.expression)
    
    @visit.register
    def _(self, stmt: st.For) -> None:
        if stmt.initializer is not None:
            self.execute(stmt.initializer)
        while stmt.condition is None or self.is_truthy(self.evaluate(stmt.condition)):
            try:
                self.execute(stmt.body)
            except LoxBreak:
                break
            except LoxContinue:
                continue
            finally:
                if stmt.increment is not None:
                    self.evaluate(stmt.increment)
    
    @visit.register
    def _(self, stmt: st.Function) -> None:
        function = fn.LoxFunction(stmt.name.lexeme, stmt.function, self.environment)
        self.environment.define(stmt.name.lexeme, function)
    
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
    def _(self, stmt: st.Return) -> Never:
        value = None
        if stmt.value is not None:
            value = self.evaluate(stmt.value)

        raise fn.Return(value)

    @visit.register
    def _(self, stmt: st.Trait) -> None:
        self.environment.define(stmt.name.lexeme, None)

        methods, class_methods = self.use_traits(stmt.traits)

        for cmethod in stmt.class_methods:
            if cmethod.name.lexeme in class_methods:
                raise LoxRuntimeError(cmethod.name, f"A previously used trait already provides class method '{cmethod.name.lexeme}'")
            function = fn.LoxFunction(cmethod.name.lexeme, cmethod.function, self.environment)
            class_methods[cmethod.name.lexeme] = function
        
        for method in stmt.methods:
            if method.name.lexeme in methods:
                raise LoxRuntimeError(method.name, f"A previously used trait already provides method '{method.name.lexeme}'")

            flags = fn.Flags(0)
            if method.name.lexeme == 'init':
                flags |= fn.Flags.Initializer
            if isinstance(method, st.Getter):
                flags |= fn.Flags.Getter

            function = fn.LoxFunction(method.name.lexeme, method.function, self.environment, flags)
            methods[method.name.lexeme] = function

        trait = cl.LoxTrait(stmt.name.lexeme, methods, class_methods)

        self.environment.assign(stmt.name, trait)
    
    @visit.register
    def _(self, stmt: st.Var) -> None:
        value = self._uninitialized
        if stmt.initializer:
            value = self.evaluate(stmt.initializer)
        
        self.environment.define(stmt.name.lexeme, value)
    
    @visit.register
    def _(self, stmt: st.While) -> None:
        while self.is_truthy(self.evaluate(stmt.condition)):
            try:
                self.execute(stmt.body)
            except LoxBreak:
                break
            except LoxContinue:
                continue

    @visit.register
    def _(self, stmt: st.Block) -> None:
        self.execute_block(stmt.statements, Environment(self.environment))
    
    def is_truthy(self, obj: Any) -> bool:
        return obj not in {None, False}
    
    def evaluate(self, expr: ex.Expr) -> Any:
        return expr.accept(self)
    
    def execute(self, stmt: st.Stmt) -> None:
        stmt.accept(self)
    
    def resolve(self, expr: ex.Expr, depth: int) -> None:
        self.locals[expr] = depth

    def lookup_variable(self, name: Token, expr: ex.Expr) -> Any:
        distance = self.locals.get(expr)
        if distance is not None:
            return self.environment.get_at(distance, name.lexeme)
        else:
            return self.globals.get(name)

    
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

    def use_traits(self, traits: list[ex.Variable]) -> tuple[dict[str, fn.LoxFunction], dict[str, fn.LoxFunction]]:
        methods: dict[str, fn.LoxFunction] = {}
        class_methods: dict[str, fn.LoxFunction] = {}

        for trait_var in traits:
            trait = self.evaluate(trait_var)
            if not isinstance(trait, cl.LoxTrait):
                raise LoxRuntimeError(trait_var.name, f"'{trait_var.name.lexeme}' is not a trait")
            
            for method_name in trait.methods:
                if method_name in methods:
                    raise LoxRuntimeError(trait_var.name, f"A previously used trait already provides method '{method_name}'")
                
            methods |= trait.methods
            
            for method_name in trait.class_methods:
                if method_name in class_methods:
                    raise LoxRuntimeError(trait_var.name, f"A previously used trait already provides class method '{method_name}'")
                
            class_methods |= trait.class_methods

        return methods, class_methods