#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path

# Ensure local src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore
from invokeai_py_client.quick.quick_client import QuickClient  # type: ignore

# Configuration via environment variables
BASE_URL = os.environ.get("IVK_TEST_BASE_URL", "http://127.0.0.1:9090")
BOARD_NAME = os.environ.get("IVK_TEST_SDXL_BOARD_NAME")  # optional GUI-visible name
MODEL_HINT = os.environ.get("IVK_TEST_SDXL_MODEL_HINT")  # optional substring to select model
SCHEDULER = os.environ.get("IVK_TEST_SDXL_SCHEDULER")    # optional scheduler name (e.g., 'euler')
_steps = os.environ.get("IVK_TEST_SDXL_STEPS")
try:
    STEPS = int(_steps) if _steps is not None else None
except Exception:
    STEPS = None

POSITIVE_PROMPT = os.environ.get(
    "IVK_TEST_SDXL_POSITIVE",
    "A futuristic city skyline with flying cars, cyberpunk aesthetic, neon lights, detailed architecture",
)
NEGATIVE_PROMPT = os.environ.get(
    "IVK_TEST_SDXL_NEGATIVE",
    "blurry, low quality, distorted, ugly",
)
WIDTH = int(os.environ.get("IVK_TEST_SDXL_WIDTH", "1024"))
HEIGHT = int(os.environ.get("IVK_TEST_SDXL_HEIGHT", "1024"))


def _ensure_board_id(repo, board_name: str | None) -> str:
    """Return a valid board_id. If board_name is provided, ensure it exists and return its id; else 'none'."""
    if not board_name:
        return "none"
    handle = repo.get_board_handle_by_name(board_name)
    if handle is None:
        handle = repo.create_board(board_name)
    return handle.board_id


def test_quick_sdxl_text_to_image(capsys):
    client = InvokeAIClient.from_url(BASE_URL)
    qc = QuickClient(client)

    repo = client.board_repo
    board_id = _ensure_board_id(repo, BOARD_NAME)

    # Execute generation
    img = qc.generate_image_sdxl_t2i(
        positive_prompt=POSITIVE_PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        width=WIDTH,
        height=HEIGHT,
        steps=STEPS,
        model_name=MODEL_HINT,
        scheduler=SCHEDULER,
        board_id=board_id,
    )
    assert img is not None, "Generation returned None (canceled or no outputs)"

    # Print metadata to real stdout
    with capsys.disabled():
        print("=" * 20, "Generated Image Metadata", "=" * 20)
        try:
            print(json.dumps(img.model_dump(exclude_none=True), ensure_ascii=False, indent=2))  # pydantic v2
        except Exception:
            fallback = getattr(img, "to_dict", lambda: {"image_name": img.image_name, "board_id": getattr(img, "board_id", None)})()
            print(json.dumps(fallback, ensure_ascii=False, indent=2))

    # Verify presence in target board (or Uncategorized)
    if board_id == "none":
        handle = repo.get_uncategorized_handle()
    else:
        handle = repo.get_board_handle(board_id)

    found = False
    for _ in range(20):  # ~10s
        time.sleep(0.5)
        names = handle.list_images()
        if img.image_name in names:
            found = True
            break

    assert found, f"Generated image {img.image_name} not found in board listing (board_id={board_id})"