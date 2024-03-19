import sys

from m2_pylox import lox as loxlib


def main() -> None:
    if len(sys.argv) > 2:
        print(f"Usage: {sys.argv[0]} [script]")
        sys.exit(64)

    lox = loxlib.get_lox()

    if len(sys.argv) == 2:
        lox.run_file(sys.argv[1])
        if lox.had_error:
            sys.exit(65)
    else:
        lox.run_prompt()


if __name__ == "__main__":
    main()
