#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make local src importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invokeai_py_client import InvokeAIClient  # type: ignore


BASE_URL = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090")
IMAGE_NAME = "61fd1c0e-5af0-4fbf-b62c-e168c2b13ea8.png"


def resolve_exact_image_name(client: InvokeAIClient, rough_name: str) -> str | None:
    # Try exact DTO
    try:
        r = client._make_request("GET", f"/images/i/{rough_name}")
        if r.status_code == 200:
            return rough_name
    except Exception:
        pass

    # Try without extension
    stem = rough_name.rsplit(".", 1)[0] if "." in rough_name else rough_name
    if stem != rough_name:
        try:
            r = client._make_request("GET", f"/images/i/{stem}")
            if r.status_code == 200:
                return stem
        except Exception:
            pass

    # Try listing uncategorized image names (board_id="none")
    try:
        rlist = client._make_request("GET", "/boards/none/image_names")
        names = rlist.json()
        if isinstance(names, list):
            # exact first
            for n in names:
                if n == rough_name or n == stem:
                    return n
            # prefix fallback
            for n in names:
                if n.startswith(stem):
                    return n
    except Exception:
        pass

    return None


def main() -> int:
    client = InvokeAIClient.from_url(BASE_URL)
    board = client.board_repo.get_uncategorized_handle()

    exact = resolve_exact_image_name(client, IMAGE_NAME)
    if not exact:
        # 1) image does not exist: raise error with reason
        print(f"[ERROR] image not found: {IMAGE_NAME}")
        raise SystemExit(1)

    # Pre-check: confirm it exists to distinguish other errors later
    try:
        pre = client._make_request("GET", f"/images/i/{exact}")
        pre_exists = pre.status_code == 200
    except Exception as e:
        # connection or other failure during existence check
        print(f"[ERROR] failed to verify existence: {e}")
        raise SystemExit(2)

    if not pre_exists:
        print(f"[ERROR] image not found: {exact}")
        raise SystemExit(1)

    # Attempt delete via board subsystem
    try:
        ok = board.delete_image(exact)
    except Exception as e:
        # 2) deletion fails due to other error or lost connection
        print(f"[ERROR] delete failed: {e}")
        raise SystemExit(2)

    if ok:
        # 3) Successfully deleted
        print(f"[OK] deleted image: {exact}")
        return 0

    # Not deleted - try to see if it still exists to categorize error
    try:
        post = client._make_request("GET", f"/images/i/{exact}")
        still_exists = post.status_code == 200
    except Exception as e:
        print(f"[ERROR] delete may have failed; connection issue verifying state: {e}")
        raise SystemExit(2)

    if still_exists:
        print(f"[ERROR] delete reported no deletion and image still exists: {exact} (unknown error)")
        raise SystemExit(2)

    # If it doesn't exist but server didn't report deletion, treat as success-false case
    # Return False (exit code 3 to indicate false/no-op deletion)
    print(f"[WARN] image already absent (no-op): {exact}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())