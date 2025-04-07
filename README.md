# nlm-py

Command-line interface for a Google service, written in Python.

## Installation

### Option 1: Local Usage (using uv)

This is useful for development or isolated testing.

```bash
# Clone the repository
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py

# Create virtual environment and install dependencies
uv venv
uv pip install -e .

# Authenticate (this will open a browser)
uv run nlm auth

# Run other commands (e.g., get help)
uv run nlm --help
```

### Option 2: Global Installation (using uv + pipx)

This makes the `nlm` command available system-wide.

```bash
# 1. Clone the repository (if you haven't already)
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py

# 2. Build the wheel file
uv build

# 3. Install pipx (if you don't have it yet)
pip install pipx
pipx ensurepath

# 4. Install the built wheel using pipx
#    (Replace the version number if it differs)
pipx install dist/nlm_py-0.1.0-py3-none-any.whl --force

# Now you can run nlm commands directly
nlm --help
nlm auth
```

## Usage

Once installed (either locally or globally), you can use the `nlm` command.

**If installed locally (Option 1):** Prefix commands with `uv run`.
```bash
uv run nlm --help
uv run nlm auth
# etc.
```

**If installed globally (Option 2):** Run commands directly.
```bash
nlm --help
nlm auth
# etc.
```

### Authentication Details

The `nlm auth` command retrieves Google authentication information from the default Chrome profile. To use a specific profile:

```bash
# Local install:
uv run nlm auth ProfileName

# Global install:
nlm auth ProfileName
```

## License

MIT
