# Contributing

Guidelines for contributing to InvokeAI Python Client.

## Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/invokeai-py-client.git
cd invokeai-py-client

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Style

- Use Black for formatting
- Follow PEP 8 guidelines
- Type hints required for public APIs
- Docstrings for all public functions

## Testing

```bash
# Run tests
python -m pytest tests/

# With coverage
python -m pytest tests/ --cov=invokeai_py_client

# Run specific test
python -m pytest tests/test_workflow.py::TestWorkflow
```

## Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Code Review Checklist

- [ ] Tests pass
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Changelog updated
- [ ] No breaking changes

See [Testing](testing.md) for test guidelines.
