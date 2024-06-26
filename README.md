# m2-pylox

This is a port of the tree-walking interpreter for the Lox programming language featured in the [Crafting Interpreters](https://craftinginterpreters.com/) book.

This project currently uses [`rye`](https://rye-up.com/) for dependency and project management.

# Implemented chapters and challenges

* Chapter 4
    - C-Style comments (`/* ... */`)
    - Nested C-Style comments (`/* ... /* ... */ ... */`)
* Chapter 5
    - Reverse Polish Notation (RPN) AST printer
* Chapter 6
    - Comma operator `,`
    - Ternary operator `?:`
    - Error productions for binary operators missing left side expression
* Chapter 7
    - Non-number comparisons. Only allowed between expressions of the same type, allowing numbers, strings and booleans.
    - Convert addition operands to strings if only one of them is already a string.
    - Handle division by zero with a runtime error.
* Chapter 8
    - Throw runtime error on uninitialized variable access.
* Chapter 9
    - `break` statement.
* Chapter 10
    - Anonymous (lambda) functions.
* Chapter 11
    - Error on unused local variables.
* Chapter 12
    - Class methods (`class` prefix before function definition)
    - Getter methods (Function name followed by block)
* Chapter 13
    - Code reuse mechanism: Traits, implementation like PHP. See additional features section for more details.

# Implementation differences

There are some changes in comparison with the reference implementation provided in the book.

* No AST generator: Two of the main issues the book's AST generator deals with can be easily be solved with standard library functionality: The data and contructor definition are simply dataclasses; the `accept()` definition is provided by inheritance, with the `visit()` method selecting the implementation based on the type of the passed parameter using `functools.singledispatchmethod` (which can easily be replaced by a dispatching function using a `match` or `isinstance` to select the correct function).
* Unsugared `for` loop: The `for` loop in this implementation isn't syntactic sugar for a block with a while loop; instead, it is a different statement type to allow better flexibility.

# Additional features

* Native functions
    - `input(prompt: String)`: Read a line from stdin and return it as a string, showing `prompt` before asking for input.
    - `randint(min: Number, max: Number)`: Pick a random number between `min` and `max`, both included.
* `continue` statement.
* `trait` and `use`.
    - Declare a trait using `trait` and providing a class body; traits cannot inherit, but can be extended by using other traits.
    - Include traits in classes or other traits via the `use` statement, this copies the trait's methods over to the class/trait using it.
    - An `use` statement can indicate one or more traits separated by commas, e.g. `use TraitA, TraitB, TraitC;`.