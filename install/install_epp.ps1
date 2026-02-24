param(
  [switch]$FromGithub,
  [string]$RepoUrl = "https://github.com/liam13141/epp.git",
  [string]$EnvDir = ".epp-env"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python was not found on PATH. Install Python 3.11+ first."
}

Write-Host "Creating virtual environment at '$EnvDir'..."
python -m venv $EnvDir

$venvPython = Join-Path $EnvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Virtual environment was created, but '$venvPython' was not found."
}

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

if ($FromGithub) {
  Write-Host "Installing E++ from GitHub..."
  & $venvPython -m pip install "git+$RepoUrl"
} else {
  Write-Host "Installing E++ from local folder..."
  & $venvPython -m pip install -e .
}

Write-Host ""
Write-Host "Install successful."
Write-Host "Activate with:"
Write-Host "  .\$EnvDir\Scripts\Activate.ps1"
Write-Host "Then run:"
Write-Host "  epp --version"
Write-Host "  epp examples/hello.epp"
