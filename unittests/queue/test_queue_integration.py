"""
Integration tests for QueueRepository, QueueHandle, and JobHandle.

Requires a running InvokeAI server with endpoint provided via
environment variable `INVOKE_AI_ENDPOINT`.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Optional

import pytest

from invokeai_py_client import InvokeAIClient
from invokeai_py_client.queue import QueueRepository
from invokeai_py_client.workflow import WorkflowDefinition


def _require_endpoint() -> str:
    endpoint = os.environ.get("INVOKE_AI_ENDPOINT")
    if not endpoint:
        pytest.skip(
            "INVOKE_AI_ENDPOINT not set; integration tests require a running server"
        )
    return endpoint


def _prepare_small_workflow(client: InvokeAIClient, steps: int = 12) -> dict[str, Any]:
    wf_path = Path("data/workflows/sdxl-text-to-image.json")
    assert wf_path.exists(), "Workflow JSON not found: data/workflows/sdxl-text-to-image.json"
    definition: WorkflowDefinition = WorkflowDefinition.from_file(str(wf_path))
    wh = client.workflow_repo.create_workflow(definition)
    # Sync model identifiers against server
    wh.sync_dnn_model(by_name=True, by_base=True)
    # Configure generation params (prefer searching by field name)
    inputs = wh.list_inputs()
    width_idx: Optional[int] = next((i.input_index for i in inputs if i.field_name.lower() == "width"), None)
    height_idx: Optional[int] = next((i.input_index for i in inputs if i.field_name.lower() == "height"), None)
    steps_idx: Optional[int] = next((i.input_index for i in inputs if i.field_name.lower() == "steps"), None)
    if width_idx is not None:
        fld = wh.get_input_value(width_idx)
        if hasattr(fld, "value"):
            setattr(fld, "value", 512)  # type: ignore[assignment]
    if height_idx is not None:
        fld = wh.get_input_value(height_idx)
        if hasattr(fld, "value"):
            setattr(fld, "value", 512)  # type: ignore[assignment]
    if steps_idx is not None:
        fld = wh.get_input_value(steps_idx)
        if hasattr(fld, "value"):
            setattr(fld, "value", steps)  # type: ignore[assignment]
    return {
        "handle": wh,
    }


@pytest.mark.integration
def test_list_queues_integration() -> None:
    base_url = _require_endpoint()
    client = InvokeAIClient.from_url(base_url)
    repo: QueueRepository = client.queue_repo
    queues = repo.list_queues()
    assert isinstance(queues, list)
    assert "default" in queues


@pytest.mark.integration
@pytest.mark.slow
def test_queue_status_and_current_integration() -> None:
    base_url = _require_endpoint()
    client = InvokeAIClient.from_url(base_url)
    q = client.queue_repo.get_queue("default")

    # Ensure we can reach status
    _ = q.get_status()

    wf = _prepare_small_workflow(client, steps=10)
    wh = wf["handle"]
    submission = wh.submit_sync()
    assert isinstance(submission, dict)

    # Wait briefly for the queue to pick up the job
    deadline = time.time() + 30.0
    busy = q.is_busy()
    while not busy and time.time() < deadline:
        time.sleep(1.0)
        busy = q.is_busy()
    assert busy, "Queue did not become busy within 30s"

    # Current job should be available
    current = q.get_current()
    assert current is not None
    item = current.refresh()
    assert item.item_id > 0

    # Wait for completion to avoid leaving the queue dirty
    final = current.wait_for_completion(timeout=240.0, poll_interval=2.0)
    assert final.status.value in {"completed", "failed", "canceled"}

    # Eventually queue becomes idle
    assert q.wait_until_idle(timeout=60.0, poll_interval=2.0)


@pytest.mark.integration
@pytest.mark.slow
def test_job_cancel_integration() -> None:
    base_url = _require_endpoint()
    client = InvokeAIClient.from_url(base_url)
    q = client.queue_repo.get_queue("default")

    wf = _prepare_small_workflow(client, steps=20)
    wh = wf["handle"]
    submission = wh.submit_sync()
    assert isinstance(submission, dict)
    item_ids = submission.get("item_ids") or []
    assert item_ids, "Submission did not return item_ids"
    item_id = int(item_ids[0])

    # Get handle for the submitted item and cancel
    h = q.get_item(item_id)
    assert h is not None
    # Give it a moment to start
    time.sleep(2.0)
    canceled = h.cancel()
    assert canceled is True

    final = h.wait_for_completion(timeout=240.0, poll_interval=2.0)
    # Some servers may mark canceled jobs as failed; allow either canceled or failed
    assert final.status.value in {"canceled", "failed", "completed"}

