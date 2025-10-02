**Title**
Model Management API (v2 model_manager endpoints) — Implemented in DnnModelRepository

**Objectives**
- Extend `DnnModelRepository` to include write-capable model management operations.
- Follow repository/handle patterns used for boards, workflows, and queues.
- Provide strongly-typed Pydantic models with `extra` fields for forward compatibility.
- Add integration tests that exercise happy-path flows against a running server.

**Deliverables**
- Extend existing repository: `src/invokeai_py_client/dnn_model/dnn_model_repo.py`
  - Add write-capable methods for install/convert/delete/scan/cache/HF helpers and install-job management
  - Keep existing read-only methods (`list_models()`, `get_model_by_key()`) intact
- Typed models within the dnn_model package:
  - Add `ModelInstJobInfo` (renamed from ModelInstallJob), `InstallJobStatus`, `ModelManagerStats`, `HFLoginStatus` (e.g., in `dnn_model_models.py` or extend `dnn_model_types.py`)
  - Add `ModelInstallConfig` Pydantic model (typed wrapper for `ModelRecordChanges`, see below)
- Client utility:
  - Add a small v2 request helper on the client (e.g., `_make_request_v2()` or `_build_url(version=2, path=...)`)
- Tests:
  - Unit tests for parsing/model typing
  - Integration tests (marked `integration`, `slow`) for install → poll job → delete/convert (requires `INVOKE_AI_ENDPOINT`)
- Docs/examples:
  - Short usage snippet for install/monitor/delete using `client.dnn_model_repo`

**API Endpoints (OpenAPI v6.8: tag model_manager)**
- List/detail:
  - `GET /api/v2/models/` — list model records (already used by `DnnModelRepository`)
  - `GET /api/v2/models/i/{key}` — model detail
- Install:
  - `POST /api/v2/models/install` — install model from string source (local path, URL, or HF repo)
  - `GET /api/v2/models/install/{id}` — get install job status
  - `DELETE /api/v2/models/install/{id}` — cancel/remove install job
  - `DELETE /api/v2/models/install` — prune finished jobs
  - (Optional) `POST /api/v2/models/install/huggingface` — HF-specific convenience
- Mutations:
  - `PUT /api/v2/models/convert/{key}` — convert model to diffusers
  - `DELETE /api/v2/models/i/{key}` — delete model
  - `GET /api/v2/models/scan_folder` — trigger scan for models
- Cache & stats:
  - `POST /api/v2/models/empty_model_cache` — drop cached models
  - `GET /api/v2/models/stats` — model manager RAM cache stats (may return null)
- Hugging Face helpers:
  - `GET /api/v2/models/hf_login` — status
  - `POST /api/v2/models/hf_login` — login
  - `DELETE /api/v2/models/hf_login` — logout

**Design**
- Build on the existing `DnnModelRepository`:
  - Add v2 write operations and return typed results; keep stateless behavior (no local caching).
  - Optional `ModelInstJobHandle` class (within the dnn_model package) can offer job-scoped helpers (`refresh`, `wait`, `cancel`).
  - Place types in the dnn_model package, preserving unknowns in `extra` for forward compatibility.
- Client integration:
  - Continue exposing `client.dnn_model_repo` as the single entry point for model reads and writes.
  - Introduce a helper to build/request v2 endpoints without changing the client’s `base_path` (defaults to `/api/v1`).
    - e.g., `_make_request_v2(method, "/models/install", **kwargs)` or `_make_request(method, self._v2("/models/install"), ...)`.
- Error handling:
  - Surface HTTP failures via existing request error semantics; later consider structured `APIError` when exceptions land.
  - Return booleans for simple mutations (200/204); return typed models for richer responses.

**Public API (proposed)**
- Repository: `DnnModelRepository`
  - Install / Jobs
    - `install_model(source: str, config: ModelInstallConfig | dict | None = None, inplace: bool | None = None, access_token: str | None = None) -> ModelInstJobHandle` — Creates and returns a job handle for a new install job (local path, URL, or HF repo id).
    - `list_install_jobs() -> list[ModelInstJobHandle]` — Lists all install jobs as handles.
    - `get_install_job(id: str) -> ModelInstJobHandle | None` — Returns a handle to a single install job.
    - `prune_install_jobs() -> bool` — Removes finished/errored install jobs from the server’s list.
    - (Optional) `install_huggingface(repo_id: str, config: ModelInstallConfig | dict | None = None, access_token: str | None = None) -> ModelInstJobHandle` — Convenience wrapper over `install_model` for HF repo ids.
  - Mutations
    - `convert_model(key: str) -> DnnModel` — Converts a safetensors model to diffusers; returns the updated model record.
    - `delete_model(key: str) -> bool` — Deletes a model by key.
    - `scan_folder(scan_path: str | None = None) -> list[FoundModel] | dict` — Triggers a scan of the models directory for changes; return shape follows upstream.
  - Cache & Stats
    - `empty_model_cache() -> bool` — Clears the RAM/VRAM model cache (locked/in-use models remain).
    - `get_stats() -> ModelManagerStats | None` — Returns cache stats or `None` if no models were loaded.
  - HF Helpers
    - `hf_login(token: str) -> bool` — Logs into Hugging Face with the provided token.
    - `hf_logout() -> bool` — Logs out of Hugging Face and clears the token.
    - `hf_status() -> HFLoginStatus` — Returns Hugging Face login status (logged in, username, scopes).

- Handle: `ModelInstJobHandle` (optional, sugar)
  - `refresh() -> ModelInstJobInfo` — Fetch latest job info from the server and update cache.
  - `info: ModelInstJobInfo | None` — Cached job info, if previously refreshed.
  - `status() -> InstallJobStatus`
  - `progress() -> float | None`
  - `is_done() -> bool`
  - `is_failed() -> bool`
  - `cancel() -> bool`
  - `wait(timeout: float = 600.0, poll_interval: float = 2.0) -> ModelInstJobInfo` (returns final state)

**Typed Models (Pydantic, v2)**
- `InstallJobStatus` (Enum[str]): allow known values and store unknown in `extra`
  - Known: `pending`, `queued`, `downloading`, `probing`, `configuring`, `installing`, `converting`, `installed`, `completed`, `failed`, `canceled`
- `ModelInstJobInfo` (BaseModel)
  - `id: str`
  - `source: str | None`
  - `status: InstallJobStatus`
  - `message: str | None`
  - `progress: float | None` (0.0–1.0)
  - `created_at: datetime | None`, `updated_at: datetime | None`, `completed_at: datetime | None`
  - `model_key: str | None` (if known after install/convert)
  - `result: dict[str, Any] | None` (raw payload for success details)
  - `error: dict[str, Any] | None`
  - `extra: dict[str, Any] = {}`
- `ModelManagerStats` (BaseModel)
  - `hit_rate: float | None`
  - `miss_rate: float | None`
  - `ram_used_mb: float | None`
  - `ram_capacity_mb: float | None`
  - `loads: int | None`
  - `evictions: int | None`
  - `extra: dict[str, Any] = {}`
- `HFLoginStatus` (BaseModel)
  - `is_logged_in: bool`
  - `username: str | None`
  - `scopes: list[str] | None`
  - `extra: dict[str, Any] = {}`

- Notes
- `DnnModel` is already defined — reuse it for convert/get/delete results.
- All models include `extra` to preserve forward-compatibility.
- Installer queue separation: Model install jobs are NOT part of the session queue (`/api/v1/queue/...`). They are tracked and managed by the model manager’s own installer service and endpoints under `/api/v2/models/install[...]`. Do not integrate installs into `queue_repo`; manage installs via `DnnModelRepository` (and `ModelInstJobHandle`).
- Download queue separation: Remote model downloads use a dedicated download queue (`/api/v1/download_queue/...`). We may add a thin wrapper later if needed, but it is not part of the session queue or the DNN model repository.

 

**Install Config (typed)**
- Upstream expects a `ModelRecordChanges` body. We expose a typed `ModelInstallConfig` that maps to this schema. All fields are optional overrides – passing `{}` accepts the server’s auto-probed defaults.
- Common fields you may set:
  - `name: str | None` — friendly name for the model
  - `description: str | None`
  - `base: BaseDnnModelType | None` — e.g., `StableDiffusionXL`, `Flux`
  - `type: DnnModelType | None` — e.g., `Main`, `VAE`, `LoRA`, `ControlNet`
  - `path: str | None` — explicit file/folder path (normally inferred)
  - `format: str | None` — format hint if needed (checkpoint/diffusers/etc.)
  - `prediction_type: str | None` — scheduler prediction type
  - `upcast_attention: bool | None`
  - `trigger_phrases: list[str] | None`
  - `default_settings: dict[str, Any] | None` — per-type defaults (main/lora/control)
  - `variant: str | None`
  - `config_path: str | None` — config file path for checkpoints
  - `extra: dict[str, Any] = {}` — forward-compatibility passthrough

Example Pydantic wrapper we will use:
```python
from pydantic import BaseModel, Field
from typing import Any, Optional
from invokeai_py_client.dnn_model import BaseDnnModelType, DnnModelType

class ModelInstallConfig(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base: Optional[BaseDnnModelType] = None
    type: Optional[DnnModelType] = None
    path: Optional[str] = None
    format: Optional[str] = None
    prediction_type: Optional[str] = None
    upcast_attention: Optional[bool] = None
    trigger_phrases: Optional[list[str]] = None
    default_settings: Optional[dict[str, Any]] = None
    variant: Optional[str] = None
    config_path: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_record_changes(self) -> dict[str, Any]:
        # Convert to upstream-compatible body, preserving known fields and extra
        body = self.model_dump(exclude_none=True)
        extra = body.pop("extra", {})
        body.update(extra)
        return body
```

Signature note
- We accept either `ModelInstallConfig` or a raw `dict` for `config`.
- `inplace: bool | None` forwards to the upstream query param for local installs.

**Compatibility & URL Builder**
- Client currently builds URLs against `/api/v1`. To call v2 endpoints reliably:
  - Add `_make_request_v2(method: str, endpoint: str, **kwargs)` that mirrors `_make_request` but prefixes `/api/v2`.
  - Alternatively, a generic `_build_url(version: int, path: str) -> str` to reuse the same `session` and retry config.

**Examples (planned)**
```python
from invokeai_py_client import InvokeAIClient

client = InvokeAIClient.from_url("http://localhost:19090")

# 1) Install a model (HF repo id) with typed config
job = client.dnn_model_repo.install_model(
    source="runwayml/stable-diffusion-v1-5",  # or local path/URL
    config=ModelInstallConfig(name="My SD1.5"),
    inplace=None,  # or True for local path installs
)

# 2) Wait for install to complete (handle returns info)
final = job.wait(timeout=1800, poll_interval=3)
assert final.status in {"installed", "completed"}

# 3) Convert a model
converted = client.dnn_model_repo.convert_model(key="sd15")

# 4) Delete a model
ok = client.dnn_model_repo.delete_model(key="sd15-old")

# 5) Cache & stats
client.dnn_model_repo.empty_model_cache()
stats = client.dnn_model_repo.get_stats()

# 6) HF login helpers
if not client.dnn_model_repo.hf_status().is_logged_in:
    client.dnn_model_repo.hf_login(token=os.environ["HF_TOKEN"])  # ensure env set externally
```

**Testing Plan**
- Unit tests (no network):
  - Model parsing of `ModelInstJobInfo`, `ModelManagerStats`, `HFLoginStatus` with `extra` preservation.
  - Repository method behavior on minimal mocked responses (if any). Keep focused and small.
- Integration tests (require `INVOKE_AI_ENDPOINT`):
  - Install a small test model (or skip if unavailable) and poll job until terminal; assert terminal state is success or handled failure.
  - Convert a known model key (skip if not present), then verify returned entity.
  - Delete a test model and verify subsequent GET returns 404.
  - HF status/login/logout flow gated by presence of token in env; otherwise skip.

**Implementation Steps**
1) Add v2 request helper to `InvokeAIClient` (`_make_request_v2` or `_build_url(version=2, ...)`).
2) Extend `DnnModelRepository` with write APIs (`install_model`, `list/get/prune` install jobs, `convert_model`, `delete_model`, `scan_folder`, `empty_model_cache`, `get_stats`, `hf_*`).
3) Add typed models in the dnn_model package; ensure unknown keys land in `extra`.
4) (Optional) Add `ModelInstJobHandle` with `refresh()`, `wait()`, and `cancel()` helpers.
5) Write unit tests for parsing and basic method plumbing.
6) Add integration tests guarded by `INVOKE_AI_ENDPOINT` and suitable markers.
7) Write examples and short docs.
8) Update `ROADMAP.md` status once initial subset lands.

**Open Questions**
- Exact shape of install job payload varies by upstream version; the model should be permissive. Confirm field names for `status`, `progress`, `message`, and `result`.
- Should we provide a bulk list of install jobs if/when upstream exposes it? For now, we support get-by-id and prune.
- Consider retries/backoff for long-running polls; initial implementation can be simple sleep/poll loops.
