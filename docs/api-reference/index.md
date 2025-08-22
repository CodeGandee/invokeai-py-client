# API Reference

Complete API documentation for the InvokeAI Python Client.

## Core Components

### [Client](client.md)
Main client class for connecting to InvokeAI server and accessing repositories.

### [Workflow](workflow.md)
Workflow management, input discovery, execution, and output mapping.

### [Boards](boards.md)
Board and image management operations.

### [Fields](fields.md)
Type-safe field system for workflow inputs.

### [Models](models.md)
Data models and enumerations used throughout the library.

### [Utilities](utilities.md)
Practical helper patterns and recipes.

## Quick Reference

### Client Initialization

```python
from invokeai_py_client import InvokeAIClient

# Recommended: parse URL into host/port/base_path automatically
client = InvokeAIClient.from_url("http://localhost:9090")

# Or explicit host/port
client = InvokeAIClient(host="localhost", port=9090)
```

- URL helper implementation: [`InvokeAIClient.from_url()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L142){:target="_blank"}
- Quick probe: [`InvokeAIClient.health_check()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L412){:target="_blank"}

```python
if client.health_check():
    print("InvokeAI is reachable")
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
