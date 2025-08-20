## HowTo: Extract & Use Upstream-Compatible InvokeAI Workflow Data Models

### Goal
Provide a robust, forward-tolerant set of Pydantic models mirroring InvokeAI's workflow JSON so local tooling can:
- Load workflows into structured objects instead of ad‑hoc dict traversal.
- Enumerate inputs/outputs reliably.
- Survive upstream additions (unknown fields preserved).
- Regenerate models easily when InvokeAI updates (copy schema-related sections, keep `extra='allow'`).

### Why
Partial mapping caused:
- Fragile key lookups (`node['data']['inputs'][field]` explosions).
- Inconsistent JSONPath assembly.
- Difficult upgrades when upstream shape changes.

A complete (best‑effort) model layer centralizes schema assumptions and degrades gracefully.

### Core Model Module
Implemented in: `src/invokeai_py_client/workflow/upstream_models.py`

Key classes (all `extra='allow'`):
- `WorkflowRoot` (name, description, `nodes`, `edges`, `form`).
- `WorkflowNode`, `WorkflowNodeData`, `WorkflowNodeField`.
- `WorkflowEdge`, `WorkflowEdgeEndpoint`.
- `WorkflowForm`, `WorkflowFormElement`, `WorkflowFormElementData`.

Utilities:
- `load_workflow_json(dict) -> WorkflowRoot`
- `iter_form_input_fields(root)` yields `(node_id, field_name, element_id, field_model)`
- `enumerate_output_nodes(root)` yields `(node_id, node_type, has_board_field_exposed)`
- `build_input_jsonpath(node_id, field)` replicates legacy JSONPath format.

### Usage Example
```python
import json
from pathlib import Path
from invokeai_py_client.workflow.upstream_models import (
    load_workflow_json, iter_form_input_fields, enumerate_output_nodes,
    build_input_jsonpath
)

wf_data = json.loads(Path('data/workflows/sdxl-flux-refine.json').read_text())
root = load_workflow_json(wf_data)

print(root.name, "nodes=", len(root.nodes))

print("Inputs:")
for node_id, field, elem_id, field_model in iter_form_input_fields(root):
    print(f"  {node_id}:{field} -> label={getattr(field_model, 'label', None)} path={build_input_jsonpath(node_id, field)}")

print("Output-capable nodes:")
for nid, ntype, exposed in enumerate_output_nodes(root):
    print(f"  {nid} ({ntype}) exposed_board={exposed}")
```

### Mapping to Existing Handle
Current `WorkflowHandle` computes input JSONPaths similarly. Migration path:
1. Replace internal parsing with `WorkflowRoot` ingestion.
2. Construct `IvkWorkflowInput` from iterator output.
3. Retire duplicate traversal logic.

### Forward Compatibility Strategy
| Concern | Mitigation |
|---------|------------|
| New fields added | `extra='allow'` keeps them in `.model_extra`. |
| Field removed | Access helpers reference optional attrs safely. |
| Structural shift (e.g., nodes array→map) | Accept both: model allows list of dicts; adapt normalizer later. |

### Regeneration Workflow (When Upstream Changes)
1. Pull latest InvokeAI version into `context/refcode/InvokeAI`.
2. Inspect workflow export JSON via GUI (sample save).
3. Update / add model attributes where high‑value (branch decisions, new metadata). Keep everything else permissive.
4. Run a fixture load test to ensure backward compatibility.

### Testing Suggestions
Create `tests/test_upstream_models_roundtrip.py`:
```python
from invokeai_py_client.workflow.upstream_models import load_workflow_json
import json, pathlib

def test_roundtrip():
    data = json.loads(pathlib.Path('data/workflows/sdxl-flux-refine.json').read_text())
    root = load_workflow_json(data)
    assert root.name
    # Ensure at least one form input discovered
    assert any(root.form.elements)
```

### Extending
Potential follow‑ups:
- Normalizer: unify `nodes` access (list vs dict) into property.
- Validator: ensure all edge endpoints reference known node ids.
- Derive dependency graph / topological order helper.
- Direct conversion to execution submission payload.

### References
- InvokeAI upstream repository: https://github.com/invoke-ai/InvokeAI
- Pydantic docs (model config & forward compatibility): https://docs.pydantic.dev/

### Summary
Adopting `upstream_models` enables a single source of truth for workflow structure while remaining flexible. This lowers maintenance friction, improves readability, and insulates the client against moderate upstream schema churn.
