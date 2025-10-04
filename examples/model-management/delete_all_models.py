"""
Manual example: delete all installed DNN models from InvokeAI.

Environment
-----------
- INVOKE_AI_ENDPOINT: full API base URL (e.g., "http://localhost:19090/api/v1").

Notes
-----
- Intended for manual execution; code runs at import (no __main__ guard).
"""
from __future__ import annotations

import os

from invokeai_py_client import InvokeAIClient


base_url = os.environ.get("INVOKE_AI_ENDPOINT")
if not base_url:
    print("[SKIP] INVOKE_AI_ENDPOINT not set; set e.g. http://localhost:19090/api/v1")
else:
    print(f"[INFO] endpoint={base_url}")
    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo
    try:
        summary = repo.delete_all_models()
        print(f"[OK] delete_all_models: {summary}")
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] delete_all_models error: {e}")

