# API Reference

Complete API documentation for the InvokeAI Python Client.

## Core Components

### [Client](client.md)
Main client class for connecting to InvokeAI server and managing sessions.

### [Workflow](workflow.md)
Workflow management, execution, and input handling.

### [Boards](boards.md)
Board and image management operations.

### [Fields](fields.md)
Type-safe field system for workflow inputs.

### [Models](models.md)
Data models and enumerations used throughout the library.

### [Utilities](utilities.md)
Helper functions and utility classes.

## Quick Reference

### Client Initialization

```python
from invokeai_py_client import InvokeAIClient

# Basic connection
client = InvokeAIClient(base_url="http://localhost:9090")

# With configuration
client = InvokeAIClient(
    base_url="http://localhost:9090",
    api_key="your-api-key",
    timeout=30
)
```

### Workflow Operations

```python
from invokeai_py_client.workflow import WorkflowDefinition

# Load workflow
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflow.json")
)

# Execute
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(submission)
```

### Board Management

```python
# Get board
board = client.board_repo.get_board_handle("my_board")

# Upload image
image_name = board.upload_image_file("image.png")

# Download image
image_data = board.download_image(image_name)
```

## Type System

The library uses a comprehensive type system with Pydantic models:

- **IvkField[T]**: Generic base for all field types
- **Primitive Fields**: String, Integer, Float, Boolean
- **Resource Fields**: Image, Board, Latents, Tensor
- **Model Fields**: ModelIdentifier, UNet, CLIP, Transformer, LoRA
- **Complex Fields**: Color, BoundingBox, Collection

## Error Handling

```python
from invokeai_py_client.exceptions import (
    InvokeAIError,
    ConnectionError,
    WorkflowError,
    BoardError,
    ValidationError
)

try:
    result = wf.submit_sync()
except WorkflowError as e:
    print(f"Workflow failed: {e}")
```

## Async Support

```python
import asyncio

async def generate():
    submission = await wf.submit_async()
    result = await wf.wait_for_completion_async(submission)
    return result

result = asyncio.run(generate())
```

## Next Steps

- Explore individual components in their dedicated pages
- Review [Examples](../examples/index.md) for practical usage
- Check [User Guide](../user-guide/index.md) for tutorials
- See [Developer Guide](../developer-guide/index.md) for advanced topics
