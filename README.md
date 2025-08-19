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

### Implementation status (confirmed in code)

- Workflow JSON preservation and minimal mutation
  - Raw GUI workflow JSON is preserved and deep-copied during submission; only targeted values are updated for mutation efficiency and forward compatibility.
  - JSONPath expressions are recorded per input to locate the target within the preserved JSON when assembling the API graph.

- Input discovery from the form tree
  - Inputs are discovered exclusively from the form.elements tree (starting at root), ignoring exposedFields. This yields a deterministic, depth-first ordering with stable indices.

- Field system safety and default-constructability
  - All IvkField subclasses are default-constructable. Model identifier fields (IvkModelIdentifierField) now include safe defaults for required attributes (key/hash/name/base/type) allowing parameter-less construction.
  - Exact-type immutability is enforced on workflow inputs: once a field’s concrete class is discovered, replacements must use the same concrete class (prevents semantic drift).

- Submission graph assembly and eventing
  - Minimal node graph extraction with normalization (e.g., board normalization, GUI helper nodes like notes are skipped) and 1:1 edge conversion to API edges.
  - Synchronous submission with polling and two async patterns:
    - Asynchronous submission with real-time event subscription (invocation_started, invocation_progress, invocation_complete, invocation_error, queue_item_status_changed, graph_complete).
    - Hybrid “submit sync, monitor async” streaming generator for progressive updates until completion.

- Connected-input pruning behavior (default-retain)
  - By default, inputs that are fed by edges are retained in the node payload to match GUI-generated payloads and satisfy server schema expectations for required fields.
  - To enable legacy pruning for experiments, set INVOKEAI_PRUNE_CONNECTED_FIELDS=1.

- Board injection scope (pragmatic)
  - When a board_id is provided, board injection is applied to output and image-handling node types: save_image, l2i, flux_vae_decode, flux_vae_encode, hed_edge_detection (only when missing on the node).

- DNN model repository (v2 traversal)
  - The DNN model repository lists and retrieves models via the v2 endpoints using the documented relative traversal approach, maintaining compatibility with evolving upstream routing.
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

## 🧪 Practical Guides: End-to-End Workflows

These guides mirror the intended usage patterns demonstrated in the test suite and show how to compose the API for real workflows.

### Guide 1: FLUX Image-to-Image (i2i) in 6 steps

1) Initialize client and board, upload an input image
```python
import os, time
from io import BytesIO
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field
from PIL import Image

client = InvokeAIClient.from_url(os.getenv("INVOKEAI_BASE_URL", "http://127.0.0.1:9090"))

# Create or use uncategorized board
board_name = f"demo_flux_i2i_{int(time.time())}"
try:
    board = client.board_repo.create_board(board_name)
except Exception:
    board = client.board_repo.get_uncategorized_board()

# Generate a simple test image (or load bytes from disk)
img = Image.new("RGB", (1024, 1024), "purple")
buf = BytesIO(); img.save(buf, format="PNG"); img_bytes = buf.getvalue()

uploaded = board.upload_image_data(image_data=img_bytes, filename="input.png")
```

2) Load the workflow
```python
wf_path = "data/workflows/flux-image-to-image.json"
workflow = WorkflowRepository(client).create_workflow_from_file(wf_path)
```

3) Build a robust (node_id, field_name) → input_index lookup
```python
lookup = {(inp.node_id, inp.field_name): inp.input_index for inp in workflow.list_inputs()}
```

4) Set simple fields (prompt, image, numeric params)
```python
# Keys match the sample workflow; adjust if your template differs
PROMPT_KEY = ("01f674f8-b3d1-4df1-acac-6cb8e0bfb63c", "prompt")
IMAGE_KEY  = ("7b056f05-a4fe-40d3-b913-1a4b3897230f", "image")
STEPS_KEY  = ("9c773392-5647-4f2b-958e-9da1707b6e6a", "num_steps")
DENOISE_KEY = ("9c773392-5647-4f2b-958e-9da1707b6e6a", "denoising_strength")
SAVE_NODE = "7e5172eb-48c1-44db-a770-8fd83e1435d1"  # flux_vae_decode node id in sample
BOARD_KEY = (SAVE_NODE, "board")

def set_value(key, value):
    if key in lookup:
        field = workflow.get_input_value(lookup[key])
        if hasattr(field, "value"):  # primitives/resources/enum
            field.value = value

set_value(PROMPT_KEY, "Dreamlike i2i test, vibrant colors, cinematic lighting")
set_value(IMAGE_KEY, uploaded.image_name)
set_value(STEPS_KEY, 12)
set_value(DENOISE_KEY, 0.7)
set_value(BOARD_KEY, getattr(board, "board_id", getattr(board, "board", {}).get("board_id", "none")))
```

5) Bind model fields via model repository → to IvkModelIdentifierField
```python
from invokeai_py_client.dnn_model import DnnModelType, BaseDnnModelType

models = client.dnn_model_repo.list_models()
def pick(pred):
    return next((m for m in models if pred(m)), None)

flux_main = pick(lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.Flux)
t5_encoder = pick(lambda m: m.type == DnnModelType.T5Encoder)
clip_embed = pick(lambda m: m.type == DnnModelType.CLIPEmbed)
flux_vae  = pick(lambda m: m.type == DnnModelType.VAE and m.base == BaseDnnModelType.Flux)

MODEL_NODE = "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90"  # flux_model_loader in sample

bindings = [
    ((MODEL_NODE, "model"), flux_main),
    ((MODEL_NODE, "t5_encoder_model"), t5_encoder),
    ((MODEL_NODE, "clip_embed_model"), clip_embed),
    ((MODEL_NODE, "vae_model"), flux_vae),
]

for key, model in bindings:
    if model and key in lookup:
        workflow.set_input_value(lookup[key], to_ivk_model_field(model))
```

6) Submit and wait for completion
```python
result = workflow.submit_sync(board_id=getattr(board, "board_id", "none"))
final = workflow.wait_for_completion_sync(timeout=int(os.getenv("WF_TIMEOUT", "180")))
print("Final status:", final.get("status"))
```

Tip: set INVOKEAI_PRUNE_CONNECTED_FIELDS=1 to prune edge-fed inputs while debugging API payloads.

Optional: dump the exact API graph (for debugging only)
```python
import json
api_graph = workflow._convert_to_api_format(getattr(board, "board_id", "none"))  # Private for inspection
with open("tmp/flux_i2i_api_graph.json", "w") as f:
    json.dump(api_graph, f, indent=2)
```

---

### Guide 2: SDXL → FLUX Refine (multi-stage, output boards)

1) Initialize client and load workflow
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository
from invokeai_py_client.ivk_fields.model_conversion import to_ivk_model_field

client = InvokeAIClient.from_url("http://127.0.0.1:9090")
wf = WorkflowRepository(client).create_workflow_from_file("data/workflows/sdxl-flux-refine.json")
lookup = {(inp.node_id, inp.field_name): inp.input_index for inp in wf.list_inputs()}
```

2) Set prompts and steps (shortened for tests)
```python
POSITIVE_NODE = "0a167316-ba62-4218-9fcf-b3cff7963df8"
NEGATIVE_NODE = "1711c26d-2b53-473c-aaf8-f600443d3c34"
SDXL_STEPS_NODE = "f7a96570-59e0-400d-8fc9-889a438534c0"
FLUX_DOMAIN_STEPS_NODE = "9c773392-5647-4f2b-958e-9da1707b6e6a"
FLUX_REFINEMENT_STEPS_NODE = "56fb09f9-0fdc-499e-9933-de31c3aa6e61"

def set_value(key, value):
    if key in lookup:
        field = wf.get_input_value(lookup[key])
        if hasattr(field, "value"):
            field.value = value

set_value((POSITIVE_NODE, "value"), "Mystical forest, bioluminescent trees, cinematic, ultra detailed")
set_value((NEGATIVE_NODE, "value"), "blurry, low quality, watermark, text, nsfw")
set_value((SDXL_STEPS_NODE, "steps"), 15)
set_value((FLUX_DOMAIN_STEPS_NODE, "num_steps"), 8)
set_value((FLUX_REFINEMENT_STEPS_NODE, "num_steps"), 12)

# Provide explicit meta params often expected by server schema
for node in [FLUX_DOMAIN_STEPS_NODE, FLUX_REFINEMENT_STEPS_NODE]:
    set_value((node, "width"), 1024)
    set_value((node, "height"), 1024)
    set_value((node, "denoising_start"), 0)
    set_value((node, "cfg_scale"), 1)
```

3) Route outputs to boards (three stages)
```python
SAVE_IMG_STAGE1 = "4414d4b5-82c3-4513-8c3f-86d88c24aadc"
SAVE_IMG_STAGE2 = "67e997b2-2d56-43f4-8d2e-886c04e18d9f"
SAVE_IMG_FINAL  = "abc466fe-12eb-48a5-87d8-488c8bda180f"

board_id = client.board_repo.get_uncategorized_board().board_id
for node in [SAVE_IMG_STAGE1, SAVE_IMG_STAGE2, SAVE_IMG_FINAL]:
    set_value((node, "board"), board_id)
```

4) Bind models based on node type
```python
from invokeai_py_client.dnn_model import DnnModelType, BaseDnnModelType

models = client.dnn_model_repo.list_models()
def pick(pred): return next((m for m in models if pred(m)), None)

sdxl_main  = pick(lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.StableDiffusionXL)
flux_main  = pick(lambda m: m.type == DnnModelType.Main and m.base == BaseDnnModelType.Flux)
t5_encoder = pick(lambda m: m.type == DnnModelType.T5Encoder)
clip_embed = pick(lambda m: m.type == DnnModelType.CLIPEmbed)
flux_vae   = pick(lambda m: m.type == DnnModelType.VAE and m.base == BaseDnnModelType.Flux)

# Node-type map for targeted model assignment
node_types = {}
for n in wf.definition.workflow.get("nodes", []):  # raw nodes preserved
    node_types[n.get("id")] = n.get("data", {}).get("type") or n.get("type")

for inp in wf.list_inputs():
    f = inp.field_name
    nt = node_types.get(inp.node_id, "")
    model = None
    if f == "model":
        if nt == "sdxl_model_loader": model = sdxl_main
        elif nt == "flux_model_loader": model = flux_main
    elif f == "t5_encoder_model": model = t5_encoder
    elif f == "clip_embed_model": model = clip_embed
    elif f == "vae_model": model = flux_vae
    if model:
        wf.set_input_value(inp.input_index, to_ivk_model_field(model))
```

5) Submit and monitor
```python
res = wf.submit_sync(board_id=board_id)
done = wf.wait_for_completion_sync(timeout=int(os.getenv("WF_TIMEOUT", "180")))
print("Final status:", done.get("status"))
```

Notes
- Connected inputs (fed by edges) are retained by default to match GUI payloads; set INVOKEAI_PRUNE_CONNECTED_FIELDS=1 to prune for experiments.
- When a board_id is provided, it is injected for output/image-handling nodes that lack a board (save_image, l2i, flux_vae_decode, flux_vae_encode, hed_edge_detection).
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
	- Build minimal API nodes: include `id`, `type`, `is_intermediate`, `use_cache` plus all literal input fields. By default, inputs fed by an edge are RETAINED to match GUI-generated payloads and satisfy the server's schema, which expects all required fields. To restore legacy pruning behavior for experiments, set the environment variable `INVOKEAI_PRUNE_CONNECTED_FIELDS=1`.
4. Edge Conversion
	- Each original GUI edge becomes an entry: `{ "source": {"node_id", "field"}, "destination": {"node_id", "field"} }`.
5. Board Injection
	- If a `board_id` was provided, apply `{"board": {"board_id": ...}}` to relevant output and image-handling node types (`save_image`, `l2i`, `flux_vae_decode`, `flux_vae_encode`, `hed_edge_detection`) when missing.
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