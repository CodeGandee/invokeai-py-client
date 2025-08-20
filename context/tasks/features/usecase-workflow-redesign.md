# Workflow Subsystem Use Cases (Redesign)

This document revisits the original `usecase-workflow.md` and updates the usage patterns to align with the **current implementation** and planned incremental improvements, while strictly conforming to the architectural rules in `usage-pattern.md`.

> Audience: InvokeAI GUI users transitioning to Python automation who only see ordered input fields in the GUI (not internal node UUIDs). All examples **avoid UUID exposure** unless explicitly placed under a debug section.

---
## 1. Design Principles (Unchanged Commitments)

| Principle | Status | Notes |
|-----------|--------|-------|
| Depth‑first ordered input indices are the ONLY public handle for inputs | Enforced | `input_index` assigned during form traversal |
| Never read or depend on `exposedFields` | Enforced | Only `form.elements` is used |
| Preserve original workflow JSON structure (no key creation/deletion) | Enforced | We only overwrite values inside existing dicts |
| All field edits funnel through typed `IvkField` instances | Enforced | `_create_field_from_node()` builds minimal typed field set |
| Raw original JSON (`WorkflowDefinition.raw_data`) remains immutable to users | Enforced | Internal copy mutated just‑before submission |
| Accept future upstream changes without schema break | Enforced | Unknown keys left untouched |

---
## 2. Delta vs Original Use Case Document

| Topic | Original | Redesign Enhancement |
|-------|----------|----------------------|
| Input Identification | Implicit index emphasis | Explicit: *index is the contract*, all examples center on `get_input(i)` |
| Field Typing | Conceptual list of types | Clarifies which types are currently implemented (`primitives`, `resources`, `model identifier`) and how to interact with them generically |
| UUID Exposure | Shown in printing examples | Hidden by default; optional debug mode only |
| Mutation Safety | Manual field value edits | Restated constraint: NEVER add/remove keys; only change values via field/assignment or `set_input_value()` |
| Output Handling | Board logic implied | Formalizes definition of output-capable node + board field exposed in form (same logic used in code) |
| Future Ergonomics | Not covered | Roadmap section for planned convenience APIs (aliases, batch set) without altering current contract |

---
## 3. Supported Field Categories (Current Implementation)

| Category | Class Examples | Has `.value` | Notes |
|----------|----------------|-------------|-------|
| Primitive | `IvkStringField`, `IvkIntegerField`, `IvkFloatField`, `IvkBooleanField` | Yes | Direct scalar assignment |
| Resource Reference | `IvkImageField`, `IvkBoardField`, `IvkLatentsField`, `IvkTensorField` | Yes | Image/latents value is a name string; board value is board_id |
| Model Identifier | `IvkModelIdentifierField` | No single `.value` | Structured properties (key, hash, name, base, type, submodel_type) |
| Enum | `IvkEnumField` | Yes | Provided if workflow JSON includes `options` / `ui_choices` |
| (Fallback) | Unrecognized complex | Appears as primitive/string | Will still submit correctly—value left as-is |

> Complex composite or conditioning field families may appear as plain dictionaries in raw JSON today. They are preserved unchanged; future phases may add typed wrappers transparently.

---
## 4. Use Case 1: Load Workflow & Discover Inputs

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowRepository, WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")
repo: WorkflowRepository = client.workflow_repo

wf_def = WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
handle = repo.create_workflow(wf_def)

inputs = handle.list_inputs()  # Ordered list; index is stable for this workflow file
print(f"Total inputs: {len(inputs)}")
for inp in inputs:
    # Minimal, UUID hidden
    field_type = type(inp.field).__name__.replace("Ivk", "")
    preview = getattr(inp.field, 'value', None)
    if isinstance(preview, str) and len(preview) > 40:
        preview = preview[:37] + '...'
    print(f"[{inp.input_index}] {inp.label or inp.field_name} <{field_type}> => {preview}")
```

**Key Points**
- Users NEVER need node IDs.
- If a label is blank in the GUI, we fall back to the field name.
- Ordering is derived strictly from the form tree depth-first traversal.

---
## 5. Use Case 2: Set Inputs by Index (Type-Aware & Safe)

### 5.1 Primitive & Resource Fields
```python
# Positive prompt at [0]
prompt_field = handle.get_input_value(0)   # IvkStringField
prompt_field.value = "A luminous nebula over icy mountains"

# Negative prompt at [1]
neg_field = handle.get_input_value(1)
neg_field.value = "blurry, low quality, distorted"

# Width at [2]; will validate constraints if present
width_field = handle.get_input_value(2)
width_field.value = 1024

# Height at [3]
height_field = handle.get_input_value(3)
height_field.value = 768

# Output board (if present) – board field may be optional
# Find first board field
board_inputs = [i for i in handle.list_inputs() if i.field_name == 'board']
if board_inputs:
    board_idx = board_inputs[0].input_index
    board_field = handle.get_input_value(board_idx)
    board_field.value = "samples"  # or a board UUID string
```

### 5.2 Model Identifier Field
```python
from invokeai_py_client.ivk_fields import IvkModelIdentifierField
model_input = next(i for i in handle.list_inputs() if isinstance(i.field, IvkModelIdentifierField))
model_field: IvkModelIdentifierField = handle.get_input_value(model_input.input_index)  # type: ignore

# Update selected properties (others left intact)
model_field.name = "cyberrealisticXL_v5"
model_field.base = "sdxl"
model_field.type = "main"
```

### 5.3 Complete Replacement (Advanced)
```python
original = handle.get_input_value(0)
replacement = type(original)(value="A crystal forest at dawn")  # Must be same concrete class
handle.set_input_value(0, replacement)
```

### 5.4 Validation
```python
errors = handle.validate_inputs()
if errors:
    for idx, msgs in errors.items():
        print(f"Input [{idx}] validation errors: {msgs}")
else:
    print("All inputs valid.")
```

**Rules Reinforced**
- Only overwrite existing value slots; never add keys.
- If a field lacks `.value` (e.g. model identifier), mutate its structured attributes individually.

---
## 6. Use Case 3: Submit Workflow & Track Progress

### 6.1 Synchronous Submission
```python
submission = handle.submit_sync(board_id="samples")
print("Batch submitted:", submission["batch_id"])
print("Session ID:", submission["session_id"])
```

### 6.2 Asynchronous with Optional Event Hooks
```python
import asyncio

async def run():
    async def on_started(evt):
        # evt may include internal node_id; not shown by default to user
        pass
    result = await handle.submit(
        board_id="samples",
        subscribe_events=True,
        on_invocation_started=on_started,
    )
    print("Submitted:", result["batch_id"])

asyncio.run(run())
```

### 6.3 Validation + Submission Pattern
```python
if handle.validate_inputs():
    raise RuntimeError("Fix input validation errors before submission")
handle.submit_sync(board_id="samples")
```

---
## 7. Use Case 4: Outputs & Image Mapping (Post-Run)

```python
# Identify output-capable board inputs
outputs = handle.list_outputs()  # Subset of inputs with board capability
for out in outputs:
    print(f"Output index [{out.input_index}] node '{out.node_name}' board field -> {out.field.value}")

# After job completion you can map output nodes to produced images
mapping = handle.map_outputs_to_images()  # Returns list[OutputMapping]
for m in mapping:
    print(f"Output [{m['input_index']}] -> board={m['board_id']} images={len(m['image_names'])} tier={m['tier']}")
```

**Evidence Tiers Recap**
1. `results` (strongest): Direct session results entries.
2. `legacy`: Fallback via legacy outputs array if present.
3. `traversal`: Structural inference if earlier tiers empty.
4. `none`: No images resolved.

---
## 8. Future Ergonomics (Planned, Not Yet Implemented)
| Feature | Rationale | User Impact |
|---------|-----------|-------------|
| `set(index, python_value)` sugar | Avoid manual field type inspection | Simpler scripts |
| Batch `set_many({...})` atomic updates | Reduce repetitive calls | Cleaner orchestration |
| Drift Map Export / Verify | Detect GUI reorder between versions | Stability in CI scenarios |
| Lightweight alias (f1,f2,...) | Script readability | Optional indirection |
| Typed wrappers for additional complex types | Richer validation | Incremental adoption |

All above will continue honoring: *index primary*, *no key mutations*, *no `exposedFields` usage*.

---
## 9. Conformance Checklist (Against `usage-pattern.md`)

| Rule | Conformity | Mechanism |
|------|------------|-----------|
| Ignore `exposedFields` | Yes | Only parse `form.elements` |
| Depth-first input order | Yes | Recursive traversal from `root` container |
| Immutable original keys | Yes | Only value overwrites via JSONPath at submit time |
| `jsonpath` stored per input | Yes | Each `IvkWorkflowInput.jsonpath` points to field dict |
| Keep literal values even if edge-connected | Yes | No pruning of node inputs before submission |
| UUID opacity for end users | Yes | Not surfaced in examples or public API text |
| Model forward compatibility | Yes | Unknown keys preserved (extra='allow') |

---
## 10. Troubleshooting Quick Table

| Symptom | Likely Cause | Resolution |
|---------|--------------|-----------|
| Validation error on submit | Required primitive `.value` is None | Assign value before submission |
| Field replacement TypeError | Different concrete field class | Recreate using `type(original)` |
| Output mapping empty | Workflow produced no images or board not exposed | Confirm output node board field is in form |
| Silent mismatch after GUI reorder | Indices changed | (Future) Use drift map verification |

---
## 11. Summary
The redesigned usage keeps **index-only interaction**, strengthens **structural safety**, and prepares for ergonomic enhancements without breaking existing workflows. Users migrating from the GUI can script confidently using just ordered indices and primitive Python assignments while the client preserves all deeper workflow semantics.

---
*End of document.*
