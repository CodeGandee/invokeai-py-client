**Title**
QueueRepository + QueueHandle + JobHandle: Queue/Job API (v6.8)

**Objectives**
- Centralize queue/job operations behind `QueueRepository`.
- Represent a queue instance with `QueueHandle` (queue‑scoped queries and actions).
- Represent a single job with `JobHandle` (single‑job queries and actions).
- Follow repository/handle patterns used for boards/workflows.
- Prefer v6.8 endpoints; map API statuses to our enums.

**Deliverables**
- New package: `src/invokeai_py_client/queue/`
  - `queue_repo.py` with `QueueRepository`
  - `queue_handle.py` with `QueueHandle`
  - `job_handle.py` with `JobHandle`
  - `__init__.py` exporting `QueueRepository`, `QueueHandle`, `JobHandle`
- `InvokeAIClient.queue_repo` property that lazily instantiates `QueueRepository`.
- Deprecate or delegate `InvokeAIClient.list_job*` stubs to `queue_repo`.
- Tests (pytest) for status queries, listings, and cancel paths (mark `integration` where hitting a live server).
- Docs: short usage snippet and API listing under docs and/or examples.

**API Endpoints (v6.8)**
- Status
  - GET `/api/v1/queue/{queue_id}/status` → queue counts and processor state.
  - GET `/api/v1/queue/{queue_id}/current` → current in‑processing item (if any).
- Listings
  - GET `/api/v1/queue/{queue_id}/list_all`[?destination] → all items (filter client-side by status).
  - GET `/api/v1/queue/{queue_id}/item_ids` → all item IDs (for bulk fetch flow).
  - POST `/api/v1/queue/{queue_id}/items_by_ids` → details for specified IDs.
  - GET `/api/v1/queue/{queue_id}/i/{item_id}` → single item by ID.
- Actions
  - PUT `/api/v1/queue/{queue_id}/i/{item_id}/cancel` → cancel one item.
  - PUT `/api/v1/queue/{queue_id}/cancel_all_except_current`
  - PUT `/api/v1/queue/{queue_id}/clear`
  - PUT `/api/v1/queue/{queue_id}/prune`
  - Optional controls: pause/resume processor, cancel_by_batch_ids, cancel_by_destination, retry_items_by_id.

**Design**
- Repository/Handle split (mirrors boards):
  - `QueueRepository` provides global queue discovery and queue‑scoped operations (by queue_id), constructs `QueueHandle` and `JobHandle`.
  - `QueueHandle` encapsulates a single queue (`queue_id`) and exposes queue‑level queries/actions; constructs `JobHandle` for items in the queue.
  - `JobHandle` encapsulates a single queue item (`queue_id`, `item_id`, cached payload) and exposes single‑item actions.
- Strong typing with Pydantic models (no raw dicts in public API):
  - Define explicit Pydantic models for all relevant queue payloads.
  - Provide an `extra: dict[str, Any] = {}` field on each model to capture unknown/new keys for forward compatibility. We'll parse responses so that unknown keys are stored in `extra` while known keys populate typed fields.
- Defaults and mapping:
  - Default `queue_id="default"` everywhere; allow override.
  - Map API queue item statuses to our `JobStatus` enum within helpers:
    - `pending → PENDING`, `in_progress → RUNNING`, `completed → COMPLETED`, `failed → FAILED`, `canceled → CANCELLED`.

**Public API (sync)**
- QueueRepository (no duplication of handle responsibilities)
  - Queues
    - `list_queues() -> list[str]`: returns available queue names. Note: v6.8 OpenAPI does not expose a queues listing endpoint; implement with a conservative fallback of `["default"]` and optionally infer configured queues when/if an upstream endpoint or runtime config exposes them.
    - `get_queue(queue_id: str = "default") -> QueueHandle`.

- QueueHandle
  - Properties
    - `queue_id: str`.
  - Status
    - `get_status() -> QueueAndProcessorStatus`.
    - `is_busy() -> bool`.
    - `count_running() -> int`.
  - Listings
    - `list_all(destination: str | None = None) -> list[QueueItem]`.
    - `list_running() -> list[QueueItem]`.
    - `list_pending() -> list[QueueItem]`.
    - `get_current() -> JobHandle | None`.
    - `get_item(item_id: int) -> JobHandle | None`.
    - `get_items_by_ids(item_ids: list[int]) -> list[JobHandle]`.
  - Actions (queue‑wide)
    - `cancel_all_except_current() -> CancelAllExceptCurrentResult`.
    - `clear() -> ClearResult`.
    - `prune() -> PruneResult`.

- JobHandle
  - Properties
    - `queue_id: str`, `item_id: int`.
    - `item: QueueItem | None` (last fetched item payload).
  - Queries
    - `refresh() -> QueueItem`: GET `/i/{item_id}` and cache into `item`.
    - `status() -> JobStatus`: from `item.status` (map API → client enum).
    - `is_pending()/is_running()/is_complete()/is_successful()/is_failed()/is_cancelled()`.
    - Accessors: `batch_id()`, `session_id()`, `created_at()`, `started_at()`, `completed_at()` (from `data`).
  - Actions
    - `cancel() -> bool`: PUT `/i/{item_id}/cancel` with DELETE fallback on 405/404 mismatch.
    - `retry() -> bool`: via repo endpoint `retry_items_by_id` (handle delegates to repo helper).
  - Utilities
    - `wait_for_completion(timeout: float = 300.0, poll: float = 1.0) -> dict`: poll `/i/{item_id}` until terminal.

**Integration Points**
- Add property to client
  - `src/invokeai_py_client/client.py`: add `self._queue_repo: QueueRepository | None = None` and `@property queue_repo` returning an instance.
  - Update docstrings and README usage examples to prefer `client.queue_repo`.
- Delegate deprecated stubs
  - `client.list_jobs()`, `client.get_job()`, `client.cancel_job()` either:
    - raise `NotImplementedError` with guidance to use `client.queue_repo`, or
    - thinly delegate to `QueueRepository` equivalents (preferred for compatibility).

**Error Handling**
- Raise `requests.HTTPError` for non-404 failures (consistent with existing repos).
- Return `None` on 404 for getters like `get_item()`.
- Later: adopt typed exceptions once `exceptions.py` is implemented (tracked separately).

**Testing (integration-only, no mocks)**
- Preconditions
  - A running InvokeAI server; endpoint is provided via environment variable `INVOKE_AI_ENDPOINT` (no fallback).
  - Tests will error or skip with a clear message if `INVOKE_AI_ENDPOINT` is not set (e.g., `export INVOKE_AI_ENDPOINT=http://localhost:19090`).
  - SDXL base model installed and the example workflow available: `examples/pipelines/sdxl-text-to-image.json`.
- Mark tests with `@pytest.mark.integration` (and `@pytest.mark.slow` where they wait on queues).
- Scenarios
  - `test_list_queues_integration`: `client.queue_repo.list_queues()` returns `["default"]`.
  - `test_queue_status_and_current_integration`:
    - Capture baseline status from `QueueHandle("default").get_status()`.
    - Create a workflow using the SDXL text-to-image definition, set prompts, and submit (non-blocking where possible) to observe `is_busy()` flip to True.
    - Poll `get_current()` until non-None, then until it changes to None or item completes.
  - `test_list_running_and_job_handles_integration`:
    - While a job is in progress, call `QueueHandle.list_running()` and wrap into `JobHandle`s.
    - Call `refresh()` on a handle and assert `status() is RUNNING`.
  - `test_job_cancel_integration`:
    - Submit a longer job (increase steps) to ensure it runs long enough.
    - Obtain its `JobHandle` via `get_current()` or `get_item(item_id)`.
    - Call `cancel()` and assert final status becomes `CANCELLED`.
  - `test_prune_and_clear_integration`:
    - After completions/cancellations, call `QueueHandle.prune()` and/or `clear()` and assert returned counts.
  - Note: Use short polling intervals with timeouts to avoid flakes; accept that very fast completions may skip transient `in_progress` assertions—use eventual conditions.

**Docs & Examples**
- Add a short usage example in `docs/` and `examples/`:
  - Create client, call `client.job_repo.get_status()`/`is_busy()`.
  - List running items, cancel current item.
- Update `ROADMAP.md` to mark JobRepository milestone when done.

**Implementation Steps**
1) Scaffold `src/invokeai_py_client/queue/{__init__.py,queue_repo.py,queue_handle.py,job_handle.py}`.
2) Wire `client.queue_repo` property and private cache.
3) Implement `JobHandle` (refresh, status mapping, cancel, wait).
4) Implement `QueueHandle` (status/listing/actions, item handle constructors).
5) Implement `QueueRepository` (list_queues discovery, queue/item helpers, actions).
6) Add unit tests for repo/handle wiring and parsing.
7) Add docs/example snippet.
8) Optional: delegate or deprecate client job stubs.

**Notes / Open Questions**
- Verb for cancel endpoints: OpenAPI shows `PUT`; `WorkflowHandle.cancel()` currently uses `DELETE`. Confirm against the running service and align (support fallback on 405).
- `IvkJob`’s `status` uses `RUNNING`; API uses `in_progress`. Ensure mapping is consistent everywhere if/when we expose `IvkJob`-typed results.
- Consider adding batch fetch helpers that use `item_ids` + `items_by_ids` for performance on large queues.

**Pydantic Models (new)**
- Queue status
  - `ProcessorStatus`: `is_started: bool`, `is_processing: bool`, `extra: dict[str, Any] = {}`.
  - `QueueStatus`: `queue_id: str`, `item_id: int | None`, `batch_id: str | None`, `session_id: str | None`, counts: `pending/in_progress/completed/failed/canceled/total: int`, `extra: dict[str, Any] = {}`.
  - `QueueAndProcessorStatus`: `queue: QueueStatus`, `processor: ProcessorStatus`, `extra: dict[str, Any] = {}`.
- Queue items
  - `ImageFieldRef`: `image_name: str`, `extra: dict[str, Any] = {}`.
  - `NodeFieldValue`: `node_path: str`, `field_name: str`, `value: str | int | float | ImageFieldRef`, `extra: dict[str, Any] = {}`.
  - `QueueItemStatus` enum: `pending | in_progress | completed | failed | canceled`.
  - `QueueItem`: explicit fields matching OpenAPI `SessionQueueItem`:
    - `item_id: int`, `status: QueueItemStatus`, `priority: int = 0`, `batch_id: str`, `queue_id: str`.
    - `origin: str | None`, `destination: str | None`, `session_id: str`.
    - Error fields: `error_type: str | None`, `error_message: str | None`, `error_traceback: str | None`.
    - Timestamps: `created_at: datetime`, `updated_at: datetime`, `started_at: datetime | None`, `completed_at: datetime | None` (parse strings to datetime).
    - Optional fields: `field_values: list[NodeFieldValue] | None`, `published_workflow_id: str | None`, `credits: float | None`.
    - Heavy fields: `session: dict[str, Any] | None` (minimal typing initially), `workflow: dict[str, Any] | None`.
    - `extra: dict[str, Any] = {}`.
- Action results
  - `CancelAllExceptCurrentResult`: `canceled: int`, `extra: dict[str, Any] = {}`.
  - `ClearResult`: `deleted: int`, `extra: dict[str, Any] = {}`.
  - `PruneResult`: `deleted: int`, `extra: dict[str, Any] = {}`.

Implementation detail: models will capture unknown keys into `extra` and ignore them for typed access. Known fields are explicitly defined to ensure strong typing.

**Example Usage (planned)**
```python
from invokeai_py_client import InvokeAIClient

client = InvokeAIClient.from_url("http://localhost:19090")

# Queues
queues = client.queue_repo.list_queues()  # ["default"]
q = client.queue_repo.get_queue("default")

# Quick status
busy = q.is_busy()
running = q.count_running()

# List and wrap as handles
items = q.list_running()
handles = [q.get_item(it.item_id) for it in items]

# Operate on a single job
h = handles[0]
h.refresh()
if h.is_running():
    h.cancel()
```
