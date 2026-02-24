"""Tokenizer for the E++ language.

E++ is intentionally line-oriented, so this lexer emits one token per line.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LineToken:
    """A single source line with metadata for parser error reporting."""

    line: int
    text: str
    kind: str  # "STATEMENT", "COMMENT", or "BLANK"


class EppLexerError(Exception):
    """Raised when source text cannot be tokenized."""

    def __init__(self, line: int, message: str) -> None:
        self.line = line
        self.message = message
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return f"Oops! On line {self.line}, {self.message}"


class EppLexer:
    """Converts raw E++ source into line tokens."""

    def tokenize(self, source: str) -> list[LineToken]:
        tokens: list[LineToken] = []

        for line_number, raw_line in enumerate(source.splitlines(), start=1):
            if line_number == 1 and raw_line.startswith("\ufeff"):
                # Handle UTF-8 files that include a BOM.
                raw_line = raw_line.lstrip("\ufeff")

            if "\x00" in raw_line:
                raise EppLexerError(line_number, "I found an invalid null character.")

            stripped = raw_line.strip()
            if not stripped:
                kind = "BLANK"
            elif stripped.startswith("#"):
                kind = "COMMENT"
            else:
                kind = "STATEMENT"

            tokens.append(LineToken(line=line_number, text=raw_line, kind=kind))

        return tokens


def tokenize_file(path: str | Path) -> list[LineToken]:
    """Read and tokenize a .epp file."""

    source = Path(path).read_text(encoding="utf-8")
    return EppLexer().tokenize(source)
