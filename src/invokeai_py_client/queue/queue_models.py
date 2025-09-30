"""
Queue and Job Pydantic models for InvokeAI API (v6.8).

Strongly-typed representations of queue status and items, with `extra` fields
to capture unknown keys for forward compatibility.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProcessorStatus(BaseModel):
    """
    Status of the session processor.

    Attributes
    ----------
    is_started : bool
        Whether the session processor is started.
    is_processing : bool
        Whether a session is being processed.
    extra : dict[str, Any]
        Unrecognized fields returned by the API.
    """

    is_started: bool = Field(..., description="Whether the session processor is started")
    is_processing: bool = Field(..., description="Whether a session is being processed")
    extra: dict[str, Any] = Field(default_factory=dict, description="Unknown fields")


class QueueStatus(BaseModel):
    """
    Status and counts of a single queue.

    Attributes
    ----------
    queue_id : str
        The ID of the queue.
    item_id : int | None
        The current queue item id.
    batch_id : str | None
        The current queue item's batch id.
    session_id : str | None
        The current queue item's session id.
    pending : int
        Number of queue items with status 'pending'.
    in_progress : int
        Number of queue items with status 'in_progress'.
    completed : int
        Number of queue items with status 'completed'.
    failed : int
        Number of queue items with status 'failed'.
    canceled : int
        Number of queue items with status 'canceled'.
    total : int
        Total number of queue items.
    extra : dict[str, Any]
        Unrecognized fields from the API.
    """

    queue_id: str
    item_id: Optional[int] = None
    batch_id: Optional[str] = None
    session_id: Optional[str] = None
    pending: int
    in_progress: int
    completed: int
    failed: int
    canceled: int
    total: int
    extra: dict[str, Any] = Field(default_factory=dict, description="Unknown fields")


class QueueAndProcessorStatus(BaseModel):
    """
    Combined status of queue and processor.
    """

    queue: QueueStatus
    processor: ProcessorStatus
    extra: dict[str, Any] = Field(default_factory=dict)


class ImageFieldRef(BaseModel):
    """
    Image field reference.
    """

    image_name: str
    extra: dict[str, Any] = Field(default_factory=dict)


class QueueItemStatus(str, Enum):
    """
    API queue item status values.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class NodeFieldValue(BaseModel):
    """
    Node field override value associated with a queue item.
    """

    node_path: str
    field_name: str
    value: str | int | float | ImageFieldRef
    extra: dict[str, Any] = Field(default_factory=dict)


class QueueItem(BaseModel):
    """
    Session queue item (condensed), based on SessionQueueItem from OpenAPI.
    """

    item_id: int
    status: QueueItemStatus
    priority: int = 0
    batch_id: str
    queue_id: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    session_id: str

    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    field_values: Optional[list[NodeFieldValue]] = None
    published_workflow_id: Optional[str] = None
    credits: Optional[float] = None

    # Heavy fields - left as untyped dicts for now
    session: Optional[dict[str, Any]] = None
    workflow: Optional[dict[str, Any]] = None

    extra: dict[str, Any] = Field(default_factory=dict)


class CancelAllExceptCurrentResult(BaseModel):
    """
    Result of canceling all items except the current one.
    """

    canceled: int
    extra: dict[str, Any] = Field(default_factory=dict)


class ClearResult(BaseModel):
    """
    Result of clearing the queue.
    """

    deleted: int
    extra: dict[str, Any] = Field(default_factory=dict)


class PruneResult(BaseModel):
    """
    Result of pruning completed/errored queue items.
    """

    deleted: int
    extra: dict[str, Any] = Field(default_factory=dict)

