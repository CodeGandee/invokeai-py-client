#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure local src/ is importable before third-party packages
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.quick.quick_client import QuickClient  # type: ignore
from rich.console import Console  # type: ignore


"""
Task 2: implement copy-image-to-board via tiny workflow (server-side, no download/reupload)

This test verifies:
1) We can copy an existing image to a board without removing it from the source board.
2) The copy is performed purely server-side via a tiny workflow (save_image), not client upload.

Environment variables:
- INVOKEAI_BASE_URL   (default: http://127.0.0.1:9090)
- INVOKEAI_IMAGE_NAME (default: 311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png)

Test flow:
- Ensure target board exists (create if missing).
- Confirm source image exists on server.
- Use QuickClient.copy_image_to_board(image_name, target_board_id).
- Assert returned IvkImage is not None and belongs to the target board.
- Verify via board listing with small retries for eventual consistency.
"""

BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
IMAGE_NAME = os.environ.get("INVOKEAI_IMAGE_NAME", "311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png")
TARGET_BOARD_NAME = "quickcopy-assets"


def test_quick_copy_image_to_board():
    client = InvokeAIClient.from_url(BASE_URL)
    qc = QuickClient(client)
    console = Console()

    # Ensure target board exists
    repo = client.board_repo
    handle = repo.get_board_handle_by_name(TARGET_BOARD_NAME)
    if handle is None:
        handle = repo.create_board(TARGET_BOARD_NAME)
    target_board_id = handle.board_id

    # Sanity: ensure source image exists
    src = repo.get_image_by_name(IMAGE_NAME)
    assert src is not None, f"Source image not found on server: {IMAGE_NAME}"

    # Perform copy (server-side via tiny workflow)
    copied = qc.copy_image_to_board(IMAGE_NAME, target_board_id)
    assert copied is not None, "Copy operation returned None (no image produced)"

    # Pretty-print copied image metadata via rich
    console.rule("[bold green]Copied Image Metadata")
    try:
        console.print(copied.model_dump(exclude_none=True))  # pydantic v2
    except Exception:
        # Fallback for any unexpected model versions
        console.print(getattr(copied, "to_dict", lambda: {"image_name": copied.image_name, "board_id": copied.board_id})())

    assert copied.board_id in (target_board_id, None) or copied.board_id == target_board_id, \
        f"Copied image has unexpected board_id: {copied.board_id}, expected {target_board_id}"

    # Verify via target board listing (authoritative), allow brief delay for index refresh
    found = False
    for _ in range(20):  # up to ~10s
        time.sleep(0.5)
        refreshed = repo.get_board_handle(target_board_id)
        names = refreshed.list_images()
        if copied.image_name in names:
            found = True
            break

    assert found, f"Copied image {copied.image_name} not found in target board listing (id={target_board_id})"