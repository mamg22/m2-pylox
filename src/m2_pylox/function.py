import random
import time
from typing import Callable, Protocol, runtime_checkable, Any, Never

from m2_pylox import interpreter as interp

@runtime_checkable
class LoxCallable(Protocol):
    def call(self, interpreter: 'interp.Interpreter', arguments: list) -> Any:
        ...
    
    def arity(self) -> int:
        ...

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