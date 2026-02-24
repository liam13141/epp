"""CLI entry point for E++.

Usage:
    python epp_runner.py script.epp
    python epp_runner.py   # starts REPL
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from epp_interpreter import EppFunction, EppInterpreter, EppRuntimeError
from epp_lexer import EppLexer, EppLexerError
from epp_parser import EppParseError, EppParser

VERSION = "0.2.0"


def execute_source(source: str, interpreter: EppInterpreter, check_only: bool = False) -> int:
    """Tokenize, parse, and execute a source string."""

    lexer = EppLexer()
    try:
        tokens = lexer.tokenize(source)
        program = EppParser(tokens).parse()
    except EppLexerError as exc:
        print(exc)
        return 1
    except EppParseError as exc:
        print(exc)
        return 1

    if check_only:
        return 0

    try:
        interpreter.execute(program)
    except EppRuntimeError as exc:
        print(exc)
        return 1
    return 0


def run_file(path: Path, check_only: bool = False, max_loop_iterations: int = 100_000) -> int:
    """Run a .epp script file."""

    if not path.exists():
        print(f"Oops! I can't find '{path}'.")
        return 1

    if not path.is_file():
        print(f"Oops! '{path}' is not a file.")
        return 1

    source = path.read_text(encoding="utf-8-sig")
    interpreter = EppInterpreter(max_loop_iterations=max_loop_iterations)
    status = execute_source(source, interpreter, check_only=check_only)
    if status == 0 and check_only:
        print(f"Looks good! '{path}' has no syntax errors.")
    return status


def run_repl(max_loop_iterations: int = 100_000) -> int:
    """Start an interactive E++ shell."""

    print("E++ REPL")
    print("Type E++ lines. Use 'exit' or 'quit' to leave. Type ':help' for REPL commands.")

    lexer = EppLexer()
    interpreter = EppInterpreter(max_loop_iterations=max_loop_iterations)
    buffer: list[str] = []

    while True:
        prompt = "epp> " if not buffer else "... "
        try:
            line = input(prompt)
        except EOFError:
            print()
            return 0

        if not buffer and line.strip().lower() in {"exit", "quit"}:
            return 0

        if not line.strip() and not buffer:
            continue

        if not buffer and line.strip().startswith(":"):
            _handle_repl_command(line.strip(), interpreter)
            continue

        buffer.append(line)

        try:
            tokens = lexer.tokenize("\n".join(buffer))
            program = EppParser(tokens).parse()
        except EppParseError as exc:
            if exc.incomplete:
                continue
            print(exc)
            buffer.clear()
            continue
        except EppLexerError as exc:
            print(exc)
            buffer.clear()
            continue

        try:
            interpreter.execute(program)
        except EppRuntimeError as exc:
            print(exc)
        finally:
            buffer.clear()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run E++ scripts or launch the E++ REPL.")
    parser.add_argument("--check", action="store_true", help="Validate syntax without executing the script.")
    parser.add_argument(
        "--max-loop-iterations",
        type=int,
        default=100_000,
        help="Safety limit for total loop iterations before stopping runaway loops.",
    )
    parser.add_argument("--version", action="version", version=f"E++ {VERSION}")
    parser.add_argument("script", nargs="?", help="Path to a .epp file")
    args = parser.parse_args(argv)

    if args.max_loop_iterations <= 0:
        parser.error("--max-loop-iterations must be greater than 0")

    if args.check and not args.script:
        parser.error("--check requires a script path")

    if args.script:
        return run_file(
            Path(args.script),
            check_only=args.check,
            max_loop_iterations=args.max_loop_iterations,
        )
    return run_repl(max_loop_iterations=args.max_loop_iterations)


def _handle_repl_command(command: str, interpreter: EppInterpreter) -> None:
    if command == ":help":
        print("REPL commands:")
        print("  :help            Show this help")
        print("  :vars            Show global variables")
        print("  :reset           Clear all variables and functions")
        print("  :load <file>     Run a .epp file in current REPL state")
        return

    if command == ":vars":
        globals_map = interpreter.global_scope
        if not globals_map:
            print("(no variables yet)")
            return

        for name in sorted(globals_map):
            value = globals_map[name]
            if isinstance(value, EppFunction):
                params = ", ".join(value.params) if value.params else ""
                print(f"{name} = <function({params})>")
            else:
                print(f"{name} = {value!r}")
        return

    if command == ":reset":
        interpreter.global_scope.clear()
        interpreter.scopes = [interpreter.global_scope]
        interpreter.loop_iterations = 0
        print("Environment reset.")
        return

    if command.startswith(":load "):
        file_path = command[len(":load ") :].strip().strip('"')
        if not file_path:
            print("Please provide a file path. Example: :load examples/hello.epp")
            return
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            print(f"Oops! I can't find '{file_path}'.")
            return
        source = path.read_text(encoding="utf-8-sig")
        execute_source(source, interpreter, check_only=False)
        return

    print("Unknown REPL command. Type ':help' to see available commands.")


if __name__ == "__main__":
    raise SystemExit(main())
