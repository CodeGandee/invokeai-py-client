# InvokeAI Python Client — Roadmap

Status: living document summarizing what exists and what’s next for this repo.

## Table of Contents

- Current Implementation
- Known Stubs / Gaps
- Next Milestones
- Stretch / Later
- Compatibility & Notes
- Changelog Intent

## Current Implementation

Highlights of what is implemented and tested.
### Client Core

- **`src/invokeai_py_client/client.py`**: HTTP session, retries, auth, URL parsing (`from_url()`), Socket.IO connect helpers (`connect_socketio()`), health check. Repositories are exposed as properties: `board_repo`, `workflow_repo`, `dnn_model_repo`.

### Boards (Repository Pattern)

- **Models**: `src/invokeai_py_client/board/board_model.py` (Board, uncategorized sentinel helpers)
- **Repository**: `src/invokeai_py_client/board/board_repo.py` (list/get/create/delete/update boards; resolve uncategorized; image lookup; move image to board by name; cache)
- **Handle**: `src/invokeai_py_client/board/board_handle.py` (list/upload/download/star/unstar/delete/move images; uses modern `board_images` APIs with legacy fallbacks; robust uncategorized handling; multipart upload with auth passthrough)

### Workflows

- **Definition**: `src/invokeai_py_client/workflow/workflow_model.py` (permissive Pydantic model; version/meta helpers)
- **Repository**: `src/invokeai_py_client/workflow/workflow_repo.py` (create from file/dict with validation scaffold; list server workflows)
- **Handle**: `src/invokeai_py_client/workflow/workflow_handle.py` (form-driven typed inputs, submission to queue, sync wait via polling, async monitoring via Socket.IO subscribe_queue, cancel; output mapping using `session.results` + prepared id mapping with legacy/traversal fallbacks; DNN model sync against installed models; utilities to enumerate output nodes and JSONPath templates)

### Upstream-Compatible Models

- **`src/invokeai_py_client/workflow/upstream_models.py`**: Typed-but-forgiving graph/form models; helpers to enumerate output-capable nodes and update board fields

### Field System (strongly-typed, default-constructable)

- **Base/mixins**: `src/invokeai_py_client/ivk_fields/base.py` (default-constructable contract, JSON helpers, image/collection mixins)
- **Primitives**: `ivk_fields/primitives.py` (String/Integer/Float/Boolean with constraints + to/from API format)
- **Resources**: `ivk_fields/resources.py` (Image/Board/Latents/Tensor/DenoiseMask/Metadata; image upload/download currently placeholders in field mixin, upload handled via BoardHandle)
- **Models**: `ivk_fields/models.py` (ModelIdentifier, UNet, CLIP, Transformer, LoRA + aliases for SDXL/Flux/T5/CLIPEmbed/VAE)
- **Conditioning**: `ivk_fields/conditioning.py` (SD, FLUX variants, SD3, CogView4)
- **Enums & choices**: `ivk_fields/enums.py` (Scheduler with alias normalization, Interpolation, ColorMode, Literals)

### Field Plugins (open/closed detection + builders via pluggy)

- **`src/invokeai_py_client/workflow/field_plugins.py`**: Prioritized detection rules (explicit type, name patterns, node primitives, value-based, enum presence, numeric constraints) and builders (string, integer, float, boolean, model, board, image, enum). Public helpers `detect_field_type()` and `build_field()`

### DNN Models (read-only discovery)

- **`src/invokeai_py_client/dnn_model/dnn_model_repo.py`**: Stateless repository for v2 model list/detail (no caching). Model entity + enums in `dnn_model_types.py`

### Queues and Jobs (Repository/Handle pattern)

- **Models**: `src/invokeai_py_client/queue/queue_models.py` (QueueAndProcessorStatus, QueueStatus, ProcessorStatus, QueueItem, action result models) — strongly typed with `extra` for forward compatibility
- **Repository**: `src/invokeai_py_client/queue/queue_repo.py` (discover queues via `list_queues()` → `['default']`, construct `QueueHandle`)
- **QueueHandle**: `src/invokeai_py_client/queue/queue_handle.py` (status, is_busy, running count; list_all/running/pending; get_current/get_item/get_items_by_ids; cancel_all_except_current/clear/prune; wait_until_idle)
- **JobHandle**: `src/invokeai_py_client/queue/job_handle.py` (refresh, status helpers, cancel with PUT→DELETE fallback, wait_for_completion)
- **Client wiring**: `client.queue_repo` property for access
- **Tests**: integration tests in `unittests/queue/test_queue_integration.py` (require `INVOKE_AI_ENDPOINT`), plus SDXL/FLUX flow tests relocated under `unittests/`

### Quick API

- **`src/invokeai_py_client/quick/quick_client.py`**: Convenience flows built atop repos/workflows. Includes server-side copy via tiny workflow and an SDXL txt2img helper. Prebuilt workflows in `src/invokeai_py_client/quick/prebuilt-workflows/`

## Known Stubs / Gaps

- Image field operations: `IvkImageField.upload()` / `download()` are placeholders (uploads handled by `BoardHandle`)
- Exceptions: `src/invokeai_py_client/exceptions.py` scaffolds not implemented yet
- Model management (write operations): Install/convert/delete/prune/scan/cache/HF login not yet exposed; `DnnModelRepository` is intentionally read-only

## Next Milestones

### 1. Model Management API (v2 model_manager endpoints)

Goals
- Support install (add), delete (remove), convert, scan, prune/cancel install jobs, cache management, HF login where relevant
- Preserve current read-only discovery in `DnnModelRepository`; introduce a write-capable manager to keep concerns clear

Endpoints (OpenAPI v6.8 tag: model_manager)
- List/detail: `GET /api/v2/models/`, `GET /api/v2/models/i/{key}`
- Install: `POST /api/v2/models/install` (string source + optional config + access_token)
- Install job: `GET /api/v2/models/install/{id}`, `DELETE /api/v2/models/install/{id}`, `DELETE /api/v2/models/install` (prune)
- Convert: `PUT /api/v2/models/convert/{key}`
- Delete model: `DELETE /api/v2/models/i/{key}`
- Scan folder: `GET /api/v2/models/scan_folder` (trigger)
- HF helpers: `GET/POST/DELETE /api/v2/models/hf_login`
- Cache: `POST /api/v2/models/empty_model_cache`, `GET /api/v2/models/stats`

Proposed Structure
- New repository: `ModelManagerRepository` (write operations), complementing read-only `DnnModelRepository`
- `ModelManagerRepository` API (initial):

```python
install_model(source: str, config: dict | None = None, access_token: str | None = None) -> dict
get_install_job(id: str) -> dict | None
cancel_install_job(id: str) -> bool
prune_install_jobs() -> bool
convert_model(key: str) -> dict
delete_model(key: str) -> bool
scan_folder() -> dict
empty_model_cache() -> bool
get_stats() -> dict | None
hf_login(token: str) -> bool
hf_logout() -> bool
hf_status() -> dict
```

Acceptance Criteria
- Unit/integration tests covering happy-path flows against a running server
- Example snippets for installing by HF repo id, monitoring an install job, and deleting a model

### 2. Model Management API (v2 model_manager endpoints)
#### Goals

- Support install (add), delete (remove), convert, scan, prune/cancel install jobs, cache management, HF login where relevant
- Preserve current read-only discovery in `DnnModelRepository`; introduce a write-capable manager to keep concerns clear
#### Endpoints (OpenAPI v6.8 tag: model_manager)

- **List/detail**: `GET /api/v2/models/`, `GET /api/v2/models/i/{key}`
- **Install**: `POST /api/v2/models/install` (string source + optional config + access_token)
- **Install job**: `GET /api/v2/models/install/{id}`, `DELETE /api/v2/models/install/{id}`, `DELETE /api/v2/models/install` (prune)
- **Convert**: `PUT /api/v2/models/convert/{key}`
- **Delete model**: `DELETE /api/v2/models/i/{key}`
- **Scan folder**: `GET /api/v2/models/scan_folder` (trigger)
- **HF helpers**: `GET/POST/DELETE /api/v2/models/hf_login`
- **Cache**: `POST /api/v2/models/empty_model_cache`, `GET /api/v2/models/stats`
#### Proposed Structure

- **New repository**: `ModelManagerRepository` (write operations), complementing read-only `DnnModelRepository`
- **`ModelManagerRepository` API (initial)**:

```python
install_model(source: str, config: dict | None = None, access_token: str | None = None) -> dict
get_install_job(id: str) -> dict | None
cancel_install_job(id: str) -> bool
prune_install_jobs() -> bool
convert_model(key: str) -> dict
delete_model(key: str) -> bool
scan_folder() -> dict
empty_model_cache() -> bool
get_stats() -> dict | None
hf_login(token: str) -> bool
hf_logout() -> bool
hf_status() -> dict
```
#### Acceptance Criteria

- Unit tests exercising happy-path responses; verify failures surface structured `APIError` once exceptions are implemented
- Example notebook/snippet in `examples/` for installing a model by HF repo id, monitoring install job, and deleting a model

## Stretch / Later

- **Videos API (v6.8)**: Add list/detail/star/delete and board_videos helpers mirroring images/boards
- **Exceptions**: Implement the exception hierarchy and switch repository/handle code to raise those instead of generic errors
- **IvkImageField.upload/download**: Wire through `BoardRepository`/`BoardHandle`, keeping field mixin behavior consistent

## Compatibility & Notes

- Python version: Targets Python 3.11+. Follows Ruff and type hints for public APIs
- OpenAPI: Uses InvokeAI OpenAPI v6.8 (`context/hints/invokeai-kb/invokeai-openapi-v6.8.json`). Tests expect `INVOKE_AI_ENDPOINT` to be set in the environment
- Test layout: `unittests/` is the actively maintained suite used in CI; `tests/` contains demos and may include outdated examples
- API versioning: v1 vs v2 base paths: current client base is `/api/v1`; v2 calls use `../v2/...`. A small internal helper may be introduced to build v2 URLs robustly

## Changelog Intent

- Each milestone should land with docs updates (`docs/`), examples, and tests
- CI must pass `pixi run quality` locally before PR
