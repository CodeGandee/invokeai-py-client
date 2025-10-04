"""
Manual example: list installed DNN models from an InvokeAI server.

Environment
-----------
- INVOKE_AI_ENDPOINT: full API base URL (e.g., "http://localhost:19090/api/v1").

Notes
-----
- This script is intended for manual execution and notebook friendliness.
- No `if __name__ == "__main__"` guard; code runs at import.
"""
from __future__ import annotations

from typing import Iterable
import os

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import DnnModel


def _fmt_model(m: DnnModel) -> str:
    name = getattr(m, "name", "")
    key = getattr(m, "key", "")
    base = getattr(m, "base", None)
    mtype = getattr(m, "type", None)
    fmt = getattr(m, "format", None)
    base_s = str(base) if base is not None else "?"
    type_s = str(mtype) if mtype is not None else "?"
    fmt_s = str(fmt) if fmt is not None else "?"
    return f"name={name} | key={key} | base={base_s} | type={type_s} | format={fmt_s}"


def _print_list(title: str, items: Iterable[str]) -> None:
    print(f"[INFO] {title}")
    for i, line in enumerate(items, 1):
        print(f"  {i:03d}. {line}")


# Resolve endpoint
base_url = os.environ.get("INVOKE_AI_ENDPOINT")
if not base_url:
    print("[SKIP] INVOKE_AI_ENDPOINT not set; set e.g. http://localhost:19090/api/v1")
else:
    print(f"[INFO] Using endpoint: {base_url}")
    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    try:
        models = repo.list_models()
    except Exception as e:  # noqa: BLE001 - surface error to user
        print(f"[ERROR] list_models failed: {e}")
        models = []

    lines = [_fmt_model(m) for m in models]
    _print_list(f"Installed models (count={len(models)})", lines)

