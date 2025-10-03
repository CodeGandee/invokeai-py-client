"""
Typed models and job handle for DNN model management (v2 model_manager endpoints).

These are intentionally lightweight and forward-compatible: unknown fields
from upstream are captured in `extra` dicts to avoid breaking changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

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
    error: str | None = None
    error_reason: str | None = None
    error_traceback: str | None = None
    bytes: int | None = None
    total_bytes: int | None = None

    # Resulting model key (if available)
    model_key: str | None = None

    # Timestamps (best-effort, upstream may not include)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    extra: dict[str, Any] = Field(default_factory=dict)


class ModelManagerStats(BaseModel):
    """
    Model manager RAM cache performance statistics. Upstream may return null.
    """

    hit_rate: float | None = None
    miss_rate: float | None = None
    ram_used_mb: float | None = None
    ram_capacity_mb: float | None = None
    loads: int | None = None
    evictions: int | None = None
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

    name: str | None = None
    description: str | None = None
    base: BaseDnnModelType | None = None
    type: DnnModelType | None = None
    path: str | None = None
    format: str | None = None
    prediction_type: str | None = None
    upcast_attention: bool | None = None
    trigger_phrases: list[str] | None = None
    default_settings: dict[str, Any] | None = None
    variant: str | None = None
    config_path: str | None = None
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
