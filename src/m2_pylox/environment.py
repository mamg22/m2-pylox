from typing import Any, Self

from m2_pylox import interpreter as interp
from m2_pylox.tokens import Token

class Environment:
    values: dict[str, Any]
    enclosing: Self | None

    def __init__(self, enclosing: Self | None = None) -> None:
        self.values = {}
        self.enclosing = enclosing
    
    def define(self, name: str, value: Any) -> None:
        self.values[name] = value
    
    def ancestor(self, distance: int) -> Self:
        environment = self
        for _ in range(distance):
            if environment.enclosing is None:
                raise ValueError("Invalid distance")
            environment = environment.enclosing

        return environment

    def get(self, name: Token) -> Any:
        if name.lexeme in self.values:
            return self.values[name.lexeme]
        elif self.enclosing is not None:
            return self.enclosing.get(name)
        else:
            raise interp.LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'")
    
    def get_at(self, distance: int, name: str) -> Any:
        return self.ancestor(distance).values.get(name)
        
    def assign(self, name: Token, value: Any) -> None:
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
        elif self.enclosing is not None:
            self.enclosing.assign(name, value)
        else:
            raise interp.LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'")
    
    def assign_at(self, distance: int, name: Token, value: Any) -> None:
        self.ancestor(distance).values[name.lexeme] = value