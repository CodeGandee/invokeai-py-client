# InvokeAI Python Client

A comprehensive exploration and demonstration of InvokeAI APIs with production-ready examples for AI workflow management.

## 🎯 Features

- **Board Management**: Create and organize image boards
- **Image Operations**: Retrieve and download generated images  
- **SDXL Workflows**: Submit and monitor text-to-image jobs
- **Error Handling**: Comprehensive job cancellation and exception management
- **Performance**: Direct database access (1600x faster monitoring)

## 🚀 Quick Examples

| Task | Demo Script | Description |
|------|-------------|-------------|
| **Boards** | [`api-demo-boards.py`](examples/api-demo-boards.py) | Board management and image organization |
| **Images** | [`api-demo-latest-image.py`](examples/api-demo-latest-image.py) | Latest image retrieval with optimization |
| **SDXL Jobs** | [`api-demo-job-submission.py`](examples/api-demo-job-submission.py) | Complete workflow submission and monitoring |
| **Exceptions** | [`api-demo-job-exception-handling.py`](examples/api-demo-job-exception-handling.py) | Error handling and job cancellation |

📋 **Complete Documentation**: [`docs/complete-project-summary.md`](docs/complete-project-summary.md)

## 🔍 API Exploration Resources

### Available Tools & Documentation

| Resource | Location | Purpose |
|----------|----------|---------|
| **OpenAPI Specification** | [`context/hints/invokeai-kb/invokeai-openapi.json`](context/hints/invokeai-kb/invokeai-openapi.json) | Complete API schema with endpoints, parameters, and responses |
| **API Endpoint List** | [`context/hints/invokeai-kb/invokeai-api-list.md`](context/hints/invokeai-kb/invokeai-api-list.md) | Human-readable API reference with descriptions |
| **InvokeAI Source Code** | [`context/refcode/InvokeAI/`](context/refcode/InvokeAI/) | Full InvokeAI source code for deep understanding |
| **Workflow Templates** | [`data/workflows/`](data/workflows/) | Ready-to-use SDXL and FLUX workflow JSON files |
| **Example API Calls** | [`data/api-calls/`](data/api-calls/) | Sample request payloads for workflow submission |

### Exploration Methodology

1. **Start with OpenAPI JSON**: Understand available endpoints and data structures
2. **Use Workflow Templates**: Load pre-built workflows from `data/workflows/`
3. **Study Source Code**: Reference `context/refcode/InvokeAI/` for implementation details
4. **Test with Examples**: Run demo scripts to see APIs in action
5. **Direct Database Access**: Use SQLite queries for performance optimization

### Key API Categories

| Category | Endpoints | Demo Coverage |
|----------|-----------|---------------|
| **Boards** | `/api/v1/boards/` | ✅ Task 1 |
| **Images** | `/api/v1/images/` | ✅ Task 2 |
| **Queue** | `/api/v1/queue/` | ✅ Task 3, 4 |
| **Workflows** | `/api/v1/workflows/` | ✅ Task 3 |

## 🛠️ Usage

### Prerequisites
- InvokeAI server running on `localhost:9090`
- Python 3.8+ with `requests` library
- SDXL models installed in InvokeAI

### Quick Test
```bash
# Test API connectivity
python examples/api-demo-boards.py

# Run complete SDXL workflow  
python examples/api-demo-job-submission.py
```

### Basic API Patterns
```python
import requests

# Standard API call pattern
response = requests.get("http://localhost:9090/api/v1/boards/")
data = response.json()

# Job submission pattern
workflow = json.load(open("data/workflows/sdxl-text-to-image.json"))
job_data = {"prepend": False, "batch": {"graph": workflow, "runs": 1}}
response = requests.post("http://localhost:9090/api/v1/queue/default/enqueue_batch", json=job_data)
```

## 📊 Performance Features

- **Direct Database Access**: SQLite queries for 1600x faster monitoring
- **Hybrid Monitoring**: Combines API calls with direct DB access
- **Error Recovery**: Comprehensive exception handling with retry patterns
- **Production Patterns**: Memory-efficient, enterprise-ready implementations

## 🗂️ Project Structure

```
examples/                    # API demonstration scripts
docs/                       # Implementation documentation  
data/                       # Workflows and example API calls
context/                    # Exploration resources and references
├── hints/invokeai-kb/     # API documentation and schemas
└── refcode/InvokeAI/      # InvokeAI source code reference
```

## 🔧 Development Setup

This project uses [pixi](https://pixi.sh/) for dependency management.

```bash
# Install dependencies
pixi install

# Run examples
pixi run python examples/api-demo-boards.py
```

### Available Commands
```bash
pixi run test             # Run tests
pixi run lint             # Code quality checks
pixi run docs-serve       # Serve documentation
```

## 📝 License

Licensed under the terms specified in the LICENSE file.