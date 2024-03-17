from functools import singledispatchmethod
from typing import override

import m2_pylox.expr as ex
from m2_pylox.visitor import Visitor, Visitable

class AstPrinter(Visitor[str]):
    def print(self, expr: ex.Expr):
        return expr.accept(self)

    @singledispatchmethod
    @override
    def visit(self, _: Visitable) -> str:
        raise NotImplementedError()
    
    @visit.register
    def _(self, expr: ex.Binary) -> str:
        return self.parenthesize(expr.operator.lexeme, expr.left, expr.right)

    @visit.register
    def _(self, expr: ex.Grouping) -> str:
        return self.parenthesize("group", expr.expression)

    @visit.register
    def _(self, expr: ex.Literal) -> str:
        if expr.value is not None:
            return str(expr.value)
        else:
            return "nil"

    @visit.register
    def _(self, expr: ex.Unary) -> str:
        return self.parenthesize(expr.operator.lexeme, expr.right)

    def parenthesize(self, name: str, *exprs: ex.Expr) -> str:
        content = " ".join([expr.accept(self) for expr in exprs])

        return f"({name} {content})"


class AstRPNPrinter(Visitor[str]):
    def print(self, expr: ex.Expr):
        return expr.accept(self)

    @singledispatchmethod
    @override
    def visit(self, _: Visitable) -> str:
        raise NotImplementedError()
    
    @visit.register
    def _(self, expr: ex.Binary) -> str:
        return " ".join([
            expr.left.accept(self),
            expr.right.accept(self),
            expr.operator.lexeme
            ])

    @visit.register
    def _(self, expr: ex.Grouping) -> str:
        return expr.expression.accept(self)

    @visit.register
    def _(self, expr: ex.Literal) -> str:
        if expr.value is not None:
            return str(expr.value)
        else:
            return "nil"

    @visit.register
    def _(self, expr: ex.Unary) -> str:
        # This implementation prefixes unary operators with 'u'
        return " ".join([
            expr.right.accept(self),
            "u" + expr.operator.lexeme
        ])


if __name__ == '__main__':
    from m2_pylox.tokens import Token, TokenType as TT
    expression = ex.Binary(
        ex.Unary(
            Token(TT.MINUS, '-', 1),
            ex.Literal(123)
        ),
        Token(TT.STAR, "*", 1),
        ex.Grouping(
            ex.Literal(45.67)
        )
    )

    print(AstPrinter().print(expression))

    rpn_expression = ex.Binary(
        ex.Binary(
            ex.Literal(1),
            Token(TT.PLUS, "+", 1),
            ex.Literal(2),
        ),
        Token(TT.STAR, "*", 1),
        ex.Binary(
            ex.Literal(4),
            Token(TT.MINUS, "-", 1),
            ex.Literal(3),
        )
    )

    print(AstRPNPrinter().print(rpn_expression))