# TinyCalc

A minimal command-line calculator for testing code-comic.

## Architecture

- `src/calculator.py` — core `add` and `subtract` operations
- `src/main.py` — CLI entry point that parses arguments and calls the calculator
- `pyproject.toml` — project metadata and dependencies

## Workflow

1. User runs `python -m src.main add 2 3`
2. `main.py` parses the operation and operands
3. `calculator.py` performs the math and returns the result
4. The result is printed to stdout
