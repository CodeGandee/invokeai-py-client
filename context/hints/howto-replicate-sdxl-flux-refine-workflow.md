# HowTo: Programmatically Replicate the SDXL → FLUX Refine Workflow (InvokeAI) and Fix 422 Errors

## Goal
Recreate (via Python client code) the same queue submission payload that the InvokeAI GUI produces for the `sdxl-flux-refine` workflow, ensuring successful batch submission (HTTP 200) instead of schema validation failures (HTTP 422).

---
## Key Findings (TL;DR)
1. **Do NOT prune edge‑connected input fields**: Required numeric/meta fields (width, height, seed, etc.) must remain inline on each node in the API graph even if also represented by edges.
2. **Board fields must be objects, not bare strings**: The server expects `{ "board_id": <value> }` (a BoardField shape), not raw strings like `"auto"` or `"none"`.
3. **Skip GUI‑only / non-executable nodes**: Nodes of type `notes` (and similar purely descriptive types) produce `union_tag_invalid` errors if sent.
4. **Inject / normalize board across image-producing nodes**: Ensure decode / save / metadata / gallery related nodes all carry a normalized board object.
5. **Rich error capture accelerates iteration**: Persist full 422 JSON detail + the graph you sent to disk for diffing against a canonical successful payload.
6. **Model binding must target correct node types**: Map each required model (SDXL base/refiner, FLUX, T5 encoder, CLIP, VAE, ControlNet) only to appropriate node IDs & field names.

---
## Canonical Artifacts
- Workflow template: `data/workflows/sdxl-flux-refine.json`
- Known-good (GUI) API call example: `data/api-calls/call-wf-sdxl-flux-refine.json`
Use these as ground truth when diffing your generated `batch_data` and `graph`.

---
## Step-by-Step Procedure
### 1. Load & Clone the Workflow
```python
from invokeai_py_client.workflow import WorkflowHandle
wf = WorkflowHandle.load_from_file("data/workflows/sdxl-flux-refine.json")
```
Keep the original intact; mutate a copy when injecting inputs.

### 2. Build a Node Input Lookup (By (node_id, field_name))
Avoid brittle positional indexing. Create a dict keyed by `(node_id, field)` to set prompt text, seeds, or model references predictably.
```python
# pseudo-structure
input_lookup = {(n['id'], f['name']): f for n in wf.nodes for f in n.get('inputs', [])}
input_lookup[(prompt_node_id, 'prompt')]['value'] = "A scenic valley at dawn"
```

### 3. Bind Models to Correct Nodes
Identify each model-bearing field (e.g., `clip`, `t5Encoder`, `vae`, `refiner_model`, `flux_model`). Ensure the repository lookup returns objects or identifiers in the format the server expects (consult your model repo abstraction). Bind only where the canonical payload shows a value.

### 4. Preserve Edge-Connected Fields
Earlier logic pruned fields that had incoming edges. This caused missing inline values required by schema validators. Disable pruning or guard it with an env flag.
```python
PRUNE = os.getenv("INVOKEAI_PRUNE_CONNECTED_FIELDS") == "1"
if not PRUNE:
    # skip removal of connected fields
    pass
```

### 5. Normalize Board Fields
Wrap raw string sentinel values into objects.
```python
def normalize_board(value):
    if isinstance(value, str):
        return {"board_id": value}
    return value

for node in api_graph['nodes']:
    if 'board' in node['data']:
        node['data']['board'] = normalize_board(node['data']['board'])
```
Apply a fallback board object to all relevant image / save / metadata nodes if missing.

### 6. Skip Non-Executable / Notes Nodes
Filter out nodes whose `type` is purely descriptive (e.g., `notes`).
```python
api_nodes = [n for n in raw_nodes if n.get('type') != 'notes']
```

### 7. Submit & Monitor; Capture Failures
Wrap submission; on non-200 persist details.
```python
resp = client.queue.submit_batch(batch_data)
if resp.status_code != 200:
    with open("tmp/last_failed_submission_detail.json", "w") as f:
        f.write(resp.text)
    raise RuntimeError(f"Submission failed: {resp.status_code}")
```

### 8. Diff Against Canonical Payload
Persist your generated graph (`tmp/last_flux_refine_submission_graph.json`) and compare structure, ensuring parity in:
- node count (after filtering notes)
- per-node `type`
- presence + shapes of `data` fields
- edge definitions (sources, targets, field names)

### 9. Iterate on Schema Errors
Common 422 patterns:
| Error Snippet | Cause | Fix |
|---------------|-------|-----|
| `union_tag_invalid`, tag: `notes` | Unsupported node type | Filter it out |
| `model_type`, expected object got string (`auto`) | Board field shape | Wrap string into object |
| Missing required field | Over-pruning | Retain edge-connected field |

### 10. Optional: Environment Flags
Provide toggles to aid debugging.
```powershell
$env:DEBUG_WORKFLOW=1
$env:INVOKEAI_PRUNE_CONNECTED_FIELDS=0  # ensure retention
```
Use flags to quickly switch behavior without code edits.

---
## Code Change Highlights (Minimal Diffs)
### `_convert_to_api_format` Adjustments (Conceptual)
```python
# ...existing code...
for node in workflow_nodes:
    if node.get('type') == 'notes':
        continue  # skip non-executable
    api_node = build_api_node(node)
    # Normalize board
    if 'board' in api_node['data']:
        api_node['data']['board'] = normalize_board(api_node['data']['board'])
    elif api_node['type'] in IMAGE_OUTPUT_NODE_TYPES:
        api_node['data']['board'] = {"board_id": default_board}
    api_nodes.append(api_node)

if not prune_connected_fields:
    # DO NOT strip fields that have incoming edges
    pass
# ...existing code...
```

### Error Persistence
```python
try:
    return self._client.queue.submit_sync(batch_data, board_id=board_id)
except HTTPError as e:
    detail = e.response.json() if e.response.headers.get('Content-Type','').startswith('application/json') else e.response.text
    with open("tmp/last_failed_submission_detail.json", "w") as f:
        json.dump(detail, f, indent=2)
    raise
```

---
## Troubleshooting Checklist
- 422 with board field: Confirm shape is `{ "board_id": "auto" }` not `"auto"`.
- Missing seeds or dimensions: Ensure they exist inline inside node `data` even if an upstream edge supplies values.
- Unexpected node count: Verify removal only of `notes` (or other documented non-runtime) nodes.
- Model resolution failure: Confirm repository returns a structure matching canonical payload (`{"model": {"id": ...}}` etc.).

---
## Edge Cases & Gotchas
| Scenario | Symptom | Resolution |
|----------|---------|-----------|
| Over-pruned fields | Server says required property missing | Retain inline value even with edge |
| Non-exposed meta fields set attempt | Warnings / ignored values | Inject directly into node data if schema allows; else omit |
| Wrong model bound to refine stage | Output artifact mismatch / error | Map by canonical node IDs, not positional order |
| Forget to filter notes | `union_tag_invalid` | Exclude before serialization |

---
## Reference Links
- InvokeAI GitHub: https://github.com/invoke-ai/InvokeAI
- (General) Workflows Overview (search in docs site): https://invoke-ai.github.io/ (navigate to Workflow / Queue API sections)

> NOTE: Exact endpoint & schema docs may evolve; always validate against the version running locally.

---
## Verification Strategy
1. Run the test harness after each change.
2. If failure: open `tmp/last_failed_submission_detail.json` + compare with canonical payload.
3. Once 200 OK: ensure output images & metadata match expectations (dimensions, denoise steps, etc.).

---
## Summary
Faithful replication hinges on **structural parity** with the GUI-produced graph: keep necessary inline data, present objects with correct shapes (especially `board`), and omit presentation-only nodes. Systematic diffing + persistent error artifacts eliminate guesswork and make convergence rapid.

---
*Last updated: 2025-08-19*
