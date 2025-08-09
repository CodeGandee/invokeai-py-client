# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python client library for interacting with InvokeAI APIs. The project is in early development stage with minimal implementation so far.

**Current Status**: Basic project structure initialized with placeholder package at version 0.1.0 by CodeGandee.

## Project Structure

```
src/
  invokeai_py_client/     # Main package directory
    __init__.py          # Package initialization and version info
tests/                   # Test directory (currently empty)
context/                 # Reference materials and documentation
  refcode/InvokeAI/      # Full InvokeAI codebase for reference
scripts/                 # Utility scripts (currently empty)
docs/                    # Documentation (currently empty)
```

## Development Commands

Since this is a new Python project without established tooling yet, standard Python commands apply:

### Installation
```bash
# Install in development mode (when pyproject.toml is created)
pip install -e .
```

### Testing
```bash
# Run tests (when test framework is set up)
python -m pytest tests/
```

### Code Quality
```bash
# Format code (when linting tools are configured)
python -m ruff format .
python -m ruff check . --fix

# Type checking (when mypy is configured) 
python -m mypy src/
```

## Architecture Notes

### Reference Codebase
The `context/refcode/InvokeAI/` directory contains the full InvokeAI codebase as reference material. Key architectural patterns from InvokeAI:

- **API Structure**: FastAPI-based web API with router-based organization
- **Invocations System**: Node-based processing pipeline with base invocation classes
- **Model Management**: Sophisticated model loading and caching system  
- **Backend Services**: Separate backend for image processing, model operations
- **Configuration**: YAML-based configuration with pyproject.toml for dependencies

### InvokeAI API Patterns
The reference codebase shows InvokeAI uses:
- FastAPI routers in `invokeai/app/api/routers/`
- Pydantic models for API schemas
- Invocation-based processing in `invokeai/app/invocations/`
- Socket.IO for real-time communication
- Dependency injection pattern for services

### Expected Client Architecture
This Python client should likely implement:
- HTTP client for InvokeAI REST API endpoints
- WebSocket client for real-time events  
- Python-friendly interfaces for common workflows
- Model classes corresponding to InvokeAI's API schemas
- Async support for long-running operations

## Development Notes

- Project is currently a skeleton - no functional implementation yet
- No dependency management file (pyproject.toml, requirements.txt) exists yet
- No testing framework configured
- No CI/CD or development tooling set up
- Reference InvokeAI codebase available in context/ for API understanding

## Next Development Steps

1. Create pyproject.toml with dependencies (requests, websocket-client, pydantic)
2. Set up development tooling (ruff, mypy, pytest)
3. Implement basic HTTP client for InvokeAI API
4. Add API model classes based on InvokeAI schemas
5. Implement common workflow patterns
6. Add comprehensive tests
7. Set up documentation generation