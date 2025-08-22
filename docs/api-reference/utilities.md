# Utilities and Helper Patterns

Focus
- Practical helpers that exist in this client today.
- To-the-point patterns you can copy into scripts.
- Links point to concrete implementations in this repo.

What’s not here
- Previous docs mentioned “AssetManager”, “TypeConverter”, “ProgressTracker”, and validator classes. These do not exist in the codebase. Use the patterns below with WorkflowHandle, BoardRepository/BoardHandle, and Client.

## Input discovery and drift helpers

Preview configured inputs
```python
# Quick summary of indices, types, and current values
rows = wf.preview()
for r in rows:
    print(f"[{r['index']:02d}] {r['label']} -> {r['value']}")
```
Source: [`WorkflowHandle.preview()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L475){:target="_blank"}

Snapshot current index map (commit this to track changes after you edit the GUI Form)
```python
wf.export_input_index_map("index-map.json")
```
Source: [`WorkflowHandle.export_input_index_map()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L502){:target="_blank"}

Compare a saved map against the current workflow (detect moved/missing/new inputs fast)
```python
report = wf.verify_input_index_map("index-map.json")
print("Unchanged:", report["unchanged"])
print("Moved:", report["moved"])
print("Missing:", report["missing"])
print("New:", report["new"])
```
Source: [`WorkflowHandle.verify_input_index_map()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L521){:target="_blank"}

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