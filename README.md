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

### Option 2: Global Installation (using uv)

This makes the `nlm` command available system-wide using uv's tool management.

```bash
# 1. Clone the repository (if you haven't already)
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py

# 2. Install the tool using uv
#    This command installs the package from the current directory (.)
#    into an isolated environment managed by uv.
uv tool install .

# 3. Ensure uv's bin directory is in your PATH
#    uv usually prompts you to do this during installation,
#    but you can run this command manually if needed.
#    Follow the instructions provided by the command.
uv tool bin

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
