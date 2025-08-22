# Examples Index and Walkthroughs

Purpose
- Provide an orientation to the example scripts and what each demonstrates.
- Help contributors quickly locate a reference pattern aligned with their task.
- Cross-link to usage and architecture docs for deeper context.

Structure
- Pipelines: higher-level client API usage on GUI-exported workflows
- Raw APIs: direct REST recipes without client abstractions
- How to run
- Common pitfalls and best practices

How to run examples
- Ensure InvokeAI server is running locally (default http://127.0.0.1:9090)
- From repo root, examples can be run with pixi or plain Python:
  - pixi: see project scripts or run directly with environment activated
  - Example commands shown inline

Pipelines (client-centric)

1) SDXL Text-to-Image
- File: [examples/pipelines/sdxl-text-to-image.py](examples/pipelines/sdxl-text-to-image.py)
- Demonstrates:
  - Client creation and workflow load:
    - [Python.InvokeAIClient.from_url()](examples/pipelines/sdxl-text-to-image.py:129)
    - [Python.WorkflowDefinition.from_file()](examples/pipelines/sdxl-text-to-image.py:132)
    - [Python.client.workflow_repo.create_workflow()](examples/pipelines/sdxl-text-to-image.py:133)
  - Model identifier synchronization:
    - [Python.workflow_handle.sync_dnn_model()](examples/pipelines/sdxl-text-to-image.py:136)
  - Input discovery and index-centric assignment:
    - [Python.workflow_handle.list_inputs()](examples/pipelines/sdxl-text-to-image.py:143)
    - [Python.workflow_handle.get_input_value()](examples/pipelines/sdxl-text-to-image.py:224)
  - Board selection via input field (dynamic detection if present):
    - [Python.next(...)](examples/pipelines/sdxl-text-to-image.py:163)
  - Submit, wait, and output mapping:
    - [Python.workflow_handle.submit_sync()](examples/pipelines/sdxl-text-to-image.py:309)
    - [Python.workflow_handle.wait_for_completion_sync()](examples/pipelines/sdxl-text-to-image.py:312)
    - [Python.workflow_handle.map_outputs_to_images()](examples/pipelines/sdxl-text-to-image.py:328)
  - Download first image via board handle:
    - [Python.client.board_repo.get_board_handle()](examples/pipelines/sdxl-text-to-image.py:347)
    - [Python.BoardHandle.download_image()](examples/pipelines/sdxl-text-to-image.py:349)
- Run:
  - pixi run -e dev python examples/pipelines/sdxl-text-to-image.py

2) FLUX Image-to-Image
- File: [examples/pipelines/flux-image-to-image.py](examples/pipelines/flux-image-to-image.py)
- Demonstrates:
  - Uploading a source image to a target board before submission:
    - [Python.client.board_repo.list_boards()](examples/pipelines/flux-image-to-image.py:184)
    - [Python.client.board_repo.get_board_handle()](examples/pipelines/flux-image-to-image.py:219)
    - [Python.BoardHandle.upload_image_data()](examples/pipelines/flux-image-to-image.py:220)
  - Explicit indices for image field, prompts, steps, denoise start, and board:
    - [Python.workflow_handle.get_input_value()](examples/pipelines/flux-image-to-image.py:317)
  - Submit, wait, map, and optional image saving:
    - [Python.workflow_handle.submit_sync()](examples/pipelines/flux-image-to-image.py:394)
    - [Python.workflow_handle.wait_for_completion_sync()](examples/pipelines/flux-image-to-image.py:400)
    - [Python.workflow_handle.map_outputs_to_images()](examples/pipelines/flux-image-to-image.py:421)
- Run:
  - pixi run -e dev python examples/pipelines/flux-image-to-image.py

3) SDXL → FLUX Refine (Multi-stage)
- File: [examples/pipelines/sdxl-flux-refine.py](examples/pipelines/sdxl-flux-refine.py)
- Demonstrates:
  - Multi-stage pipeline with multiple board inputs and extended sampler configuration
  - Full input enumeration and outputs enumeration tables:
    - [Python.workflow_handle.list_inputs()](examples/pipelines/sdxl-flux-refine.py:128)
    - [Python.workflow_handle.list_outputs()](examples/pipelines/sdxl-flux-refine.py:141)
  - Apply board selection consistently across stages:
    - [Python.workflow_handle.get_input_value()](examples/pipelines/sdxl-flux-refine.py:281)
  - Submit, wait, map, and consolidated in-memory image collection
    - [Python.workflow_handle.submit_sync()](examples/pipelines/sdxl-flux-refine.py:326)
    - [Python.workflow_handle.wait_for_completion_sync()](examples/pipelines/sdxl-flux-refine.py:330)
    - [Python.workflow_handle.map_outputs_to_images()](examples/pipelines/sdxl-flux-refine.py:346)
- Run:
  - pixi run -e dev python examples/pipelines/sdxl-flux-refine.py

Raw APIs (direct REST)

1) Boards and Images Overview
- File: [examples/raw-apis/api-demo-boards.py](examples/raw-apis/api-demo-boards.py)
- Endpoints used:
  - GET /api/v1/boards/
  - GET /api/v1/boards/{board_id}
  - GET /api/v1/boards/{board_id}/image_names
  - GET /api/v1/boards/none/image_names
- Usage reference:
  - [Python.test_api_connection()](examples/raw-apis/api-demo-boards.py:22)
  - [Python.get_all_boards()](examples/raw-apis/api-demo-boards.py:37)

2) Upload Image as Asset
- File: [examples/raw-apis/api-demo-upload-image.py](examples/raw-apis/api-demo-upload-image.py)
- Endpoint:
  - POST /api/v1/images/upload (multipart/form-data)
- Flow:
  - Resolve or create target board, then upload file
  - Verify by listing board images

3) Queue — Latest Finished Job
- File: [examples/raw-apis/api-demo-job-queue.py](examples/raw-apis/api-demo-job-queue.py)
- Endpoints:
  - GET /api/v1/queue/{queue_id}/list_all
  - GET /api/v1/queue/{queue_id}/list?status=completed
- Extract image names from queue session results:
  - [Python.extract_generated_image()](examples/raw-apis/api-demo-job-queue.py:83)

4) Queue — Hybrid DB + API
- File: [examples/raw-apis/api-demo-job-queue-hybrid.py](examples/raw-apis/api-demo-job-queue-hybrid.py)
- Adds direct SQLite lookup of latest completed item for speed with fallback to API

5) Latest Image from Board (Optimized)
- File: [examples/raw-apis/api-demo-latest-image.py](examples/raw-apis/api-demo-latest-image.py)
- Endpoints:
  - GET /api/v1/images/names?board_id=&order_dir=DESC&limit=1
  - POST /api/v1/images/images_by_names
  - GET /api/v1/images/i/{image_name}/full
- Pattern:
  - Use server-side ordering to avoid large list pagination client-side

6) Starred Images
- File: [examples/raw-apis/api-demo-starred-images.py](examples/raw-apis/api-demo-starred-images.py)
- Endpoints:
  - GET /api/v1/boards/{board_id}/image_names
  - POST /api/v1/images/images_by_names
  - GET /api/v1/images/i/{image_name}/metadata
- Pattern:
  - Filter DTOs by starred flag and optionally download

Choosing an example for your task
- I want a minimal end-to-end text-to-image with mapped outputs:
  - Use SDXL Text-to-Image
- I want an image-to-image pipeline with an uploaded seed image:
  - Use FLUX Image-to-Image
- I want a multi-stage workflow demonstrating multiple boards and index discipline:
  - Use SDXL → FLUX Refine
- I need to script raw HTTP calls (e.g., for ops or dashboards):
  - Use Raw APIs (Boards, Queue, Latest, Upload, Starred)

Common pitfalls and notes
- Form discipline: Only fields exposed in the GUI Form are discoverable inputs. If something is missing, add it to the Form and re-export.
- Index drift: If you modify the Form (add/remove/reorder fields or containers), re-run input enumeration and update IDX_* constants.
- Board names vs IDs: GUI board names are not globally unique; API board_id is authoritative. Examples use a “first match wins” strategy for convenience.
- Outputs not mapped: Ensure the output-capable node’s board field is exposed in the Form; otherwise mapping may return zero items.

Pointers back to docs
- Usage pattern (step-by-step): [context/summaries/developer/01-usage-pattern.md](context/summaries/developer/01-usage-pattern.md)
- Architecture and invariants: [context/summaries/developer/02-architecture.md](context/summaries/developer/02-architecture.md)
- Upstream API mappings: [context/summaries/developer/03-upstream-apis.md](context/summaries/developer/03-upstream-apis.md)
- Project overview: [context/summaries/developer/00-overview.md](context/summaries/developer/00-overview.md)