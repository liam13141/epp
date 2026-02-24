"""Interpreter for E++ AST nodes."""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
import re
import time
from typing import Any, Callable, Optional
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from epp_parser import (
    AddStatement,
    AskStatement,
    BreakStatement,
    CallStatement,
    Condition,
    ContinueStatement,
    CreateListStatement,
    DivideStatement,
    ForEachStatement,
    FunctionDefStatement,
    IfStatement,
    MultiplyStatement,
    Program,
    RemoveStatement,
    RepeatTimesStatement,
    RepeatWhileStatement,
    ReturnStatement,
    SayStatement,
    SetStatement,
    Statement,
    SubtractStatement,
)


class EppRuntimeError(Exception):
    """Human-friendly runtime errors."""

    def __init__(self, line: int, message: str) -> None:
        self.line = line
        self.message = message
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return f"Oops! On line {self.line}, {self.message}"


class ReturnSignal(Exception):
    """Internal control-flow signal for function returns."""

    def __init__(self, value: Any, line: int) -> None:
        self.value = value
        self.line = line
        super().__init__("return")


class BreakSignal(Exception):
    """Internal control-flow signal for loop breaks."""

    def __init__(self, line: int) -> None:
        self.line = line
        super().__init__("break")


class ContinueSignal(Exception):
    """Internal control-flow signal for loop continues."""

    def __init__(self, line: int) -> None:
        self.line = line
        super().__init__("continue")


@dataclass
class EppFunction:
    name: str
    params: list[str]
    body: list[Statement]
    line: int


class MiniFlaskApp:
    """A tiny Flask-like app built only with Python standard library."""

    def __init__(self, name: str = "E++ App") -> None:
        self.name = str(name)
        self._routes: dict[str, dict[str, Any]] = {
            "GET": {},
            "POST": {},
        }

    def add_route(self, method: str, path: str, handler: Any) -> None:
        normalized_method = str(method).upper().strip()
        normalized_path = self._normalize_path(path)
        if normalized_method not in self._routes:
            raise ValueError(f"Unsupported HTTP method '{method}'. Use GET or POST.")
        self._routes[normalized_method][normalized_path] = handler

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        on_start: Optional[Callable[[str], None]] = None,
        on_request: Optional[Callable[[str], None]] = None,
    ) -> bool:
        try:
            from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: PLC0415
        except Exception as exc:
            raise RuntimeError("I couldn't import Python's built-in HTTP server.") from exc

        app = self
        host_text = str(host)
        port_number = int(port)

        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                status, headers, body = app.dispatch_request(
                    method="GET",
                    raw_path=self.path,
                    body_bytes=b"",
                    headers=self.headers,
                )
                self._send_response(status, headers, body)
                if on_request is not None:
                    on_request(f"request GET http://{host_text}:{port_number}{self.path} -> {int(status)}")

            def do_POST(self) -> None:  # noqa: N802
                raw_length = self.headers.get("Content-Length", "0")
                try:
                    length = int(raw_length)
                except Exception:
                    length = 0
                body_bytes = self.rfile.read(length) if length > 0 else b""
                status, headers, body = app.dispatch_request(
                    method="POST",
                    raw_path=self.path,
                    body_bytes=body_bytes,
                    headers=self.headers,
                )
                self._send_response(status, headers, body)
                if on_request is not None:
                    on_request(f"request POST http://{host_text}:{port_number}{self.path} -> {int(status)}")

            def _send_response(self, status: int, headers: dict[str, str], body: bytes) -> None:
                self.send_response(int(status))
                outbound_headers = dict(headers)
                outbound_headers.setdefault("Content-Length", str(len(body)))
                for key, value in outbound_headers.items():
                    self.send_header(str(key), str(value))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                # Keep terminal output clean for beginner scripts.
                return

        server = ThreadingHTTPServer((host_text, port_number), RequestHandler)
        if on_start is not None:
            on_start(f"http://{host_text}:{port_number}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return True

    def simulate_request(
        self,
        method: str = "GET",
        path: str = "/",
        body: Any = "",
    ) -> tuple[int, dict[str, str], str]:
        body_bytes = body if isinstance(body, bytes) else str(body).encode("utf-8")
        status, headers, response_bytes = self.dispatch_request(
            method=method,
            raw_path=path,
            body_bytes=body_bytes,
            headers={},
        )
        return status, headers, response_bytes.decode("utf-8", errors="replace")

    def dispatch_request(
        self,
        method: str,
        raw_path: str,
        body_bytes: bytes,
        headers: Any,
    ) -> tuple[int, dict[str, str], bytes]:
        method = str(method).upper().strip()
        parsed = urlsplit(raw_path)
        path = parsed.path or "/"
        handler = self._routes.get(method, {}).get(path)
        if handler is None:
            return 404, {"Content-Type": "text/plain; charset=utf-8"}, b"Not Found"

        try:
            result = handler() if callable(handler) else handler
        except Exception as exc:
            message = f"Route handler failed: {exc}"
            return 500, {"Content-Type": "text/plain; charset=utf-8"}, message.encode("utf-8")

        try:
            return self._to_http_response(result)
        except Exception as exc:
            message = f"Route response failed: {exc}"
            return 500, {"Content-Type": "text/plain; charset=utf-8"}, message.encode("utf-8")

    @staticmethod
    def _headers_to_dict(headers: Any) -> dict[str, str]:
        if headers is None:
            return {}
        if isinstance(headers, dict):
            return {str(key): str(value) for key, value in headers.items()}
        try:
            return {str(key): str(value) for key, value in headers.items()}
        except Exception:
            return {}

    @staticmethod
    def _normalize_path(path: str) -> str:
        text = str(path).strip()
        if not text:
            return "/"
        if not text.startswith("/"):
            text = "/" + text
        return text

    @staticmethod
    def _to_http_response(result: Any) -> tuple[int, dict[str, str], bytes]:
        status = 200
        headers: dict[str, str] = {}
        body_value = result

        if isinstance(result, tuple):
            if len(result) == 2:
                body_value, status = result
            elif len(result) == 3:
                body_value, status, custom_headers = result
                headers = MiniFlaskApp._headers_to_dict(custom_headers)
            else:
                raise ValueError("Route tuple must be (body, status) or (body, status, headers).")

        if isinstance(body_value, (dict, list)):
            body_bytes = json.dumps(body_value).encode("utf-8")
            headers.setdefault("Content-Type", "application/json; charset=utf-8")
        elif isinstance(body_value, bytes):
            body_bytes = body_value
            headers.setdefault("Content-Type", "application/octet-stream")
        else:
            body_text = str(body_value)
            body_bytes = body_text.encode("utf-8")
            if MiniFlaskApp._looks_like_html(body_text):
                headers.setdefault("Content-Type", "text/html; charset=utf-8")
            else:
                headers.setdefault("Content-Type", "text/plain; charset=utf-8")

        return int(status), headers, body_bytes

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        stripped = text.lstrip().lower()
        if stripped.startswith("<!doctype html"):
            return True
        if not stripped.startswith("<"):
            return False
        markers = ("<html", "<head", "<body", "<div", "<span", "<h1", "<h2", "<p", "<a", "<main", "<section")
        return any(stripped.startswith(marker) for marker in markers)


class PixelWindow:
    """Small tkinter-based pixel window for simple E++ games."""

    def __init__(self) -> None:
        self.tk = None
        self.root = None
        self.canvas = None
        self.width = 0
        self.height = 0
        self.pixel_size = 1
        self.is_open = False
        self.background = "black"
        self.keys_down: set[str] = set()
        self.keys_pressed: set[str] = set()

    def open(
        self,
        width: int,
        height: int,
        title: str = "E++ Pixel Window",
        pixel_size: int = 10,
        background: str = "black",
    ) -> bool:
        width = int(width)
        height = int(height)
        pixel_size = int(pixel_size)
        if width <= 0 or height <= 0:
            raise ValueError("Window size must be greater than zero.")
        if pixel_size <= 0:
            raise ValueError("Pixel size must be greater than zero.")

        self.close()

        try:
            import tkinter as tk  # noqa: PLC0415
        except Exception as exc:
            raise RuntimeError("tkinter is not available on this Python installation.") from exc

        try:
            root = tk.Tk()
        except Exception as exc:
            raise RuntimeError(
                "I could not open a GUI window. If you are in a headless terminal, run this on desktop Python."
            ) from exc

        self.tk = tk
        self.root = root
        self.width = width
        self.height = height
        self.pixel_size = pixel_size
        self.background = str(background)
        self.keys_down.clear()
        self.keys_pressed.clear()

        self.root.title(str(title))
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.canvas = tk.Canvas(
            self.root,
            width=self.width * self.pixel_size,
            height=self.height * self.pixel_size,
            highlightthickness=0,
            bg=self.background,
        )
        self.canvas.pack()

        # Bind key handlers broadly so games still receive input even if
        # focus lands on canvas/root differently across platforms.
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.root.bind_all("<KeyPress>", self._on_key_press)
        self.root.bind_all("<KeyRelease>", self._on_key_release)
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)
        self._focus_window()
        self.is_open = True
        self._pump_events()
        return True

    def close(self) -> None:
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
        self.root = None
        self.canvas = None
        self.is_open = False
        self.keys_down.clear()
        self.keys_pressed.clear()

    def poll(self) -> bool:
        """Advance one frame of window events."""

        if not self.is_open:
            return False
        self.keys_pressed.clear()
        self._focus_window()
        return self._pump_events()

    def present(self) -> None:
        if not self.is_open:
            return
        self._pump_events()

    def clear(self, color: str | None = None) -> None:
        self._ensure_open()
        if color is not None:
            self.background = str(color)
            self.canvas.configure(bg=self.background)
        self.canvas.delete("all")

    def draw_pixel(self, x: int, y: int, color: str = "white") -> None:
        self._ensure_open()
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        px = x * self.pixel_size
        py = y * self.pixel_size
        self.canvas.create_rectangle(
            px,
            py,
            px + self.pixel_size,
            py + self.pixel_size,
            outline=str(color),
            fill=str(color),
            width=0,
        )

    def draw_rect(self, x: int, y: int, w: int, h: int, color: str = "white") -> None:
        self._ensure_open()
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        if w <= 0 or h <= 0:
            return
        px = x * self.pixel_size
        py = y * self.pixel_size
        self.canvas.create_rectangle(
            px,
            py,
            px + (w * self.pixel_size),
            py + (h * self.pixel_size),
            outline=str(color),
            fill=str(color),
            width=0,
        )

    def draw_text(self, x: int, y: int, text: Any, color: str = "white", size: int = 12) -> None:
        self._ensure_open()
        x = int(x)
        y = int(y)
        size = max(int(size), 6)
        px = x * self.pixel_size
        py = y * self.pixel_size
        self.canvas.create_text(
            px,
            py,
            text=str(text),
            fill=str(color),
            font=("Courier New", size, "bold"),
            anchor="nw",
        )

    def key_down(self, key_name: str) -> bool:
        return self._normalize_key(str(key_name)) in self.keys_down

    def key_pressed(self, key_name: str) -> bool:
        return self._normalize_key(str(key_name)) in self.keys_pressed

    def set_title(self, title: Any) -> None:
        self._ensure_open()
        self.root.title(str(title))

    def _ensure_open(self) -> None:
        if not self.is_open or self.root is None or self.canvas is None:
            raise RuntimeError("No window is open. Call 'call open_window with ...' first.")

    def _pump_events(self) -> bool:
        if not self.is_open or self.root is None:
            return False
        try:
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            self.close()
            return False
        return self.is_open

    def _on_close(self) -> None:
        self.close()

    def _focus_window(self) -> None:
        if self.root is None:
            return
        try:
            self.root.focus_force()
            if self.canvas is not None:
                self.canvas.focus_set()
        except Exception:
            pass

    @staticmethod
    def _normalize_key(key_name: str) -> str:
        key = key_name.lower()
        aliases = {
            "esc": "escape",
            "enter": "return",
            "spacebar": "space",
        }
        return aliases.get(key, key)

    def _on_key_press(self, event: Any) -> None:
        key = self._normalize_key(str(getattr(event, "keysym", "")))
        if not key:
            return
        self.keys_down.add(key)
        self.keys_pressed.add(key)

    def _on_key_release(self, event: Any) -> None:
        key = self._normalize_key(str(getattr(event, "keysym", "")))
        if not key:
            return
        self.keys_down.discard(key)


class EppInterpreter:
    """Walks and executes an E++ Program AST."""

    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[Any], None] = print,
        max_loop_iterations: int = 100_000,
    ) -> None:
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.global_scope: dict[str, Any] = {}
        self.scopes: list[dict[str, Any]] = [self.global_scope]
        self.max_loop_iterations = max_loop_iterations
        self.loop_iterations = 0
        self._active_expression_line = 1
        self.pixel_window = PixelWindow()

    def execute(self, program: Program) -> None:
        self.loop_iterations = 0
        try:
            self._execute_block(program.statements)
        except ReturnSignal as return_signal:
            raise EppRuntimeError(return_signal.line, "I found 'return' outside of a function.") from None
        except BreakSignal as break_signal:
            raise EppRuntimeError(break_signal.line, "I found 'stop' outside of a loop.") from None
        except ContinueSignal as continue_signal:
            raise EppRuntimeError(continue_signal.line, "I found 'skip' outside of a loop.") from None

    def _execute_block(self, statements: list[Statement]) -> None:
        for statement in statements:
            self._execute_statement(statement)

    def _execute_statement(self, statement: Statement) -> None:
        if isinstance(statement, SetStatement):
            value = self._evaluate_expression(statement.expression, statement.line)
            self._current_scope()[statement.name] = value
            return

        if isinstance(statement, SayStatement):
            value = self._evaluate_expression(statement.expression, statement.line)
            self.output_fn(value)
            return

        if isinstance(statement, AskStatement):
            prompt = self._evaluate_expression(statement.prompt_expression, statement.line)
            answer = self.input_fn(str(prompt))
            self._current_scope()[statement.target_name] = answer
            return

        if isinstance(statement, CreateListStatement):
            self._current_scope()[statement.name] = []
            return

        if isinstance(statement, AddStatement):
            self._apply_add(statement)
            return

        if isinstance(statement, SubtractStatement):
            value = self._evaluate_expression(statement.value_expression, statement.line)
            scope = self._scope_with_name(statement.target_name, statement.line)
            target = scope[statement.target_name]
            try:
                scope[statement.target_name] = target - value
            except Exception as exc:
                raise EppRuntimeError(
                    statement.line,
                    f"I couldn't subtract from '{statement.target_name}': {exc}",
                ) from None
            return

        if isinstance(statement, MultiplyStatement):
            value = self._evaluate_expression(statement.value_expression, statement.line)
            scope = self._scope_with_name(statement.target_name, statement.line)
            target = scope[statement.target_name]
            try:
                scope[statement.target_name] = target * value
            except Exception as exc:
                raise EppRuntimeError(
                    statement.line,
                    f"I couldn't multiply '{statement.target_name}': {exc}",
                ) from None
            return

        if isinstance(statement, DivideStatement):
            value = self._evaluate_expression(statement.value_expression, statement.line)
            scope = self._scope_with_name(statement.target_name, statement.line)
            target = scope[statement.target_name]
            try:
                scope[statement.target_name] = target / value
            except ZeroDivisionError:
                raise EppRuntimeError(statement.line, "Division by zero is not allowed.") from None
            except Exception as exc:
                raise EppRuntimeError(
                    statement.line,
                    f"I couldn't divide '{statement.target_name}': {exc}",
                ) from None
            return

        if isinstance(statement, RemoveStatement):
            scope = self._scope_with_name(statement.list_name, statement.line)
            list_value = scope[statement.list_name]
            if not isinstance(list_value, list):
                raise EppRuntimeError(statement.line, f"'{statement.list_name}' is not a list.")
            item = self._evaluate_expression(statement.value_expression, statement.line)
            try:
                list_value.remove(item)
            except ValueError:
                raise EppRuntimeError(
                    statement.line,
                    f"I couldn't remove {item!r} because it is not in '{statement.list_name}'.",
                ) from None
            return

        if isinstance(statement, IfStatement):
            self._run_if_statement(statement)
            return

        if isinstance(statement, RepeatTimesStatement):
            count_value = self._evaluate_expression(statement.count_expression, statement.line)
            if not isinstance(count_value, int):
                if isinstance(count_value, (float, bool)):
                    count_value = int(count_value)
                else:
                    raise EppRuntimeError(
                        statement.line,
                        "The 'repeat ... times' value must be a number.",
                    )
            if count_value < 0:
                raise EppRuntimeError(statement.line, "The repeat count must be zero or greater.")
            for _ in range(count_value):
                self._bump_loop_counter(statement.line)
                try:
                    self._execute_block(statement.body)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return

        if isinstance(statement, RepeatWhileStatement):
            while self._evaluate_condition(statement.condition):
                self._bump_loop_counter(statement.line)
                try:
                    self._execute_block(statement.body)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return

        if isinstance(statement, ForEachStatement):
            iterable = self._evaluate_expression(statement.iterable_expression, statement.line)
            try:
                iterator = iter(iterable)
            except TypeError:
                raise EppRuntimeError(statement.line, "I can only loop over iterable values.") from None

            for item in iterator:
                self._bump_loop_counter(statement.line)
                self._current_scope()[statement.item_name] = item
                try:
                    self._execute_block(statement.body)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return

        if isinstance(statement, FunctionDefStatement):
            self._current_scope()[statement.name] = EppFunction(
                name=statement.name,
                params=statement.params,
                body=statement.body,
                line=statement.line,
            )
            return

        if isinstance(statement, CallStatement):
            arguments = [self._evaluate_expression(arg, statement.line) for arg in statement.arguments]
            self._call_function(statement.name, arguments, statement.line)
            return

        if isinstance(statement, ReturnStatement):
            value = self._evaluate_expression(statement.expression, statement.line) if statement.expression else None
            raise ReturnSignal(value=value, line=statement.line)

        if isinstance(statement, BreakStatement):
            raise BreakSignal(statement.line)

        if isinstance(statement, ContinueStatement):
            raise ContinueSignal(statement.line)

        raise EppRuntimeError(1, f"Internal error: unsupported statement type {type(statement).__name__}.")

    def _apply_add(self, statement: AddStatement) -> None:
        value = self._evaluate_expression(statement.value_expression, statement.line)
        scope = self._scope_with_name(statement.target_name, statement.line)
        target = scope[statement.target_name]

        if isinstance(target, list):
            target.append(value)
            return

        try:
            scope[statement.target_name] = target + value
        except Exception as exc:
            raise EppRuntimeError(
                statement.line,
                f"I couldn't add to '{statement.target_name}': {exc}",
            ) from None

    def _run_if_statement(self, statement: IfStatement) -> None:
        if self._evaluate_condition(statement.condition):
            self._execute_block(statement.body)
            return

        for branch in statement.elif_branches:
            if self._evaluate_condition(branch.condition):
                self._execute_block(branch.body)
                return

        if statement.else_body is not None:
            self._execute_block(statement.else_body)

    def _bump_loop_counter(self, line: int) -> None:
        self.loop_iterations += 1
        if self.loop_iterations > self.max_loop_iterations:
            raise EppRuntimeError(
                line,
                "This loop seems to be running forever. Consider adding a stop condition.",
            )

    def _call_function(self, name: str, args: list[Any], line: int) -> Any:
        value: Any | None = None
        found = False
        for scope in reversed(self.scopes):
            if name in scope:
                value = scope[name]
                found = True
                break

        if not found:
            builtins = self._base_namespace()
            if name in builtins:
                value = builtins[name]
                found = True

        if not found:
            raise EppRuntimeError(line, f"I can't find '{name}'. Try defining it first.")

        if isinstance(value, EppFunction):
            return self._call_user_function(value, args, line)

        if not callable(value):
            raise EppRuntimeError(line, f"'{name}' is not a function.")

        try:
            return value(*args)
        except TypeError as exc:
            raise EppRuntimeError(line, f"I couldn't call '{name}' with those arguments: {exc}") from None
        except Exception as exc:
            raise EppRuntimeError(line, f"Function '{name}' failed: {exc}") from None

    def _call_user_function(self, function: EppFunction, args: list[Any], line: int) -> Any:
        if len(args) != len(function.params):
            raise EppRuntimeError(
                line,
                f"Function '{function.name}' expects {len(function.params)} argument(s), but got {len(args)}.",
            )

        local_scope = dict(zip(function.params, args))
        self.scopes.append(local_scope)
        try:
            self._execute_block(function.body)
        except ReturnSignal as signal:
            return signal.value
        finally:
            self.scopes.pop()
        return None

    def _evaluate_condition(self, condition: Condition) -> bool:
        if condition.operator == "truthy":
            return bool(self._evaluate_expression(condition.left_expression, condition.line))

        left = self._evaluate_expression(condition.left_expression, condition.line)
        right = self._evaluate_expression(condition.right_expression or "", condition.line)
        try:
            if condition.operator == ">":
                return left > right
            if condition.operator == "<":
                return left < right
            if condition.operator == ">=":
                return left >= right
            if condition.operator == "<=":
                return left <= right
            if condition.operator == "==":
                return left == right
            if condition.operator == "!=":
                return left != right
            if condition.operator == "contains":
                return right in left
            if condition.operator == "not_contains":
                return right not in left
        except Exception as exc:
            raise EppRuntimeError(condition.line, f"I couldn't evaluate this condition: {exc}") from None

        raise EppRuntimeError(condition.line, f"Unknown condition operator '{condition.operator}'.")

    def _evaluate_expression(self, expression: str, line: int) -> Any:
        normalized = self._normalize_expression(expression)
        call_expression = self._parse_call_expression(normalized)
        if call_expression:
            function_name, raw_arguments = call_expression
            arguments = [self._evaluate_expression(argument, line) for argument in self._split_arguments(raw_arguments)]
            return self._call_function(function_name, arguments, line)

        namespace = self._build_namespace()
        previous_line = self._active_expression_line
        self._active_expression_line = line
        try:
            return eval(normalized, {"__builtins__": {}}, namespace)
        except NameError as exc:
            missing_name_match = re.search(r"'([^']+)'", str(exc))
            missing_name = missing_name_match.group(1) if missing_name_match else "that name"
            raise EppRuntimeError(
                line,
                f"I can't find '{missing_name}'. Try setting it first.",
            ) from None
        except SyntaxError:
            raise EppRuntimeError(
                line,
                f"I couldn't read the expression '{expression}'.",
            ) from None
        except Exception as exc:
            raise EppRuntimeError(
                line,
                f"I couldn't evaluate '{expression}': {exc}",
            ) from None
        finally:
            self._active_expression_line = previous_line

    def _build_namespace(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for scope in self.scopes:
            merged.update(scope)

        namespace = self._base_namespace()
        for name, value in merged.items():
            if isinstance(value, EppFunction):
                namespace[name] = self._make_function_proxy(value)
            else:
                namespace[name] = value
        return namespace

    def _base_namespace(self) -> dict[str, Any]:
        return {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "range": range,
            "list": list,
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "round": round,
            "sorted": sorted,
            "random": self._fn_random,
            "random_int": random.randint,
            "random_float": random.uniform,
            "choice": random.choice,
            "sleep": time.sleep,
            "flask_app": self._fn_flask_app,
            "flask_get": self._fn_flask_get,
            "flask_post": self._fn_flask_post,
            "flask_run": self._fn_flask_run,
            "flask_test_request": self._fn_flask_test_request,
            "flask_html": self._fn_flask_html,
            "flask_fetch": self._fn_flask_fetch,
            "flask_fetch_json": self._fn_flask_fetch_json,
            "create_web_app": self._fn_flask_app,
            "when_someone_visits": self._fn_flask_get,
            "when_someone_posts": self._fn_flask_post,
            "start_web_server": self._fn_flask_run,
            "test_web_request": self._fn_flask_test_request,
            "make_html_page": self._fn_flask_html,
            "fetch_from_api": self._fn_flask_fetch,
            "fetch_json_from_api": self._fn_flask_fetch_json,
            "open_window": self._fn_open_window,
            "close_window": self._fn_close_window,
            "window_is_open": self._fn_window_is_open,
            "window_open": self._fn_window_is_open,
            "poll_window": self._fn_poll_window,
            "present": self._fn_present,
            "clear_screen": self._fn_clear_screen,
            "draw_pixel": self._fn_draw_pixel,
            "draw_rect": self._fn_draw_rect,
            "draw_text": self._fn_draw_text,
            "key_down": self._fn_key_down,
            "key_pressed": self._fn_key_pressed,
            "set_window_title": self._fn_set_window_title,
        }

    def _fn_open_window(
        self,
        width: Any,
        height: Any,
        title: Any = "E++ Pixel Window",
        pixel_size: Any = 10,
        background: Any = "black",
    ) -> bool:
        return self.pixel_window.open(
            width=int(width),
            height=int(height),
            title=str(title),
            pixel_size=int(pixel_size),
            background=str(background),
        )

    def _fn_close_window(self) -> None:
        self.pixel_window.close()

    def _fn_window_is_open(self) -> bool:
        return self.pixel_window.is_open

    def _fn_poll_window(self) -> bool:
        return self.pixel_window.poll()

    def _fn_present(self) -> None:
        self.pixel_window.present()

    def _fn_clear_screen(self, color: Any = "black") -> None:
        self.pixel_window.clear(str(color))

    def _fn_draw_pixel(self, x: Any, y: Any, color: Any = "white") -> None:
        self.pixel_window.draw_pixel(int(x), int(y), str(color))

    def _fn_draw_rect(self, x: Any, y: Any, w: Any, h: Any, color: Any = "white") -> None:
        self.pixel_window.draw_rect(int(x), int(y), int(w), int(h), str(color))

    def _fn_draw_text(
        self,
        x: Any,
        y: Any,
        text: Any,
        color: Any = "white",
        size: Any = 12,
    ) -> None:
        self.pixel_window.draw_text(int(x), int(y), text, str(color), int(size))

    def _fn_key_down(self, key_name: Any) -> bool:
        return self.pixel_window.key_down(str(key_name))

    def _fn_key_pressed(self, key_name: Any) -> bool:
        return self.pixel_window.key_pressed(str(key_name))

    def _fn_set_window_title(self, title: Any) -> None:
        self.pixel_window.set_title(title)

    @staticmethod
    def _as_flask_app(app: Any) -> MiniFlaskApp:
        if not isinstance(app, MiniFlaskApp):
            raise ValueError("That value is not a Flask app. Create one with 'call flask_app'.")
        return app

    def _fn_flask_app(self, name: Any = "E++ App") -> MiniFlaskApp:
        return MiniFlaskApp(str(name))

    def _fn_flask_get(self, app: Any, path: Any, handler_or_text: Any) -> bool:
        flask_app = self._as_flask_app(app)
        flask_app.add_route("GET", str(path), handler_or_text)
        return True

    def _fn_flask_post(self, app: Any, path: Any, handler_or_text: Any) -> bool:
        flask_app = self._as_flask_app(app)
        flask_app.add_route("POST", str(path), handler_or_text)
        return True

    def _fn_flask_run(
        self,
        app: Any,
        host: Any = "127.0.0.1",
        port: Any = 5000,
    ) -> bool:
        flask_app = self._as_flask_app(app)
        host_text = str(host)
        port_number = int(port)
        return flask_app.run(
            host=host_text,
            port=port_number,
            on_start=lambda url: self.output_fn(f"successful {url}"),
            on_request=lambda message: self.output_fn(message),
        )

    def _fn_flask_test_request(
        self,
        app: Any,
        method: Any = "GET",
        path: Any = "/",
        body: Any = "",
    ) -> str:
        flask_app = self._as_flask_app(app)
        _status, _headers, response_body = flask_app.simulate_request(
            method=str(method),
            path=str(path),
            body=body,
        )
        return response_body

    @staticmethod
    def _normalize_headers(headers: Any) -> dict[str, str]:
        if headers is None:
            return {}
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary like {\"Authorization\": \"Bearer ...\"}.")
        return {str(key): str(value) for key, value in headers.items()}

    @staticmethod
    def _fn_flask_html(html: Any, status: Any = 200) -> tuple[str, int, dict[str, str]]:
        return (
            str(html),
            int(status),
            {"Content-Type": "text/html; charset=utf-8"},
        )

    def _fn_flask_fetch(
        self,
        url: Any,
        method: Any = "GET",
        body: Any = None,
        headers: Any = None,
        timeout: Any = 10,
    ) -> str:
        url_text = str(url).strip()
        if not url_text:
            raise ValueError("Please provide a URL to fetch.")

        method_text = str(method).upper().strip() or "GET"
        timeout_value = float(timeout)
        request_headers = self._normalize_headers(headers)

        payload: bytes | None = None
        if body is not None:
            if isinstance(body, bytes):
                payload = body
            elif isinstance(body, (dict, list)):
                payload = json.dumps(body).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json; charset=utf-8")
            else:
                payload = str(body).encode("utf-8")

        request = urllib.request.Request(
            url=url_text,
            data=payload,
            headers=request_headers,
            method=method_text,
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_value) as response:
                raw = response.read()
                return raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            raise ValueError(f"API request failed with HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise ValueError(f"API request failed: {exc.reason}") from None

    def _fn_flask_fetch_json(
        self,
        url: Any,
        method: Any = "GET",
        body: Any = None,
        headers: Any = None,
        timeout: Any = 10,
    ) -> Any:
        text = self._fn_flask_fetch(
            url=url,
            method=method,
            body=body,
            headers=headers,
            timeout=timeout,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError("The API response was not valid JSON.") from None

    @staticmethod
    def _normalize_expression(expression: str) -> str:
        stripped = expression.strip()
        fetch_json_match = re.fullmatch(r"fetch\s+json\s+from\s+(.+)", stripped, flags=re.IGNORECASE)
        if fetch_json_match:
            expression = f"fetch_json_from_api({fetch_json_match.group(1).strip()})"
            stripped = expression.strip()

        fetch_match = re.fullmatch(r"fetch\s+from\s+(.+)", stripped, flags=re.IGNORECASE)
        if fetch_match:
            expression = f"fetch_from_api({fetch_match.group(1).strip()})"
            stripped = expression.strip()

        html_match = re.fullmatch(r"(?:html|web)\s+page\s+(.+)", stripped, flags=re.IGNORECASE)
        if html_match:
            expression = f"make_html_page({html_match.group(1).strip()})"
            stripped = expression.strip()

        if re.fullmatch(r"random(?:\s+number)?", stripped, flags=re.IGNORECASE):
            expression = "random()"
        else:
            between_match = re.fullmatch(
                r"random(?:\s+number)?\s+between\s+(.+?)\s+and\s+(.+)",
                stripped,
                flags=re.IGNORECASE,
            )
            if between_match:
                low = between_match.group(1).strip()
                high = between_match.group(2).strip()
                expression = f"random({low}, {high})"
            else:
                choice_match = re.fullmatch(r"random\s+choice\s+from\s+(.+)", stripped, flags=re.IGNORECASE)
                if choice_match:
                    expression = f"choice({choice_match.group(1).strip()})"

        expression = re.sub(r"\btrue\b", "True", expression, flags=re.IGNORECASE)
        expression = re.sub(r"\bfalse\b", "False", expression, flags=re.IGNORECASE)
        expression = re.sub(r"\bnothing\b", "None", expression, flags=re.IGNORECASE)
        return expression

    @staticmethod
    def _fn_random(minimum: Any = None, maximum: Any = None) -> Any:
        if minimum is None and maximum is None:
            return random.random()

        if minimum is None or maximum is None:
            raise ValueError("random(...) needs either 0 arguments or 2 arguments.")

        if isinstance(minimum, bool) or isinstance(maximum, bool):
            minimum = int(minimum)
            maximum = int(maximum)

        if isinstance(minimum, int) and isinstance(maximum, int):
            low = min(minimum, maximum)
            high = max(minimum, maximum)
            return random.randint(low, high)

        low = float(minimum)
        high = float(maximum)
        if low > high:
            low, high = high, low
        return random.uniform(low, high)

    @staticmethod
    def _parse_call_expression(expression: str) -> Optional[tuple[str, str]]:
        match = re.fullmatch(
            r"(?:call|run)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+with\s+(.+))?",
            expression.strip(),
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        return match.group(1), (match.group(2) or "").strip()

    @staticmethod
    def _split_arguments(raw: str) -> list[str]:
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

    def _make_function_proxy(self, function: EppFunction) -> Callable[..., Any]:
        def proxy(*args: Any) -> Any:
            return self._call_user_function(function, list(args), self._active_expression_line)

        return proxy

    def _scope_with_name(self, name: str, line: int) -> dict[str, Any]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope
        raise EppRuntimeError(line, f"I can't find '{name}'. Try 'set {name} to ...' first.")

    def _current_scope(self) -> dict[str, Any]:
        return self.scopes[-1]
