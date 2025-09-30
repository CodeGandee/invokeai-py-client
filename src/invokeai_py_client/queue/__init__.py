"""
Queue subsystem for InvokeAI client using repository/handle pattern.

This package provides queue and job management functionality:

Classes
-------
QueueRepository
    Entry point for queue discovery and access to queue handles.

QueueHandle
    Represents a single queue (by id). Exposes queue-scoped queries and actions.

JobHandle
    Represents a single queue item (job) within a queue. Exposes job-scoped
    queries and actions like refresh, wait, cancel.
"""

from invokeai_py_client.queue.queue_repo import QueueRepository
from invokeai_py_client.queue.queue_handle import QueueHandle
from invokeai_py_client.queue.job_handle import JobHandle

__all__ = [
    "QueueRepository",
    "QueueHandle",
    "JobHandle",
]

