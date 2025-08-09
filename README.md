# InvokeAI Python Client

A Python client library for interacting with InvokeAI APIs.

## Development Setup

This project uses [pixi](https://pixi.sh/) for dependency management, integrated within `pyproject.toml`.

### Quick Start

1. **Install pixi** (if not already installed):
   ```bash
   # On Windows
   iwr -useb https://pixi.sh/install.ps1 | iex
   
   # On macOS/Linux
   curl -fsSL https://pixi.sh/install.sh | bash
   ```

2. **Install dependencies**:
   ```bash
   pixi install
   ```

3. **Activate the development environment**:
   ```bash
   pixi shell
   # or run commands directly:
   pixi run python --version
   ```

### Available Environments

- **default**: Base environment with core dependencies
- **dev**: Development environment with testing and linting tools
- **docs**: Documentation environment with mkdocs
- **test**: Testing environment with additional test utilities

### Available Tasks

```bash
# Development
pixi run install          # Install the package in editable mode
pixi run dev-setup        # Setup development environment

# Testing
pixi run test             # Run tests
pixi run test-cov         # Run tests with coverage

# Code Quality
pixi run lint             # Check code with ruff
pixi run lint-fix         # Fix auto-fixable issues
pixi run format           # Format code with ruff
pixi run typecheck        # Check types with mypy
pixi run quality          # Run lint, typecheck, and test

# Documentation
pixi run docs-serve       # Serve docs locally
pixi run docs-build       # Build documentation

# Pre-commit
pixi run pre-commit-install  # Install pre-commit hooks
pixi run pre-commit-run      # Run pre-commit on all files
```

### Environment Management

Switch between environments:
```bash
pixi run -e dev python --version    # Run in dev environment
pixi run -e test pytest             # Run tests in test environment
pixi run -e docs mkdocs serve       # Serve docs
```

## Project Structure

```
src/
  invokeai_py_client/     # Main package
tests/                    # Test files
docs/                     # Documentation
pyproject.toml           # Project configuration with pixi integration
```
