"""
Unit test: scan external model folder via v2 model_manager scan_folder API.

This test requires a running InvokeAI server and the external models
directory to be provided by environment variables:

- `INVOKE_AI_ENDPOINT` (e.g., "http://localhost:19090/api/v1")
- `CONTAINER_EXTERNAL_MODEL_DIR` (absolute path to scan)

If either variable is missing, the test is skipped.
"""
from __future__ import annotations

import os
from typing import Any

import pytest

from invokeai_py_client import InvokeAIClient


def _require_endpoint() -> str:
    ep = os.environ.get("INVOKE_AI_ENDPOINT")
    if not ep:
        pytest.skip(
            "INVOKE_AI_ENDPOINT not set; integration tests require a running server"
        )
    return ep


def _require_scan_dir() -> str:
    p = os.environ.get("CONTAINER_EXTERNAL_MODEL_DIR")
    if not p:
        pytest.skip(
            "CONTAINER_EXTERNAL_MODEL_DIR not set; skipping scan_folder test"
        )
    return p


@pytest.mark.integration
def test_scan_folder_lists_models() -> None:
    base_url = _require_endpoint()
    scan_dir = _require_scan_dir()

    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    result: Any = repo.scan_folder(scan_dir)

    # Print scan results for manual inspection
    print(f"[SCAN] directory: {scan_dir}")
    try:
        print(f"[SCAN] found {len(result)} entries")
    except Exception:
        pass
    for item in result:
        if hasattr(item, "path") and hasattr(item, "is_installed"):
            print(f" - {getattr(item, 'path')} (installed={getattr(item, 'is_installed')})")
        elif isinstance(item, dict):
            p = item.get("path")
            inst = item.get("is_installed")
            print(f" - {p} (installed={inst})")

    # The endpoint returns a list of FoundModel (pydantic) or raw list of dicts
    assert isinstance(result, list)
    # No hard assertion on non-empty (folder may be empty); validate shape if present
    for item in result:
        # Pydantic model (FoundModel) has attributes; dict has keys
        if hasattr(item, "path") and hasattr(item, "is_installed"):
            assert isinstance(getattr(item, "path"), str)
            assert isinstance(getattr(item, "is_installed"), bool)
        elif isinstance(item, dict):
            assert isinstance(item.get("path"), str)
            assert isinstance(item.get("is_installed"), bool)
        else:
            pytest.fail(f"Unexpected scan_folder item type: {type(item)!r}")
