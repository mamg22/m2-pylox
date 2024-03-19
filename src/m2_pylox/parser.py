import m2_pylox.expr as ex
from m2_pylox import lox
from m2_pylox.tokens import Token, TokenType as TT, TokenGroup as TG


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token] | None = None) -> None:
        if tokens is None:
            tokens = []
        self.tokens = tokens
        self.current = 0

    def parse(self) -> ex.Expr | None:
        try:
            return self.expression()
        except ParseError:
            return None
    
    def expression(self) -> ex.Expr:
        return self.comma()

    def comma(self) -> ex.Expr:
        return self.handle_left_binary(self.conditional, TT.COMMA)

    def conditional(self) -> ex.Expr:
        condition = self.equality()

        if self.match(TT.QUESTION):
            on_true = self.expression()
            self.consume(TT.COLON, "Expected ':' after expression")
            on_false = self.conditional()
            return ex.Conditional(condition, on_true, on_false)
        
        return condition


    def equality(self) -> ex.Expr:
        return self.handle_left_binary(self.comparison, *TG.Equality)
    
    def comparison(self) -> ex.Expr:
        return self.handle_left_binary(self.term, *TG.Comparison)

    def term(self) -> ex.Expr:
        return self.handle_left_binary(self.factor, *TG.Term)
    

    def factor(self) -> ex.Expr:
        return self.handle_left_binary(self.unary, *TG.Factor)

    def unary(self) -> ex.Expr:
        if self.match(TT.BANG, TT.MINUS):
            operator = self.previous()
            right = self.unary()
            return ex.Unary(operator, right)
        
        return self.primary()

    def primary(self) -> ex.Expr:
        if self.match(TT.FALSE):
            return ex.Literal(False)
        elif self.match(TT.TRUE):
            return ex.Literal(True)
        elif self.match(TT.NIL):
            return ex.Literal(None)
        
        if self.match(TT.NUMBER, TT.STRING):
            return ex.Literal(self.previous().literal)

        if self.match(TT.LEFT_PAREN):
            expr = self.expression()
            self.consume(TT.RIGHT_PAREN, "Expected ')' after expression.")
            return ex.Grouping(expr)

        # Error productions
        for token_group, matcher in (
            (TG.Equality, self.comparison),
            (TG.Comparison, self.term),
            (TG.Term, self.factor),
            (TG.Factor, self.primary),
            ({TT.COMMA}, self.conditional),
        ):
            if self.match(*token_group):
                tok = self.previous()
                self.error(tok, "Expected expression before operator")
                matcher()
                return ex.Expr()

        raise self.error(self.peek(), "Expected expression.")

    def handle_left_binary(self, matcher, *token_list) -> ex.Expr:
        expr = matcher()

        while self.match(*token_list):
            operator = self.previous()
            right = self.handle_left_binary(matcher, *token_list)
            expr = ex.Binary(expr, operator, right)
        
        return expr

    
    def match(self, *types: TT) -> bool:
        for type in types:
            if self.check(type):
                self.advance()
                return True
        
        return False

    def consume(self, type: TT, message: str) -> Token:
        if self.check(type):
            return self.advance()

        raise self.error(self.peek(), message)

    def check(self, type: TT) -> bool:
        if self.at_end():
            return False
        
        return self.peek().type == type

    def advance(self) -> Token:
        if not self.at_end():
            self.current += 1
        
        return self.previous()

    def at_end(self) -> bool:
        return self.peek().type == TT.EOF

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def error(self, token: Token, message: str) -> ParseError:
        lox.get_lox().error(token, message)
        return ParseError()

    def synchronize(self) -> None:
        self.advance()

        while not self.at_end():
            if self.previous().type == TT.SEMICOLON:
                return

            if self.peek().type in {
                TT.CLASS,
                TT.FUN,
                TT.VAR,
                TT.FOR,
                TT.IF,
                TT.WHILE,
                TT.PRINT,
                TT.RETURN,
            }:
                return

            self.advance()