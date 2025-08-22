# Utilities and Helper Patterns

This section provides practical helper functions and patterns that exist in the current client implementation, focusing on copy-pasteable code snippets with direct links to concrete implementations in the repository. Note that previously documented utility classes like "AssetManager", "TypeConverter", "ProgressTracker", and validator classes do not exist in the codebase—instead, use the patterns documented below with WorkflowHandle, BoardRepository/BoardHandle, and the main Client class.

## Input Discovery and Drift Management

Utilities for managing workflow inputs and detecting changes when GUI workflows are modified.

### `preview()` - Input Summary Display

```python
def preview(self) -> list[dict[str, Any]]:
```

Generate a quick summary of all workflow inputs with current values for debugging and inspection.

**Returns:**
- `list[dict]`: List of input summaries with keys:
  - `index` (int): Stable input index
  - `label` (str): Display name or field name
  - `type` (str): Field type name  
  - `value` (Any): Current field value
  - `required` (bool): Whether input is mandatory

**Example:**
```python
# Display all inputs with values
rows = wf.preview()
for r in rows:
    required = "* " if r['required'] else "  "
    print(f"{required}[{r['index']:02d}] {r['label']} ({r['type']}) -> {r['value']}")

# Output:
# * [00] Positive Prompt (IvkStringField) -> A beautiful landscape
#   [01] Negative Prompt (IvkStringField) -> blur, artifacts
# * [02] Width (IvkIntegerField) -> 1024
```

**Source:** [`WorkflowHandle.preview()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L475){:target="_blank"}

### Index Map Management - Workflow Change Detection

When GUI workflows are modified, input indices can change. These utilities help track and detect changes.

#### `export_input_index_map()` - Create Baseline Snapshot

```python
def export_input_index_map(self, filepath: str) -> None:
```

Export current input-to-index mapping to a file for change detection.

**Parameters:**
- `filepath` (str): Path where to save the index map JSON

**Use Case:**
- Run after finalizing GUI workflow structure
- Commit the generated file to version control
- Use as baseline for detecting future changes

**Example:**
```python
# Save current input mapping
wf.export_input_index_map("workflow-inputs.json")

# Commit to version control
# git add workflow-inputs.json
# git commit -m "Add input index baseline for stable automation"
```

#### `verify_input_index_map()` - Detect Changes

```python
def verify_input_index_map(self, filepath: str) -> dict[str, Any]:
```

Compare current workflow inputs against a saved index map to detect changes.

**Parameters:**
- `filepath` (str): Path to previously saved index map

**Returns:**
- `dict[str, Any]`: Change report with keys:
  - `unchanged` (list): Inputs that stayed the same
  - `moved` (list): Inputs that changed index positions
  - `missing` (list): Inputs that were removed
  - `new` (list): Inputs that were added

**Example:**
```python
# Check for workflow changes
report = wf.verify_input_index_map("workflow-inputs.json")

print(f"Unchanged inputs: {len(report['unchanged'])}")
print(f"Moved inputs: {len(report['moved'])}")
print(f"Missing inputs: {len(report['missing'])}")  
print(f"New inputs: {len(report['new'])}")

# Handle moved inputs
for moved in report["moved"]:
    old_idx = moved["old_index"] 
    new_idx = moved["new_index"]
    name = moved["name"]
    print(f"Input '{name}' moved from [{old_idx}] to [{new_idx}]")
```

**Change Management Workflow:**
1. Create baseline with `export_input_index_map()` after GUI editing
2. Use `verify_input_index_map()` before automation scripts
3. Update scripts if indices have changed
4. Re-export new baseline if changes are accepted

**Source:** [`WorkflowHandle.export_input_index_map()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L502){:target="_blank"} | [`WorkflowHandle.verify_input_index_map()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L521){:target="_blank"}

## Submission and monitoring patterns

Blocking submit + poll
```python
# Submit (raises early on invalid inputs)
submission = wf.submit_sync()

# Poll for terminal status; optional progress callback logs transitions
queue_item = wf.wait_for_completion_sync(
    poll_interval=2.0,
    timeout=180.0,
    progress_callback=lambda qi: print("Status:", qi.get("status")),
)
```
Source: [`WorkflowHandle.submit_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L767){:target="_blank"}, [`WorkflowHandle.wait_for_completion_sync()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1077){:target="_blank"}

Async submit with event callbacks (Socket.IO)
```python
async def on_progress(evt: dict):
    if evt.get("session_id") == wf.session_id:
        print(f"Progress: {evt.get('progress', 0)*100:.0f}%")

result = await wf.submit(
    subscribe_events=True,
    on_invocation_progress=on_progress,
)
# Later, wait on completion with events instead of polling:
completed = await wf.wait_for_completion(timeout=300)
```
Source: [`WorkflowHandle.submit()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L876){:target="_blank"}, [`WorkflowHandle.wait_for_completion()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1154){:target="_blank"}

Hybrid streaming: simple submit + async event stream
```python
async for evt in wf.submit_sync_monitor_async():
    et = evt.get("event_type")
    if et == "submission":
        print("Batch:", evt["batch_id"])
    elif et == "invocation_progress":
        print("Progress:", evt.get("progress"))
    elif et in ("graph_complete", "queue_item_status_changed"):
        print("Done:", et)
```
Source: [`WorkflowHandle.submit_sync_monitor_async()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1258){:target="_blank"}

Cancel a running job
```python
# Sync
wf.cancel()

# Async
await wf.cancel_async()
```
Source: [`WorkflowHandle.cancel()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1430){:target="_blank"}, [`WorkflowHandle.cancel_async()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1459){:target="_blank"}

## Output mapping (node → image filenames)

Map output-capable nodes (with board fields exposed in the Form) to their produced images:
```python
mappings = wf.map_outputs_to_images(queue_item)
for m in mappings:
    print(
        f"idx={m['input_index']:02d} node={m['node_id'][:8]} "
        f"board={m['board_id']} images={m.get('image_names')}"
    )
```
Source: [`WorkflowHandle.map_outputs_to_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1787){:target="_blank"}

Get just the set of output nodes (their board inputs) if you need to pre-inspect:
```python
for out in wf.list_outputs():
    print(out.input_index, out.node_name, out.field_name)
```
Source: [`WorkflowHandle.list_outputs()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L554){:target="_blank"}

## Boards and images (quick recipes)

Resolve a board and upload/download images
```python
# List boards (include uncategorized)
boards = client.board_repo.list_boards(include_uncategorized=True)

# Get a handle (None or "none" gives uncategorized)
bh = client.board_repo.get_board_handle(None)

# Upload from bytes (lands in Assets; uncategorized omits board_id intentionally)
img = bh.upload_image_data(open("sample.png","rb").read(), filename="sample.png")

# Download (guarded by membership in this board)
data = bh.download_image(img.image_name, full_resolution=True)
open(img.image_name, "wb").write(data)
```
Source references:
- [`BoardRepository.list_boards()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L59){:target="_blank"}
- [`BoardRepository.get_board_handle()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L267){:target="_blank"}
- [`BoardHandle.upload_image_data()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L272){:target="_blank"}
- [`BoardHandle.download_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L357){:target="_blank"}

## Validation helpers

Validate all inputs before submit (aggregates per-index errors)
```python
errors = wf.validate_inputs()
if errors:
    for idx, msgs in errors.items():
        print(f"[{idx}] {', '.join(msgs)}")
    raise SystemExit("Fix inputs and retry")
```
Source: [`WorkflowHandle.validate_inputs()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L641){:target="_blank"}

Type-safe setting pattern (work with the concrete field you get)
```python
from invokeai_py_client.ivk_fields import IvkStringField

fld = wf.get_input_value(0)
if isinstance(fld, IvkStringField):
    fld.value = "A futuristic city at night"
```
Source: [`WorkflowHandle.get_input_value()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L678){:target="_blank"}

## Reliability patterns (generic)

Simple retry wrapper for transient HTTP errors (copy-paste)
```python
import time, requests

def retry(fn, attempts=3, delay=1.0, backoff=2.0):
    for i in range(attempts):
        try:
            return fn()
        except requests.RequestException as e:
            if i == attempts - 1:
                raise
            time.sleep(delay)
            delay *= backoff

# Example: robust board listing
boards = retry(lambda: client.board_repo.list_boards(include_uncategorized=True))
```

## Cross-references

- Workflows: [docs/api-reference/workflow.md](workflow.md)
- Client: [docs/api-reference/client.md](client.md)
- Boards: [docs/api-reference/boards.md](boards.md)
- User guides and examples:
  - Inputs: [docs/user-guide/inputs.md](../user-guide/inputs.md)
  - Output mapping: [docs/user-guide/output-mapping.md](../user-guide/output-mapping.md)
  - Examples index: [docs/examples/index.md](../examples/index.md)