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
    - Generic method to handle left-associative binary operators (Not in challenges section, mentioned after defining `comparison()`)
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
    - Tried to add `continue` too, but the way to handle it conflicts with desugared `for` loops, since the increment becomes part of the loop body, which is skipped by `continue`, causing an infinite loop; maybe I'll add it later with a different approach.
* Chapter 10
    - Anonymous (lambda) functions.
* Chapter 11
    - Error on unused local variables.
* Chapter 12
    - Class methods (`class` prefix before function definition)
    - Getter methods (Function name followed by block)
* Chapter 13

# Implementation differences

There are some changes in comparison with the reference implementation provided in the book.

* No AST generator: Two of the main issues the book's AST generator deals with can be easily be solved with standard library functionality: The data and contructor definition are simply dataclasses; the `accept()` definition is provided by inheritance, with the `visit()` method selecting the implementation based on the type of the passed parameter using `functools.singledispatchmethod` (which can easily be replaced by a dispatching function using a `match` or `isinstance` to select the correct function).