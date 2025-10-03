"""
Manual Model Management API test: install a local model and monitor progress.

Prerequisites
- Running InvokeAI server. Provide its base API URL via `INVOKE_AI_ENDPOINT`, e.g.:
  export INVOKE_AI_ENDPOINT="http://localhost:9090/api/v1"
- The model file exists and is readable by the InvokeAI server process:
  default: /mnt/extra/sdxl/main/realisticfoundryxl_v10.safetensors
  override with env `MODEL_PATH` if needed.

Usage
- Run directly as a script (this is a manual test):
  python tests/manual_model_install_progress.py

Notes
- This script performs network operations against your server and prints progress.
- It does not assert or exit non‑zero on failures; check output to diagnose issues.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Optional

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import (
    InstallJobStatus,
)


DEFAULT_MODEL_PATH = "/mnt/extra/sdxl/main/realisticfoundryxl_v10.safetensors"


def main() -> int:
    base_url = os.environ.get("INVOKE_AI_ENDPOINT")
    if not base_url:
        print("[SKIP] INVOKE_AI_ENDPOINT not set; please export it to run this manual test.")
        return 0

    model_path = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
    inplace_env = os.environ.get("MODEL_INPLACE", "1")
    inplace = inplace_env not in {"0", "false", "False"}

    print(f"[INFO] Server: {base_url}")
    print(f"[INFO] Model path: {model_path}")
    print(f"[INFO] Inplace: {inplace}")

    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    try:
        print("[STEP] starting model install…")
        job = repo.install_model(source=model_path, inplace=inplace)
        print(f"[INFO] install job id: {job.job_id}")
    except Exception as e:
        print(f"[ERROR] failed to start install: {e}")
        return 0

    start = time.time()
    last_status: Optional[str] = None
    last_prog: Optional[float] = None
    timeout = int(os.environ.get("MODEL_INSTALL_TIMEOUT", "1800"))  # seconds

    try:
        while time.time() - start < timeout:
            info = job.refresh()
            status = info.status.value if isinstance(info.status, InstallJobStatus) else str(info.status)
            prog: Optional[float] = job.progress()
            if status != last_status or (prog is not None and prog != last_prog):
                msg = f"[POLL {int(time.time()-start):4d}s] status={status}"
                if info.bytes is not None and info.total_bytes:
                    msg += f" bytes={info.bytes}/{info.total_bytes} ({(info.bytes/info.total_bytes):.1%})"
                elif prog is not None:
                    msg += f" progress={(prog*100):.1f}%"
                if info.model_key:
                    msg += f" model_key={info.model_key}"
                print(msg)
                last_status, last_prog = status, prog

            if status in {"completed", "error", "cancelled"}:
                break
            time.sleep(2)

        final = job.refresh()
        print("[DONE] final status:")
        print(f"        id={final.id}, status={final.status}")
        if final.model_key:
            print(f"        model_key={final.model_key}")
        if final.error:
            print(f"        error={final.error}")
        if final.error_reason:
            print(f"        error_reason={final.error_reason}")
    except KeyboardInterrupt:
        print("\n[INTERRUPT] cancelling job…")
        try:
            ok = job.cancel()
            print(f"[INFO] cancel requested: {ok}")
        except Exception as e:
            print(f"[WARN] cancel failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

