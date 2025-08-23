#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure local src/ is importable before third-party packages
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore


"""
Task 1: Move image to board (verified via InvokeAI Web APIs)

This test demonstrates how to:
1) Create (or fetch) a board named "mytest" and obtain its board_id (target-board-id).
2) Find image metadata (IvkImage) by image name via BoardRepository.
3) Move the image 311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png to board "mytest" using the target board_id.
4) Verify the move by listing images on the destination board and/or checking image metadata.

Related client APIs:
- [python.InvokeAIClient.from_url()](src/invokeai_py_client/client.py:143)
- [python.BoardRepository.get_board_handle_by_name()](src/invokeai_py_client/board/board_repo.py:317)
- [python.BoardRepository.create_board()](src/invokeai_py_client/board/board_repo.py:176)
- [python.BoardRepository.get_image_by_name()](src/invokeai_py_client/board/board_repo.py:402)
- [python.BoardRepository.get_image_current_board_id()](src/invokeai_py_client/board/board_repo.py:429)
- [python.BoardRepository.get_board_handle()](src/invokeai_py_client/board/board_repo.py:268)
- [python.BoardHandle.move_image_to()](src/invokeai_py_client/board/board_handle.py:402)
- [python.BoardHandle.list_images()](src/invokeai_py_client/board/board_handle.py:106)

Backend API mapping (for reference):
- Create Board: POST /api/v1/boards/
- Get Board: GET /api/v1/boards/{board_id}
- List Board Image Names: GET /api/v1/boards/{board_id}/image_names
- Image metadata: GET /api/v1/images/i/{image_name}
- Update image board assignment: PATCH /api/v1/images/i/{image_name} with {"board_id": "..."} or board_id as query param

Environment variables:
- INVOKEAI_BASE_URL   (default: http://127.0.0.1:9090)
- INVOKEAI_IMAGE_NAME (default: 311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png)
"""

BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
IMAGE_NAME = os.environ.get("INVOKEAI_IMAGE_NAME", "311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png")
TARGET_BOARD_NAME = "mytest"


def _resolve_image_name(repo, image_name: str) -> str | None:
    """
    Resolve the canonical server image_name using BoardRepository and fallbacks.

    Order:
      1) Try exact metadata lookup via repo.get_image_by_name(image_name)
      2) If name has extension, also try stem (without extension)
      3) List uncategorized image names and attempt exact or prefix match
    """
    # 1) exact lookup
    img = repo.get_image_by_name(image_name)
    if img:
        return img.image_name

    # 2) try stem
    if "." in image_name:
        stem = image_name.rsplit(".", 1)[0]
        img2 = repo.get_image_by_name(stem)
        if img2:
            return img2.image_name
    else:
        stem = image_name

    # 3) search uncategorized names for match
    try:
        names_resp = repo._client._make_request("GET", "/boards/none/image_names")
        names = names_resp.json() if hasattr(names_resp, "json") else []
        if isinstance(names, list):
            # exact match on full or stem
            for n in names:
                if n == image_name or n == stem:
                    return n
            # prefix heuristic on stem
            for n in names:
                if n.startswith(stem):
                    return n
    except Exception:
        pass

    return None


def test_move_image_to_board_task1():
    client = InvokeAIClient.from_url(BASE_URL)
    repo = client.board_repo

    # 1) Ensure board "mytest" exists, capture target board_id
    handle = repo.get_board_handle_by_name(TARGET_BOARD_NAME)
    if handle is None:
        handle = repo.create_board(TARGET_BOARD_NAME)
    target_board_id = handle.board_id
    assert target_board_id, "Failed to create or locate target board id"

    # 2) Resolve the image's canonical server name
    resolved_name = _resolve_image_name(repo, IMAGE_NAME)
    assert resolved_name is not None, f"Image not found on server: {IMAGE_NAME}"

    # 3) Determine current board of the image (or uncategorized) and move by target_board_id
    current_board_id = repo.get_image_current_board_id(resolved_name) or "none"
    source_handle = repo.get_board_handle(current_board_id)
    moved = source_handle.move_image_to(resolved_name, target_board_id)
    assert moved, f"Failed to move image {resolved_name} to board id {target_board_id}"

    # 4) Verify by listing images on the target board (authoritative)
    found_via_listing = False
    for _ in range(12):  # wait up to ~6s in 0.5s steps for eventual consistency
        time.sleep(0.5)
        refreshed = repo.get_board_handle(target_board_id)
        names = refreshed.list_images()
        if resolved_name in names:
            found_via_listing = True
            break

    if not found_via_listing:
        meta = repo.get_image_by_name(resolved_name)
        meta_board = meta.board_id if meta else None
        raise AssertionError(
            f"Image {resolved_name} not found in target board listing (id={target_board_id}); metadata board_id={meta_board}"
        )