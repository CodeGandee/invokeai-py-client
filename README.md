# InvokeAI Python Client

> A typed Python client that turns GUI‑authored InvokeAI workflow JSON files into programmable, reproducible automation scripts.

The library discovers ordered user‑configurable inputs directly from a workflow's `form` tree, lets you assign values with strong typing, submits jobs (sync / async / streaming), and maps declared output nodes back to produced image filenames.

---
## 1. Introduction, Scope & Audience

### What This Is
Focused, typed access to a subset of InvokeAI capabilities: loading exported workflow JSON, enumerating & setting form inputs, submitting executions, tracking progress, managing boards/images, resolving models, and mapping outputs.

### Scope (Core Domains)
1. Workflows – load, list ordered inputs, set, submit (sync/async/stream), map outputs.
2. Boards & Images – list/create, upload, associate outputs.
3. DNN Models – discover & bind to model identifier fields.

Out‑of‑scope (current): arbitrary graph mutation, full REST surface parity, subgraph re‑execution, advanced visualization.

### Intended Users
- **Automation / Power Users**: Script reproducible runs built from GUI workflows.
- **Tooling Authors**: Build higher‑level CLIs or dashboards on top of stable input ordering & output mapping.
- **Contributors**: Extend field detection or repository behaviors without destabilizing public APIs.

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

### Minimal SDXL Text‑to‑Image
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

### Output Mapping Essentials
`workflow.list_outputs()` returns board-exposed output nodes (ordered subset). After completion, `map_outputs_to_images(queue_item)` yields dictionaries including: `node_id`, `tier`, `image_names`, `board_id`.

### Execution Modes
| Mode | When | API |
|------|------|-----|
| Blocking | Simple scripts | `submit_sync()` + `wait_for_completion_sync()` |
| Async + Events | Concurrent UI / dashboards | `await submit(subscribe_events=True)` + callbacks |
| Hybrid Streaming | Need events while blocking | `async for evt in submit_sync_monitor_async()` |

### Drift Detection (Optional)
Export the current index map; later compare after a new GUI export to classify unchanged / moved / missing / new inputs (see design docs). Useful for regenerating stable automation scripts.

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

### Roadmap (Indicative)
| Area | Direction |
|------|-----------|
| Diagnostics | Field detection stats & fallback counts |
| Strict Mode | Fail fast on unknown field types |
| Payload Preview | Inspect built submission graph pre-enqueue |
| Output Mapping | Extend beyond images (latents / masks) |
| Performance | Cache discovery artifacts |

Out‑of‑scope for now: arbitrary graph mutation, server caching policy shaping, rich visualization layers.

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