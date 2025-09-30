# InvokeAI Upstream APIs — Mappings and Reference

Purpose
- Provide a concise map from the Python client’s high-level operations to InvokeAI’s REST endpoints.
- Highlight key endpoints and common request/response patterns used by this client.
- Link to raw REST examples and the OpenAPI reference for deeper detail.

Primary references
- Endpoint list summary: [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md)
- Full OpenAPI spec: [context/hints/invokeai-kb/invokeai-openapi-v6.3.json](context/hints/invokeai-kb/invokeai-openapi-v6.3.json)
- Raw REST examples:
  - Boards list/details/images: [examples/raw-apis/api-demo-boards.py](examples/raw-apis/api-demo-boards.py)
  - Latest image on a board (optimized): [examples/raw-apis/api-demo-latest-image.py](examples/raw-apis/api-demo-latest-image.py)
  - Upload image: [examples/raw-apis/api-demo-upload-image.py](examples/raw-apis/api-demo-upload-image.py)
  - Queue examples: [examples/raw-apis/api-demo-job-queue.py](examples/raw-apis/api-demo-job-queue.py)
  - Hybrid queue (DB + API): [examples/raw-apis/api-demo-job-queue-hybrid.py](examples/raw-apis/api-demo-job-queue-hybrid.py)
  - Fully worked job submitter: [examples/raw-apis/api-demo-job-submission.py](examples/raw-apis/api-demo-job-submission.py)

Client→API mappings (common flows)

1) Workflow submission and monitoring
- Client calls
  - Submit:
    - [Python.workflow_handle.submit_sync()](examples/pipelines/sdxl-text-to-image.py:309)
  - Wait/poll:
    - [Python.workflow_handle.wait_for_completion_sync()](examples/pipelines/sdxl-text-to-image.py:312)
  - Map outputs:
    - [Python.workflow_handle.map_outputs_to_images()](examples/pipelines/sdxl-text-to-image.py:328)
- Likely REST endpoints involved
  - Enqueue: /api/v1/queue/{queue_id}/enqueue_batch
  - Queue item retrieval & status:
    - /api/v1/queue/{queue_id}/i/{item_id}
    - /api/v1/queue/{queue_id}/status
    - /api/v1/queue/{queue_id}/b/{batch_id}/status
    - Listing:
      - /api/v1/queue/{queue_id}/list
      - /api/v1/queue/{queue_id}/list_all
  - See overview lines in the OpenAPI and endpoint list:
    - [Markdown.invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md:171)
- Raw example: end-to-end submit + monitor + download
  - Submit batch: [Python.InvokeAIJobSubmitter.submit_workflow_job()](examples/raw-apis/api-demo-job-submission.py:212)
  - Convert UI workflow to API graph payload: [Python.InvokeAIJobSubmitter.convert_workflow_to_api_format()](examples/raw-apis/api-demo-job-submission.py:149)
  - Get queue item details after submit: [Python.InvokeAIJobSubmitter.submit_workflow_job()](examples/raw-apis/api-demo-job-submission.py:249)
  - Monitor until terminal state: [Python.InvokeAIJobSubmitter.monitor_job_progress()](examples/raw-apis/api-demo-job-submission.py:349)

2) Boards and images
- Client calls
  - List boards:
    - [Python.client.board_repo.list_boards()](examples/pipelines/sdxl-text-to-image.py:173)
  - Get board handle and download image:
    - [Python.client.board_repo.get_board_handle()](examples/pipelines/sdxl-text-to-image.py:347)
    - [Python.BoardHandle.download_image()](examples/pipelines/sdxl-text-to-image.py:349)
  - Upload image (image-to-image assets):
    - [Python.BoardHandle.upload_image_data()](examples/pipelines/flux-image-to-image.py:220)
- REST endpoints
  - Boards:
    - GET /api/v1/boards/
    - GET /api/v1/boards/{board_id}
    - GET /api/v1/boards/{board_id}/image_names
  - Images:
    - GET /api/v1/images/names
    - POST /api/v1/images/images_by_names
    - GET /api/v1/images/i/{image_name}/metadata
    - GET /api/v1/images/i/{image_name}/full
    - POST /api/v1/images/upload
  - API list anchors:
    - [Markdown.invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md:117)
- Raw examples
  - Boards listing and details: [examples/raw-apis/api-demo-boards.py](examples/raw-apis/api-demo-boards.py)
  - Upload image and verify placement: [examples/raw-apis/api-demo-upload-image.py](examples/raw-apis/api-demo-upload-image.py)
  - Latest image via sorted names + DTOs: [examples/raw-apis/api-demo-latest-image.py](examples/raw-apis/api-demo-latest-image.py)
  - Starred images retrieval & download: [examples/raw-apis/api-demo-starred-images.py](examples/raw-apis/api-demo-starred-images.py)

3) Models (DNN)
- Client call (normalize workflow model identifiers to server-known records):
  - [Python.workflow_handle.sync_dnn_model()](examples/pipelines/sdxl-text-to-image.py:136)
- REST endpoints
  - GET /api/v2/models/
  - POST /api/v2/models/get_by_attrs
  - GET /api/v2/models/i/{key}
  - Model image, conversion, cache, and install endpoints as needed:
    - [Markdown.invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md:12)

4) App and configuration
- Basic health and version:
  - GET /api/v1/app/version (used in raw examples)
- Config, runtime config, invocation cache control:
  - /api/v1/app/config, /api/v1/app/runtime_config, /api/v1/app/invocation_cache/*
  - See:
    - [Markdown.invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md:151)

Payloads and patterns

A) Enqueue a workflow graph (batch)
- Typical client converts exported GUI JSON into an API graph with:
  - Nodes: dict of node_id → typed properties and input values
  - Edges: list of connections { source: {node_id, field}, destination: {node_id, field} }
- See conversion logic:
  - [Python.InvokeAIJobSubmitter.convert_workflow_to_api_format()](examples/raw-apis/api-demo-job-submission.py:149)
- Batch submit example (excerpt)
```python
# Build batch payload  [Python.InvokeAIJobSubmitter.submit_workflow_job()](examples/raw-apis/api-demo-job-submission.py:224)
batch_data = {
    "prepend": False,
    "batch": {
        "graph": api_graph,
        "runs": 1
    }
}
resp = session.post(f"{base_url}/api/v1/queue/default/enqueue_batch", json=batch_data)
```

B) Query queue items and monitor
- Latest completed job via list_all (then filter client-side):
  - [Python.get_latest_completed_job()](examples/raw-apis/api-demo-job-queue.py:27)
- Hybrid approach (DB + API) for speed:
  - [Python.get_latest_completed_job_hybrid()](examples/raw-apis/api-demo-job-queue-hybrid.py:100)

C) Boards and images
- Enumerate boards and get image names
```python
# List boards
resp = requests.get(f"{BASE_URL}/api/v1/boards/", params={"all": True})
boards = resp.json()

# List images in board
resp = requests.get(f"{BASE_URL}/api/v1/boards/{board_id}/image_names")
image_names = resp.json()
```
- Get latest image name using server-side sort (optimized)
  - [Python.get_latest_image_from_board()](examples/raw-apis/api-demo-latest-image.py:66)
- Download image
```python
img = requests.get(f"{BASE_URL}/api/v1/images/i/{image_name}/full").content
```
- Upload image via multipart form-data
  - [Python.upload_image_to_board()](examples/raw-apis/api-demo-upload-image.py:56)

D) Image DTOs and metadata
- Get DTOs for a set of names
```python
dto_resp = requests.post(f"{BASE_URL}/api/v1/images/images_by_names", json={"image_names": names})
dtos = dto_resp.json()
```
- Get metadata for a single image
```python
meta = requests.get(f"{BASE_URL}/api/v1/images/i/{image_name}/metadata").json()
```

Security, performance, and pagination notes
- Pagination and ordering
  - Some endpoints provide pagination or optimized ordering (e.g., /images/names with order_dir and limit).
  - The queue /list endpoint supports parameters; /list_all trades control for simplicity.
- Direct DB access (local deployments only)
  - The hybrid raw example demonstrates SQLite for ultra-fast reads; only applicable when the database is accessible:
    - [Python.get_latest_completed_job_direct()](examples/raw-apis/api-demo-job-queue-hybrid.py:41)
- Authentication
  - Typical local workflows run without auth; for secured deployments, configure headers/tokens in your requests session.
- Large payloads
  - Enqueue payloads can be sizable; keep runs and graph compact. Prefer server-side image references by name where possible.

How client abstractions align with REST
- The client preserves an immutable workflow JSON and performs value-only substitutions for indices discovered from the Form, then enqueues via the queue API.
- Mapping outputs relies on runtime session results that enumerate node-level outputs; the client correlates to inputs (especially board fields) for index-aware image mapping.
- Boards and images APIs are used for side tasks (enumeration, upload, download) and are surfaced via BoardRepo/BoardHandle.

Troubleshooting quick checks
- API reachability: [Python.test_api_connection()](examples/raw-apis/api-demo-boards.py:22)
- No outputs mapped:
  - Ensure your decode/save nodes expose their board field in the GUI Form; otherwise, mapping may return an empty list.
  - See enumeration: [Python.workflow_handle.list_outputs()](examples/pipelines/flux-image-to-image.py:285)
- Model not found at runtime:
  - Use model sync: [Python.workflow_handle.sync_dnn_model()](examples/pipelines/sdxl-text-to-image.py:136)

Pointers back to developer docs
- Client usage pattern: [context/summaries/developer/01-usage-pattern.md](context/summaries/developer/01-usage-pattern.md)
- Architecture and invariants: [context/summaries/developer/02-architecture.md](context/summaries/developer/02-architecture.md)
- Examples index and walkthroughs: [context/summaries/developer/04-examples-index.md](context/summaries/developer/04-examples-index.md)
