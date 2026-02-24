"""Regression tests for the E++ language runtime."""

from __future__ import annotations

import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from epp_interpreter import EppInterpreter, EppRuntimeError
from epp_lexer import EppLexer
from epp_parser import EppParser
from epp_runner import execute_source


def run_source(source: str, inputs: list[str] | None = None) -> tuple[int, list[str]]:
    """Execute E++ source and return (status, captured_output)."""

    queued_inputs = list(inputs or [])
    output: list[str] = []

    def input_fn(prompt: str) -> str:
        output.append(prompt)
        if not queued_inputs:
            return ""
        return queued_inputs.pop(0)

    interpreter = EppInterpreter(input_fn=input_fn, output_fn=lambda value: output.append(str(value)))
    status = execute_source(source, interpreter)
    return status, output


class EppLanguageTests(unittest.TestCase):
    def test_readable_aliases_for_variables_math_and_output(self) -> None:
        status, output = run_source(
            """
let total be 10
increase total by 5
decrease total by 3
show total
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["12"])

    def test_readable_aliases_for_blocks_functions_and_calls(self) -> None:
        status, output = run_source(
            """
function grade with score
  when score is bigger than 89 then
    give back "A"
  or if score is greater than or equal to 80 then
    give back "B"
  else
    give back "C"
  finish if
finish function

make list nums
add 1 to nums
add 2 to nums
for every item in nums
  print item
finish for

set letter to run grade with 82
say letter
do 1 times
  say "once"
finish repeat
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["1", "2", "B", "once"])

    def test_readable_aliases_for_input_and_assignment(self) -> None:
        status, output = run_source(
            """
ask "Name? " and save as name
put "Hi " + name into message
print message
""".strip(),
            inputs=["Sam"],
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["Name? ", "Hi Sam"])

    def test_end_function_alias(self) -> None:
        status, output = run_source(
            """
function identity with x
  give back x
end function
say run identity with 4
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["4"])

    def test_otherwise_if_branch(self) -> None:
        status, output = run_source(
            """
set score to 85
if score is greater than 90 then
  say "A"
otherwise if score is at least 80 then
  say "B"
otherwise
  say "C"
end if
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["B"])

    def test_otherwise_if_preserves_case_in_string_literals(self) -> None:
        status, output = run_source(
            """
set mode_name to "Normal"
if mode_name equals "Easy" then
  say "easy"
otherwise if mode_name equals "Normal" then
  say "normal"
otherwise
  say "other"
end if
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["normal"])

    def test_break_and_continue(self) -> None:
        status, output = run_source(
            """
set total to 0
repeat 10 times
  add 1 to total
  if total equals 3 then
    skip repeat
  end if
  if total equals 6 then
    stop repeat
  end if
end repeat
say total
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["6"])

    def test_call_expression_and_return_value(self) -> None:
        status, output = run_source(
            """
define add_two with a and b
  return a + b
end define
set value to call add_two with 3, 4
say value
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["7"])

    def test_contains_condition(self) -> None:
        status, output = run_source(
            """
create list items
add 2 to items
add 5 to items
if items contains 5 then
  say "found"
otherwise
  say "missing"
end if
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["found"])

    def test_loop_safety_limit(self) -> None:
        source = """
set x to 1
repeat while x equals 1
  say "loop"
end repeat
""".strip()
        tokens = EppLexer().tokenize(source)
        program = EppParser(tokens).parse()
        interpreter = EppInterpreter(output_fn=lambda _: None, max_loop_iterations=10)
        with self.assertRaises(EppRuntimeError) as context:
            interpreter.execute(program)
        self.assertIn("running forever", str(context.exception))

    def test_pixel_game_builtins_are_available(self) -> None:
        interpreter = EppInterpreter(output_fn=lambda _: None)
        namespace = interpreter._base_namespace()
        expected = [
            "random",
            "flask_app",
            "flask_get",
            "flask_post",
            "flask_run",
            "flask_test_request",
            "flask_html",
            "flask_fetch",
            "flask_fetch_json",
            "create_web_app",
            "when_someone_visits",
            "when_someone_posts",
            "start_web_server",
            "test_web_request",
            "make_html_page",
            "fetch_from_api",
            "fetch_json_from_api",
            "open_window",
            "close_window",
            "window_is_open",
            "window_open",
            "poll_window",
            "present",
            "clear_screen",
            "draw_pixel",
            "draw_rect",
            "draw_text",
            "key_down",
            "key_pressed",
            "set_window_title",
        ]
        for name in expected:
            self.assertIn(name, namespace)
            self.assertTrue(callable(namespace[name]))

    def test_random_support_in_expressions_and_plain_english_forms(self) -> None:
        status, output = run_source(
            """
set r1 to call random with 1, 6
if r1 < 1 or r1 > 6 then
  say "bad1"
otherwise
  say "ok1"
end if

set r2 to random between 10 and 20
if r2 < 10 or r2 > 20 then
  say "bad2"
otherwise
  say "ok2"
end if

set r3 to random
if r3 >= 0 and r3 <= 1 then
  say "ok3"
otherwise
  say "bad3"
end if

create list pool
add "A" to pool
add "B" to pool
set picked to random choice from pool
if pool contains picked then
  say "ok4"
otherwise
  say "bad4"
end if
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["ok1", "ok2", "ok3", "ok4"])

    def test_flask_like_builtin_routes_work_without_external_dependencies(self) -> None:
        interpreter = EppInterpreter(output_fn=lambda _: None)
        namespace = interpreter._base_namespace()

        app = namespace["flask_app"]("Demo")
        namespace["flask_get"](app, "/", "Hello from E++ web")
        namespace["flask_post"](app, "/submit", {"ok": True})

        status, headers, body = app.simulate_request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", headers.get("Content-Type", ""))
        self.assertEqual(body, "Hello from E++ web")

        status, headers, body = app.simulate_request("POST", "/submit", "ignored")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        self.assertIn('"ok": true', body)

        status, _headers, body = app.simulate_request("GET", "/missing")
        self.assertEqual(status, 404)
        self.assertEqual(body, "Not Found")

    def test_flask_like_builtins_are_callable_from_epp(self) -> None:
        status, output = run_source(
            """
set app to call flask_app with "Mini Site"
call flask_get with app, "/", "Home"
set body to call flask_test_request with app, "GET", "/"
say body
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["Home"])

    def test_flask_run_logs_successful_with_server_url(self) -> None:
        output: list[str] = []
        interpreter = EppInterpreter(output_fn=lambda value: output.append(str(value)))
        namespace = interpreter._base_namespace()
        app = namespace["flask_app"]("Demo")

        def fake_run(
            host: str = "127.0.0.1",
            port: int = 5000,
            on_start: Any = None,
            on_request: Any = None,
        ) -> bool:
            if on_start is not None:
                on_start(f"http://{host}:{port}")
            if on_request is not None:
                on_request(f"request GET http://{host}:{port}/health -> 200")
            return True

        app.run = fake_run  # type: ignore[method-assign]

        result = namespace["flask_run"](app, "127.0.0.1", 5050)
        self.assertTrue(result)
        self.assertEqual(
            output,
            [
                "successful http://127.0.0.1:5050",
                "request GET http://127.0.0.1:5050/health -> 200",
            ],
        )

    def test_flask_can_return_html(self) -> None:
        interpreter = EppInterpreter(output_fn=lambda _: None)
        namespace = interpreter._base_namespace()
        app = namespace["flask_app"]("Demo")
        html = namespace["flask_html"]("<h1>Hello HTML</h1>")
        namespace["flask_get"](app, "/", html)

        status, headers, body = app.simulate_request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertEqual(body, "<h1>Hello HTML</h1>")

    def test_fetch_api_helpers(self) -> None:
        class ApiHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/json":
                    payload = json.dumps({"status": "ok", "count": 2}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                payload = b"plain-response"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            interpreter = EppInterpreter(output_fn=lambda _: None)
            namespace = interpreter._base_namespace()
            base_url = f"http://127.0.0.1:{port}"

            text = namespace["fetch_from_api"](f"{base_url}/text")
            self.assertEqual(text, "plain-response")

            data = namespace["fetch_json_from_api"](f"{base_url}/json")
            self.assertIsInstance(data, dict)
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("count"), 2)

            status, output = run_source(
                f"""
fetch from "{base_url}/text" and store in txt
say txt
fetch json from "{base_url}/json" and store in payload
say payload["status"]
""".strip()
            )
            self.assertEqual(status, 0)
            self.assertEqual(output, ["plain-response", "ok"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1.0)

    def test_english_web_syntax_is_supported(self) -> None:
        status, output = run_source(
            """
create a website called "Easy Site" and store in app
when someone visits "/" on app show html page "<h1>Easy</h1>"
set body to call test_web_request with app, "GET", "/"
say body
""".strip()
        )
        self.assertEqual(status, 0)
        self.assertEqual(output, ["<h1>Easy</h1>"])


if __name__ == "__main__":
    unittest.main()
