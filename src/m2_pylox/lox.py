import os
import sys

from m2_pylox.ast_printer import AstPrinter
from m2_pylox.tokens import Token, TokenType as TT


class Lox:
    def __init__(self) -> None:
        self.had_error = False

    def run_file(self, path: str | os.PathLike) -> None:
        with open(path, "r") as file:
            prog = file.read()
            self.run(prog)

    def run_prompt(self) -> None:
        try:
            while line := input("> "):
                self.run(line)
                self.had_error = False
        except EOFError:
            print("Bye.")

    def run(self, source: str) -> None:
        from m2_pylox.scanner import Scanner
        from m2_pylox.parser import Parser

        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        parser = Parser(tokens)
        expression = parser.parse()

        if self.had_error or expression is None:
            return

        print(AstPrinter().print(expression))

    def error(self, where: int | Token, message: str) -> None:
        if isinstance(where, int):
            self.report(where, "", message)
        else:
            if where.type == TT.EOF:
                self.report(where.line, " at end", message)
            else:
                self.report(where.line, f" at '{where.lexeme}'", message)

    def report(self, line: int, where: str, message: str) -> None:
        print(f"[line {line}] Error{where}: {message}", file=sys.stderr)
        self.had_error = True


lox_instance = None


def get_lox() -> Lox:
    global lox_instance
    if lox_instance is None:
        lox_instance = Lox()
    return lox_instance
