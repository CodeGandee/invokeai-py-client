"""
Manual example: delete a DNN model by key (or by exact name lookup).

Environment
-----------
- INVOKE_AI_ENDPOINT: full API base URL (e.g., "http://localhost:19090/api/v1").
- MODEL_KEY: exact model key to delete (preferred).
- MODEL_NAME (optional): exact model name to resolve to key if MODEL_KEY not set.

Notes
-----
- Intended for manual execution; code runs at import (no __main__ guard).
"""
from __future__ import annotations

import os
from typing import Optional

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import DnnModel


def _resolve_key_by_name(models: list[DnnModel], name: str) -> Optional[str]:
    for m in models:
        if getattr(m, "name", None) == name:
            return getattr(m, "key", None)
    return None


base_url = os.environ.get("INVOKE_AI_ENDPOINT")
model_key = os.environ.get("MODEL_KEY")
model_name = os.environ.get("MODEL_NAME")

if not base_url:
    print("[SKIP] INVOKE_AI_ENDPOINT not set; set e.g. http://localhost:19090/api/v1")
else:
    print(f"[INFO] endpoint={base_url}")
    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    target_key: Optional[str] = model_key
    if target_key is None and model_name:
        try:
            models = repo.list_models()
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] list_models failed: {e}")
            models = []
        target_key = _resolve_key_by_name(models, model_name)
        if target_key is None:
            print(f"[SKIP] model name not found: {model_name}")

    if target_key is None:
        print("[SKIP] specify MODEL_KEY or MODEL_NAME")
    else:
        print(f"[STEP] delete model key={target_key}")
        try:
            ok = repo.delete_model(target_key)
            if ok:
                print("[OK] deleted")
            else:
                print("[WARN] server did not confirm deletion (404 or similar)")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] delete_model error: {e}")

