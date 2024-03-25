from contextlib import contextmanager
from typing import Callable

import m2_pylox.expr as ex
from m2_pylox import lox
from m2_pylox import stmt as st
from m2_pylox.tokens import Token, TokenType as TT, TokenGroup as TG


class ParseError(Exception):
    pass


class ParserContext:
    loop_depth: int

    def __init__(self):
        self.loop_depth = 0


class Parser:
    def __init__(self, tokens: list[Token] | None = None) -> None:
        if tokens is None:
            tokens = []
        self.tokens = tokens
        self.current = 0

        self.context_stack = [ParserContext()]
    
    def current_context(self) -> ParserContext:
        return self.context_stack[-1]
    
    def push_context(self) -> None:
        self.context_stack.append(ParserContext())
    
    def pop_context(self) -> ParserContext:
        if len(self.context_stack) == 1:
            raise Exception("Cannot pop root context from parser")
        
        return self.context_stack.pop()
    
    @contextmanager
    def loop_context(self):
        context = self.current_context()
        try:
            context.loop_depth += 1
            yield
        finally:
            context.loop_depth -= 1

    def parse(self) -> list[st.Stmt]:
        statements: list[st.Stmt] = []
        while not self.at_end():
            decl = self.declaration()
            if decl is not None:
                statements.append(decl)

        return statements
    
    def declaration(self) -> st.Stmt | None:
        try:
            if self.match(TT.VAR):
                return self.var_declaration()
            
            return self.statement()
        except ParseError:
            self.synchronize()
            return None
    
    def var_declaration(self) -> st.Stmt:
        name = self.consume(TT.IDENTIFIER, "Expected variable name")

        initializer = None
        if self.match(TT.EQUAL):
            initializer = self.expression()
        
        self.consume(TT.SEMICOLON, "Expected ';' after variable declaration")
        return st.Var(name, initializer)
    
    def while_statement(self) -> st.Stmt:
        with self.loop_context():
            self.consume(TT.LEFT_PAREN, "Expected '(' after 'while'")
            condition = self.expression()
            self.consume(TT.RIGHT_PAREN, "Expected ')' after condition")
            body = self.statement()

            return st.While(condition, body)
    
    def statement(self) -> st.Stmt:
        if self.match(TT.BREAK):
            return self.break_statement()
        if self.match(TT.FOR):
            return self.for_statement()
        if self.match(TT.IF):
            return self.if_statement()
        if self.match(TT.PRINT):
            return self.print_statement()
        if self.match(TT.WHILE):
            return self.while_statement()
        if self.match(TT.LEFT_BRACE):
            return st.Block(self.block())

        return self.expression_statement()

    def break_statement(self) -> st.Stmt:
        previous = self.previous()
        if self.current_context().loop_depth > 0:
            self.consume(TT.SEMICOLON, f"Expected ';' after '{previous.lexeme}'")
            return st.Break()
        else:
            raise self.error(self.previous(), "Control flow statement used outside loop")
    
    def for_statement(self) -> st.Stmt:
        with self.loop_context():
            self.consume(TT.LEFT_PAREN, "Expected '(' after 'for'")

            if self.match(TT.SEMICOLON):
                initializer = None
            elif self.match(TT.VAR):
                initializer = self.var_declaration()
            else:
                initializer = self.expression_statement()
            
            condition = None
            if not self.check(TT.SEMICOLON):
                condition = self.expression()

            self.consume(TT.SEMICOLON, "Expected ';' after loop condition")

            increment = None
            if not self.check(TT.RIGHT_PAREN):
                increment = self.expression()

            self.consume(TT.RIGHT_PAREN, "Expected ')' after for clauses")

            body = self.statement()

            if increment is not None:
                body = st.Block([body, st.Expression(increment)])
            
            if condition is None:
                condition = ex.Literal(True)

            body = st.While(condition, body)

            if initializer is not None:
                body = st.Block([initializer, body])

            return body
    
    def if_statement(self) -> st.Stmt:
        self.consume(TT.LEFT_PAREN, "Expected '(' after 'if'")
        condition = self.expression()
        self.consume(TT.RIGHT_PAREN, "Expected ')' after if condition")

        then_branch = self.statement()
        else_branch = None
        if self.match(TT.ELSE):
            else_branch = self.statement()
        
        return st.If(condition, then_branch, else_branch)
    
    def print_statement(self) -> st.Stmt:
        value = self.expression()
        self.consume(TT.SEMICOLON, "Expected ';' after value")
        return st.Print(value)
    
    def expression_statement(self) -> st.Stmt:
        expr = self.expression()
        self.consume(TT.SEMICOLON, "Expected ';' after expression")
        return st.Expression(expr)
    
    def block(self) -> list[st.Stmt]:
        statements: list[st.Stmt] = []

        while not self.check(TT.RIGHT_BRACE) and not self.at_end():
            decl = self.declaration()
            if decl is not None:
                statements.append(decl)
        
        self.consume(TT.RIGHT_BRACE, "Expected '}' after block")
        return statements

    
    def expression(self) -> ex.Expr:
        return self.comma()

    def comma(self) -> ex.Expr:
        return self.handle_left_binary(self.assignment, TT.COMMA)
    
    def assignment(self) -> ex.Expr:
        expr = self.conditional()

        if self.match(TT.EQUAL):
            equals = self.previous()
            value = self.assignment()

            if isinstance(expr, ex.Variable):
                name = expr.name
                return ex.Assign(name, value)
            
            self.error(equals, "Invalid assignment target")

        return expr

    def conditional(self) -> ex.Expr:
        condition = self.logical_or()

        if self.match(TT.QUESTION):
            on_true = self.expression()
            self.consume(TT.COLON, "Expected ':' after expression")
            on_false = self.conditional()
            return ex.Conditional(condition, on_true, on_false)
        
        return condition

    def logical_or(self) -> ex.Expr:
        return self.handle_left_binary(self.logical_and, TT.OR, expr_type=ex.Logical)
    
    def logical_and(self) -> ex.Expr:
        return self.handle_left_binary(self.equality, TT.AND, expr_type=ex.Logical)

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
        
        return self.call()
    
    def call(self) -> ex.Expr:
        expr = self.primary()

        while True:
            if self.match(TT.LEFT_PAREN):
                expr = self.finish_call(expr)
            else:
                break
    
        return expr

    def finish_call(self, callee: ex.Expr) -> ex.Expr:
        arguments: list[ex.Expr] = []

        if not self.check(TT.RIGHT_PAREN):
            # Use an operator with lower precedence, since comma breaks function arguments
            arguments.append(self.assignment())
            while self.match(TT.COMMA):
                if len(arguments) >= 255:
                    self.error(self.peek(), "Can't have more than 255 arguments")
                arguments.append(self.assignment())
        
        paren = self.consume(TT.RIGHT_PAREN, "Expected ')' after arguments")

        return ex.Call(callee, paren, arguments)

    def primary(self) -> ex.Expr:
        if self.match(TT.FALSE):
            return ex.Literal(False)
        elif self.match(TT.TRUE):
            return ex.Literal(True)
        elif self.match(TT.NIL):
            return ex.Literal(None)
        
        if self.match(TT.NUMBER, TT.STRING):
            return ex.Literal(self.previous().literal)
        
        if self.match(TT.IDENTIFIER):
            return ex.Variable(self.previous())

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

    def handle_left_binary(
            self,
            matcher: Callable[[], ex.Expr],
            *token_list: TT, 
            expr_type: type = ex.Binary
            ) -> ex.Expr:
        expr = matcher()

        while self.match(*token_list):
            operator = self.previous()
            right = matcher()
            expr = expr_type(expr, operator, right)
        
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