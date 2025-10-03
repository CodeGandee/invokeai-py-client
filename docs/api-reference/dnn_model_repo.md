# DNN Model Repository (v2 Model Manager)

Typed, repository-style access to InvokeAI's v2 model manager APIs for discovery and management of models.

## Overview

- Discovery: list and get models (no client-side cache)
- Management: install (local path/URL/HF), monitor jobs, convert, delete, scan folder
- Cache & Stats: empty RAM/VRAM cache; get cache stats
- HF Helpers: login/logout/status
- Native exceptions: no raw `requests.HTTPError` surfaces

## Repository

```python
from invokeai_py_client import InvokeAIClient
client = InvokeAIClient.from_url("http://localhost:9090")
repo = client.dnn_model_repo
```

### list_models()

List all models on the server (fresh call).

```python
models = repo.list_models()
print(len(models))
```

### get_model_by_key(key)

Get a single model by its unique key. Returns `None` on 404.

```python
m = repo.get_model_by_key("abc-123")
if m:
    print(m.name, m.base, m.type)
```

### install_model(source, *, config=None, inplace=None, access_token=None)

Start an installation job from local path, URL, or `repo_id`.

- Success: returns a `ModelInstJobHandle`; `handle.wait_until()` returns final info
- Already installed (HTTP 409): returns a handle with synthetic COMPLETED info and `info.extra['reason']=='already_installed'`
- Failure: raises `ModelInstallStartError` (creation) or `ModelInstallJobFailed` (processing)

```python
handle = repo.install_model("/mnt/extra/sdxl/main/my_model.safetensors", inplace=True)
try:
    info = handle.wait_until(timeout=None)
    print("installed", getattr(info, "model_key", None))
except ModelInstallJobFailed as e:
    print("failed:", getattr(e.info, "error", None))
```

### list_install_jobs()

List all install jobs as handles with preloaded info.

```python
for h in repo.list_install_jobs():
    print(h.job_id, getattr(h.info, "status", None))
```

### get_install_job(id)

Get a single install job handle by id, or `None` if not found.

### prune_install_jobs()

Prune completed/errored jobs from server list.

### convert_model(key)

Convert a model to diffusers format.

### delete_model(key)

Delete a model by key (returns `True` for 200/204).

### delete_all_models()

Best-effort batch delete of all models; returns a summary dict.

### scan_folder(scan_path)

Scan a folder for models; returns list of `(path, is_installed)` as `FoundModel`.

### empty_model_cache(), get_stats()

Clear RAM/VRAM cache and fetch cache stats (may be `None`).

### hf_status(), hf_login(token), hf_logout()

Check/login/logout Hugging Face token on the server.

## Job Handle (ModelInstJobHandle)

```python
h = repo.install_model("/mnt/models/file.safetensors")
info = h.wait_until(timeout=None)  # COMPLETED returns; ERROR/CANCELLED raises
```

- `refresh()`: fetch latest info
- `status()`: convenience status getter
- `progress()`: byte progress if available
- `raise_if_failed()`: raise `ModelInstallJobFailed` if failed/cancelled
- `wait_until(timeout=None, poll_interval=2.0)`: block until terminal

## Native Exceptions

- `APIRequestError(status_code, payload)`: wraps HTTP errors
- `ModelInstallStartError`: install creation failed
- `ModelInstallJobFailed(info)`: job ended with ERROR/CANCELLED
- `ModelInstallTimeout(last_info, timeout)`: wait_until timed out

## Examples

### Install from HF repo id

```python
h = repo.install_huggingface("org/name")
info = h.wait_until(timeout=None)
print("installed", getattr(info, "model_key", None))
```

### Scan and install all (non-fatal skips)

```python
entries = repo.scan_folder("/mnt/extra")
for e in entries:
    path = getattr(e, "path", None) or e.get("path")
    if not path:
        continue
    try:
        h = repo.install_model(path, inplace=True)
        info = h.wait_until(timeout=None)
        print("installed", getattr(info, "model_key", None))
    except ModelInstallJobFailed as err:
        print("failed", getattr(err.info, "error", None))
```

