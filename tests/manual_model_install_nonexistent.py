"""
Manual test: attempt to install a non-existent local model and handle the error.

Default path: /tmp/fakemodel.safetensors (override with MODEL_PATH).

Behavior
- If server rejects the request (HTTP error), catch and report.
- If server accepts and creates a job, poll until terminal and expect status=error.

Run
- export INVOKE_AI_ENDPOINT="http://localhost:19090/api/v1"
- python tests/manual_model_install_nonexistent.py
"""
from __future__ import annotations

import os
import sys
import time
from typing import Optional

import requests

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import InstallJobStatus


DEFAULT_MODEL_PATH = "/tmp/fakemodel.safetensors"


def main() -> int:
    base_url = os.environ.get("INVOKE_AI_ENDPOINT")
    if not base_url:
        print("[SKIP] INVOKE_AI_ENDPOINT not set")
        return 0

    model_path = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
    print(f"[INFO] Using endpoint: {base_url}")
    print(f"[INFO] Installing non-existent model: {model_path}")

    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    try:
        job = repo.install_model(source=model_path, inplace=True)
        print(f"[INFO] Started job id: {job.job_id}")
    except requests.HTTPError as e:
        print(f"[OK] Caught HTTP error on install: {e}")
        return 0
    except Exception as e:
        print(f"[OK] Caught exception on install: {e}")
        return 0

    # If we get here, the server accepted the install; poll until error/completed.
    start = time.time()
    timeout = int(os.environ.get("MODEL_INSTALL_TIMEOUT", "120"))
    last_status: Optional[str] = None
    while time.time() - start < timeout:
        info = job.refresh()
        status = info.status.value if isinstance(info.status, InstallJobStatus) else str(info.status)
        if status != last_status:
            print(f"[POLL {int(time.time()-start):3d}s] status={status}")
            last_status = status
        if status in {"completed", "error", "cancelled"}:
            break
        time.sleep(2)

    final = job.refresh()
    if final.status == InstallJobStatus.ERROR:
        print("[OK] Job reached error state as expected.")
        if final.error:
            print(f"      error={final.error}")
        if final.error_reason:
            print(f"      error_reason={final.error_reason}")
        return 0
    else:
        print(f"[WARN] Unexpected terminal state: {final.status}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

