import os
import sys


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

        scanner = Scanner(source)
        tokens = scanner.scan_tokens()

        for token in tokens:
            print(token)

    def error(self, line: int, message: str) -> None:
        self.report(line, "", message)

    def report(self, line: int, where: str, message: str) -> None:
        print(f"[line {line}] Error{where}: {message}", file=sys.stderr)
        self.had_error = True


lox_instance = None


def get_lox() -> Lox:
    global lox_instance
    if lox_instance is None:
        lox_instance = Lox()
    return lox_instance
