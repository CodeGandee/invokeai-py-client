"""
JobHandle for interacting with a single InvokeAI queue item.

Provides refresh, status helpers, cancel, and wait-for-completion.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

import requests

from invokeai_py_client.queue.queue_models import QueueItem, QueueItemStatus

if TYPE_CHECKING:  # pragma: no cover
    from invokeai_py_client.client import InvokeAIClient


class JobHandle:
    """
    Handle for a single queue item (job).

    Construct with `JobHandle.from_client_ids()` instead of calling the
    constructor directly.
    """

    def __init__(self) -> None:
        self.m_client: Optional["InvokeAIClient"] = None
        self.m_queue_id: Optional[str] = None
        self.m_item_id: Optional[int] = None
        self.m_item: Optional[QueueItem] = None

    @classmethod
    def from_client_ids(
        cls, client: "InvokeAIClient", queue_id: str, item_id: int
    ) -> "JobHandle":
        inst = cls()
        inst.m_client = client
        inst.m_queue_id = queue_id
        inst.m_item_id = item_id
        return inst

    # -------------------- Read-only properties --------------------
    @property
    def queue_id(self) -> str:
        if self.m_queue_id is None:
            raise RuntimeError("JobHandle not initialized")
        return self.m_queue_id

    @property
    def item_id(self) -> int:
        if self.m_item_id is None:
            raise RuntimeError("JobHandle not initialized")
        return self.m_item_id

    @property
    def item(self) -> Optional[QueueItem]:
        return self.m_item

    # -------------------- Mutators for internal state --------------------
    def set_item(self, item: QueueItem) -> None:
        """Set cached item payload."""
        self.m_item = item

    # -------------------- API helpers --------------------
    def refresh(self) -> QueueItem:
        """
        Refresh this job's data from the API and update cache.
        """
        url = f"/queue/{self.queue_id}/i/{self.item_id}"
        resp = self._client()._make_request("GET", url)
        data = resp.json()
        # Reuse QueueHandle's parsing routine by importing lazily
        from invokeai_py_client.queue.queue_handle import QueueHandle

        item = QueueHandle._parse_queue_item(data)  # type: ignore[attr-defined]
        self.m_item = item
        return item

    def status(self) -> QueueItemStatus:
        """Get the current status (refreshes if cache is empty)."""
        if self.m_item is None:
            self.refresh()
        assert self.m_item is not None  # for type checker
        return self.m_item.status

    def is_pending(self) -> bool:
        return self.status() == QueueItemStatus.PENDING

    def is_running(self) -> bool:
        return self.status() == QueueItemStatus.IN_PROGRESS

    def is_complete(self) -> bool:
        return self.status() in {
            QueueItemStatus.COMPLETED,
            QueueItemStatus.FAILED,
            QueueItemStatus.CANCELED,
        }

    def is_successful(self) -> bool:
        return self.status() == QueueItemStatus.COMPLETED

    def is_failed(self) -> bool:
        return self.status() == QueueItemStatus.FAILED

    def is_canceled(self) -> bool:
        return self.status() == QueueItemStatus.CANCELED

    def cancel(self) -> bool:
        """
        Cancel this job. Uses PUT per OpenAPI; falls back to DELETE for older servers.
        """
        url = f"/queue/{self.queue_id}/i/{self.item_id}/cancel"
        try:
            resp = self._client()._make_request("PUT", url)
            return bool(resp.status_code == 200)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 405):
                # Try DELETE on legacy behavior
                resp2 = self._client()._make_request("DELETE", url)
                return bool(resp2.status_code == 200)
            raise

    def wait_for_completion(self, timeout: float = 300.0, poll_interval: float = 1.0) -> QueueItem:
        """
        Poll until the job reaches a terminal state or timeout is reached.
        """
        deadline = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < deadline:
            item = self.refresh()
            if item.status in {
                QueueItemStatus.COMPLETED,
                QueueItemStatus.FAILED,
                QueueItemStatus.CANCELED,
            }:
                return item
            import time

            time.sleep(poll_interval)
        # One last refresh so caller gets final state as of timeout
        return self.refresh()

    # -------------------- Private helpers --------------------
    def _client(self) -> "InvokeAIClient":
        if self.m_client is None:
            raise RuntimeError("JobHandle not initialized")
        return self.m_client
