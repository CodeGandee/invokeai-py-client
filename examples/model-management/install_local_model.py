"""
Manual example: install a local model file/folder into InvokeAI via the model manager.

Environment
-----------
- INVOKE_AI_ENDPOINT: full API base URL (e.g., "http://localhost:19090/api/v1").
- MODEL_PATH: absolute path to local model (file or folder).
- MODEL_INPLACE (optional): '1' to install in-place for local paths (default: 1).

Behavior
--------
- Starts an install job and waits until terminal status.
- Treats "already installed" (HTTP 409) as a successful skip and reports it.
- Surfaces server/job failures with messages (no HTTP details leaked).

Notes
-----
- Intended for manual execution; code runs at import (no __main__ guard).
- Avoids sys.exit to stay notebook-friendly.
"""
from __future__ import annotations

import os
from typing import Any

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import (
    APIRequestError,
    ModelInstallJobFailed,
    ModelInstallStartError,
)


def _env_bool(name: str, default: bool = True) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v not in {"0", "false", "False", "no", "NO"}


base_url = os.environ.get("INVOKE_AI_ENDPOINT")
model_path = os.environ.get("MODEL_PATH")
inplace = _env_bool("MODEL_INPLACE", True)

if not base_url:
    print("[SKIP] INVOKE_AI_ENDPOINT not set; set e.g. http://localhost:19090/api/v1")
elif not model_path:
    print("[SKIP] MODEL_PATH not set")
else:
    print(f"[INFO] endpoint={base_url}")
    print(f"[INFO] model_path={model_path} inplace={inplace}")

    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    try:
        handle = repo.install_model(source=model_path, inplace=inplace)
    except ModelInstallStartError as e:
        print(f"[FAIL] install start error: {e}")
        handle = None
    except APIRequestError as e:
        print(f"[FAIL] api error: {e}")
        handle = None
    except Exception as e:  # noqa: BLE001 - surface error
        print(f"[FAIL] unexpected error: {e}")
        handle = None

    if handle is not None:
        info = handle.info or handle.refresh()
        skipped = False
        try:
            if info is not None and getattr(info, "extra", {}).get("reason") == "already_installed":
                skipped = True
                final = info
            else:
                final = handle.wait_until(timeout=None, poll_interval=2.0)
            status = getattr(final, "status", None)
            model_key = getattr(final, "model_key", None)
            if skipped:
                print(f"[OK] skipped (already installed) | status={status} | model_key={model_key}")
            else:
                print(f"[OK] completed | status={status} | model_key={model_key}")
        except ModelInstallJobFailed as e:
            finfo: Any | None = getattr(e, "info", None)
            fstatus = getattr(finfo, "status", None)
            ferr = getattr(finfo, "error", None)
            freason = getattr(finfo, "error_reason", None)
            print(f"[FAIL] job failed | status={fstatus} | error={ferr or ''} | reason={freason or ''}")

