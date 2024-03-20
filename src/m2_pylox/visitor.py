from abc import ABC, abstractmethod

class Visitor[T](ABC):
    @abstractmethod
    def visit(self, visited: 'Visitable[T]') -> T:
        ...

class Visitable[T]:
    def accept(self, visitor: Visitor[T]) -> T:
        return visitor.visit(self)