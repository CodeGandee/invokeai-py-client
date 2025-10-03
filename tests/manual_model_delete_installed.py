"""
Manual Model Management API test: delete a newly installed model by key.

Prerequisites
- Running InvokeAI server. Provide base API URL via `INVOKE_AI_ENDPOINT`, e.g.:
  export INVOKE_AI_ENDPOINT="http://localhost:19090/api/v1"
- Provide a model key via `MODEL_KEY` (preferred), or a model source path via `MODEL_PATH`.
  If neither is set, this script will try to pick the most recent completed
  install job with a `model_key`.

Usage
- Run directly as a script (manual test):
  python tests/manual_model_delete_installed.py

Notes
- This script is non-destructive beyond deleting the specified model record/files
  (per server semantics). Use with caution.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import DnnModel


DEFAULT_MODEL_PATH = "/mnt/extra/sdxl/main/realisticfoundryxl_v10.safetensors"


def _find_model_key_by_path(client: InvokeAIClient, model_path: str) -> Optional[str]:
    try:
        models = client.dnn_model_repo.list_models()
    except Exception as e:
        print(f"[WARN] list_models failed: {e}")
        return None
    # Prefer exact source path match if available
    for m in models:
        try:
            if getattr(m, "source", None) == model_path:
                return m.key  # type: ignore[attr-defined]
        except Exception:
            continue
    # Fallback: fuzzy match by filename in path field
    fname = os.path.basename(model_path)
    for m in models:
        try:
            path_val = getattr(m, "path", "")
            if isinstance(path_val, str) and fname and fname in path_val:
                return m.key  # type: ignore[attr-defined]
        except Exception:
            continue
    return None


def _find_model_key_from_jobs(client: InvokeAIClient) -> Optional[str]:
    try:
        jobs = client.dnn_model_repo.list_install_jobs()
    except Exception as e:
        print(f"[WARN] list_install_jobs failed: {e}")
        return None
    # Most recent first (handles created in order)
    for h in reversed(jobs):
        try:
            info = h.refresh()
            mk = getattr(info, "model_key", None)
            if mk:
                return mk
        except Exception:
            continue
    return None


def main() -> int:
    base_url = os.environ.get("INVOKE_AI_ENDPOINT")
    if not base_url:
        print("[SKIP] INVOKE_AI_ENDPOINT not set; please export it to run this manual test.")
        return 0

    client = InvokeAIClient.from_url(base_url)

    key = os.environ.get("MODEL_KEY")
    if not key:
        model_path = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
        print(f"[INFO] MODEL_KEY not provided; trying MODEL_PATH={model_path}")
        key = _find_model_key_by_path(client, model_path)
    if not key:
        print("[INFO] Falling back to latest completed install job with model_key…")
        key = _find_model_key_from_jobs(client)
    if not key:
        print("[ERROR] Could not determine model key to delete. Set MODEL_KEY or MODEL_PATH.")
        return 0

    print(f"[STEP] Deleting model key: {key}")
    try:
        ok = client.dnn_model_repo.delete_model(key)
        print(f"[INFO] delete_model returned: {ok}")
    except Exception as e:
        print(f"[ERROR] delete_model failed: {e}")
        return 0

    # Verify best-effort
    try:
        found = client.dnn_model_repo.get_model_by_key(key)
        if isinstance(found, DnnModel):
            print("[WARN] Model still present after delete (server may have delayed removal)")
        else:
            print("[OK] Model not found after delete")
    except Exception:
        print("[OK] get_model_by_key raised; treat as deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())

