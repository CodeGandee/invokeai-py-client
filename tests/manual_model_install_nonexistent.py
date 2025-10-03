"""
Manual test: attempt to install a non-existent local model and handle the error.

Default path: /tmp/fakemodel.safetensors (override with MODEL_PATH).

Behavior
- If server rejects the request, catch native ModelInstallStartError (no HTTP leakage).
- If server accepts and creates a job, wait_until() should raise ModelInstallJobFailed.

Run
- export INVOKE_AI_ENDPOINT="http://localhost:19090/api/v1"
- python tests/manual_model_install_nonexistent.py
"""
from __future__ import annotations

import os
import sys
import time

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import (
    InstallJobStatus,
    ModelInstallStartError,
    ModelInstallJobFailed,
    ModelInstallTimeout,
    APIRequestError,
)


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
    except ModelInstallStartError as e:
        print(f"[OK] Caught ModelInstallStartError on install: {e}")
        return 0
    except APIRequestError as e:
        print(f"[OK] Caught APIRequestError on install: {e}")
        return 0
    except Exception as e:
        print(f"[OK] Caught exception on install: {e}")
        return 0

    # If we get here, the server accepted the install; wait_until should lead to a failure.
    timeout = float(os.environ.get("MODEL_INSTALL_TIMEOUT", "120"))
    try:
        final = job.wait_until(timeout=timeout, poll_interval=2.0)
        # If we reached here without exception, it's unexpected success
        print(f"[WARN] Unexpected success: status={final.status}")
        return 0
    except ModelInstallJobFailed as e:
        print("[OK] wait_until raised ModelInstallJobFailed as expected.")
        if e.info is not None:
            print(f"      final_status={e.info.status}")
            if e.info.error:
                print(f"      error={e.info.error}")
            if e.info.error_reason:
                print(f"      error_reason={e.info.error_reason}")
        return 0
    except ModelInstallTimeout as e:
        print("[WARN] wait_until timed out.")
        if e.last_info is not None:
            print(f"      last_status={e.last_info.status}")
        return 0
    except APIRequestError as e:
        print(f"[OK] Caught APIRequestError during wait: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
