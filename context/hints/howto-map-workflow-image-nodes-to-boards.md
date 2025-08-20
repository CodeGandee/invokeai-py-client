## How To: Derive Final Node → (Board, Image Filenames) Mapping After Workflow Completion

This revised guide focuses specifically on obtaining a reliable mapping from *original workflow output / image‑producing nodes* to their final **board IDs** and **persisted image filenames** using only the completed queue item (the JSON returned/polled from the InvokeAI queue API or captured from the UI). It supersedes earlier notes that only covered board extraction.

---
### 1. Core Data Structures in a Completed Queue Item

Inside a finished queue item JSON you'll commonly see (keys may differ slightly across versions):

```
session.graph.nodes                 # Original submission graph ("authoritative" node ids)
session.execution_graph.nodes       # Prepared / expanded runtime nodes ("prepared" ids)
session.results                     # Per executed (prepared) node result objects
session.prepared_source_mapping     # prepared_id -> original_id mapping
session.source_prepared_mapping     # original_id -> [prepared_id, ...] (sometimes present)
outputs (top-level)                 # Legacy explicit outputs array (may be empty)
```

Why each matters:
| Source | Purpose |
|--------|---------|
| `session.results` | Authoritative place to read final `image.image_name` produced by a prepared node. |
| `prepared_source_mapping` | Bridges dynamic prepared node identifiers back to original graph node ids you care about. |
| `execution_graph.nodes` | Fallback for inline `image.image_name` or `board` metadata if `results` absent. |
| `graph.nodes` | Original nodes; contains `board.board_id` assignments injected at submission time. |
| `outputs` (legacy) | Older API style: direct list of node outputs including images; use only as fallback. |

---
### 2. Image‑Producing Node Types

Common node types that either generate or finalize images:
`save_image`, `l2i`, `flux_vae_decode`, `flux_vae_encode`, `hed_edge_detection`, plus any custom nodes whose `results` payload embeds `image.image_name`.

Treat `save_image` as the canonical *terminal* producer when present; others may be intermediate but still have boards.

---
### 3. Priority (Evidence) Ladder

When assembling the mapping, walk evidence sources in this order (stop for a node once an image list is found):
1. **Results Layer** – For each prepared node in `session.results`, read `image.image_name` (if present) and map to original via `prepared_source_mapping`.
2. **Legacy Outputs Array** – Iterate `queue_item['outputs']` for image entries keyed by `node_id`.
3. **Graph/Execution Inline Images** – Traverse `session.execution_graph.nodes.*` (or even descendants) to locate embedded `image.image_name` objects linked to an original node through mappings.
4. **Structural Fallback (Traversal)** – If an original output node has no direct evidence, breadth‑first traverse forward edges starting at that node collecting any downstream `image.image_name` (heuristic; use only as last resort).

Board ID always comes first from the *original* node (`session.graph.nodes[original_id].board.board_id`); if missing, accept `none` (uncategorized). Avoid pulling board from prepared nodes unless the original lacks it (future compatibility).

---
### 4. Algorithm Summary

For each original output node identified by your workflow handle:
```
image_names = []
if results has any prepared node mapping back to original -> collect names
elif legacy outputs list has entries for original -> collect
elif inline / traversal shows image(s) reachable -> collect (heuristic)
board_id = original_node.board.board_id or 'none'
```

De‑duplicate filenames; preserve order of discovery (results order generally reflects generation sequence).

---
### 5. Reference Implementation (Pure JSON Processing)

```python
from __future__ import annotations
import json, collections
from pathlib import Path

API_CALL_PATH = Path("data/api-calls/call-wf-sdxl-flux-refine.json")
data = json.loads(API_CALL_PATH.read_text())

session = data.get('session', {})
graph = (session.get('graph') or {}).get('nodes', {}) or {}
exec_nodes = (session.get('execution_graph') or {}).get('nodes', {}) or {}
edges = (session.get('execution_graph') or {}).get('edges', []) or []
results = session.get('results', {}) or {}
prepared_to_original = session.get('prepared_source_mapping', {}) or {}

# Build forward adjacency for traversal fallback
forward = collections.defaultdict(list)
for e in edges:
    try:
        src = e.get('source', {}).get('node_id')
        dst = e.get('destination', {}).get('node_id')
        if src and dst:
            forward[src].append(dst)
    except Exception:
        pass

# 1. Collect images from results (prepared -> original)
images_by_original = collections.defaultdict(list)
for prepared_id, payload in results.items():
    orig = prepared_to_original.get(prepared_id, prepared_id)
    img_obj = (payload or {}).get('image') or {}
    name = img_obj.get('image_name')
    if name and name not in images_by_original[orig]:
        images_by_original[orig].append(name)

# 2. Legacy outputs array fallback
for out in data.get('outputs', []) or []:
    node_id = out.get('node_id') or out.get('id')
    img_obj = out.get('image') or {}
    name = img_obj.get('image_name')
    if node_id and name and name not in images_by_original[node_id]:
        images_by_original[node_id].append(name)

# 3. Descendant traversal (only if still empty for a candidate)
def traverse_images(start_id: str):
    seen, stack, found = set(), [start_id], []
    while stack:
        nid = stack.pop()
        if nid in seen: continue
        seen.add(nid)
        node_data = exec_nodes.get(nid) or {}
        img_obj = node_data.get('image') or {}
        name = img_obj.get('image_name')
        if name and name not in found:
            found.append(name)
        for nxt in forward.get(nid, []):
            if nxt not in seen:
                stack.append(nxt)
    return found

# Define which original nodes we consider output candidates (adjust filter as needed)
OUTPUT_TYPES = {'save_image'}
original_output_nodes = [nid for nid, n in graph.items() if (n.get('type') in OUTPUT_TYPES)]

final_rows = []
for nid in original_output_nodes:
    if not images_by_original.get(nid):
        traversal = traverse_images(nid)
        if traversal:
            images_by_original[nid].extend(traversal)
    board_id = (graph.get(nid, {}).get('board') or {}).get('board_id') or 'none'
    final_rows.append({
        'node_id': nid,
        'board_id': board_id,
        'images': images_by_original.get(nid, [])
    })

for r in final_rows:
    print(f"node {r['node_id']} -> board {r['board_id']} -> images: {', '.join(r['images']) or '(none)'}")
```

---
### 6. Handling Multiple Prepared Nodes per Original

Some originals (especially iterative or batched processors) may yield multiple prepared IDs. Consolidate by *original* and preserve unique filenames. Always map prepared → original first so you don't double‑count across branches.

---
### 7. Edge Cases & Pitfalls

| Situation | Symptom | Mitigation |
|-----------|---------|------------|
| `session.results` missing | No images collected in tier 1 | Rely on legacy outputs or traversal; log absence for diagnostics. |
| Output node lacks `board` | board_id unresolved | Use placeholder `'none'`; only downstream asset metadata lookup can refine. |
| Duplicate filenames | Repeated entries | De‑duplicate per original node. |
| Prepared mapping absent | prepared/source keys missing | Treat prepared ids as originals (identity mapping). |
| Traversal over-collection | Intermediate images falsely attributed | Only invoke traversal as last resort & optionally restrict depth. |

---
### 8. Validation Checklist

After a run, verify:
1. Every declared output node is present in the final mapping.
2. At least one evidence tier succeeded (record which for observability).
3. No duplicate image names per node.
4. Board IDs look plausible (UUIDs or 'none').
5. (Optional) Count of collected image files equals expected gallery additions.

---
### 9. Debug Tips

Print a tier provenance column (e.g., `source = results|outputs|traversal`) for each output node to quickly see why images may be missing. If all tiers fail, dump a slim summary of keys present under `session` to confirm server variant.

---
### 10. Provenance (Who Consumed an Output Image?)

Use execution graph edges where `source.field == 'image'` to map producer → consumer. This clarifies whether a saved image was terminal or fed refinement.

---
### 11. Minimal Table Format (Example)

```
+----+--------------------------------+--------------------------------------+---------------------------------------------+
| #  | Output Node (orig)             | Board ID                             | Image Filenames                             |
+----+--------------------------------+--------------------------------------+---------------------------------------------+
| 1  | 4414d4b5-82c3-4513-8c3f-...     | none                                 | 20e0fa8f-...png                              |
| 2  | 67e997b2-2d56-43f4-...         | a17c2b12-d25a-4e41-9217-d94a543b9e73 | e03e4e0d-...png                              |
| 3  | abc466fe-12eb-48a5-...         | a17c2b12-d25a-4e41-9217-d94a543b9e73 | 89ed9e5c-...png                              |
+----+--------------------------------+--------------------------------------+---------------------------------------------+
```

---
### 12. Quick Summary

1. Prefer `session.results` + `prepared_source_mapping` for image filenames.
2. Fall back to legacy `outputs` list.
3. Last resort: traversal/inline images in `execution_graph`.
4. Board always sourced from original submission node.
5. De‑duplicate & annotate evidence tier for observability.

---
### 13. References

- InvokeAI upstream: https://github.com/invoke-ai/InvokeAI
- `jsonpath-ng`: https://github.com/h2non/jsonpath-ng
- Project workflow runner example: see `tmp/task3_2_run_workflow_outputs.py` (multi‑tier implementation).

---
### 14. Next Enhancements (Optional)

| Enhancement | Benefit |
|-------------|---------|
| Board diff pre/post (query board endpoints) | Confirms uncategorized vs explicit routing | 
| WebSocket / event stream ingestion | Real‑time progressive mapping | 
| Add provenance depth limits | Prevent misattribution in dense graphs | 
| Structured test fixtures (golden queue JSON) | Regression safety for mapping logic | 
| Unified `get_outputs()` on workflow handle | Reuse logic across scripts | 

---
Use this pattern to produce a deterministic, debuggable mapping without relying on external timing heuristics or post‑hoc asset scans.
