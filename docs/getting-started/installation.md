# Installation

This guide covers different ways to install the InvokeAI Python Client.

## Installation Methods

### Using Pixi (Recommended)

[Pixi](https://pixi.sh/) provides the best development experience with automatic dependency management:

```bash
# Install pixi if you haven't already
curl -fsSL https://pixi.sh/install.sh | bash

# Add to your project
pixi add invokeai-py-client

# Or clone and develop
git clone https://github.com/CodeGandee/invokeai-py-client
cd invokeai-py-client
pixi run dev-setup
```

### Using pip

Install from PyPI:

```bash
pip install invokeai-py-client
```

Or install the latest development version:

```bash
pip install git+https://github.com/CodeGandee/invokeai-py-client.git
```

### Development Installation

For contributing or testing the latest features:

```bash
# Clone the repository
git clone https://github.com/CodeGandee/invokeai-py-client
cd invokeai-py-client

# Using pixi (recommended)
pixi run dev-setup

# Or using pip
pip install -e ".[dev]"
```

## Dependencies

The client installs these core dependencies:

- requests — HTTP client for REST API calls
- python-socketio — Socket.IO client for real-time events
- pydantic — Data validation and models
- Pillow — Image operations (used in examples)
- rich — Terminal formatting (used in examples)

Note:
- JSONPath libraries are not required; the client performs value substitution without JSONPath.

## Verifying Installation

Test your installation with this simple script:

```python
from invokeai_py_client import InvokeAIClient

# Connect to your InvokeAI server
client = InvokeAIClient.from_url("http://localhost:9090")

# Quick probe (True/False)
print("Health:", client.health_check())

# List boards (requires a running server)
try:
    boards = client.board_repo.list_boards()
    print(f"Boards available: {len(boards)}")
except Exception as e:
    print(f"Failed to list boards (is the server running?): {e}")
```

## Environment Setup

### InvokeAI Server

Ensure your InvokeAI server is running:

```bash
# Default server location
http://localhost:9090

# Check if accessible
curl http://localhost:9090/api/v1/app/version
```

### Python Environment

We recommend using a virtual environment:

=== "venv"

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install invokeai-py-client
    ```

=== "conda"

    ```bash
    conda create -n invokeai python=3.10
    conda activate invokeai
    pip install invokeai-py-client
    ```

=== "pixi"

    ```bash
    pixi init
    pixi add python>=3.9
    pixi add invokeai-py-client
    ```

## Platform-Specific Notes

### Windows

- Use PowerShell or Windows Terminal for best results
- Path separators: Use raw strings (r"C:\path\to\file") or forward slashes

### macOS

- Install Xcode Command Line Tools if prompted
- Use Homebrew to install Python 3.9+ if needed

### Linux

- Most distributions include Python 3.9+
- Install python3-dev package if you encounter build errors

## Troubleshooting

### Connection Refused

If you get a connection error:

1. Check if InvokeAI is running: `curl http://localhost:9090/api/v1/app/version`
2. Verify the correct URL and port
3. Check firewall settings

### Import Errors

If imports fail:

1. Verify installation: `pip show invokeai-py-client`
2. Check Python version: `python --version` (must be 3.9+)
3. Reinstall: `pip install --force-reinstall invokeai-py-client`

### SSL/TLS Errors

For self-signed certificates:

```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

client = InvokeAIClient.from_url("https://localhost:9090", verify_ssl=False)
```

!!! warning "Security Note"
    Only disable SSL verification for local development or trusted servers.

## Next Steps

With the client installed, proceed to the [Quick Start](quickstart.md) guide to run your first workflow!