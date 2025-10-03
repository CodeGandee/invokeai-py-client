"""
QueueHandle for interacting with a single InvokeAI queue.

This handle exposes queue-scoped queries and actions and constructs
JobHandle instances for queue items.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional, TYPE_CHECKING

import requests

from invokeai_py_client.queue.queue_models import (
    CancelAllExceptCurrentResult,
    ClearResult,
    PruneResult,
    QueueAndProcessorStatus,
    QueueStatus,
    ProcessorStatus,
    QueueItem,
    QueueItemStatus,
)

if TYPE_CHECKING:  # pragma: no cover
    from invokeai_py_client.client import InvokeAIClient
    from invokeai_py_client.queue.job_handle import JobHandle


class QueueHandle:
    """
    Handle for a single queue.

    Construct with `QueueHandle.from_client_and_id()` instead of calling the
    constructor directly.

    Attributes
    ----------
    queue_id : str
        The queue identifier for this handle.
    """

    def __init__(self) -> None:
        """Initialize with default None members; use factory to set state."""
        self.m_client: Optional["InvokeAIClient"] = None
        self.m_queue_id: Optional[str] = None

    @classmethod
    def from_client_and_id(cls, client: "InvokeAIClient", queue_id: str) -> "QueueHandle":
        """
        Factory method to create a handle for the specified queue.

        Parameters
        ----------
        client : InvokeAIClient
            The InvokeAI client.
        queue_id : str
            Queue identifier (usually "default").
        """
        inst = cls()
        inst.m_client = client
        inst.m_queue_id = queue_id
        return inst

    @property
    def queue_id(self) -> str:
        """The queue identifier for this handle."""
        if self.m_queue_id is None:
            raise RuntimeError("QueueHandle not initialized")
        return self.m_queue_id

    # -------------------- Status --------------------
    def get_status(self) -> QueueAndProcessorStatus:
        """
        Get the status of the queue and processor.
        """
        url = f"/queue/{self.queue_id}/status"
        resp = self._client()._make_request("GET", url)
        data = resp.json()
        # Split unknown keys into extra fields
        queue = data.get("queue", {})
        processor = data.get("processor", {})
        q = QueueAndProcessorStatus(
            queue=self._parse_queue_status(queue),
            processor=self._parse_processor_status(processor),
            extra={k: v for k, v in data.items() if k not in {"queue", "processor"}},
        )
        return q

    def is_busy(self) -> bool:
        """
        Check if the queue has pending or running work.
        """
        s = self.get_status()
        return bool(
            s.processor.is_processing or s.queue.in_progress > 0 or s.queue.pending > 0
        )

    def count_running(self) -> int:
        """
        Number of in-progress items in the queue.
        """
        return self.get_status().queue.in_progress

    # -------------------- Listings --------------------
    def list_all(self, destination: str | None = None) -> list[QueueItem]:
        """
        List all queue items, optionally filtered by destination.
        """
        url = f"/queue/{self.queue_id}/list_all"
        params: dict[str, Any] = {}
        if destination is not None:
            params["destination"] = destination
        resp = self._client()._make_request("GET", url, params=params)
        items = resp.json()
        return [self._parse_queue_item(it) for it in items]

    def list_running(self) -> list[QueueItem]:
        """List items with status 'in_progress'."""
        return [it for it in self.list_all() if it.status == QueueItemStatus.IN_PROGRESS]

    def list_pending(self) -> list[QueueItem]:
        """List items with status 'pending'."""
        return [it for it in self.list_all() if it.status == QueueItemStatus.PENDING]

    def get_current(self) -> Optional["JobHandle"]:
        """
        Get the currently executing queue item as a JobHandle.
        Returns None if idle.
        """
        from invokeai_py_client.queue.job_handle import JobHandle

        url = f"/queue/{self.queue_id}/current"
        try:
            resp = self._client()._make_request("GET", url)
        except requests.HTTPError as e:  # pragma: no cover - edge behavior
            if e.response is not None and e.response.status_code == 404:
                return None
            raise
        item = self._parse_queue_item(resp.json())
        h = JobHandle.from_client_ids(self._client(), self.queue_id, item.item_id)
        h.set_item(item)
        return h

    def get_item(self, item_id: int) -> Optional["JobHandle"]:
        """
        Get a JobHandle for the given item id if it exists; otherwise None.
        """
        from invokeai_py_client.queue.job_handle import JobHandle

        url = f"/queue/{self.queue_id}/i/{item_id}"
        try:
            resp = self._client()._make_request("GET", url)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise
        item = self._parse_queue_item(resp.json())
        h = JobHandle.from_client_ids(self._client(), self.queue_id, item_id)
        h.set_item(item)
        return h

    def get_items_by_ids(self, item_ids: list[int]) -> list["JobHandle"]:
        """
        Get JobHandles for the given item ids via the bulk endpoint.
        """
        from invokeai_py_client.queue.job_handle import JobHandle

        if not item_ids:
            return []
        url = f"/queue/{self.queue_id}/items_by_ids"
        resp = self._client()._make_request("POST", url, json={"item_ids": item_ids})
        items = [self._parse_queue_item(it) for it in resp.json()]
        handles: list[JobHandle] = []
        for it in items:
            h = JobHandle.from_client_ids(self._client(), self.queue_id, it.item_id)
            h.set_item(it)
            handles.append(h)
        return handles

    # -------------------- Actions --------------------
    def cancel_all_except_current(self) -> CancelAllExceptCurrentResult:
        """Cancel all queue items except the currently-processing one."""
        url = f"/queue/{self.queue_id}/cancel_all_except_current"
        resp = self._client()._make_request("PUT", url)
        data = resp.json()
        return CancelAllExceptCurrentResult(canceled=data.get("canceled", 0), extra={k: v for k, v in data.items() if k != "canceled"})

    def clear(self) -> ClearResult:
        """Clear the queue, canceling the current item immediately."""
        url = f"/queue/{self.queue_id}/clear"
        resp = self._client()._make_request("PUT", url)
        data = resp.json()
        return ClearResult(deleted=data.get("deleted", 0), extra={k: v for k, v in data.items() if k != "deleted"})

    def prune(self) -> PruneResult:
        """Prune completed or errored items from the queue."""
        url = f"/queue/{self.queue_id}/prune"
        resp = self._client()._make_request("PUT", url)
        data = resp.json()
        return PruneResult(deleted=data.get("deleted", 0), extra={k: v for k, v in data.items() if k != "deleted"})

    # -------------------- Utilities --------------------
    def wait_until_idle(self, timeout: float = 300.0, poll_interval: float = 1.0) -> bool:
        """
        Wait until the queue is idle or until timeout.

        Returns
        -------
        bool
            True if idle; False if timeout elapsed.
        """
        deadline = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < deadline:
            if not self.is_busy():
                return True
            import time

            time.sleep(poll_interval)
        return False

    # -------------------- Private helpers --------------------
    def _client(self) -> "InvokeAIClient":
        if self.m_client is None:
            raise RuntimeError("QueueHandle not initialized")
        return self.m_client

    @staticmethod
    def _parse_queue_status(data: dict[str, Any]) -> QueueStatus:
        extra_keys = {
            k for k in data.keys() if k not in {
                "queue_id",
                "item_id",
                "batch_id",
                "session_id",
                "pending",
                "in_progress",
                "completed",
                "failed",
                "canceled",
                "total",
            }
        }
        return QueueStatus(
            queue_id=data.get("queue_id", "default"),
            item_id=data.get("item_id"),
            batch_id=data.get("batch_id"),
            session_id=data.get("session_id"),
            pending=int(data.get("pending", 0)),
            in_progress=int(data.get("in_progress", 0)),
            completed=int(data.get("completed", 0)),
            failed=int(data.get("failed", 0)),
            canceled=int(data.get("canceled", 0)),
            total=int(data.get("total", 0)),
            extra={k: data[k] for k in extra_keys},
        )

    @staticmethod
    def _parse_processor_status(data: dict[str, Any]) -> ProcessorStatus:
        extra_keys = {k for k in data.keys() if k not in {"is_started", "is_processing"}}
        return ProcessorStatus(
            is_started=bool(data.get("is_started", False)),
            is_processing=bool(data.get("is_processing", False)),
            extra={k: data[k] for k in extra_keys},
        )

    @staticmethod
    def _parse_queue_item(data: dict[str, Any]) -> QueueItem:
        # Let Pydantic parse and coerce datetimes for known fields; stash unknowns in extra
        known_keys = {
            "item_id",
            "status",
            "priority",
            "batch_id",
            "queue_id",
            "origin",
            "destination",
            "session_id",
            "error_type",
            "error_message",
            "error_traceback",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
            "field_values",
            "published_workflow_id",
            "credits",
            "session",
            "workflow",
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}
        item = QueueItem(**{k: v for k, v in data.items() if k in known_keys}, extra=extra)
        return item
