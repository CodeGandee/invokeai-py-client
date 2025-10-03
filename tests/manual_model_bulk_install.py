"""
Manual script: scan external model folder and install all models.

Environment
- INVOKE_AI_ENDPOINT: base API URL (e.g., http://localhost:19090/api/v1)
- CONTAINER_EXTERNAL_MODEL_DIR: absolute folder path to scan
- MODEL_INPLACE (optional): '1' to install in-place for local paths (default: 1)
- MODEL_INSTALL_TIMEOUT (optional): per-model timeout seconds (default: 1800)

Behavior
- Scans the folder; for each entry, attempts install via DnnModelRepository.install_model().
- Prints success/failure per model; does not stop on errors.
- Skips entries already reported as installed by the scan.

Usage
- python tests/manual_model_bulk_install.py
"""
from __future__ import annotations

import os
import sys
from typing import Any

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.dnn_model import (
    APIRequestError,
    ModelInstallJobFailed,
    ModelInstallStartError,
    ModelInstallTimeout,
)


def env_bool(name: str, default: bool = True) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v not in {"0", "false", "False", "no", "NO"}


def main() -> int:
    base_url = os.environ.get("INVOKE_AI_ENDPOINT")
    scan_dir = os.environ.get("CONTAINER_EXTERNAL_MODEL_DIR")
    if not base_url:
        print("[SKIP] INVOKE_AI_ENDPOINT not set")
        return 0
    if not scan_dir:
        print("[SKIP] CONTAINER_EXTERNAL_MODEL_DIR not set")
        return 0

    inplace = env_bool("MODEL_INPLACE", True)
    # Per updated guidance: do not treat timeout as failure. We will wait until
    # completion once a job begins processing. Keep env hook but ignore for logic.
    _ = float(os.environ.get("MODEL_INSTALL_TIMEOUT", "1800"))
    effective_timeout = None  # wait indefinitely once processing begins

    print(f"[INFO] endpoint={base_url}")
    print(f"[INFO] scan_dir={scan_dir}")
    print(f"[INFO] inplace={inplace} timeout=indefinite once processing begins")

    client = InvokeAIClient.from_url(base_url)
    repo = client.dnn_model_repo

    try:
        entries: list[Any] = repo.scan_folder(scan_dir)  # type: ignore[assignment]
    except Exception as e:
        print(f"[ERROR] scan_folder failed: {e}")
        return 0

    print(f"[SCAN] {len(entries)} entries")
    total = len(entries)
    success = 0
    failures = 0
    skipped = 0

    for idx, item in enumerate(entries, 1):
        if hasattr(item, "path"):
            path = getattr(item, "path")
            is_installed = bool(getattr(item, "is_installed"))
        elif isinstance(item, dict):
            path = str(item.get("path"))
            is_installed = bool(item.get("is_installed"))
        else:
            print(f"[{idx:03d}/{total}] [SKIP] unexpected entry type: {type(item)!r}")
            skipped += 1
            continue

        if not path:
            print(f"[{idx:03d}/{total}] [SKIP] missing path in entry")
            skipped += 1
            continue

        if is_installed:
            print(f"[{idx:03d}/{total}] [SKIP] already installed: {path}")
            skipped += 1
            continue

        print(f"[{idx:03d}/{total}] [STEP] install: {path}")
        try:
            job = repo.install_model(source=path, inplace=inplace)
            # Client handles all terminal states: completed returns info;
            # error/cancelled raise ModelInstallJobFailed; None timeout means wait indefinitely.
            final = job.wait_until(timeout=effective_timeout, poll_interval=2.0)
            print(f"[{idx:03d}/{total}] [OK] status={final.status} model_key={getattr(final, 'model_key', None)}")
            success += 1
        except ModelInstallStartError as e:
            print(f"[{idx:03d}/{total}] [FAIL] start: {e}")
            failures += 1
        except ModelInstallJobFailed as e:
            info = e.info
            if info is not None:
                print(
                    f"[{idx:03d}/{total}] [FAIL] final_status={info.status} error={info.error or ''} reason={info.error_reason or ''}"
                )
            else:
                print(f"[{idx:03d}/{total}] [FAIL] job failed (no info)")
            failures += 1
        # No timeout handling; we wait until terminal once processing starts
        except APIRequestError as e:
            print(f"[{idx:03d}/{total}] [FAIL] api: {e} (status={getattr(e, 'status_code', None)})")
            failures += 1
        except Exception as e:
            print(f"[{idx:03d}/{total}] [FAIL] unexpected: {e}")
            failures += 1

    print(
        f"[SUMMARY] total={total} success={success} failures={failures} skipped={skipped}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
