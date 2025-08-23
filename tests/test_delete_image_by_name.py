#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add local src/ to import path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore

# Config
BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
IMAGE_NAME = os.environ.get("INVOKEAI_IMAGE_NAME", "0712249f-1047-4314-a338-d6807920f245.png")


def _resolve_exact_image_name(client: InvokeAIClient, rough_name: str) -> str | None:
    """
    Resolve the server's exact image_name token for a given rough name.

    Strategy:
    - Try direct DTO lookup with provided name
    - Try without extension
    - List uncategorized image names and find exact match
    - As a last resort, match by prefix (without extension)
    """
    # 1) Try as-is
    try:
        resp = client._make_request("GET", f"/images/i/{rough_name}")
        if resp.status_code == 200:
            return rough_name
    except Exception:
        pass

    # 2) Try without extension
    if "." in rough_name:
        stem = rough_name.rsplit(".", 1)[0]
        try:
            resp2 = client._make_request("GET", f"/images/i/{stem}")
            if resp2.status_code == 200:
                return stem
        except Exception:
            pass
    else:
        stem = rough_name

    # 3) Check uncategorized names list
    try:
        names_resp = client._make_request("GET", "/boards/none/image_names")
        names = names_resp.json() if hasattr(names_resp, "json") else []
        if isinstance(names, list) and names:
            # Exact matches first
            for n in names:
                if n == rough_name or n == stem:
                    return n
            # Fallback: match by prefix (id portion)
            for n in names:
                if n.startswith(stem):
                    return n
    except Exception:
        pass

    return None


def test_delete_image_by_name():
    """
    Delete a specific image by name using the board subsystem.

    Steps:
      1. Resolve exact image_name token via API (handles extension/name variants).
      2. Delete using board subsystem (uncategorized handle).
      3. Verify first deletion returns True.
      4. Verify second deletion returns False.

    APIs exercised:
      - DTO check: GET /api/v1/images/i/{image_name}
      - List uncategorized names: GET /api/v1/boards/none/image_names
      - Delete: DELETE /api/v1/images/i/{image_name} via BoardHandle.delete_image()
    """
    client = InvokeAIClient.from_url(BASE_URL)
    board = client.board_repo.get_uncategorized_handle()

    # Resolve the exact server-side image_name
    exact = _resolve_exact_image_name(client, IMAGE_NAME)
    assert exact is not None, f"Image not found on server: {IMAGE_NAME}"

    # 1) Delete once (should succeed if image exists)
    deleted = board.delete_image(exact)
    assert deleted is True, f"Failed to delete image {exact}"

    # 2) Delete again (should now fail/return False)
    deleted_again = board.delete_image(exact)
    assert deleted_again is False, f"Image {exact} still exists after deletion"