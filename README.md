# InvokeAI Python Client

Typed Python client + examples for interacting with an InvokeAI server (REST + Socket.IO).

Domains:
1. Workflows – load exported GUI workflow JSON, inspect & set inputs, submit to queue, monitor progress (sync, async, streaming).
2. Boards & Images – list/create/update/delete boards, basic image access (advanced flows in examples).
3. DNN Models – stateless discovery of installed models via v2 API (no local cache layer yet).

Emphasis: repository pattern, strongly‑typed Pydantic models, dynamic field inference, JSONPath-based workflow mutation, optional real‑time event subscriptions.

## 🎯 Project Goals & Scope

Provide a *pythonic*, type‑safe wrapper around selected InvokeAI APIs (not a 1:1 clone). Goals:
- Treat exported GUI workflow JSON as source of truth (forward compatible)
- Derive stable index‑based public inputs from workflow `form` tree
- Represent InvokeAI primitives & complex types as default‑constructable `IvkField` subclasses
- Offer sync, async, and streaming submission patterns
- Keep library largely stateless (minimal internal caching)
- Facilitate extension via repository isolation

## 📚 Key Terminology (summary)
Full glossary in `context/design/terminology.md`.

| Term | Meaning |
|------|---------|
| InvokeAI (`invokeai`) | The running inference backend. |
| Client API (`client-api`) | This Python wrapper project. |
| InvokeAI Client (`InvokeAIClient`) | Connection façade exposing repositories. |
| Workflow Definition (`WorkflowDefinition`) | Preserved raw JSON + light helpers. |
| Workflow Handle (`WorkflowHandle`) | Mutable execution state & submission logic. |
| Workflow Inputs (`IvkWorkflowInput`) | Public parameters derived from `form`. |
| Field Types (`Ivk*Field`) | Typed wrappers for InvokeAI values/resources. |

Field concrete class is locked after discovery—replacement must use the exact same class (type safety).

## ✅ Current Feature Set

- InvokeAIClient with retrying HTTP session & async Socket.IO support
- WorkflowDefinition (raw JSON preservation + metadata access)
- WorkflowHandle
  - Form traversal → ordered typed inputs (string/int/float/bool/model/board/image/enum)
  - Field type locking (prevents accidental semantic changes)
  - JSONPath updates → minimal mutation of original graph for submission
  - Submission modes:
	- `submit_sync()` + polling (`wait_for_completion_sync`)
	- `await submit(..., subscribe_events=True)` (callbacks)
	- `async for event in submit_sync_monitor_async()` streaming generator
  - Queue tracking: batch_id, item_id, session_id
  - Socket.IO events: invocation_started / invocation_progress / invocation_complete / invocation_error / queue_item_status_changed / graph_complete
- BoardRepository & BoardHandle (list/create/update/delete, uncategorized handling, handle caching + refresh)
- DnnModelRepository (fresh list & single lookup via v2 endpoints)
- Rich DNN model taxonomy (type, base architecture, storage format enums) + helpers
- IvkField system (primitive + complex) with Pydantic validation & (de)serialization mixins
- Example scripts & tests covering practical automation flows

### Not Yet Implemented (Stubs / Roadmap)
- Client high-level job methods (`list_jobs`, `get_job`, `cancel_job`, legacy `list_models` / `get_model_info` variants)
- Workflow output retrieval & cleanup helpers (`get_outputs`, `cleanup_*`) – currently raise `NotImplementedError`
- Automatic model availability resolution & obsolete node fixing (placeholders in `WorkflowRepository`)
- Direct database access (previous mention removed; not implemented)
- Image / artifact convenience download helpers (present only in examples now)
- Model reference validation & auto-fix passes

## 📦 Installation

Using pixi (project default):
```bash
pixi install
```

Using pip (editable source checkout):
```bash
pip install -e .
```

## 🚀 Quick Start

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")
wf_def = WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
workflow = client.workflow_repo.create_workflow(wf_def)

for inp in workflow.list_inputs():
	print(f"[{inp.input_index}] {inp.label} -> {type(inp.field).__name__}")

prompt_field = workflow.get_input_value(0)
if hasattr(prompt_field, 'value'):
	prompt_field.value = "A cinematic sunset over mountains"

submission = workflow.submit_sync(board_id="my-board")
print("Submitted batch", submission["batch_id"], "session", submission["session_id"])
queue_item = workflow.wait_for_completion_sync(timeout=120)
print("Final status:", queue_item.get("status"))
```

### Async Progress Streaming Example
```python
import asyncio
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

async def main():
	client = InvokeAIClient.from_url("http://localhost:9090")
	wf_def = WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
	wf = client.workflow_repo.create_workflow(wf_def)
	field0 = wf.get_input_value(0)
	if hasattr(field0, 'value'):
		field0.value = "A watercolor fox in a forest"

	def on_progress(evt):
		p = evt.get('progress')
		if p is not None:
			print(f"Progress: {p*100:.0f}%")

	await wf.submit(subscribe_events=True, on_invocation_progress=on_progress)
	result = await wf.wait_for_completion(timeout=90)
	print("Completed with status:", result.get("status"))

asyncio.run(main())
```

### Board Listing Example
```python
from invokeai_py_client import InvokeAIClient

client = InvokeAIClient.from_url("http://localhost:9090")
for board in client.board_repo.list_boards():
	print(board.board_name, board.image_count)
```

### DNN Model Discovery (v2)
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import BaseDnnModelType

client = InvokeAIClient.from_url("http://localhost:9090")
models = client.dnn_model_repo.list_models()
flux_models = [m for m in models if m.is_compatible_with_base(BaseDnnModelType.Flux)]
print("Flux-compatible models:", [m.name for m in flux_models])

# Single model lookup (None if missing)
one = client.dnn_model_repo.get_model_by_key(models[0].key)
print("Example model:", one)

"""Note: v2 endpoints are reached using '/../v2/models/' relative traversal from the v1 base path. This may change if upstream routing evolves."""
```

## 🔍 Supporting Resources

| Resource | Location | Notes |
|----------|----------|-------|
| OpenAPI JSON | `context/hints/invokeai-kb/invokeai-openapi.json` | Raw endpoint schema |
| API List (Markdown) | `context/hints/invokeai-kb/invokeai-api-list.md` | Human-readable list |
| Workflow Templates | `data/workflows/` | Example SDXL / FLUX graphs |
| Example Scripts | `examples/` | End-to-end demonstrations |
| Docs & Design Notes | `docs/` | Architecture & task summaries |

## 🧱 Architectural Highlights
- Repository pattern isolates HTTP details from usage code
- JSONPath updates avoid reconstructing graphs wholesale
- Pydantic models provide early validation & typed access
- Socket.IO integration enables real-time node-level progress (optional)
- Field system enforces default-constructability for dynamic creation & reflection
- Deterministic input ordering (depth-first `form` traversal) ensures stable indexing
- Heuristic type inference tolerates new/unrecognized node types

## 📤 Workflow Submission Payload (Task 2.1.1 Reference)
How a workflow submission request is assembled before POSTing to `/api/v1/queue/{queue_id}/enqueue_batch`:

1. Input Discovery
	- Traverse `definition.form.elements` depth‑first starting at `root` collecting `node-field` entries.
	- For each exposed field build an `IvkWorkflowInput` containing: label, node id, field name, required flag, index, and a JSONPath pointing directly to `...nodes[?(@.id='{node_id}')].data.inputs.{field}.value` inside the preserved raw JSON.
2. Value Mutation (JSONPath)
	- On submission `_convert_to_api_format()` deep copies `definition.raw_data`.
	- Each input’s current field value is written into the copy via its stored JSONPath (future: cache compiled expressions for speed).
3. Node Extraction & Pruning
	- Build minimal API nodes: include `id`, `type`, `is_intermediate`, `use_cache` plus only literal input fields that are NOT fed by an incoming edge (edge‑connected inputs are omitted—InvokeAI resolves them from the edge list).
4. Edge Conversion
	- Each original GUI edge becomes an entry: `{ "source": {"node_id", "field"}, "destination": {"node_id", "field"} }`.
5. Board Injection
	- If a `board_id` was provided, apply `{"board": {"board_id": ...}}` to output node types (`save_image`, `l2i`) when missing.
6. Batch Envelope
	- Final POST body: `{ "prepend": (priority>0), "batch": { "graph": {id:"workflow", nodes:{...}, edges:[...]}, "runs": 1 } }`.
7. Tracking
	- Response yields `batch.batch_id` + `item_ids`; first item_id is resolved to a queue item to obtain `session_id` for Socket.IO subscription.

Current improvement opportunities (roadmap):
- Cache compiled JSONPath objects.
- Warn when a stored JSONPath matches zero locations (drift detection).
- Add `build_submission_payload()` helper for dry runs / debugging.
- Uniform `to_api_format()` on all field classes to remove type branching.

This section documents the stable contract so downstream code or contributors can reason about changes confidently.

## 🧪 Testing
```bash
pixi run test
```