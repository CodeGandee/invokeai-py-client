#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add local src/ to import path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore

# Configuration
BOARD_NAME = "delete-test"
BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")


def test_delete_board_by_name():
    """
    Delete board(s) named 'delete-test' using the board subsystem.

    Steps:
      1. Connect to InvokeAI at 127.0.0.1:9090 (override via INVOKEAI_BASE_URL).
      2. Locate boards by exact name.
      3. Delete each found board including its images.
      4. Verify deletion by ensuring subsequent lookup returns None.

    APIs exercised:
      - Board discovery by name: see [BoardRepository.get_boards_by_name()](src/invokeai_py_client/board/board_repo.py:152)
      - Board deletion: see [BoardRepository.delete_board()](src/invokeai_py_client/board/board_repo.py:219)
      - Verify deletion via lookup: see [BoardRepository.get_board_by_id()](src/invokeai_py_client/board/board_repo.py:117)
    """
    client = InvokeAIClient.from_url(BASE_URL)
    repo = client.board_repo

    # 1) Find boards with target name
    boards = repo.get_boards_by_name(BOARD_NAME)
    assert boards, f"Board '{BOARD_NAME}' not found"

    # 2) Delete each found board (skip uncategorized/system board protection)
    for b in boards:
        board_id = b.board_id or "none"
        # Safety: never delete the uncategorized/system board
        if board_id == "none":
            continue

        ok = repo.delete_board(board_id, delete_images=True)
        assert ok, f"Failed to delete board id={board_id}"

        # 3) Verify deletion with a brief retry loop for backend consistency
        deleted = False
        for _ in range(6):
            time.sleep(0.5)
            if repo.get_board_by_id(board_id) is None:
                deleted = True
                break
        assert deleted, f"Board still present after deletion id={board_id}"