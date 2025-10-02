"""
Typed models and job handle for DNN model management (v2 model_manager endpoints).

These are intentionally lightweight and forward-compatible: unknown fields
from upstream are captured in `extra` dicts to avoid breaking changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from invokeai_py_client.dnn_model.dnn_model_types import BaseDnnModelType, DnnModelType


class InstallJobStatus(str, Enum):
    """
    Status values for model install jobs.
    Mirrors upstream values from InvokeAI's ModelInstallJob.
    """

    WAITING = "waiting"
    DOWNLOADING = "downloading"
    DOWNLOADS_DONE = "downloads_done"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ModelInstJobInfo(BaseModel):
    """
    Minimal info for a model install job.
    """

    id: int
    status: InstallJobStatus

    # Error and progress info
    error: Optional[str] = None
    error_reason: Optional[str] = None
    error_traceback: Optional[str] = None
    bytes: Optional[int] = None
    total_bytes: Optional[int] = None

    # Resulting model key (if available)
    model_key: Optional[str] = None

    # Timestamps (best-effort, upstream may not include)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    extra: dict[str, Any] = Field(default_factory=dict)


class ModelManagerStats(BaseModel):
    """
    Model manager RAM cache performance statistics. Upstream may return null.
    """

    hit_rate: Optional[float] = None
    miss_rate: Optional[float] = None
    ram_used_mb: Optional[float] = None
    ram_capacity_mb: Optional[float] = None
    loads: Optional[int] = None
    evictions: Optional[int] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class HFLoginStatus(str, Enum):
    """
    HuggingFace login token status, per upstream.
    """

    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class FoundModel(BaseModel):
    """Scan result item for `scan_folder` endpoint."""

    path: str
    is_installed: bool
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelInstallConfig(BaseModel):
    """
    Typed wrapper for upstream `ModelRecordChanges` body.
    All fields are optional; passing an empty dict accepts server defaults.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    base: Optional[BaseDnnModelType] = None
    type: Optional[DnnModelType] = None
    path: Optional[str] = None
    format: Optional[str] = None
    prediction_type: Optional[str] = None
    upcast_attention: Optional[bool] = None
    trigger_phrases: Optional[list[str]] = None
    default_settings: Optional[dict[str, Any]] = None
    variant: Optional[str] = None
    config_path: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_record_changes(self) -> dict[str, Any]:
        body = self.model_dump(exclude_none=True)
        extra = body.pop("extra", {})
        body.update(extra)
        return body


@dataclass
class _V2Endpoint:
    """Utility constants for v2 endpoints."""

    INSTALL_BASE: str = "/models/install"
    INSTALL_BY_ID: str = "/models/install/{id}"
    INSTALL_HF: str = "/models/install/huggingface"
    CONVERT: str = "/models/convert/{key}"
    MODEL_BY_KEY: str = "/models/i/{key}"
    STATS: str = "/models/stats"
    EMPTY_CACHE: str = "/models/empty_model_cache"
    HF_LOGIN: str = "/models/hf_login"
    SCAN_FOLDER: str = "/models/scan_folder"

