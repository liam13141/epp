# Install E++

E++ can now be installed like a normal Python tool.

## Option 1: Install from GitHub (recommended for new users)

```bash
python -m pip install --upgrade pip
python -m pip install git+https://github.com/liam13141/epp.git
```

Then run:

```bash
epp --version
epp
```

## Option 2: Install from a local clone

From the project root:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Then run:

```bash
epp examples/hello.epp
```

## Option 3: One-command installer scripts

### Windows (PowerShell)

From project root:

```powershell
.\install\install_epp.ps1
```

Install directly from GitHub:

```powershell
.\install\install_epp.ps1 -FromGithub
```

### Linux/macOS

From project root:

```bash
sh ./install/install_epp.sh
```

Install directly from GitHub:

```bash
FROM_GITHUB=1 sh ./install/install_epp.sh
```

## If `epp` command is not found

Use the module form:

```bash
python -m epp_runner --version
python -m epp_runner examples/hello.epp
```

Or restart your terminal so PATH refreshes after install.
