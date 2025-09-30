"""
QueueRepository: entry point for queue access in InvokeAI client.

Provides discovery and returns QueueHandle instances. Queue-scoped
operations are performed on QueueHandle; this repository does not
duplicate that functionality.
"""

from __future__ import annotations

from typing import Optional

from invokeai_py_client.queue.queue_handle import QueueHandle

if False:  # TYPE_CHECKING guard
    from invokeai_py_client.client import InvokeAIClient  # pragma: no cover


class QueueRepository:
    """
    Repository for queue discovery and handle construction.

    Use `QueueRepository.from_client()` to construct.
    """

    def __init__(self) -> None:
        self.m_client: Optional["InvokeAIClient"] = None

    @classmethod
    def from_client(cls, client: "InvokeAIClient") -> "QueueRepository":
        inst = cls()
        inst.m_client = client
        return inst

    def list_queues(self) -> list[str]:
        """
        List available queue identifiers.

        Notes
        -----
        As of v6.8, InvokeAI does not expose a queue listing endpoint.
        We conservatively return ["default"].
        """
        return ["default"]

    def get_queue(self, queue_id: str = "default") -> QueueHandle:
        """
        Get a handle for the specified queue.
        """
        return QueueHandle.from_client_and_id(self._client(), queue_id)

    # -------------------- Private helpers --------------------
    def _client(self) -> "InvokeAIClient":
        if self.m_client is None:
            raise RuntimeError("QueueRepository not initialized")
        return self.m_client

