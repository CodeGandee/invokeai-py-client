# Workflow API

Focus
- Accurate, to-the-point reference for running GUI-exported workflows via the client.
- Signatures and return types match the working examples in this repository.

Quick links to usage in examples
- Create workflow: [`WorkflowDefinition.from_file()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L132){:target="_blank"} + [`client.workflow_repo.create_workflow()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L133){:target="_blank"}
- Discover inputs: [`workflow_handle.list_inputs()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L143){:target="_blank"}
- Get/set values: [`workflow_handle.get_input_value()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L224){:target="_blank"}
- Submit and monitor: [`workflow_handle.submit_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L309){:target="_blank"}, [`workflow_handle.wait_for_completion_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L312){:target="_blank"}
- Map outputs to images: [`workflow_handle.map_outputs_to_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L328){:target="_blank"}

## WorkflowDefinition

A lightweight loader/holder for your exported workflow JSON. The client treats workflow JSON as immutable source-of-truth; only value substitution happens at submit time (no node/edge surgery).

```python
class WorkflowDefinition:
    """Workflow definition loaded from exported GUI JSON."""

    @classmethod
    def from_file(cls, filepath: str) -> 'WorkflowDefinition':
        """Load workflow JSON from disk into a definition."""
```

- Usage: [`WorkflowDefinition.from_file()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py#L132){:target="_blank"}
- Notes:
  - The internal JSON mirrors the GUI export. Fields like legacy `exposedFields` are not used for discovery (the client traverses the Form tree depth-first; see User Guide).
  - Structure validation is performed internally; you typically do not need to call a separate validator.

## WorkflowHandle

Represents a workflow instance bound to a server, with ordered input discovery, typed field access, submission, and output mapping.

```python
class WorkflowHandle:
    """Handle for workflow execution and mapping."""

    # Input discovery and access
    def list_inputs(self) -> list[IvkWorkflowInput]:
        """Depth-first (pre-order) list of form-exposed inputs."""

    def get_input_value(self, index: int) -> 'IvkField':
        """Return the typed field object at the given index.
        Set values via field.value where supported."""

    # Optional: synchronize model identifier fields to server-known records
    def sync_dnn_model(self, by_name: bool = True, by_base: bool = True) -> list[tuple[object, object]]:
        """Resolve/normalize model fields (returns list of (original, resolved) pairs for changed fields)."""

    # Submission (blocking convenience)
    def submit_sync(self) -> dict[str, object]:
        """Enqueue the prepared workflow graph. Returns submission metadata (batch_id, item_ids, session_id)."""

    def wait_for_completion_sync(
        self,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
        progress_callback: 'Callable[[dict], None]' | None = None,
    ) -> dict[str, object]:
        """Poll until the single enqueued item finishes. Returns the final queue item dict."""

    # Output mapping (after completion)
    def map_outputs_to_images(self, queue_item: dict[str, object]) -> list['OutputMapping']:
        """Map output-capable nodes to produced image names based on runtime session results."""
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
