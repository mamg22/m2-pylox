from typing import Any, Self

from m2_pylox import interpreter as interp
from m2_pylox import function as fn
from m2_pylox.tokens import Token


class LoxInstance:
    klass: 'LoxClass | None'
    fields: dict[str, Any]

    def __init__(self, klass: 'LoxClass | None') -> None:
        self.klass = klass
        self.fields = {}
    
    def __str__(self) -> str:
        return f"<instance {self.klass}>"
    
    def get(self, name: Token) -> Any:
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
        
        if self.klass is not None:
            method = self.klass.find_method(name.lexeme)
            if method is not None:
                return method.bind(self)
        
        raise interp.LoxRuntimeError(name, f"Undefined property '{name.lexeme}'")
    
    def set(self, name: Token, value: Any) -> None:
        self.fields[name.lexeme] = value


class LoxClass(LoxInstance):
    name: str
    superclass: Self | None
    methods: dict[str, 'fn.LoxFunction']

    def __init__(
        self, name: str, metaclass: Self | None, superclass: Self | None, methods: dict[str, "fn.LoxFunction"]
    ) -> None:
        super().__init__(metaclass)

        self.name = name
        self.superclass = superclass
        self.methods = methods
    
    def __str__(self) -> str:
        return f"<class {self.name}>"
    
    def call(self, interpreter: 'interp.Interpreter', arguments: list[Any]) -> Any:
        instance = LoxInstance(self)

        initializer = self.find_method('init')
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)

        return instance
    
    def arity(self) -> int:
        initializer = self.find_method('init')
        if initializer is not None:
            return initializer.arity()
        return 0
    
    def find_method(self, name: str) -> 'fn.LoxFunction | None':
        method = self.methods.get(name)
        if method is None and self.superclass is not None:
            return self.superclass.find_method(name)
        return method

class LoxTrait:
    name: str
    methods: dict[str, 'fn.LoxFunction']
    class_methods: dict[str, 'fn.LoxFunction']

    def __init__(
        self,
        name: str,
        methods: dict[str, "fn.LoxFunction"],
        class_methods: dict[str, "fn.LoxFunction"],
    ) -> None:
        self.name = name
        self.methods = methods
        self.class_methods = class_methods

    def __str__(self) -> str:
        return f"<trait {self.name}>"