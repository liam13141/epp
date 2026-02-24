# E++ (English Plus Plus)

E++ is an interpreted programming language that uses plain-English statements
instead of traditional symbols and keywords.

It is implemented in Python, runs with the standard library only, and is
designed for:

- beginners learning programming flow
- readable scripts for non-programmers
- quick command-line experimentation

It is not designed as a secure sandbox or production replacement for Python.

## Contents

- [What E++ Is](#what-e-is)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Layout](#project-layout)
- [Beginner Website](#beginner-website)
- [Language Reference](#language-reference)
- [Readable Aliases](#readable-aliases)
- [CLI and REPL](#cli-and-repl)
- [Error Model](#error-model)
- [Examples](#examples)
- [Architecture](#architecture)
- [Development and Testing](#development-and-testing)
- [VS Code Integration](#vs-code-integration)
- [Limitations](#limitations)
- [Extending the Language](#extending-the-language)

## What E++ Is

E++ is line-oriented and block-based:

- one statement per line
- comments start with `#`
- blocks are explicit with closing words:
  - `end if`
  - `end repeat`
  - `end for`
  - `end define`

The interpreter uses Python-style dynamic values under the hood:

- integers, floats, strings, booleans
- lists
- function return values
- expression evaluation (safe-ish but not fully sandboxed)

## Installation

### Fast install from GitHub

```bash
python -m pip install --upgrade pip
python -m pip install git+https://github.com/liam13141/epp.git
```

Then run:

```bash
epp --version
epp
```

If `epp` is not found in your terminal yet, use:

```bash
python -m epp_runner --version
python -m epp_runner
```

### Install from local source

From the project root:

```bash
python -m pip install -e .
```

### One-command installer scripts

- Windows PowerShell: `.\install\install_epp.ps1`
- Linux/macOS: `sh ./install/install_epp.sh`

Full install guide: [INSTALL.md](INSTALL.md)

## Quick Start

### 1) Run a script

```bash
epp examples/hello.epp
```

### 2) Start the REPL

```bash
epp
```

### 3) Syntax check only (no execution)

```bash
epp --check examples/advanced_control_flow.epp
```

### 4) Run tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 5) Run the pixel window game

```bash
epp examples/pixel_dodge.epp
```

### 6) Run the built-in Flask-like web demo (no external deps)

```bash
epp examples/flask_hello.epp
```

### 7) Backward-compatible direct runner

```bash
python epp_runner.py examples/hello.epp
```

## Project Layout

- `epp_lexer.py`: source line tokenizer
- `epp_parser.py`: parser and AST node types
- `epp_interpreter.py`: runtime evaluator/executor
- `epp_runner.py`: CLI entry point and REPL shell
- `pyproject.toml`: package metadata (`pip install`)
- `install/`: one-command install scripts
- `examples/`: runnable `.epp` scripts
- `tests/`: regression tests (`unittest`)
- `corce/`: beginner learning website (HTML/CSS/JS)
- `.vscode/`: debug/task settings for one-click run

## Beginner Website

The `corce/` folder contains a beginner-focused website for learning E++.

What it includes:

- step-by-step lesson path with progress tracking
- two-way translator:
  - E++ -> Python
  - Python -> E++
- beginner checklist for first program setup
- quick quiz and cheat sheet

Open it by launching `corce/index.html` in your browser.

## Language Reference

This section documents the current implemented behavior.

### Readable Aliases

You can mix the classic E++ style and a more conversational style.

Examples of equivalent forms:

- `set x to 10` or `let x be 10`
- `set x to 10` or `put 10 into x`
- `say x` or `print x` or `show x`
- `add 5 to x` or `increase x by 5`
- `subtract 3 from x` or `decrease x by 3`
- `create list items` or `make list items`
- `remove 5 from items` or `take 5 from items`
- `if ... then` or `when ... then`
- `otherwise if ... then` or `or if ... then`
- `otherwise` or `else`
- `end if` or `finish if`
- `repeat 5 times` or `do 5 times`
- `repeat while condition` or `while condition do`
- `for each item in items` or `for every item in items`
- `end repeat` or `finish repeat`
- `end for` or `finish for`
- `define greet with name` or `function greet with name`
- `end define` or `end function` or `finish function`
- `return value` or `give back value`
- `call greet with "Ava"` or `run greet with "Ava"`
- `stop loop` or `break loop`
- `skip loop` or `next loop`

### Variables

```epp
set x to 10
let y be 20
put x + y into total
set name to "Alice"
set enabled to true
set empty_value to nothing
```

Notes:

- `set` always writes to the current scope.
- `true`, `false`, and `nothing` map to Python `True`, `False`, and `None`.

### Output

```epp
say "Hello, world"
print "Hello again"
show "Name: " + name
say x
say "Name: " + name
```

### Input

```epp
ask "What is your name? " and store in name
ask "Favorite color? " and save as color
```

Notes:

- `ask` stores text input (string).
- Convert manually when needed:

```epp
ask "Age: " and store in age_text
set age to int(age_text)
```

### Arithmetic and Mutation

```epp
set x to 10
add 5 to x
increase x by 2
subtract 3 from x
decrease x by 1
multiply x by 2
divide x by 4
```

`add` has dual behavior:

- numeric/string style `target + value` for normal variables
- append behavior for lists (`add value to mylist`)

### Lists

```epp
create list nums
make list more_nums
add 5 to nums
add 8 to nums
remove 5 from nums
take 8 from nums
say nums
```

### Conditionals

#### Basic

```epp
if x is greater than 10 then
  say "big"
otherwise
  say "small"
end if

when x is greater than 10 then
  print "big"
else
  print "small"
finish if
```

#### `otherwise if` chains

```epp
if score is at least 90 then
  say "A"
otherwise if score is at least 80 then
  say "B"
otherwise if score is at least 70 then
  say "C"
otherwise
  say "D"
end if

when score is at least 90 then
  show "A"
or if score is at least 80 then
  show "B"
else
  show "C"
finish if
```

#### Supported condition patterns

- `a is greater than b`
- `a is greater than or equal to b`
- `a is less than b`
- `a is less than or equal to b`
- `a is bigger than b`
- `a is smaller than b`
- `a is at least b`
- `a is at most b`
- `a equals b`
- `a is equal to b`
- `a is not b`
- `a is not equal to b`
- `a contains b`
- `a does not contain b`
- truthy expression:
  - `if some_value then`

### Loops

#### Repeat fixed count

```epp
repeat 5 times
  say "loop"
end repeat

do 5 times
  print "loop"
finish repeat
```

#### Repeat while condition

```epp
repeat while x is less than 10
  add 1 to x
end repeat

while x is less than 10 do
  increase x by 1
finish repeat
```

#### For each

```epp
for each item in mylist
  say item
end for

for every item in mylist
  print item
finish for
```

#### Loop control

```epp
if x equals 3 then
  skip repeat
end if

if x equals 8 then
  stop repeat
end if
```

Accepted forms:

- `skip`
- `skip repeat`
- `skip for`
- `skip loop`
- `next`
- `next loop`
- `stop`
- `stop repeat`
- `stop for`
- `stop loop`
- `break`
- `break loop`

`skip` outside loops and `stop` outside loops raise runtime errors.

### Functions

#### Define

```epp
define greet with name
  say "Hello " + name
end define

function greet with name
  print "Hello " + name
finish function
```

Parameter styles:

- comma-separated: `define f with a, b, c`
- `and`-separated: `define f with a and b and c`

#### Return

```epp
define square with n
  return n * n
end define

function square with n
  give back n * n
finish function
```

#### Call statement

```epp
call greet with "Alice"
run greet with "Alice"
```

#### Call expression (capture value)

```epp
set answer to call square with 12
set answer2 to run square with 20
say answer
```

### Expressions

Most Python-like expressions work:

```epp
set total to (price * count) + tax
set okay to x > 5 and y < 20
set top3 to sorted(scores)[0:3]
```

Built-in functions available in expressions:

- `len`, `str`, `int`, `float`, `bool`, `range`, `list`
- `abs`, `min`, `max`, `sum`, `round`, `sorted`
- `random()` or `call random` -> float `0.0` to `1.0`
- `random(min, max)` or `call random with min, max`
  - returns an `int` when both args are integers
  - returns a `float` otherwise
- `random_int(min, max)`
- `random_float(min, max)`
- `choice(items)`
- `sleep(seconds)`
- built-in Flask-like web functions (dependency-free):
  - `flask_app(name="E++ App")`
  - `flask_get(app, path, handler_or_text)`
  - `flask_post(app, path, handler_or_text)`
  - `flask_run(app, host="127.0.0.1", port=5000)`
  - `flask_test_request(app, method="GET", path="/", body="")` (test helper)
  - `flask_html(html, status=200)` / `make_html_page(...)` (forces HTML response)
  - `flask_fetch(url, method="GET", body=nothing, headers=nothing, timeout=10)`
  - `flask_fetch_json(url, method="GET", body=nothing, headers=nothing, timeout=10)`
  - beginner aliases:
    - `create_web_app`, `when_someone_visits`, `when_someone_posts`
    - `start_web_server`, `test_web_request`
    - `fetch_from_api`, `fetch_json_from_api`
- pixel window functions (for games):
  - `open_window(width, height, title="E++ Pixel Window", pixel_size=10, background="black")`
  - `window_is_open()` / `window_open()`
  - `poll_window()`
  - `present()`
  - `clear_screen(color="black")`
  - `draw_pixel(x, y, color="white")`
  - `draw_rect(x, y, w, h, color="white")`
  - `draw_text(x, y, text, color="white", size=12)`
  - `key_down(key_name)`
  - `key_pressed(key_name)`
  - `set_window_title(title)`
  - `close_window()`

User-defined functions are callable in expressions too.

Random-friendly plain-English expression forms are also supported:

```epp
set roll to random between 1 and 6
set noise to random
set card to random choice from deck
```

### Window and Pixel Games

E++ can open a real desktop window (via Python `tkinter`) for simple pixel games.

Minimal loop shape:

```epp
call open_window with 64, 48, "My Game", 10, "black"
set running to true

repeat while running
  call poll_window
  set open_now to call window_is_open
  if open_now == false then
    set running to false
  otherwise
    call clear_screen with "black"
    call draw_rect with 10, 10, 3, 3, "lime"
    call present
    call sleep with 0.03
  end if
end repeat
```

Input tips:

- Arrow keys: `"left"`, `"right"`, `"up"`, `"down"`
- Common keys: `"space"`, `"return"`, `"escape"`, `"a"`-`"z"`
- Use `key_down(...)` for held keys and `key_pressed(...)` for one-frame taps.

### Web Apps (Flask-like, No Dependencies)

E++ includes a tiny Flask-like web server built with Python's standard library.
You do not need to install `flask`.

Example:

```epp
set app to call create_web_app with "My Site"
call when_someone_visits with app, "/", call make_html_page with "<h1>Hello from E++</h1>"
say "Open http://127.0.0.1:5000"
call start_web_server with app, "127.0.0.1", 5000
```

Notes:

- `flask_get` / `flask_post` accept plain text, dictionaries/lists (auto-JSON), or callable handlers.
- callable handlers are called with no arguments.
- HTML can be returned with `flask_html(...)` / `make_html_page(...)`, or by returning a string that starts with common HTML tags.
- You can call external APIs with `fetch_from_api(...)` and `fetch_json_from_api(...)`.
- `flask_run` prints startup log: `successful http://host:port`
- `flask_run` logs every request: `request METHOD http://host:port/path -> status`
- stop the server with `Ctrl+C`.

Extra plain-English web statements are supported:

```epp
create a website called "Easy Site" and store in app
when someone visits "/" on app show html page "<h1>Welcome</h1>"
fetch json from "https://catfact.ninja/fact" and store in fact_data
```

### Comments and Blank Lines

```epp
# This is a comment

set x to 1
```

## CLI and REPL

### CLI

```bash
python epp_runner.py [options] [script]
```

Options:

- `--check`: parse only, do not execute
- `--max-loop-iterations N`: loop safety cap (default `100000`)
- `--version`: show interpreter version

Examples:

```bash
python epp_runner.py --check examples/hello.epp
python epp_runner.py --max-loop-iterations 20000 examples/number_quest.epp
python epp_runner.py --version
```

### REPL

Start:

```bash
python epp_runner.py
```

Exit commands:

- `exit`
- `quit`

REPL utility commands:

- `:help` - show REPL commands
- `:vars` - print global variables/functions
- `:reset` - clear current environment
- `:load <file>` - execute a file into current REPL session

Notes:

- multi-line blocks are supported in REPL; the prompt changes to `... ` until
  an `end ...` closes the block
- variables persist across REPL entries unless `:reset` is used

## Error Model

E++ uses friendly English errors with line numbers.

### Parse error example

```text
Oops! On line 4, I don't understand 'grabb x'. Did you mean 'set x to 10'?
```

### Runtime error examples

- undefined variable
- division by zero
- list remove for missing item
- wrong function argument count
- `return` outside function
- `stop` or `skip` outside loops
- runaway loop safety cap exceeded

The parser also reports missing block closures clearly, for example when
`end if` is missing.

## Examples

- `examples/hello.epp`: basic syntax walkthrough
- `examples/counter.epp`: repeat-while loop and branching
- `examples/functions_and_lists.epp`: functions + list operations
- `examples/advanced_control_flow.epp`: `otherwise if`, `contains`, `skip`/`stop`
- `examples/number_quest.epp`: multi-round terminal game with scoring
- `examples/readable_basics.epp`: conversational alias style for beginners
- `examples/pixel_dodge.epp`: windowed pixel game (movement, collision, score)
- `examples/flask_hello.epp`: dependency-free Flask-like web server demo
- `examples/test.epp`: scratch file for quick experiments

Recommended first run order:

1. `hello.epp`
2. `counter.epp`
3. `functions_and_lists.epp`
4. `advanced_control_flow.epp`
5. `number_quest.epp`
6. `pixel_dodge.epp`
7. `flask_hello.epp`

## Architecture

### 1) Lexer (`epp_lexer.py`)

- tokenizes by lines, preserving line numbers
- classifies lines as:
  - `STATEMENT`
  - `COMMENT`
  - `BLANK`
- handles UTF-8 BOM and null-character checks

### 2) Parser (`epp_parser.py`)

- turns line tokens into AST nodes
- handles block structure without indentation
- supports nested control-flow and nested function bodies
- includes typo suggestions for unknown commands

Main statement nodes include:

- assignments and IO
- math/list operations
- `if`/`otherwise if`/`otherwise`
- `repeat` and `for each`
- function define/call/return
- loop controls (`stop`, `skip`)

### 3) Interpreter (`epp_interpreter.py`)

- executes AST statements
- manages scope stack for functions
- evaluates expressions with controlled namespace
- provides friendly runtime errors
- enforces loop-iteration safety limit

### 4) Runner (`epp_runner.py`)

- CLI entry point
- file execution mode
- REPL mode with helper commands
- syntax-check mode (`--check`)

## Development and Testing

### Python version

Use Python 3.11+ (3.12 recommended).

### Compile check

```bash
python -m py_compile epp_lexer.py epp_parser.py epp_interpreter.py epp_runner.py
```

### Run tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Add a new language feature safely

1. update parser AST and syntax handling
2. update interpreter execution logic
3. add/update examples
4. add regression tests
5. update this README

## VS Code Integration

Included in `.vscode/`:

- run/debug launch configs for current `.epp` file
- build tasks for E++ run and REPL
- Code Runner mapping for `.epp` extension
- recommended extensions list

Typical workflow:

1. open a `.epp` file
2. use Run and Debug -> `Run Current E++ File`
3. or press `Ctrl+Shift+B` for task-based run

## Limitations

Current intentional limitations:

- no import/module system
- no dictionaries or custom classes via E++ syntax
- no file IO statements in E++ syntax
- no static type checking
- no debugger/step tracer yet
- windowed graphics require desktop Python with `tkinter` available

Security note:

- expressions are evaluated with restricted built-ins, but this is not a
  hardened sandbox
- do not run untrusted `.epp` scripts

## Extending the Language

If you want to add new statements:

1. Add an AST node in `epp_parser.py`.
2. Add parse rule(s) in `_parse_statement`.
3. Add execution logic in `epp_interpreter.py`.
4. Add tests in `tests/test_epp.py`.
5. Add a minimal example in `examples/`.

Good first extension ideas:

- dictionaries and key/value syntax
- string helper statements (`uppercase`, `split`, etc.)
- file read/write statements
- `try`/`catch` style beginner-friendly error handling
- `--trace` CLI mode for step-by-step execution
