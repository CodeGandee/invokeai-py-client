## How to Get Workflow Output Images and Their Boards (InvokeAI)

This guide explains how to obtain the image names (filenames) produced by a workflow execution **and** the board each image was saved to, using only InvokeAI HTTP APIs (no GUI scraping). It covers what the queue item returns, why it may be missing direct image data, and the fallback queries required.

### 1. Understand What the Queue Item Does (and Does Not) Contain

After submitting a workflow via `/api/v1/queue/{queue_id}/enqueue_batch`, you poll `GET /api/v1/queue/{queue_id}/i/{item_id}` until `status == "completed"`.

Depending on the server version/build:
1. Older / alternative builds may embed an `outputs` array including `{ node_id, image: { image_name }, ... }` – you can directly map node → image names.
2. Newer (current reference code) queue items often **omit** explicit image output objects. Instead, only the execution graph metadata (`session.execution_graph.results`) lists node result types (`image_output`, `latents_output`, etc.) **without** the `image_name` values.

Therefore, a completed queue item alone may not yield image filenames.

### 2. Where the Image Filenames Actually Live

When a `save_image` (or similar output-capable node) runs, the backend stores the created image via the Images service. Each saved image is associated with:

* `image_name` (e.g. `e007a5d1-....png`)
* `board_id` (or uncategorized `none`)
* `session_id` (the workflow session that produced it)
* metadata (prompt, seed, etc.)

The queue item does **not** enumerate these; you must query image or board endpoints after completion.

### 3. Required API Endpoints

Referenced from the OpenAPI spec (`invokeai-openapi.json`) and source code (`invokeai/app/api/routers/*.py`).

| Purpose | Endpoint | Notes |
|---------|----------|-------|
| Get queue item (status) | `GET /api/v1/queue/{queue_id}/i/{item_id}` | Poll until `completed` |
| List images on a board | `GET /api/v1/boards/{board_id}/image_names` | Returns list of image names only |
| Get image DTO (board, metadata) | `GET /api/v1/images/i/{image_name}` | Returns `board_id`, `metadata`, `session_id` |
| (Optional) Filter images by board/category | same as above with query params | `board_id="none"` for uncategorized |

There is **no direct filter-by-session API**; you correlate via either:
* Known `board_id` assigned during submission (uniform board for all outputs), or
* Board contents before vs. after run (diff), or
* Later enhancement: custom naming/tagging (e.g., embed session_id into prompt metadata if supported).

### 4. Strategy to Map Output Nodes → (Board, Image Names)

1. Submit workflow. Record: `item_id`, `session_id`, list of output node IDs (`save_image` nodes) from the workflow definition.
2. Determine board assignment logic:
   * If you passed a single `board_id` to all output nodes (typical), you only need that board.
   * If each node has an explicit board field exposed, record each node's board.
3. After completion, for each distinct board in the output set:
   * Fetch existing image names BEFORE submission (optional optimization) – a pre-snapshot.
   * Fetch image names AFTER completion: `GET /api/v1/boards/{board_id}/image_names`.
   * Compute the set difference to isolate new images.
4. If multiple output nodes write to the **same** board, attribution of individual filenames to specific `save_image` nodes requires heuristics because the API does not return per-node ordering. Options:
   * If execution order is stable, query creation timestamps indirectly by calling `GET /api/v1/images/i/{image_name}` (DTO may include created metadata; inspect fields – extend client if needed).
   * Emit distinctive `metadata.prompt` prefixes per output node (different prompt strings) so you can query each new image DTO and match the prompt substring to the originating node.
5. Assemble mapping: `node_id -> board_id -> [image_names]`.

### 5. Practical Example (Python Pseudocode)

```python
import requests

BASE = "http://127.0.0.1:9090/api/v1"
queue_id = "default"
board_ids = {  # discovered from workflow graph
    "4414d4b5-...": "none",
    "67e997b2-...": "a17c2b12-...",
    "abc466fe-...": "a17c2b12-...",
}

def list_board(board_id):
    r = requests.get(f"{BASE}/boards/{board_id}/image_names")
    r.raise_for_status()
    return set(r.json())

# 1. Snapshot before
pre = {b: list_board(b) for b in set(board_ids.values())}

# 2. Submit workflow (not shown) → get item_id

# 3. Poll queue until completed
while True:
    qi = requests.get(f"{BASE}/queue/{queue_id}/i/{item_id}").json()
    if qi["status"] in {"completed", "failed", "canceled"}: break

assert qi["status"] == "completed"

# 4. Snapshot after
post = {b: list_board(b) for b in pre}

new_images_by_board = {b: sorted(post[b] - pre[b]) for b in pre}

# 5. Optional attribution by prompt metadata (distinct prompts) or assumption all new on board belong to nodes writing there
mapping = {}
for node_id, board_id in board_ids.items():
    mapping[node_id] = {
        "board": board_id,
        "image_names": new_images_by_board.get(board_id, [])
    }
```

### 6. Improving Attribution (Distinct Prompts)

Assign unique prompt prefixes per output node (e.g., `NODE_A::<random>`, `NODE_B::<random>`). After generation:

1. For each new image name on a board, `GET /api/v1/images/i/{image_name}`.
2. Examine metadata prompt: match prefix to node.
3. Place image into the specific node's list.

Snippet:

```python
def get_image_dto(image_name):
    r = requests.get(f"{BASE}/images/i/{image_name}")
    r.raise_for_status()
    return r.json()

for board_id, images in new_images_by_board.items():
    for image_name in images:
        dto = get_image_dto(image_name)
        prompt = (dto.get("metadata") or {}).get("prompt", "")
        for node_id, b in board_ids.items():
            if b == board_id and node_prompts_prefix[node_id] in prompt:
                mapping[node_id]["image_names"].append(image_name)
                break
```

### 7. Why Not Use Timestamps Alone?

Timestamps can collide or be reordered by async processing. Relying on prompt metadata or explicit per-node boards is more robust and reproducible.

### 8. Socket.IO Events (Optional Real-Time Path)

The server emits events (`invocation_complete`) via Socket.IO (`/ws` origin). Each event payload can include the `result` structure for the node. Some builds include inline `image.image_name` for `save_image` invocation results. To use:

1. Connect with python-socketio client.
2. Subscribe to queue room (`subscribe_queue`, queue_id).
3. Record each `invocation_complete` event for nodes of type `save_image` or those producing `image_output`.
4. Extract `image.image_name` if present; fallback to board diff method if absent.

### 9. Summary Decision Tree

```
Queue item has outputs with image names? -> Use directly.
Else Socket.IO events include image names? -> Capture during run.
Else Use board diff (pre/post) + optional prompt prefixes for attribution.
```

### 10. Key Source Code References

* Queue item polling: `invokeai/app/api/routers/session_queue.py`
* Board images listing: `invokeai/app/api/routers/boards.py` (`/{board_id}/image_names`)
* Image DTO retrieval: `invokeai/app/api/routers/images.py` (`/i/{image_name}`)
* Socket events wiring: `invokeai/app/api/sockets.py`

### 11. Recommendations for Client Library Enhancement

Add a `resolve_output_images()` helper that:
1. Accepts `WorkflowHandle` + mapping of output nodes → boards.
2. Snapshots board contents pre-submission.
3. Submits workflow (or accepts completed queue item).
4. Snapshots board contents post-completion.
5. Optionally refines attribution via prompt metadata.

Return structure:
```json
{
  "nodes": {
    "<node_id>": { "board": "<board_id>", "image_names": ["...png"] }
  },
  "new_images": ["..."],
  "boards": { "<board_id>": { "added": ["..."], "count_before": 10, "count_after": 13 } }
}
```

### 12. Caveats

* If another concurrent workflow writes to the same board between snapshots, diff attribution becomes ambiguous – mitigate by creating a temporary per-run board.
* Deleted or re-categorized images between snapshots may distort diffs; perform snapshots back-to-back relative to submission and completion polling.
* If generation fails mid-run, partial images may appear; handle by recording queue status.

### 13. Minimal cURL Examples

```bash
# Poll queue item
curl -s http://127.0.0.1:9090/api/v1/queue/default/i/158 | jq '.status'

# List image names on a board
dcurl -s http://127.0.0.1:9090/api/v1/boards/a17c2b12-d25a-4e41-9217-d94a543b9e73/image_names | jq '.'

# Get image DTO (board, metadata, session)
curl -s http://127.0.0.1:9090/api/v1/images/i/e007a5d1-bdc1-41ae-95a8-bf1ae9a215fc.png | jq '{image_name, board_id, session_id}'
```

---
**In short:** The definitive post-run source of (board, image_name) is the Images/Boards API, not the queue item. Use board snapshots (and optionally prompt tagging) to reconstruct the mapping of output nodes to their generated images in a version-agnostic way.
