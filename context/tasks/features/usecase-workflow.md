# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

## Requirements of the workflow subsystem in `client-api`

### Before you start
in below, we use `data\workflows\flux-image-to-image.json` as an example workflow definition file, denote this as `example-workflow.json`.

we already have partial implementation of the workflow subsystem in `src\invokeai_py_client\workflow.py`, but it is not complete, and the APIs are subject to change.

### Requirements

- The `client-api` should have a `workflow-repo` that manages the workflows, just like the `board-repo` (see `src\invokeai_py_client\repositories\board.py`), it should have methods to list, get, create, delete workflows, and also methods to upload and download workflow definitions.

- our design should work with any workflow definition that is exported from the InvokeAI GUI.

- each workflow has different kinds of nodes, and different numbers of inputs and outputs. Note that, workflows typically write their outputs to a `board`, so in order to find out the outputs of a workflow, we need to look at the nodes in the workflow and see which nodes write to which boards.

- in GUI, user can add some of the fields of the nodes as inputs, by adding them to the `form` section of the workflow definition, these fields are called `workflow-inputs`, they map to some of the fields in the nodes, and they are somewhat like the public interface of the workflow. Our API should capture this concept, and expose these `workflow-inputs` to the user, allowing direct field manipulation through the `get_input` method.

- we know that InvokeAI has a type system, some of them are already defined in our data models, see `src\invokeai_py_client\models.py`, for more info you can see `context\hints\invokeai-kb\about-invokeai-workflow-input-types.md`. We shall define data models for these types (naming them as `Ivk<TypeName>`), and use these data models for the workflow input fields.

- we know that heavy data like images and masks are referred to by their names in the workflow definition, the names are given by the InvokeAI backend when these data are uploaded to the backend, and to get the actual data, we need to download them from the backend given the names. 
  
- when everything is set, we can submit the workflow to the backend, and InvokeAI will execute the workflow, the execution will create a job, and we can track the job status, and get the results back when the job is done. The results will be in the form of `client-types`, which can be used to get the output. `examples/` contains some demos of how to interact with InvokeAI backend about workflows, you can refer to them for more details.

- note that, after everything is done, results are retrieved, those inputs and outputs uploaded to InvokeAI can be discarded, we need to explicitly delete them in the backend, otherwise they will stay in the backend and occupy space.
  
## Workflow subsystem usage pattern

here we describe the use cases of the workflow subsystem in `client-api`, before designing the API, we need to understand how users will use it.

Below we use `data\workflows\sdxl-flux-refine.json` as an example workflow definition file, denote this as `example-workflow.json`, some useful info as to how to find things can be found in `context\tasks\features\task-explore-workflow.md`

### Use case 1: loading `example-workflow.json` and listing inputs

**Scenario**: A developer wants to load a SDXL-FLUX workflow from a JSON file and discover what inputs can be configured before execution.

**Code Example**:
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition, WorkflowHandle, IvkWorkflowInput
## Workflow subsystem usage pattern

```

The workflow subsystem now centers around an immutable *definition* plus a lightweight *handle* that supports:
  - Index‑centric input inspection & mutation (`list_inputs()`, `preview()`, `set_input_value_simple()`, `set_many()`).
  - Safe batch updates (atomic validation & overwrite guard for edge‑fed fields).
  - Dynamic model / prompt discovery without hard‑coding node UUIDs (heuristics use labels, field names, node types).
  - Submission helpers (`submit_sync`) plus polling convenience on the handle.
  - Introspection utilities for output-node to produced-assets mapping (see mapping test).

Below: refreshed end‑to‑end usage with `data/workflows/sdxl-flux-refine.json` as the running example.

### Use case 1: Load workflow & inspect inputs (index‑centric)

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository

client = InvokeAIClient(base_url="http://127.0.0.1:9090")
repo = WorkflowRepository(client)
workflow = repo.create_workflow_from_file("data/workflows/sdxl-flux-refine.json")

print(f"Workflow: {workflow.definition.name}  inputs={len(workflow.inputs)}")

# List (ordered) inputs; each has stable input_index
for inp in workflow.list_inputs():
    f = inp.field
    val = getattr(f, 'value', None)
    print(f"[{inp.input_index:02d}] {inp.label or inp.field_name} | node_type={inp.node_type} field={inp.field_name} type={type(f).__name__} value={val}")

# Quick preview (condensed rows) via helper
for row in workflow.preview():
    # row: {index,label,type,value}
    print(row)
```

Key points:
  - Input ordering derives from the workflow form; indices are stable across runs of the same definition.
  - `workflow.inputs` is a cached list; prefer `list_inputs()` to respect any future lazy refresh logic.

### Use case 2: Dynamic discovery & bulk updates (no UUID literals)

```python
PROMPT_TXT = "Majestic sunset over alpine lake, ultra-detailed, 8k"
NEG_TXT    = "blurry, low quality, distorted"
SDXL_STEPS = 20
FLUX_STEPS = 12

inputs = workflow.list_inputs()

def find_index(pred):
    for i in inputs:
        try:
            if pred(i):
                return i.input_index
        except Exception:
            continue
    return None

# Heuristics using labels / field names / node types
pos_idx = find_index(lambda x: x.field_name in {"value","prompt"} and 'positive prompt' in (x.label or '').lower())
neg_idx = find_index(lambda x: x.field_name in {"value","prompt"} and 'negative prompt' in (x.label or '').lower())
width_idx = find_index(lambda x: x.field_name == 'width')
height_idx = find_index(lambda x: x.field_name == 'height')

# Steps: first two num_steps fields map to SDXL then FLUX phase
step_indices = [i.input_index for i in inputs if i.field_name == 'num_steps']

# Model identifiers: choose by node_type suffix/prefix (no UUID)
def model_idx(selector):
    return find_index(lambda x: x.field_name == 'model' and selector in (x.node_type or ''))

sdxl_model_idx = model_idx('sdxl')
flux_model_idx = model_idx('flux')

updates = {}
if pos_idx is not None: updates[pos_idx] = PROMPT_TXT
if neg_idx is not None: updates[neg_idx] = NEG_TXT
if width_idx is not None: updates[width_idx] = 1024
if height_idx is not None: updates[height_idx] = 1024
if step_indices: updates[step_indices[0]] = SDXL_STEPS
if len(step_indices) > 1: updates[step_indices[1]] = FLUX_STEPS

# Example: setting model fields requires structured dict (already provided by model repo in real tests)
def as_model_dict(m):
    return None if not m else {
        'key': m.key,
        'hash': m.hash,
        'name': m.name,
        'base': getattr(m.base,'value',str(m.base)),
        'type': getattr(m.type,'value',str(m.type)),
    }

# (Pseudo) assume we selected models earlier
sdxl_model = flux_model = None  # replace with real selections
if sdxl_model_idx is not None and sdxl_model: updates[sdxl_model_idx] = as_model_dict(sdxl_model)
if flux_model_idx is not None and flux_model: updates[flux_model_idx] = as_model_dict(flux_model)

print(f"Applying {len(updates)} updates via set_many()")
workflow.set_many(updates)

for row in workflow.preview():
    print(row)
```

Advantages:
  - Single atomic `set_many()` minimizes round‑trips & prevents partial state.
  - Logic resilient to node ID churn; only relies on semantic labels/types.
  - Safe: implementation guards against overwriting inputs connected by graph edges (edge‑fed).

### Use case 3: Validation & submission (wrapped helpers – no raw API calls)

The client API intentionally hides raw HTTP polling & Socket.IO wiring. Use the high‑level helpers on `WorkflowHandle` instead of calling InvokeAI endpoints directly.

#### 3.1 Minimal synchronous submission
```python
# 1. Validate (optional but recommended)
errors = workflow.validate_inputs()
if errors:
    for idx, msgs in errors.items():
        print(f"[INVALID] {idx}: {', '.join(msgs)}")
    raise SystemExit("Input validation failed")

# 2. Submit (blocking enqueue only)
submission = workflow.submit_sync(board_id="none")
print("Batch:", submission["batch_id"], "Session:", workflow.session_id)

# 3. Wait for completion (handles polling & status transitions)
queue_item = workflow.wait_for_completion_sync(
    poll_interval=0.5,
    timeout=120.0,
    progress_callback=lambda qi: print("Status=", qi["status"])  # fires only on status change
)

print("Final status:", queue_item["status"])

# (Optional) Map outputs to produced image names in one call
queue_item2, mappings = workflow.wait_for_completion_sync(map_outputs=True)
for m in mappings:
    print(f"Output index {m.input_index} -> {m.image_names}")
```

Key points:
  - No manual URL construction or `requests` usage is needed.
  - `submit_sync()` stores `batch_id`, `session_id`, `item_id` internally on the handle.
  - `wait_for_completion_sync()` encapsulates polling/backoff & raises on failure/timeout.
  - Set `map_outputs=True` to return output→image mappings (uses handle’s internal logic, not ad‑hoc board scans).

#### 3.2 Asynchronous submission with real‑time events (no manual Socket.IO code)
```python
import asyncio

async def run_async_workflow():
    # Submit + subscribe to events by passing callbacks
    def on_started(evt):
        print("▶", evt.get("node_type"), "started")
    def on_progress(evt):
        p = evt.get("progress")
        if p is not None:
            print(f"⏳ {p*100:.0f}%")
    def on_complete(evt):
        print("✅", evt.get("node_type"), "done")
    def on_error(evt):
        print("❌ Error in", evt.get("node_type"), evt.get("error"))

    await workflow.submit(
        board_id="none",
        subscribe_events=True,
        on_invocation_started=on_started,
        on_invocation_progress=on_progress,
        on_invocation_complete=on_complete,
        on_invocation_error=on_error,
    )

    # Await completion via event stream (no polling)
    queue_item = await workflow.wait_for_completion(timeout=90.0)
    print("Final status:", queue_item["status"])

    # Optional: include output mappings
    queue_item2, mappings = await workflow.wait_for_completion(map_outputs=True)
    for m in mappings:
        print(f"Output {m.input_index}: {m.image_names}")

asyncio.run(run_async_workflow())
```

Notes:
    - Both patterns rely solely on `WorkflowHandle` methods; no direct InvokeAI REST paths or Socket.IO room names are needed in user code.
    - Call `workflow.cancel()` / `await workflow.cancel_async()` to abort.
    - Internal state (`session_id`, `item_id`) is set during submission; helpers will raise if called prematurely.

### Use case 4: Output mapping (node → produced images)

The handle exposes `list_outputs()` (ordered like inputs) to identify output nodes; mapping real images currently uses queue/session data as shown in the dedicated test (`test_node_to_image_output_mapping.py`). A distilled snippet:

```python
queue_item = qi  # obtained after completion
session = queue_item.get('session', {})
results = session.get('results', {})
src_map = session.get('prepared_source_mapping', {})

images_by_original = {}
for prepared_id, payload in results.items():
    orig = src_map.get(prepared_id, prepared_id)
    img = (payload or {}).get('image', {})
    name = img.get('image_name')
    if name:
        images_by_original.setdefault(orig, []).append(name)

for out in workflow.list_outputs():
    print(out.node_id, images_by_original.get(out.node_id, []))
```

Fallback tiers (already implemented in test script): legacy `outputs` array, and traversal search through execution graph if modern results absent.

### Use case 5: Rapid experimentation / preview

`preview()` returns a lightweight snapshot for logging or UI binding without enumerating entire field objects:

```python
for row in workflow.preview():
    # row = { 'index','label','type','value' }
    print(row)
```

### Design summary (refactored)

| Concern | Previous Approach | Current Approach |
|---------|-------------------|------------------|
| Input addressing | Node UUID + field name | Stable integer index (0..N-1) |
| Bulk mutation | Repeated per-field set | `set_many()` atomic update |
| Safety | Manual caution | Edge-fed overwrite guard + validation |
| Discovery | Hard-coded IDs common | Label/field/node_type heuristics |
| Output mapping | Ad-hoc board scans | Structured session results + fallbacks |
| Model fields | Manual nested edits | Normalized dict accepted by `set_many()` |

Best practices:
  - Never persist node UUID literals in application code; rely on indices or semantic heuristics.
  - Batch whenever configuring more than one input.
  - Validate before submission; fail fast on missing required fields.
  - Persist the exported API graph for reproducibility / debugging.
  - Treat output node → image mapping as a read‑only post‑processing step.