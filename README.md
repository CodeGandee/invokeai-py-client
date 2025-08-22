# InvokeAI Python Client

[![Documentation](https://img.shields.io/badge/docs-github.io-blue)](https://codegandee.github.io/invokeai-py-client/)
[![PyPI](https://img.shields.io/pypi/v/invokeai-py-client)](https://pypi.org/project/invokeai-py-client/)
[![License](https://img.shields.io/github/license/CodeGandee/invokeai-py-client)](LICENSE)

> Turn an [InvokeAI](https://github.com/invoke-ai/InvokeAI) GUI workflow into a high‑throughput Python batch pipeline: export the workflow JSON and run large, parameterized image generations with minimal ceremony.

Built for existing GUI users: discovers ordered form inputs, provides typed setters, submits (sync / async / streaming), and maps output nodes to produced image filenames—enabling loops, sweeps, scheduled batches, regressions, and reproducible artifacts.

**[📚 Documentation](https://codegandee.github.io/invokeai-py-client/) | [🚀 Quick Start](https://codegandee.github.io/invokeai-py-client/getting-started/quickstart/) | [📖 API Reference](https://codegandee.github.io/invokeai-py-client/api-reference/) | [💡 Examples](https://codegandee.github.io/invokeai-py-client/examples/)**

---
## 1. Introduction, Scope & Audience

### About InvokeAI
InvokeAI is an open creative engine and professional-grade web UI for image generation, refinement, and workflow authoring. It provides:
- A modern browser UI (generation, refinement, unified canvas)
- Node-based workflow editor & export (the JSON this client consumes)
- Board & gallery management with metadata-rich images
- Support for multiple model families (SD1.x / SD2 / SDXL / FLUX, ckpt & diffusers)
- Model & embedding management, upscaling, control components

This client does not re‑implement the UI; instead it leverages the exported workflow artifact and selected REST endpoints to let GUI users automate large, repeatable runs in Python.

### What This Is
Focused, typed access to a subset of InvokeAI capabilities: loading exported workflow JSON, enumerating & setting form inputs, submitting executions, tracking progress, managing boards/images, resolving models, and mapping outputs.

### Scope (Core Domains)
1. Workflows – load, list ordered inputs, set, submit (sync/async/stream), map outputs.
2. Boards & Images – list/create, upload, associate outputs.
3. DNN Models – discover & bind to model identifier fields.

Out‑of‑scope (current): arbitrary graph mutation, full REST surface parity, subgraph re‑execution, advanced visualization.

### Intended Users
Primary audience: existing InvokeAI GUI users who prototype workflows visually and then want to *automate large or repeatable runs (batch processing, parameter sweeps, scheduled jobs, regression comparisons)* using Python—without re‑authoring or reverse‑engineering the graph.

Secondary audiences:
- **Tool / CLI Builders**: Layer higher‑level interfaces atop stable ordered inputs & output mapping.
- **Contributors / Extenders**: Add field detection rules or repositories while preserving public invariants.

### Design Principles (Condensed)
- Treat exported workflow JSON as immutable source of truth (value‑only substitution on submit).
- Stable, depth‑first index ordering of form inputs (ignore legacy `exposedFields`).
- Strongly typed `Ivk*Field` objects; open/closed detection registry (no giant if/elif chains in user code).
- Minimal state; explicit operations (no hidden mutation of the original definition).

---
## 2. User Guide: Usage Pattern & Examples

### High‑Level Flow
1. Export a workflow from InvokeAI GUI.
2. Load JSON → `WorkflowDefinition`.
3. Create handle via `client.workflow_repo.create_workflow(def)`.
4. Enumerate ordered inputs (`list_inputs()`) and note indices.
5. Set `.value` on the retrieved field objects you care about.
6. Submit (`submit_sync()` / `await submit(...)`).
7. Wait for completion & map outputs (`map_outputs_to_images`).

Invariants: only form‑derived inputs are public; unchanged literals stay untouched; indices shift only if the GUI form structure changes (containers/fields add/remove/reorder).

> Important: Only parameters you place into the workflow's **Form** panel in the InvokeAI GUI are discoverable as ordered inputs here. Drag (or add) the fields you want to control into the Form region before exporting the workflow JSON. Anything left outside remains a literal in the graph and cannot be programmatically changed via this client.

![InvokeAI workflow form showing exposed fields](examples/pipelines/gui-sdxl-text-to-image.png)

### Input Fields (Important)

Input discovery relies only on a depth‑first traversal of the Form tree in the exported workflow JSON. Many InvokeAI workflow fields lack a stable `label`, and field names are not globally unique, so the **index** is the single stable handle while the form layout remains unchanged.

Ordering rule (plain terms): traverse containers in the order they appear; inside each, visit child fields top → bottom (and nested containers recursively). Visually: think of reading the form from top to bottom, descending into each container as you encounter it.

![Input Discovery and Mapping Flow](docs/examples/input-mapping.svg)

> **Note**: The diagram above illustrates the depth-first input discovery process from the [sdxl-flux-refine.py](examples/pipelines/sdxl-flux-refine.py) example workflow. For more detailed workflow examples and documentation, see the [examples documentation](docs/examples/).

Code example (listing + index mapping only):

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition
from invokeai_py_client.ivk_fields import SchedulerName  # enum of valid schedulers

client = InvokeAIClient.from_url("http://localhost:9090")
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
)

# Depth‑first discovery (pre‑order). Indices are the ONLY stable handle.
indexed = []
for inp in wf.list_inputs():  # depth-first / pre-order over the Form tree
    label = (inp.label or inp.field_name) or '-'
    print(f"[{inp.input_index:02d}] {label}  field={inp.field_name}  node={inp.node_name}")
    indexed.append((inp.input_index, label, inp.field_name))

# Access a field by index (example: set positive prompt if index 1)
pos_idx = 1  # taken from printed list above
pos_field = wf.get_input_value(pos_idx)
if hasattr(pos_field, 'value'):
    pos_field.value = "A cinematic sunset over snowy mountains"

# Tip: avoid containers -> indices match simple top→bottom visual order.
```

Pattern: defining stable index constants + retrieval/logging (excerpted & simplified from `sdxl-text-to-image.py`):

```python
# After listing inputs once, you may snapshot their indices for the current workflow version.
IDX_MODEL = 0
IDX_POS_PROMPT = 1
IDX_NEG_PROMPT = 2
IDX_WIDTH = 3
IDX_HEIGHT = 4
IDX_STEPS = 5
IDX_CFG_SCALE = 6
IDX_SCHEDULER = 7

# Retrieve by index (assert expected field types where helpful)
field_model = wf.get_input_value(IDX_MODEL)
pos = wf.get_input_value(IDX_POS_PROMPT); pos.value = "A cinematic sunset"
neg = wf.get_input_value(IDX_NEG_PROMPT); neg.value = "blurry, low quality"
width = wf.get_input_value(IDX_WIDTH); width.value = 1024
height = wf.get_input_value(IDX_HEIGHT); height.value = 1024
steps = wf.get_input_value(IDX_STEPS); steps.value = 30
cfg = wf.get_input_value(IDX_CFG_SCALE); cfg.value = 7.5
sched = wf.get_input_value(IDX_SCHEDULER); sched.value = SchedulerName.DPMPP_3M_K.value

# Optional logging helper
def log(idx):
    meta = wf.get_input(idx)
    val = getattr(wf.get_input_value(idx), 'value', None)
    print(f"[{idx}] {(meta.label or meta.field_name)!r} -> {val!r}")

for i in [IDX_POS_PROMPT, IDX_NEG_PROMPT, IDX_WIDTH, IDX_HEIGHT, IDX_STEPS, IDX_CFG_SCALE, IDX_SCHEDULER]:
    log(i)
```

Simplest workflow authoring strategy:
- If index reasoning feels confusing, **don’t use containers**. Then the indices are just the vertical order of fields (top = 0, next = 1, ...).
- When you *must* reorganize the form, expect downstream indices to shift. Re‑run `list_inputs()` and update any hard‑coded indices in scripts.

Practical tips:
- Keep a small comment block in your automation script capturing the current index → label snapshot.
- Group frequently tuned parameters early so their indices are less likely to shift when you add rare/advanced ones later.
- Avoid gratuitous container nesting unless you need visual grouping in the GUI.

### Output Fields (Boards & Image Mapping)

An "output field" in this client context is simply a **board selector exposed in the Form** for an output‑capable node. Only those board fields you expose become part of ordered inputs and therefore:

1. Let you configure which board receives that node's images at submission time.
2. Provide a stable anchor for mapping node → produced image filenames after completion.

If a node writes to a board but you did NOT expose its board field in the Form, this client will still map its images if the node type is output‑capable; however it becomes **your responsibility** to ensure either:
- The node's board output is disabled in the workflow graph, or
- The workflow JSON hard‑codes a valid board id (e.g. `'none'` for uncategorized) so images land somewhere valid.

Key points:
- Board configuration happens through input fields (they appear in `list_inputs()` with `field_name == 'board'`).
- Boards belong to nodes; after execution we correlate queue/session data and return per‑node image name lists.
- Node → image mapping uses only what the server produced; the workflow JSON structure itself is not mutated.

Unified mapping example (node_id and input_index linkage):

Each `IvkWorkflowInput` (and thus each output from `wf.list_outputs()`) carries a `node_id`. We first build a map `node_id -> input_index` for board-exposed outputs, then map runtime results back to both the originating node and its input index.

```python
# 1. Execute (assumes inputs already set)
queue_item = wf.wait_for_completion_sync(timeout=180)

# 2. Enumerate board-exposed output fields (these are IvkWorkflowInput objects)
outputs = wf.list_outputs()
output_index_by_node_id = {o.node_id: o.input_index for o in outputs}

# 3. Runtime node -> image filenames
mappings = wf.map_outputs_to_images(queue_item)

# 4. Display per-node info (includes board + images)
for m in mappings:
    node_id = m['node_id']
    idx = output_index_by_node_id.get(node_id, -1)
    images = m.get('image_names') or []
    print(f"idx={idx:02d} node={node_id[:8]} board={m.get('board_id')} images={images}")

# 5. Invert to input_index -> [image_names]
index_to_images: dict[int, list[str]] = {}
for m in mappings:
    idx = output_index_by_node_id.get(m['node_id'])
    if idx is None:
        continue
    for name in m.get('image_names') or []:
        index_to_images.setdefault(idx, []).append(name)

print("Index to images:")
for idx, names in sorted(index_to_images.items()):
    print(f"  {idx:02d} -> {names}")

# 6. Optional richer structure (node_id -> (input_index, first_image_name))
images_by_node: dict[str, tuple[int, str]] = {}
for m in mappings:
    idx = output_index_by_node_id.get(m['node_id'], -1)
    first_name = (m.get('image_names') or [''])[0]
    images_by_node[m['node_id']] = (idx, first_name)
```

Pre‑flight (optional) you can inspect which nodes are considered outputs:

```python
for out in wf.list_outputs():
    # out is similar shape to an input descriptor but represents a board-exposed output node
    print(out.node_id, getattr(out, 'field_name', 'board'))
```

Recommendation: expose the board fields for every final image you care about so you can cleanly route different outputs to distinct boards during automation.

### Minimal SDXL Text‑to‑Image
Full script: `examples/pipelines/sdxl-text-to-image.py`
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
)

# Inspect ordered inputs
for inp in wf.list_inputs():
    print(f"[{inp.input_index}] {inp.label}")

# Set prompt (assume index 0 from listing) and steps (found by inspection)
prompt = wf.get_input_value(0)
if hasattr(prompt, "value"):
    prompt.value = "A cinematic sunset over snowy mountains"

# Submit & block
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=180)
print("Status:", result.get("status"))

# Map output nodes to image names
for m in wf.map_outputs_to_images(result):
    print(m["node_id"], m.get("image_names"))
```

### Minimal Flux Image‑to‑Image (Conceptual)
Full script (see broader refinement & multi-output pattern in): `examples/pipelines/sdxl-flux-refine.py`
```python
from invokeai_py_client import InvokeAIClient, WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/flux-image-to-image.json")
)

# Assume you already uploaded an image and know its name
INPUT_IMAGE_NAME = "my_source.png"

for inp in wf.list_inputs():
    print(f"[{inp.input_index}] {inp.label} :: {inp.field_name}")

# Set model / image / prompts using indices discovered above
image_field = wf.get_input_value(1)
if hasattr(image_field, 'value'):
    image_field.value = INPUT_IMAGE_NAME

positive_prompt = wf.get_input_value(5)
if hasattr(positive_prompt, 'value'):
    positive_prompt.value = "Futuristic portrait, volumetric lighting"

wf.submit_sync()
queue_item = wf.wait_for_completion_sync(timeout=240)
for m in wf.map_outputs_to_images(queue_item):
    print("Output node", m['node_id'], "->", m.get('image_names'))
```


### Execution Modes
| Mode | When | API |
|------|------|-----|
| Blocking | Simple scripts | `submit_sync()` + `wait_for_completion_sync()` |
| Async + Events | Concurrent UI / dashboards | `await submit(subscribe_events=True)` + callbacks |
| Hybrid Streaming | Need events while blocking | `async for evt in submit_sync_monitor_async()` |


---
## 3. Developer Guide: Architecture & Design

### Module Overview
| Module / Layer | Purpose |
|----------------|---------|
| `client.py` | Connection + HTTP plumbing + repository access. |
| `workflow/` | Definition loading, input discovery, submission building, output mapping. |
| `ivk_fields/` | Typed field classes + model/board/image resource wrappers. |
| `board/` | Board repository & image download/upload helpers. |
| `models/` (DNN) | Model metadata lookup & synchronization helpers. |

### Discovery & Field System
Depth‑first traversal of the workflow `form` tree produces an ordered list of `IvkWorkflowInput` objects. Each holds: `input_index`, `label`, `field_name`, `node_name`, concrete `field` (an `Ivk*Field`). Detection is plugin driven: predicate → builder. New field types can register externally (open/closed principle).

### Submission Pipeline
1. Copy raw workflow JSON. 2. Substitute only values that users changed (by visiting discovered inputs). 3. Post resulting graph to enqueue endpoint. No structural edits: edges/nodes remain intact.

### Output Mapping
Filters form inputs whose `field_name == 'board'` and whose node type is output‑capable (implements board persistence). After completion, correlates session/queue data to produce image filename lists per node (tiered results vs intermediates if applicable).

### Key Invariants
- Ordered inputs reflect GUI form semantics, not node graph topological order.
- Field concrete class is stable post‑discovery (no replacement with different runtime type).
- Literals remain even if an edge also supplies a value (mirrors GUI precedence model).
- No hidden mutation of original workflow definition object.

### Extensibility Points
| Area | Mechanism |
|------|-----------|
| Field detection | Register predicate/builder pairs. |
| Model resolution | `sync_dnn_model` strategies (by name / base). |
| Output mapping | Extend node capability classification. |
| Drift tooling | Export & verify input index map JSON. |

### Validation & Drift
`validate_inputs()` performs per‑field checks pre‑submission. Drift utilities compare previously exported `jsonpath` + index records to current discovery to surface: unchanged / moved / missing / new.

### Contributing
1. Review invariants (`context/design/usage-pattern.md`).
2. Keep public method signatures stable when feasible.
3. Add/adjust tests for discovery, submission, mapping, or field changes.
4. Sync docs with behavior changes (README + design notes).

### Testing
```bash
pixi run test
```

### License
See [LICENSE](LICENSE).

---
If something diverges from behavior, open an issue or PR—docs and code should evolve together.