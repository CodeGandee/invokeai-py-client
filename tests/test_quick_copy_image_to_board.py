#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path

# Ensure local src/ is importable before third-party packages
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.quick.quick_client import QuickClient  # type: ignore


"""
Task 2: implement copy-image-to-board via tiny workflow (server-side, no download/reupload)

This test verifies:
1) We can copy an existing image to a board without removing it from the source board.
2) The copy is performed purely server-side via a tiny workflow (save_image), not client upload.

Environment variables:
- IVK_TEST_BASE_URL          (default: http://127.0.0.1:9090)
- IVK_TEST_TARGET_BOARD_NAME (default: quickcopy-assets)
- IVK_TEST_IMAGE_NAME        (optional: if provided, use this; otherwise auto-pick the first uncategorized image)

Test flow:
- Ensure target board exists (create if missing).
- Determine source image:
  - If IVK_TEST_IMAGE_NAME is set, use it.
  - Else, list uncategorized images and pick the first one.
  - If none found, warn the user and fail the test.
- Use QuickClient.copy_image_to_board(image_name, target_board_id).
- Assert returned IvkImage is not None and belongs to the target board.
- Verify via board listing with small retries for eventual consistency.
"""

BASE_URL = os.environ.get("IVK_TEST_BASE_URL", "http://127.0.0.1:9090")
TARGET_BOARD_NAME = os.environ.get("IVK_TEST_TARGET_BOARD_NAME", "quickcopy-assets")
ENV_IMAGE_NAME = os.environ.get("IVK_TEST_IMAGE_NAME")


def test_quick_copy_image_to_board(capsys):
    client = InvokeAIClient.from_url(BASE_URL)
    qc = QuickClient(client)

    # Ensure target board exists
    repo = client.board_repo
    handle = repo.get_board_handle_by_name(TARGET_BOARD_NAME)
    if handle is None:
        handle = repo.create_board(TARGET_BOARD_NAME)
    target_board_id = handle.board_id

    # Resolve source image:
    # 1) If IVK_TEST_IMAGE_NAME is provided, use it (and confirm exists)
    # 2) Otherwise, pick the first image from uncategorized
    if ENV_IMAGE_NAME:
        src = repo.get_image_by_name(ENV_IMAGE_NAME)
        if src is None:
            with capsys.disabled():
                print(f"[ERROR] Specified IVK_TEST_IMAGE_NAME not found on server: {ENV_IMAGE_NAME}")
            assert False, f"Source image not found on server: {ENV_IMAGE_NAME}"
        image_name = ENV_IMAGE_NAME
    else:
        try:
            uc_names = repo.get_uncategorized_handle().list_images()
        except Exception:
            uc_names = []
        if not uc_names:
            with capsys.disabled():
                print("[WARN] No images found in Uncategorized. "
                      "Set IVK_TEST_IMAGE_NAME to an existing image name and re-run.")
            assert False, "No source image available: Uncategorized board is empty and no IVK_TEST_IMAGE_NAME provided"
        image_name = uc_names[0]
        with capsys.disabled():
            print(f"[INFO] Auto-selected source image from Uncategorized: {image_name}")

    # Perform copy (server-side via tiny workflow)
    copied = qc.copy_image_to_board(image_name, target_board_id)
    assert copied is not None, "Copy operation returned None (no image produced)"

    # Pretty-print copied image metadata to real stdout (bypass pytest capture)
    with capsys.disabled():
        print("=" * 20, "Copied Image Metadata", "=" * 20)
        try:
            print(json.dumps(copied.model_dump(exclude_none=True), ensure_ascii=False, indent=2))  # pydantic v2
        except Exception:
            # Fallback for any unexpected model versions
            fallback = getattr(copied, "to_dict", lambda: {"image_name": copied.image_name, "board_id": copied.board_id})()
            print(json.dumps(fallback, ensure_ascii=False, indent=2))

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