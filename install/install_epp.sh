#!/usr/bin/env sh
set -eu

FROM_GITHUB="${FROM_GITHUB:-0}"
REPO_URL="${REPO_URL:-https://github.com/liam13141/epp.git}"
ENV_DIR="${ENV_DIR:-.epp-env}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found on PATH. Install Python 3.11+ first." >&2
  exit 1
fi

echo "Creating virtual environment at '$ENV_DIR'..."
python3 -m venv "$ENV_DIR"

VENV_PY="$ENV_DIR/bin/python"
if [ ! -f "$VENV_PY" ]; then
  echo "Virtual environment created, but '$VENV_PY' was not found." >&2
  exit 1
fi

echo "Upgrading pip..."
"$VENV_PY" -m pip install --upgrade pip

if [ "$FROM_GITHUB" = "1" ]; then
  echo "Installing E++ from GitHub..."
  "$VENV_PY" -m pip install "git+$REPO_URL"
else
  echo "Installing E++ from local folder..."
  "$VENV_PY" -m pip install -e .
fi

echo
echo "Install successful."
echo "Activate with:"
echo "  ./$ENV_DIR/bin/activate"
echo "Then run:"
echo "  epp --version"
echo "  epp examples/hello.epp"
