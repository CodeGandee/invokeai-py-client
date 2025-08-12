"""Lightweight data models used by the client API.

These are simple containers (dataclasses-like) that describe data exchanged
with the InvokeAI backend, such as jobs and assets.

All fields are intentionally minimal and can be extended during implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class JobState(str, Enum):
    """Enumeration of job states as exposed by the client.

    The values are stringly-typed to ease JSON serialization.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class JobInfo:
    """Metadata about a job submitted to InvokeAI.

    Parameters
    ----------
    id : str
        Unique job identifier assigned by the server.
    state : JobState
        The current state of the job.
    created_at : Optional[str]
        ISO timestamp when the job was created, if known.
    updated_at : Optional[str]
        ISO timestamp when the job last changed state, if known.
    error : Optional[str]
        Error message if the job failed.
    extra : Dict[str, Any]
        Arbitrary extra metadata returned by the server.
    """

    id: str
    state: JobState
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None
    extra: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}


@dataclass
class AssetInfo:
    """Information about an asset stored in InvokeAI (e.g., image).

    Parameters
    ----------
    name : str
        The asset's identifier/name in the backend.
    kind : str
        A simple discriminator for asset kind (e.g., "image").
    size_bytes : Optional[int]
        Asset size if known.
    metadata : Dict[str, Any]
        Additional metadata.
    """

    name: str
    kind: str
    size_bytes: Optional[int] = None
    metadata: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BoardInfo:
    """Simple representation of a board (InvokeAI concept).

    Parameters
    ----------
    id : str
        Unique board identifier.
    name : str
        Human-friendly board name.
    """

    id: str
    name: str
