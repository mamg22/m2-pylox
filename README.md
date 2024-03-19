# m2-pylox

This is a port of the tree-walking interpreter for the Lox programming language featured in the [Crafting Interpreters](https://craftinginterpreters.com/) book.

This project currently uses [`rye`](https://rye-up.com/) for dependency and project management.

# Implemented challenges

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


# Implementation differences

There are some changes in comparison with the reference implementation provided in the book.

* No AST generator: Two of the main issues the book's AST generator deals with can be easily be solved with standard library functionality: The data and contructor definition are simply dataclasses; the `accept()` definition is provided by inheritance, with the `visit()` method selecting the implementation based on the type of the passed parameter using `functools.singledispatchmethod` (which can easily be replaced by a dispatching function using a `match` or `isinstance` to select the correct function).