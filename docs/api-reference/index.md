# API Reference

Complete API documentation for the InvokeAI Python Client.

## Core Components

### [📡 Client](client.md)
**Main client interface** - Connection management, repositories, and HTTP/Socket.IO operations
- `InvokeAIClient` class with `from_url()` helper
- Repository properties: `board_repo`, `workflow_repo`, `dnn_model_repo`  
- Connection methods: `health_check()`, `socketio_session()`
- Context management and resource cleanup

### [⚡ Workflow](workflow.md)  
**Workflow execution system** - Definition loading, input management, and job monitoring
- `WorkflowDefinition.from_file()` for loading GUI exports
- `WorkflowHandle` for input discovery and execution control
- Submission methods: `submit_sync()`, `wait_for_completion_sync()`
- Output mapping: `map_outputs_to_images()` for result extraction

### [🖼️ Boards](boards.md)
**Image organization** - Board management and image operations using Repository pattern
- `BoardRepository` for board lifecycle (create, delete, list)
- `BoardHandle` for per-board operations (upload, download, organize)
- Uncategorized board handling with special "none" board_id
- Image categorization and metadata management

### [🔧 Fields](fields.md)
**Type-safe input system** - Pydantic-based field types for workflow inputs
- Field categories: Primitive, Resource, Model, Complex, Enum
- Base class: `IvkField[T]` with validation and API conversion
- Specific types: `IvkStringField`, `IvkImageField`, `IvkModelIdentifierField`
- Default constructability requirement for all field types

### [📊 Models](models.md)
**Data structures** - Pydantic models and enumerations for API integration  
- Enums: `JobStatus`, `ImageCategory`, `BaseModelEnum`
- Models: `IvkImage`, `IvkJob`, `IvkDnnModel`
- Type-safe API response handling and serialization
- Workflow execution state tracking

### [🛠️ Utilities](utilities.md)
**Helper patterns** - Practical utilities for common operations
- Input discovery: `preview()`, index map management
- Workflow monitoring: async submission patterns
- Validation helpers and type-safe field access
- Reliability patterns and error handling

## Quick Reference

### 🚀 Client Initialization & Health Check

```python
from invokeai_py_client import InvokeAIClient

# Recommended: URL-based initialization with automatic parsing
client = InvokeAIClient.from_url("http://localhost:9090")

# Alternative: explicit parameters
client = InvokeAIClient(
    host="192.168.1.100", 
    port=9090,
    use_https=True,
    timeout=60.0
)

# Verify connection
if client.health_check():
    print("✅ InvokeAI server is reachable")
else:
    print("❌ Cannot connect to InvokeAI server")
```

### 🎯 Essential Workflow Pattern

```python
from invokeai_py_client.workflow import WorkflowDefinition

# 1. Load workflow definition
definition = WorkflowDefinition.from_file("workflow.json")
wf = client.workflow_repo.create_workflow(definition)

# 2. Configure inputs by index (stable API)
wf.get_input_value(0).value = "A beautiful landscape"  # Prompt
wf.get_input_value(1).value = 20                       # Steps  

# 3. Execute workflow
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=180)

# 4. Extract generated images
for mapping in wf.map_outputs_to_images(result):
    print(f"Generated: {mapping.get('image_names', [])}")
```

### 📂 Board & Image Management

```python
# List and create boards
boards = client.board_repo.list_boards(include_uncategorized=True)
new_board = client.board_repo.create_board("My Project")

# Upload and download images
image = new_board.upload_image("reference.jpg")
image_data = new_board.download_image(image.image_name, full_resolution=True)

# Organize images
uncategorized = client.board_repo.get_uncategorized_handle()  
uncategorized.move_image_to(image.image_name, new_board.board_id)
```

### Workflow Operations

```python
from invokeai_py_client.workflow import WorkflowDefinition

# Load workflow definition from file and create a handle
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflow.json")
)

# Discover inputs (indices are the stable public handle)
for inp in wf.list_inputs():
    print(f"[{inp.input_index:02d}] {inp.label or inp.field_name}")

# Set values on typed fields (example)
fld = wf.get_input_value(0)
if hasattr(fld, "value"):
    fld.value = "A cinematic sunset over snowy mountains"

# Submit and wait (blocking convenience)
submission = wf.submit_sync()
queue_item = wf.wait_for_completion_sync(timeout=180)

# Map outputs to images (per node)
for m in wf.map_outputs_to_images(queue_item):
    print(m["node_id"], m.get("image_names"))
```

### Board Management

```python
# Resolve a board and upload/download images
boards = client.board_repo.list_boards(include_uncategorized=True)

handle = client.board_repo.get_board_handle("none")  # uncategorized

# Upload from file
img = handle.upload_image("image.png")

# Or upload from bytes
img2 = handle.upload_image_data(open("image.png", "rb").read(), filename="image.png")

# Download full-resolution image
data = handle.download_image(img.image_name, full_resolution=True)
open(img.image_name, "wb").write(data)
```

## Type System

The library uses a strongly-typed field system with Pydantic validation:

- IvkField[T]: generic base for all fields
- Primitive: IvkStringField, IvkIntegerField, IvkFloatField, IvkBooleanField
- Resource: IvkImageField, IvkBoardField, IvkLatentsField, IvkTensorField
- Models/Configs: IvkModelIdentifierField, IvkUNetField, IvkCLIPField, IvkTransformerField, IvkLoRAField
- Complex: IvkColorField, IvkBoundingBoxField, IvkCollectionField
- Enums: IvkEnumField, IvkSchedulerField, SchedulerName

See details: [Fields](fields.md)

## Async Support

Use async submission and event-driven completion:

```python
import asyncio

async def run():
    # Async submit with optional event subscription
    result = await wf.submit(subscribe_events=True)

    # Wait for completion via events (no polling)
    done = await wf.wait_for_completion(timeout=300)
    print("Final status:", done.get("status"))

asyncio.run(run())
```

Or a hybrid stream of events while keeping a simple submit path:

```python
async for evt in wf.submit_sync_monitor_async():
    print(evt.get("event_type"), evt.get("status") or "")
```

## Next Steps

- Explore individual components in their dedicated pages
- Review [Examples](../examples/index.md) for practical usage
- Check [User Guide](../user-guide/index.md) for tutorials
- See [Developer Guide](../developer-guide/index.md) for advanced topics
