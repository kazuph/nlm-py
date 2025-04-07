# nlm-py

Command-line interface for a Google service, written in Python.

## Installation

### Local Usage (using uv)
```bash
# Clone the repository
git clone https://github.com/kazuph/nlm-py.git
cd nlm-py

# Create virtual environment and install dependencies
uv venv
uv pip install -e .

# Authenticate (this will open a browser)
uv run nlm auth
```

### Global Installation (Recommended: using pipx)

Using pipx allows you to install Python applications without polluting the global environment:

```bash
# Install pipx (if you don't have it yet)
pip install pipx
pipx ensurepath

# Install nlm-py
pipx install git+https://github.com/kazuph/nlm-py.git
```

## Usage

Get help on available commands:
```bash
nlm --help
```

### Authentication

To authenticate with the service, run:
```bash
nlm auth
```
This retrieves Google authentication information from the default Chrome profile. To use a specific profile:
```bash
nlm auth ProfileName
```

## License

MIT
