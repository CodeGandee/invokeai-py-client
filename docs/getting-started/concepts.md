# Core Concepts

Understanding these key concepts will help you use the InvokeAI Python Client effectively.

## Workflow Definition

A WorkflowDefinition is the JSON representation of a workflow exported from the InvokeAI GUI. It contains:

- Nodes: Processing units (models, prompts, samplers, etc.)
- Edges: Connections between nodes
- Form: User-configurable parameters

```python
from invokeai_py_client.workflow import WorkflowDefinition

# Load from file
workflow_def = WorkflowDefinition.from_file("my-workflow.json")

# Definition metadata
print(f"Workflow: {workflow_def.name}")       # Title from JSON
print(f"Version: {workflow_def.version}")     # From meta.version
print(f"Nodes: {len(workflow_def.nodes)}")
```

!!! info "Immutability Principle"
    The client treats workflow JSON as immutable. When you set values and submit, only the values are substituted—the graph structure never changes.

## Form-Based Input Discovery

The Form is the key to programmable workflows. Only fields added to the Form panel in the GUI are accessible from Python.

Why this matters:
- Form fields = Programmable inputs
- Non-form values = Fixed in the workflow
- Best practice: Add all parameters you want to control to the Form before export

## Index-Based Access

The client uses indices as the primary way to access inputs. Indices are determined by depth-first traversal of the Form structure (containers in order, fields top-to-bottom, recursion for nested containers).

### Index Discovery

```python
# List all inputs with their indices
for inp in wf.list_inputs():
    print(f"[{inp.input_index:2d}] {inp.label or inp.field_name}")

# Example output:
# [ 0] Positive Prompt
# [ 1] Negative Prompt
# [ 2] Width
# [ 3] Height
```

Why indices?
- Stability: Indices don't change unless you restructure the Form
- Uniqueness: Always unique, unlike labels or field names
- Performance: Direct array access is fast

## Typed Field System

Every input has a strongly-typed field class that provides validation and type safety.

### Field Types (common)

| Field Class | Purpose | Value Type |
|------------|---------|------------|
| IvkStringField | Text inputs | str (via .value) |
| IvkIntegerField | Whole numbers | int (via .value) |
| IvkFloatField | Decimal numbers | float (via .value) |
| IvkBooleanField | Checkboxes | bool (via .value) |
| IvkImageField | Image references | str image_name (via .value) |
| IvkBoardField | Board selection | str board_id (via .value) |
| IvkModelIdentifierField | Model selection | attributes (key/hash/name/base/type) |

Working with fields:

```python
# Get a field by index
field = wf.get_input_value(0)

# If the field has a .value, set it directly:
if hasattr(field, "value"):
    field.value = "New prompt text"

# Example of catching a validation error (integer expected)
try:
    steps = wf.get_input_value(4)  # Typically an IvkIntegerField
    if hasattr(steps, "value"):
        steps.value = "not a number"  # Will raise ValueError
except ValueError as e:
    print(f"Invalid value: {e}")
```

Notes:
- Some fields (e.g., IvkModelIdentifierField, IvkUNetField) do not use .value—set their specific attributes instead (e.g., key, name, base, type).

## Workflow Handle

A WorkflowHandle is your interface to a loaded workflow. It provides methods to:

- List and access inputs
- Set values
- Submit for execution
- Track progress
- Map outputs

```python
# Create a handle from a definition
wf = client.workflow_repo.create_workflow(workflow_def)

# The handle maintains state
if hasattr(wf.get_input_value(0), "value"):
    wf.get_input_value(0).value = "New value"

# Submit creates a new execution
submission = wf.submit_sync()
```

## Execution Model

The client supports multiple execution modes.

### Synchronous (Blocking)

```python
# Submit and wait in sequence
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=120)
```

### Asynchronous

```python
# Submit without blocking
async def run_async():
    submission = await wf.submit()
    # Do other work...
    result = await wf.wait_for_completion()
```

### With Status Monitoring

```python
# Track status transitions during execution
def on_progress(queue_item):
    print(f"Status: {queue_item.get('status')}")

result = wf.wait_for_completion_sync(
    timeout=180,
    progress_callback=on_progress,
)
```

Tip: The progress callback receives the latest queue item dict. Not all servers provide a numeric percentage—log status transitions reliably.

## Output Mapping

After execution, the client maps output nodes to the images they produced.

What counts as an output?
1) The node can save images to a board, and
2) Its board field is exposed in the Form (so it is discoverable and configurable)

Mapping:

```python
# Get mappings after completion
mappings = wf.map_outputs_to_images(queue_item)

# Each mapping contains:
# - node_id: The output node
# - board_id: Where images were saved
# - image_names: List of produced images
# - input_index: Form index (if exposed)
# - tier: evidence tier ("results", "legacy", "traversal", "none")
# - label: field label for the board input

for m in mappings:
    print(f"Node {m['node_id'][:8]} -> {m.get('image_names')} (tier={m.get('tier')})")
```

## Board Management

Boards organize images in InvokeAI. The client provides full board control:

```python
# List all boards (including uncategorized)
boards = client.board_repo.list_boards(include_uncategorized=True)

# Get a board handle (use "none" for uncategorized)
board = client.board_repo.get_board_handle("none")

# Upload an image file
image = board.upload_image("input.png")   # returns IvkImage

# Download an image
data = board.download_image(image.image_name, full_resolution=True)
```

Special “none” board:
- The uncategorized board uses the literal string "none". Passing None to get_board_handle is also normalized to "none".

## Model Synchronization

Workflows may reference models that don't exactly match server records. The client can synchronize these:

```python
# Sync model references before submission
changes = wf.sync_dnn_model(by_name=True, by_base=True)

for old, new in changes:
    print(f"Updated: {getattr(old,'name','')} -> {getattr(new,'name','')}")
```

## Design Principles

- Immutable Workflows: Original JSON is never modified; only values are substituted on submit.
- Index-Based Stability: Indices are the authoritative way to access inputs; labels/names are for display only.
- Type Safety: Every field has a concrete type; validation occurs on assignment.
- Explicit Operations: No hidden mutations or side effects; clear, predictable behavior.

## Common Patterns

Snapshot indices for reuse in scripts:

```python
# After discovering inputs once, snapshot the indices
IDX_PROMPT = 0
IDX_NEGATIVE = 1
IDX_WIDTH = 2
IDX_HEIGHT = 3
IDX_STEPS = 4

# Use throughout your script
wf.get_input_value(IDX_PROMPT).value = "New prompt"
wf.get_input_value(IDX_STEPS).value = 30
```

Batch processing:

```python
for item in dataset:
    # Set inputs
    wf.get_input_value(IDX_PROMPT).value = item["prompt"]
    wf.get_input_value(IDX_WIDTH).value = item["width"]

    # Submit and track
    submission = wf.submit_sync()
    result = wf.wait_for_completion_sync()

    # Store results
    item["result"] = wf.map_outputs_to_images(result)
```

Safe field access helper:

```python
def set_field_safely(wf, index, value):
    """Set a field value with error handling."""
    try:
        field = wf.get_input_value(index)
        if hasattr(field, "value"):
            field.value = value
            return True
        else:
            print(f"Field {index} has no value property")
            return False
    except IndexError:
        print(f"No field at index {index}")
        return False
    except ValueError as e:
        print(f"Invalid value for field {index}: {e}")
        return False