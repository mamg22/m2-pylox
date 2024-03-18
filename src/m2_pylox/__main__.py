import sys

from m2_pylox.lox import get_lox


def main() -> None:
    if len(sys.argv) > 2:
        print(f"Usage: {sys.argv[0]} [script]")
        sys.exit(64)

    lox = get_lox()

    if len(sys.argv) == 2:
        lox.run_file(sys.argv[1])
        if lox.had_error:
            sys.exit(65)
    else:
        lox.run_prompt()


if __name__ == "__main__":
    main()