"""
Model manager exceptions for DNN model operations.

These exceptions are used to avoid leaking HTTP/requests errors to users of the
client. They provide structured information where relevant.
"""

from __future__ import annotations

from typing import Any


class InvokeAIClientError(Exception):
    """Base exception for InvokeAI client failures."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:  # noqa: D401
        super().__init__(message)
        self.message = message
        self.details = details or {}


class APIRequestError(InvokeAIClientError):
    """Wraps HTTP errors with status code and response payload, if available."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.status_code = status_code
        self.payload = payload


class ModelManagerError(InvokeAIClientError):
    """Base exception for model manager operations."""


class ModelInstallStartError(ModelManagerError):
    """Raised when an install job cannot be created (API rejects install)."""


class ModelInstallJobFailed(ModelManagerError):
    """Raised when an install job ends in a failure/cancelled state."""

    def __init__(self, message: str, *, info: Any | None = None) -> None:  # info is ModelInstJobInfo
        super().__init__(message)
        self.info = info


class ModelInstallTimeout(ModelManagerError):
    """Raised when waiting for an install job completion times out."""

    def __init__(self, message: str, *, last_info: Any | None = None, timeout: float | None = None) -> None:
        super().__init__(message)
        self.last_info = last_info
        self.timeout = timeout
