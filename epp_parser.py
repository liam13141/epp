"""Parser for E++.

The parser consumes line tokens and produces a small AST that the interpreter
can execute directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
import re
from typing import Optional

from epp_lexer import LineToken


@dataclass
class Program:
    statements: list["Statement"]


class Statement:
    """Marker base class for AST statement nodes."""


@dataclass
class SetStatement(Statement):
    name: str
    expression: str
    line: int


@dataclass
class SayStatement(Statement):
    expression: str
    line: int


@dataclass
class AddStatement(Statement):
    value_expression: str
    target_name: str
    line: int


@dataclass
class SubtractStatement(Statement):
    value_expression: str
    target_name: str
    line: int


@dataclass
class MultiplyStatement(Statement):
    target_name: str
    value_expression: str
    line: int


@dataclass
class DivideStatement(Statement):
    target_name: str
    value_expression: str
    line: int


@dataclass
class CreateListStatement(Statement):
    name: str
    line: int


@dataclass
class RemoveStatement(Statement):
    value_expression: str
    list_name: str
    line: int


@dataclass
class AskStatement(Statement):
    prompt_expression: str
    target_name: str
    line: int


@dataclass
class Condition:
    left_expression: str
    operator: str  # ">", "<", ">=", "<=", "==", "!=", "contains", "not_contains", "truthy"
    right_expression: Optional[str]
    line: int


@dataclass
class ElseIfBranch:
    condition: Condition
    body: list["Statement"]
    line: int


@dataclass
class IfStatement(Statement):
    condition: Condition
    body: list[Statement]
    elif_branches: list[ElseIfBranch]
    else_body: Optional[list[Statement]]
    line: int


@dataclass
class RepeatTimesStatement(Statement):
    count_expression: str
    body: list[Statement]
    line: int


@dataclass
class RepeatWhileStatement(Statement):
    condition: Condition
    body: list[Statement]
    line: int


@dataclass
class ForEachStatement(Statement):
    item_name: str
    iterable_expression: str
    body: list[Statement]
    line: int


@dataclass
class FunctionDefStatement(Statement):
    name: str
    params: list[str]
    body: list[Statement]
    line: int


@dataclass
class ReturnStatement(Statement):
    expression: Optional[str]
    line: int


@dataclass
class CallStatement(Statement):
    name: str
    arguments: list[str]
    line: int


@dataclass
class BreakStatement(Statement):
    line: int


@dataclass
class ContinueStatement(Statement):
    line: int


class EppParseError(Exception):
    """Friendly parser errors for beginner users."""

    def __init__(
        self,
        line: Optional[int],
        message: str,
        suggestion: Optional[str] = None,
        incomplete: bool = False,
    ) -> None:
        self.line = line
        self.message = message
        self.suggestion = suggestion
        self.incomplete = incomplete
        super().__init__(self.__str__())

    def __str__(self) -> str:
        prefix = "Oops! "
        if self.line is not None:
            prefix = f"Oops! On line {self.line}, "
        text = prefix + self.message
        if self.suggestion:
            text += f" {self.suggestion}"
        return text


class EppParser:
    """Parses line tokens into a Program AST."""

    CLOSING_KEYWORDS = {"otherwise", "end if", "end repeat", "end define", "end for"}
    CLOSING_PREFIXES = ("otherwise if ",)
    CLOSING_ALIASES = {
        "else": "otherwise",
        "finish if": "end if",
        "finish repeat": "end repeat",
        "finish for": "end for",
        "end function": "end define",
        "finish define": "end define",
        "finish function": "end define",
    }
    CLOSING_PREFIX_ALIASES = {
        "or if ": "otherwise if ",
    }
    COMMAND_SUGGESTIONS = {
        "set": "set x to 10",
        "let": "let x be 10",
        "put": "put 10 into x",
        "say": 'say "Hello World"',
        "print": 'print "Hello World"',
        "show": 'show "Hello World"',
        "add": "add 5 to x",
        "increase": "increase x by 5",
        "subtract": "subtract 3 from x",
        "decrease": "decrease x by 3",
        "multiply": "multiply x by 2",
        "divide": "divide x by 4",
        "if": "if x is greater than 10 then",
        "when": "when x is greater than 10 then",
        "otherwise": "otherwise",
        "else": "else",
        "otherwise if": "otherwise if x is less than 5 then",
        "or if": "or if x is less than 5 then",
        "repeat": "repeat 5 times",
        "do": "do 5 times",
        "for each": "for each item in mylist",
        "for every": "for every item in mylist",
        "define": "define greet with name",
        "function": "function greet with name",
        "return": "return x",
        "give back": "give back x",
        "call": 'call greet with "Alice"',
        "run": 'run greet with "Alice"',
        "create list": "create list mylist",
        "make list": "make list mylist",
        "remove": "remove 5 from mylist",
        "take": "take 5 from mylist",
        "ask": 'ask "What is your name?" and store in name',
        "create website": 'create a website called "My Site" and store in app',
        "when someone visits": 'when someone visits "/" on app show "Hello"',
        "when someone posts": 'when someone posts "/submit" on app show "Done"',
        "start web server": 'start web server for app on "127.0.0.1" port 5000',
        "fetch from": 'fetch from "https://example.com" and store in text',
        "fetch json from": 'fetch json from "https://api.example.com/data" and store in data',
        "stop": "stop repeat",
        "break": "break loop",
        "skip": "skip repeat",
        "next": "next loop",
        "end if": "end if",
        "finish if": "finish if",
        "end repeat": "end repeat",
        "finish repeat": "finish repeat",
        "end define": "end define",
        "end function": "end function",
        "finish function": "finish function",
        "end for": "end for",
        "finish for": "finish for",
    }

    def __init__(self, tokens: list[LineToken]) -> None:
        self.tokens = tokens
        self.position = 0

    def parse(self) -> Program:
        body, _, _ = self._parse_block(end_keywords=set())
        return Program(statements=body)

    def _parse_block(
        self,
        end_keywords: set[str],
        end_prefixes: tuple[str, ...] = (),
    ) -> tuple[list[Statement], Optional[str], Optional[int]]:
        statements: list[Statement] = []

        while self._has_more():
            token = self._advance()
            if token.kind != "STATEMENT":
                continue

            canonical = self._canonical(token.text)
            canonical = self._normalize_closing_token(canonical)
            if canonical in end_keywords:
                return statements, token.text.strip(), token.line

            if any(canonical.startswith(prefix) for prefix in end_prefixes):
                return statements, token.text.strip(), token.line

            if self._is_closing_keyword(canonical):
                if end_keywords:
                    expected_parts = sorted(end_keywords)
                    expected_parts.extend(prefix.strip() + "..." for prefix in end_prefixes)
                    expected = " or ".join(expected_parts)
                    suggestion = f"I expected {expected} before this line."
                else:
                    suggestion = "This closing word does not match any open block."
                raise EppParseError(token.line, f"'{token.text.strip()}' is out of place.", suggestion)

            statements.append(self._parse_statement(token))

        if end_keywords or end_prefixes:
            expected_parts = sorted(end_keywords)
            expected_parts.extend(prefix.strip() + "..." for prefix in end_prefixes)
            expected = " or ".join(expected_parts)
            line = self.tokens[-1].line if self.tokens else 1
            raise EppParseError(
                line,
                f"I reached the end of the file, but I'm still waiting for {expected}.",
                incomplete=True,
            )

        return statements, None, None

    def _parse_statement(self, token: LineToken) -> Statement:
        text = token.text.strip()

        set_match = re.fullmatch(
            r"(?:set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to|let\s+([A-Za-z_][A-Za-z0-9_]*)\s+be)\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if set_match:
            variable_name = set_match.group(1) or set_match.group(2)
            return SetStatement(
                name=variable_name,
                expression=set_match.group(3).strip(),
                line=token.line,
            )

        put_match = re.fullmatch(r"put\s+(.+)\s+into\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.IGNORECASE)
        if put_match:
            return SetStatement(
                name=put_match.group(2),
                expression=put_match.group(1).strip(),
                line=token.line,
            )

        say_match = re.fullmatch(r"(?:say|print|show)\s+(.+)", text, flags=re.IGNORECASE)
        if say_match:
            return SayStatement(expression=say_match.group(1).strip(), line=token.line)

        ask_match = re.fullmatch(
            r"ask\s+(.+)\s+and\s+(?:store|save)\s+(?:in|as)\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.IGNORECASE,
        )
        if ask_match:
            return AskStatement(
                prompt_expression=ask_match.group(1).strip(),
                target_name=ask_match.group(2),
                line=token.line,
            )

        create_website_match = re.fullmatch(
            r"(?:create|make|build)\s+(?:a\s+)?(?:website|web\s+site|web\s+app)"
            r"(?:\s+called\s+(.+?))?\s+and\s+(?:store|save)\s+(?:it\s+)?(?:in|as)\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.IGNORECASE,
        )
        if create_website_match:
            title_expression = create_website_match.group(1).strip() if create_website_match.group(1) else '"E++ Website"'
            return SetStatement(
                name=create_website_match.group(2),
                expression=f"call create_web_app with {title_expression}",
                line=token.line,
            )

        visit_route_match = re.fullmatch(
            r"when\s+someone\s+visits\s+(.+)\s+on\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:show|send|return)\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if visit_route_match:
            return CallStatement(
                name="when_someone_visits",
                arguments=[
                    visit_route_match.group(2),
                    visit_route_match.group(1).strip(),
                    visit_route_match.group(3).strip(),
                ],
                line=token.line,
            )

        post_route_match = re.fullmatch(
            r"when\s+someone\s+posts(?:\s+to)?\s+(.+)\s+on\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:show|send|return)\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if post_route_match:
            return CallStatement(
                name="when_someone_posts",
                arguments=[
                    post_route_match.group(2),
                    post_route_match.group(1).strip(),
                    post_route_match.group(3).strip(),
                ],
                line=token.line,
            )

        start_web_server_match = re.fullmatch(
            r"start\s+(?:the\s+)?(?:web|website)\s+server\s+for\s+([A-Za-z_][A-Za-z0-9_]*)"
            r"(?:\s+on\s+(.+?)\s+port\s+(.+))?",
            text,
            flags=re.IGNORECASE,
        )
        if start_web_server_match:
            arguments = [start_web_server_match.group(1)]
            host_expression = start_web_server_match.group(2)
            port_expression = start_web_server_match.group(3)
            if host_expression and port_expression:
                arguments.append(host_expression.strip())
                arguments.append(port_expression.strip())
            return CallStatement(name="start_web_server", arguments=arguments, line=token.line)

        fetch_json_match = re.fullmatch(
            r"fetch\s+json\s+from\s+(.+)\s+and\s+(?:store|save)\s+(?:in|as)\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.IGNORECASE,
        )
        if fetch_json_match:
            return SetStatement(
                name=fetch_json_match.group(2),
                expression=f"call fetch_json_from_api with {fetch_json_match.group(1).strip()}",
                line=token.line,
            )

        fetch_text_match = re.fullmatch(
            r"fetch\s+from\s+(.+)\s+and\s+(?:store|save)\s+(?:in|as)\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.IGNORECASE,
        )
        if fetch_text_match:
            return SetStatement(
                name=fetch_text_match.group(2),
                expression=f"call fetch_from_api with {fetch_text_match.group(1).strip()}",
                line=token.line,
            )

        create_list_match = re.fullmatch(r"(?:create|make)\s+list\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.IGNORECASE)
        if create_list_match:
            return CreateListStatement(name=create_list_match.group(1), line=token.line)

        add_match = re.fullmatch(r"add\s+(.+)\s+to\s+([A-Za-z_][A-Za-z0-9_]*)", text, flags=re.IGNORECASE)
        if add_match:
            return AddStatement(
                value_expression=add_match.group(1).strip(),
                target_name=add_match.group(2),
                line=token.line,
            )

        increase_match = re.fullmatch(r"increase\s+([A-Za-z_][A-Za-z0-9_]*)\s+by\s+(.+)", text, flags=re.IGNORECASE)
        if increase_match:
            return AddStatement(
                value_expression=increase_match.group(2).strip(),
                target_name=increase_match.group(1),
                line=token.line,
            )

        subtract_match = re.fullmatch(
            r"subtract\s+(.+)\s+from\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.IGNORECASE,
        )
        if subtract_match:
            return SubtractStatement(
                value_expression=subtract_match.group(1).strip(),
                target_name=subtract_match.group(2),
                line=token.line,
            )

        decrease_match = re.fullmatch(r"decrease\s+([A-Za-z_][A-Za-z0-9_]*)\s+by\s+(.+)", text, flags=re.IGNORECASE)
        if decrease_match:
            return SubtractStatement(
                value_expression=decrease_match.group(2).strip(),
                target_name=decrease_match.group(1),
                line=token.line,
            )

        multiply_match = re.fullmatch(
            r"multiply\s+([A-Za-z_][A-Za-z0-9_]*)\s+by\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if multiply_match:
            return MultiplyStatement(
                target_name=multiply_match.group(1),
                value_expression=multiply_match.group(2).strip(),
                line=token.line,
            )

        divide_match = re.fullmatch(
            r"divide\s+([A-Za-z_][A-Za-z0-9_]*)\s+by\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if divide_match:
            return DivideStatement(
                target_name=divide_match.group(1),
                value_expression=divide_match.group(2).strip(),
                line=token.line,
            )

        remove_match = re.fullmatch(
            r"(?:remove|take)\s+(.+)\s+from\s+([A-Za-z_][A-Za-z0-9_]*)",
            text,
            flags=re.IGNORECASE,
        )
        if remove_match:
            return RemoveStatement(
                value_expression=remove_match.group(1).strip(),
                list_name=remove_match.group(2),
                line=token.line,
            )

        if_match = re.fullmatch(r"(?:if|when)\s+(.+)\s+then", text, flags=re.IGNORECASE)
        if if_match:
            return self._parse_if_statement(
                condition_text=if_match.group(1).strip(),
                if_line=token.line,
            )

        repeat_while_match = re.fullmatch(r"repeat\s+while\s+(.+)", text, flags=re.IGNORECASE)
        if not repeat_while_match:
            repeat_while_match = re.fullmatch(r"while\s+(.+)\s+do", text, flags=re.IGNORECASE)
        if repeat_while_match:
            condition = self._parse_condition(repeat_while_match.group(1).strip(), token.line)
            body, _, _ = self._parse_block(end_keywords={"end repeat"})
            return RepeatWhileStatement(condition=condition, body=body, line=token.line)

        repeat_times_match = re.fullmatch(r"repeat\s+(.+)\s+times", text, flags=re.IGNORECASE)
        if not repeat_times_match:
            repeat_times_match = re.fullmatch(r"do\s+(.+)\s+times", text, flags=re.IGNORECASE)
        if repeat_times_match:
            body, _, _ = self._parse_block(end_keywords={"end repeat"})
            return RepeatTimesStatement(
                count_expression=repeat_times_match.group(1).strip(),
                body=body,
                line=token.line,
            )

        for_each_match = re.fullmatch(
            r"for\s+(?:each|every)\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if for_each_match:
            body, _, _ = self._parse_block(end_keywords={"end for"})
            return ForEachStatement(
                item_name=for_each_match.group(1),
                iterable_expression=for_each_match.group(2).strip(),
                body=body,
                line=token.line,
            )

        define_match = re.fullmatch(
            r"(?:define|function)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+with\s+(.+))?",
            text,
            flags=re.IGNORECASE,
        )
        if define_match:
            params = self._split_parameters(define_match.group(2) or "", token.line)
            body, _, _ = self._parse_block(end_keywords={"end define"})
            return FunctionDefStatement(
                name=define_match.group(1),
                params=params,
                body=body,
                line=token.line,
            )

        break_match = re.fullmatch(r"(?:stop(?:\s+(?:repeat|for|loop))?|break(?:\s+loop)?)", text, flags=re.IGNORECASE)
        if break_match:
            return BreakStatement(line=token.line)

        continue_match = re.fullmatch(r"(?:skip(?:\s+(?:repeat|for|loop))?|next(?:\s+loop)?)", text, flags=re.IGNORECASE)
        if continue_match:
            return ContinueStatement(line=token.line)

        return_match = re.fullmatch(r"(?:return|give\s+back)(?:\s+(.+))?", text, flags=re.IGNORECASE)
        if return_match:
            expression = return_match.group(1).strip() if return_match.group(1) else None
            return ReturnStatement(expression=expression, line=token.line)

        call_match = re.fullmatch(
            r"(?:call|run)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+with\s+(.+))?",
            text,
            flags=re.IGNORECASE,
        )
        if call_match:
            arguments = self._split_arguments(call_match.group(2) or "")
            return CallStatement(name=call_match.group(1), arguments=arguments, line=token.line)

        self._raise_unknown_statement(token)
        raise AssertionError("Unreachable")

    def _parse_if_statement(self, condition_text: str, if_line: int) -> IfStatement:
        condition = self._parse_condition(condition_text, if_line)
        if_body, block_end_text, block_line = self._parse_block(
            end_keywords={"otherwise", "end if"},
            end_prefixes=self.CLOSING_PREFIXES,
        )
        block_end = self._normalize_closing_token(self._canonical(block_end_text)) if block_end_text else None

        elif_branches: list[ElseIfBranch] = []
        while block_end and block_end.startswith("otherwise if "):
            branch_line = block_line or if_line
            raw_end = (block_end_text or "").strip()
            branch_match = re.fullmatch(r"(?:otherwise|or)\s+if\s+(.+)\s+then", raw_end, flags=re.IGNORECASE)
            if not branch_match:
                raise EppParseError(
                    branch_line,
                    "I expected 'otherwise if ... then' or 'or if ... then'.",
                    "Try: otherwise if x equals 10 then",
                )
            branch_condition_raw = branch_match.group(1).strip()
            if not branch_condition_raw:
                raise EppParseError(
                    branch_line,
                    "I expected a condition after 'otherwise if'.",
                    "Try: otherwise if score is greater than 100 then",
                )
            branch_condition = self._parse_condition(branch_condition_raw, branch_line)
            branch_body, block_end_text, block_line = self._parse_block(
                end_keywords={"otherwise", "end if"},
                end_prefixes=self.CLOSING_PREFIXES,
            )
            block_end = self._normalize_closing_token(self._canonical(block_end_text)) if block_end_text else None
            elif_branches.append(ElseIfBranch(condition=branch_condition, body=branch_body, line=branch_line))

        else_body: Optional[list[Statement]] = None
        if block_end == "otherwise":
            else_body, _, _ = self._parse_block(end_keywords={"end if"})

        return IfStatement(
            condition=condition,
            body=if_body,
            elif_branches=elif_branches,
            else_body=else_body,
            line=if_line,
        )

    def _parse_condition(self, raw_condition: str, line: int) -> Condition:
        patterns = [
            (r"(.+?)\s+is\s+greater\s+than\s+or\s+equal\s+to\s+(.+)", ">="),
            (r"(.+?)\s+is\s+less\s+than\s+or\s+equal\s+to\s+(.+)", "<="),
            (r"(.+?)\s+is\s+not\s+equal\s+to\s+(.+)", "!="),
            (r"(.+?)\s+is\s+equal\s+to\s+(.+)", "=="),
            (r"(.+?)\s+is\s+at\s+least\s+(.+)", ">="),
            (r"(.+?)\s+is\s+at\s+most\s+(.+)", "<="),
            (r"(.+?)\s+does\s+not\s+contain\s+(.+)", "not_contains"),
            (r"(.+?)\s+contains\s+(.+)", "contains"),
            (r"(.+?)\s+is\s+greater\s+than\s+(.+)", ">"),
            (r"(.+?)\s+is\s+bigger\s+than\s+(.+)", ">"),
            (r"(.+?)\s+is\s+less\s+than\s+(.+)", "<"),
            (r"(.+?)\s+is\s+smaller\s+than\s+(.+)", "<"),
            (r"(.+?)\s+equals\s+(.+)", "=="),
            (r"(.+?)\s+is\s+not\s+(.+)", "!="),
        ]
        for pattern, operator in patterns:
            match = re.fullmatch(pattern, raw_condition, flags=re.IGNORECASE)
            if match:
                return Condition(
                    left_expression=match.group(1).strip(),
                    operator=operator,
                    right_expression=match.group(2).strip(),
                    line=line,
                )
        return Condition(left_expression=raw_condition.strip(), operator="truthy", right_expression=None, line=line)

    def _split_parameters(self, raw: str, line: int) -> list[str]:
        if not raw.strip():
            return []

        if "," in raw:
            parts = [part.strip() for part in raw.split(",")]
        else:
            parts = [part.strip() for part in re.split(r"\s+and\s+", raw, flags=re.IGNORECASE)]

        params: list[str] = []
        for part in parts:
            if not part:
                continue
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
                raise EppParseError(
                    line,
                    f"'{part}' is not a valid parameter name.",
                    "Use names like 'x', 'total', or 'item_count'.",
                )
            params.append(part)

        return params

    def _split_arguments(self, raw: str) -> list[str]:
        raw = raw.strip()
        if not raw:
            return []

        arguments: list[str] = []
        chunk: list[str] = []
        quote_char: Optional[str] = None
        depth = 0

        for character in raw:
            if quote_char:
                chunk.append(character)
                if character == quote_char:
                    quote_char = None
                continue

            if character in {'"', "'"}:
                quote_char = character
                chunk.append(character)
                continue

            if character in "([{":
                depth += 1
                chunk.append(character)
                continue

            if character in ")]}":
                depth = max(depth - 1, 0)
                chunk.append(character)
                continue

            if character == "," and depth == 0:
                candidate = "".join(chunk).strip()
                if candidate:
                    arguments.append(candidate)
                chunk = []
                continue

            chunk.append(character)

        candidate = "".join(chunk).strip()
        if candidate:
            arguments.append(candidate)

        return arguments

    def _raise_unknown_statement(self, token: LineToken) -> None:
        raw_text = token.text.strip()
        canonical = self._canonical(raw_text)

        command_key = canonical
        if " " in command_key:
            first_two = " ".join(command_key.split()[:2])
        else:
            first_two = command_key

        suggestion_keys = list(self.COMMAND_SUGGESTIONS.keys())
        close_match = get_close_matches(command_key, suggestion_keys, n=1, cutoff=0.45)
        if not close_match:
            close_match = get_close_matches(first_two, suggestion_keys, n=1, cutoff=0.45)

        suggestion = None
        if close_match:
            example = self.COMMAND_SUGGESTIONS[close_match[0]]
            suggestion = f"Did you mean '{example}'?"

        if suggestion is None:
            suggestion = "Try commands like 'set x to 10' or 'say \"Hello\"'."

        raise EppParseError(token.line, f"I don't understand '{raw_text}'.", suggestion)

    def _is_closing_keyword(self, canonical: str) -> bool:
        canonical = self._normalize_closing_token(canonical)
        if canonical in self.CLOSING_KEYWORDS:
            return True
        return any(canonical.startswith(prefix) for prefix in self.CLOSING_PREFIXES)

    def _has_more(self) -> bool:
        return self.position < len(self.tokens)

    def _advance(self) -> LineToken:
        token = self.tokens[self.position]
        self.position += 1
        return token

    @staticmethod
    def _canonical(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def _normalize_closing_token(self, canonical: str) -> str:
        normalized = self.CLOSING_ALIASES.get(canonical, canonical)
        for alias, target_prefix in self.CLOSING_PREFIX_ALIASES.items():
            if normalized.startswith(alias):
                return target_prefix + normalized[len(alias) :]
        return normalized
