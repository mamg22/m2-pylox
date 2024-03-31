import random
import time
from typing import Callable, Protocol, Self, runtime_checkable, Any, Never

from m2_pylox.environment import Environment
import m2_pylox.expr as ex
import m2_pylox.stmt as st
from m2_pylox import loxclass as cl
from m2_pylox import interpreter as interp

@runtime_checkable
class LoxCallable(Protocol):
    def call(self, interpreter: 'interp.Interpreter', arguments: list) -> Any:
        ...
    
    def arity(self) -> int:
        ...
    


class Return(Exception):
    value: Any

    def __init__(self, value: Any):
        self.value = value

class LoxFunction:
    name: str | None
    declaration: ex.Function
    closure: Environment
    is_initializer: bool

    def __init__(self,
                 name: str | None,
                 declaration: ex.Function,
                 closure: Environment,
                 is_initializer: bool = False
                 ) -> None:
        self.name = name
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer
    
    def call(self, interpreter: 'interp.Interpreter', arguments: list) -> Any:
        environment = Environment(self.closure)

        for param, arg in zip(self.declaration.params, arguments):
            environment.define(param.lexeme, arg)
        
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except Return as ret:
            return ret.value
        finally:
            if self.is_initializer:
                return self.closure.get_at(0, 'this')
        
        return None
    
    def arity(self) -> int:
        return len(self.declaration.params)
    
    def bind(self, instance: cl.LoxInstance) -> 'LoxFunction':
        environment = Environment(self.closure)
        environment.define("this", instance)
        return LoxFunction(self.name, self.declaration, environment, self.is_initializer)

    def __str__(self) -> str:
        if self.name is not None:
            return f"<fn {self.name}>"
        else:
            return "<fn>"
    

class NativeFunction:
    def __init__(self, name: str, arity: int, function: Callable) -> None:
        self.name = name
        self._arity = arity
        self.function = function

    def call(self, interpreter: 'interp.Interpreter', arguments: list) -> Any:
        return self.function(interpreter, arguments)

    def arity(self) -> int:
        return self._arity

    def __str__(self) -> str:
        return f"<native fn: {self.name}>"


type LoxFunctionCall = Callable[[interp.Interpreter, list], Any]

def native_fn(*, arity: int, name: str | None = None) -> Callable[[LoxFunctionCall], NativeFunction]:
    def native_fn_decorator(fn: LoxFunctionCall) -> NativeFunction:
        nonlocal name
        if name is None:
            name = fn.__name__

        return NativeFunction(name, arity, fn)

    return native_fn_decorator

@native_fn(arity=0)
def clock(interpreter, args: list[Never]) -> float:
    return time.time()

@native_fn(arity=2)
def randint(interpreter: 'interp.Interpreter', args: list[float]) -> int:
    randmin, randmax = args
    if not (interpreter.is_number(randmin) and interpreter.is_number(randmax)):
        raise interp.LoxRuntimeError(None, "Invalid arguments for randint(), expected (number, number)")

    return random.randint(int(randmin), int(randmax))

@native_fn(arity=1, name="input")
def lox_input(interpreter: 'interp.Interpreter', args: list[str]) -> str:
    prompt = args[0]
    if not isinstance(prompt, str):
        raise interp.LoxRuntimeError(None, "Invalid arguments for prompt(), expected (string)")

    return input(prompt)