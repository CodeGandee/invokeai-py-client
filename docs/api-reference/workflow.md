# Workflow API

Complete reference for workflow execution system covering GUI-exported workflow loading, input management, job submission, and result extraction. Key operations include workflow creation via [`WorkflowDefinition.from_file()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L132){:target="_blank"} and [`create_workflow()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L133){:target="_blank"}, input discovery with [`list_inputs()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L143){:target="_blank"}, value management via [`get_input_value()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L224){:target="_blank"}, execution through [`submit_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L309){:target="_blank"}/[`wait_for_completion_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L312){:target="_blank"}, and result mapping with [`map_outputs_to_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L328){:target="_blank"}.

## WorkflowDefinition

Immutable container for workflow JSON exported from the InvokeAI GUI. Represents the complete workflow structure including nodes, edges, and exposed form inputs.

### Design Philosophy

The client treats workflow JSON as **immutable source-of-truth**:
- No node/edge surgery or structural modifications
- Only value substitution occurs during submission
- Preserves workflow integrity and reproducibility
- Enables reliable input discovery and validation

### `from_file()` - Load Workflow Definition

```python
@classmethod
def from_file(cls, filepath: str) -> WorkflowDefinition:
```

Load and validate a workflow definition from exported GUI JSON.

**Parameters:**
- `filepath` (str): Path to the workflow JSON file exported from InvokeAI GUI

**Returns:**
- `WorkflowDefinition`: Validated workflow definition ready for execution

**Validation Process:**
- Validates JSON structure and required fields
- Verifies node types and connections
- Extracts and indexes form inputs for discovery
- Performs compatibility checks with current InvokeAI version

**Example:**
```python
# Load SDXL text-to-image workflow
definition = WorkflowDefinition.from_file("workflows/sdxl-txt2img.json")

# Load FLUX image-to-image workflow  
flux_def = WorkflowDefinition.from_file("workflows/flux-img2img.json")

# Load with error handling
try:
    definition = WorkflowDefinition.from_file("complex-workflow.json")
except ValueError as e:
    print(f"Invalid workflow: {e}")
```

**Important Notes:**
- **Form Tree Discovery**: Input discovery uses depth-first traversal of the Form tree, not legacy `exposedFields`
- **Structure Validation**: Automatic validation ensures compatibility
- **Immutable Design**: Definition cannot be modified after loading - create new definitions for variations

**Source:** [`WorkflowDefinition.from_file()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L132){:target="_blank"}

## WorkflowHandle

Stateful workflow instance bound to a server, providing input management, execution control, and output mapping. Handles are created by `WorkflowRepository` and maintain session state throughout the workflow lifecycle.

### Input Discovery and Management

#### `list_inputs()` - Discover Workflow Inputs

```python
def list_inputs(self) -> list[IvkWorkflowInput]:
```

Discover all form-exposed inputs in depth-first (pre-order) traversal order.

**Returns:**
- `list[IvkWorkflowInput]`: Ordered list of input descriptors with metadata

**Input Descriptor Properties:**
- `input_index` (int): Stable index for accessing this input (primary key)
- `label` (str | None): User-friendly display name from GUI
- `field_name` (str): Field name within the node
- `node_name` (str): Display name of the containing node
- `node_id` (str): Unique node identifier
- `field` (IvkField): Typed field instance with current value
- `required` (bool): Whether input is mandatory

**Index Stability:**
- **Indices are the stable public API** - use these for programmatic access
- Order is deterministic: depth-first traversal of Form tree
- Indices remain consistent across workflow execution (not labels/names)

**Example:**
```python
# Discover and display inputs
for inp in wf.list_inputs():
    print(f"[{inp.input_index:02d}] {inp.label or inp.field_name}")
    print(f"    Node: {inp.node_name} ({inp.node_id})")
    print(f"    Type: {type(inp.field).__name__}")
    print(f"    Required: {inp.required}")
```

#### `get_input_value()` - Access Typed Field

```python
def get_input_value(self, index: int) -> IvkField:
```

Retrieve the typed field object at the specified index for value manipulation.

**Parameters:**
- `index` (int): Input index from `list_inputs()` (stable identifier)

**Returns:**
- `IvkField`: Typed field instance (IvkStringField, IvkIntegerField, etc.)

**Field Value Patterns:**
- **Fields with `.value`**: Primitives, resources, enums - set via `field.value = new_value`
- **Fields without `.value`**: Models, complex types - set attributes directly
- **Type safety**: Fields maintain their concrete types for IDE support

**Example:**
```python
# Set prompt text (string field)
prompt_field = wf.get_input_value(0)
if hasattr(prompt_field, 'value'):
    prompt_field.value = "A majestic mountain landscape"

# Configure model (model identifier field)  
model_field = wf.get_input_value(5)
if hasattr(model_field, 'name'):
    model_field.name = "SDXL Base 1.0"

# Type-safe assignment
from invokeai_py_client.ivk_fields import IvkStringField
fld = wf.get_input_value(0)
if isinstance(fld, IvkStringField):
    fld.value = "Type-safe string assignment"
```

### Model Synchronization

#### `sync_dnn_model()` - Normalize Model References

```python
def sync_dnn_model(
    self, 
    by_name: bool = True, 
    by_base: bool = True
) -> list[tuple[object, object]]:
```

Resolve and normalize model identifier fields against server-available models.

**Parameters:**
- `by_name` (bool): Match models by name (default: True)
- `by_base` (bool): Match models by base type (SDXL, FLUX, etc.) (default: True)

**Returns:**
- `list[tuple[object, object]]`: List of (original, resolved) pairs for changed fields

**Resolution Process:**
- Queries server for available models
- Matches workflow model fields against server inventory
- Updates field attributes (key, hash, name) with server values
- Ensures model compatibility and availability

**Example:**
```python
# Sync all model fields before execution
changed = wf.sync_dnn_model(by_name=True, by_base=True)
for original, resolved in changed:
    print(f"Updated model: {original.name} -> {resolved.name}")

# Name-only matching (more permissive)
wf.sync_dnn_model(by_name=True, by_base=False)
```

### Workflow Execution

#### `submit_sync()` - Synchronous Submission

```python
def submit_sync(self) -> dict[str, object]:
```

Submit the workflow for execution using blocking/synchronous approach.

**Returns:**
- `dict[str, object]`: Submission metadata including:
  - `batch_id` (str): Unique identifier for this batch
  - `item_ids` (list[str]): Queue item IDs for tracking
  - `session_id` (str): Session identifier for results

**Pre-submission Process:**
- Validates all workflow inputs using `validate_inputs()`
- Converts field values to API format
- Handles image uploads if needed
- Enqueues workflow graph for execution

**Example:**
```python
# Configure inputs
wf.get_input_value(0).value = "Beautiful landscape"  # Prompt
wf.get_input_value(1).value = 20                     # Steps

# Submit workflow
submission = wf.submit_sync()
print(f"Submitted batch: {submission['batch_id']}")
print(f"Queue items: {submission['item_ids']}")
```

#### `wait_for_completion_sync()` - Blocking Wait

```python
def wait_for_completion_sync(
    self,
    poll_interval: float = 2.0,
    timeout: float = 300.0,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict[str, object]:
```

Poll the queue until workflow execution completes.

**Parameters:**
- `poll_interval` (float): Seconds between status polls (default: 2.0)
- `timeout` (float): Maximum wait time in seconds (default: 300.0)
- `progress_callback` (Callable | None): Optional callback for status updates

**Returns:**
- `dict[str, object]`: Final queue item with execution results and status

**Polling Behavior:**
- Polls queue status at regular intervals
- Calls progress callback on status changes
- Returns on completion, failure, or timeout
- Raises `TimeoutError` if timeout exceeded

**Example:**
```python
# Simple blocking wait
queue_item = wf.wait_for_completion_sync(timeout=180)
print(f"Final status: {queue_item.get('status')}")

# With progress monitoring
def on_progress(item):
    status = item.get('status', 'unknown')
    progress = item.get('progress', 0)
    print(f"Status: {status} ({progress*100:.0f}%)")

result = wf.wait_for_completion_sync(
    poll_interval=1.0,
    timeout=300.0,
    progress_callback=on_progress
)
```

#### `map_outputs_to_images()` - Extract Generated Images

```python
def map_outputs_to_images(self, queue_item: dict[str, object]) -> list[OutputMapping]:
```

Map output-capable nodes to their generated images based on execution results.

**Parameters:**
- `queue_item` (dict): Completed queue item from `wait_for_completion_sync()`

**Returns:**
- `list[OutputMapping]`: List of output mappings with structure:
  - `node_id` (str): Node that produced the output
  - `input_index` (int): Index of the board field that controlled output location
  - `board_id` (str | None): Board where images were saved
  - `tier` (str | int | None): Output classification/priority  
  - `image_names` (list[str]): Names of generated images

**Mapping Process:**
- Identifies nodes with board fields exposed in the Form
- Matches execution results to board destinations
- Extracts image names from session data
- Provides structured access to generated outputs

**Example:**
```python
# Execute workflow and map outputs
submission = wf.submit_sync()
completed = wf.wait_for_completion_sync(timeout=180)

# Extract all generated images
for mapping in wf.map_outputs_to_images(completed):
    print(f"Node: {mapping['node_id']}")
    print(f"Board: {mapping['board_id']}")
    print(f"Images: {mapping.get('image_names', [])}")
    
    # Download images if needed
    if mapping.get('image_names'):
        board_handle = client.board_repo.get_board_handle(mapping['board_id'])
        for img_name in mapping['image_names']:
            data = board_handle.download_image(img_name)
            # Save or process image data
```

- Discovery and access in practice:
  - [`workflow_handle.list_inputs()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L143){:target="_blank"}
  - [`workflow_handle.get_input_value()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L224){:target="_blank"}
- Submission and monitoring:
  - [`workflow_handle.submit_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L309){:target="_blank"}
  - [`workflow_handle.wait_for_completion_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L312){:target="_blank"}
- Output mapping:
  - [`workflow_handle.map_outputs_to_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L328){:target="_blank"}
  - Also shown in different pipelines: [`wait_for_completion_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/flux-image-to-image.py#L400){:target="_blank"}, [`map_outputs_to_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/flux-image-to-image.py#L421){:target="_blank"}

See complete usage examples in [`sdxl-text-to-image.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py){:target="_blank"} and [`flux-image-to-image.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/flux-image-to-image.py){:target="_blank"}

Return type details
- IvkWorkflowInput (discovery descriptor) provides:
  - input_index (int), label (str|None), field_name (str), node_name (str), node_id (str), field (typed Ivk*Field), required (bool).
- IvkField (typed field instances) include, e.g., IvkStringField, IvkIntegerField, IvkFloatField, IvkSchedulerField, IvkModelIdentifierField, IvkImageField, IvkBoardField. Most support a `.value` attribute for assignment.
- OutputMapping (mapping record) is a dict-like object with:
  - node_id: str
  - board_id: str | None
  - tier: str | int | None  (implementation-specific classification of outputs)
  - image_names: list[str]

## WorkflowRepository

Factory/facade for working with workflows via the connected client.

```python
class WorkflowRepository:
    """Repository for loading definitions and creating handles."""

    def create_workflow(self, definition: WorkflowDefinition) -> WorkflowHandle:
        """Bind a definition to the server and return a handle."""
```

- Usage: [`client.workflow_repo.create_workflow()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L133){:target="_blank"}

## End-to-end usage

```python
# Create and execute a workflow
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflow.json")
)

# Optional: normalize model identifier fields
wf.sync_dnn_model(by_name=True, by_base=True)

# Inspect inputs (indices are the stable public handle)
for inp in wf.list_inputs():
    print(f"[{inp.input_index:02d}] {inp.label or inp.field_name} :: {inp.node_name}")

# Retrieve typed fields and set values
pos = wf.get_input_value(0)
if hasattr(pos, "value"):
    pos.value = "A cinematic sunset over snowy mountains"

# Submit and wait (blocking convenience)
submission = wf.submit_sync()
queue_item = wf.wait_for_completion_sync(timeout=180)

# Map outputs to image names (per-node)
for m in wf.map_outputs_to_images(queue_item):
    print(m["node_id"], m.get("image_names"))
```

Example usage references (click to view source):
- [`WorkflowDefinition.from_file()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L132){:target="_blank"}
- [`client.workflow_repo.create_workflow()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L133){:target="_blank"}
- [`workflow_handle.sync_dnn_model()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L136){:target="_blank"}
- [`workflow_handle.list_inputs()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L143){:target="_blank"}
- [`workflow_handle.get_input_value()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L224){:target="_blank"}
- [`workflow_handle.submit_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L309){:target="_blank"}
- [`workflow_handle.wait_for_completion_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L312){:target="_blank"}
- [`workflow_handle.map_outputs_to_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L328){:target="_blank"}

See complete working examples in [`sdxl-text-to-image.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py){:target="_blank"}

## Notes on accuracy and behavior

- Indices, not labels/names, are the stable public API for inputs. Order is depth-first (pre-order) over the Form container tree (matches examples and the User Guide).
- `wait_for_completion_sync(...)` does not require a submission argument; it polls the item enqueued by the prior `submit_sync()`. This matches all examples.
- `map_outputs_to_images(queue_item)` returns structured mappings (node_id, board_id, tier, image_names), not a raw list of strings.
- The client does not mutate the workflow graph (immutable JSON + value-only substitution on submit).

See also
- User Guide, Workflow Basics: [docs/user-guide/workflow-basics.md](../user-guide/workflow-basics.md)
- Inputs (index-based access): [docs/user-guide/inputs.md](../user-guide/inputs.md)
- Output mapping: [docs/user-guide/output-mapping.md](../user-guide/output-mapping.md)
