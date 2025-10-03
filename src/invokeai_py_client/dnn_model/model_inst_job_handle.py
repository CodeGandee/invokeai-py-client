"""
ModelInstJobHandle: handle for a single model install job.

Provides refresh, status helpers, cancel, and wait-for-completion.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

import requests

from invokeai_py_client.dnn_model.dnn_model_models import (
    InstallJobStatus,
    ModelInstJobInfo,
    _V2Endpoint,
)
from invokeai_py_client.dnn_model.dnn_model_exceptions import (
    APIRequestError,
    ModelInstallJobFailed,
    ModelInstallTimeout,
)

if TYPE_CHECKING:  # pragma: no cover
    from invokeai_py_client.client import InvokeAIClient


class ModelInstJobHandle:
    """
    Handle for a single model install job.

    Construct via repository methods; do not instantiate directly.
    """

    def __init__(self) -> None:
        self._client: InvokeAIClient | None = None
        self._job_id: int | None = None
        self._info: ModelInstJobInfo | None = None

    @classmethod
    def from_client_and_id(cls, client: InvokeAIClient, job_id: int) -> ModelInstJobHandle:
        inst = cls()
        inst._client = client
        inst._job_id = job_id
        return inst

    # -------------------- Properties --------------------
    @property
    def job_id(self) -> int:
        if self._job_id is None:
            raise RuntimeError("ModelInstJobHandle not initialized")
        return self._job_id

    @property
    def info(self) -> ModelInstJobInfo | None:
        return self._info

    # -------------------- API helpers --------------------
    def refresh(self) -> ModelInstJobInfo:
        """Fetch latest job info and cache it."""
        # If we have a synthetic terminal info (e.g., already installed), return it
        if self._info is not None and self._info.status in {
            InstallJobStatus.COMPLETED,
            InstallJobStatus.ERROR,
            InstallJobStatus.CANCELLED,
        } and (self._job_id is None or self._job_id < 0):
            return self._info

        url = _V2Endpoint.INSTALL_BY_ID.format(id=self.job_id)
        try:
            resp = self._client_v2("GET", url)
        except requests.HTTPError as e:  # pragma: no cover
            raise self._to_api_error(e) from e
        data = resp.json()
        self._info = self._parse_job_info(data)
        return self._info

    def status(self) -> InstallJobStatus:
        if self._info is None:
            self.refresh()
        assert self._info is not None
        return self._info.status

    def is_done(self) -> bool:
        s = self.status()
        return s in {InstallJobStatus.COMPLETED, InstallJobStatus.ERROR, InstallJobStatus.CANCELLED}

    def is_failed(self) -> bool:
        return self.status() == InstallJobStatus.ERROR

    def progress(self) -> float | None:
        if self._info is None:
            self.refresh()
        assert self._info is not None
        if self._info.bytes is None or self._info.total_bytes is None or self._info.total_bytes == 0:
            return None
        return float(self._info.bytes) / float(self._info.total_bytes)

    def cancel(self) -> bool:
        """Cancel the install job."""
        url = _V2Endpoint.INSTALL_BY_ID.format(id=self.job_id)
        try:
            resp = self._client_v2("DELETE", url)
            return bool(resp.status_code in (200, 201, 204))
        except requests.HTTPError as e:  # pragma: no cover - depends on server behavior
            if e.response is not None and e.response.status_code in (404, 415):
                return False
            raise self._to_api_error(e) from e

    def wait_until(self, timeout: float | None = 600.0, poll_interval: float = 2.0) -> ModelInstJobInfo:
        """Wait until the job reaches a terminal state or timeout elapses.

        When `timeout` is None, wait indefinitely.
        Raises ModelInstallJobFailed on failure/cancelled, ModelInstallTimeout on timeout.
        """
        start = datetime.now()
        deadline = None if timeout is None else (start + timedelta(seconds=timeout))
        last_info: ModelInstJobInfo | None = None
        while True:
            # If we already know the terminal state, short-circuit
            if self._info is not None and self._info.status in {
                InstallJobStatus.COMPLETED,
                InstallJobStatus.ERROR,
                InstallJobStatus.CANCELLED,
            }:
                info = self._info
                if info.status == InstallJobStatus.COMPLETED:
                    return info
                raise ModelInstallJobFailed(
                    f"install job {self.job_id} ended with status={info.status}", info=info
                )
            info = self.refresh()
            last_info = info
            if info.status in {InstallJobStatus.COMPLETED, InstallJobStatus.ERROR, InstallJobStatus.CANCELLED}:
                if info.status == InstallJobStatus.COMPLETED:
                    return info
                raise ModelInstallJobFailed(
                    f"install job {self.job_id} ended with status={info.status}", info=info
                )
            import time

            time.sleep(poll_interval)
            if deadline is not None and datetime.now() >= deadline:
                raise ModelInstallTimeout(
                    f"install job {self.job_id} timed out after {timeout}s", last_info=last_info, timeout=timeout
                )

    # Backward compatible alias
    def wait(self, timeout: float | None = 600.0, poll_interval: float = 2.0) -> ModelInstJobInfo:  # pragma: no cover
        return self.wait_until(timeout=timeout, poll_interval=poll_interval)

    def raise_if_failed(self) -> None:
        """Raise ModelInstallJobFailed if the job is failed/cancelled."""
        info = self.refresh() if self._info is None else self._info
        assert info is not None
        if info.status in {InstallJobStatus.ERROR, InstallJobStatus.CANCELLED}:
            raise ModelInstallJobFailed(
                f"install job {self.job_id} ended with status={info.status}", info=info
            )

    # -------------------- Private helpers --------------------
    def _client_v2(self, method: str, endpoint: str, **kwargs):
        if self._client is None:
            raise RuntimeError("ModelInstJobHandle not initialized")
        return self._client._make_request_v2(method, endpoint, **kwargs)

    @staticmethod
    def _parse_job_info(data: dict) -> ModelInstJobInfo:
        # Extract known fields and stash the rest as extra
        status_raw = str(data.get("status", "waiting"))
        try:
            status = InstallJobStatus(status_raw)
        except Exception:
            # Unknown value, map to ERROR-like terminal state to avoid infinite waits
            status = InstallJobStatus.ERROR

        model_key: str | None = None
        cfg_out = data.get("config_out") or {}
        if isinstance(cfg_out, dict):
            mk = cfg_out.get("key")
            if isinstance(mk, str):
                model_key = mk

        known = {
            "id": int(data.get("id", 0)),
            "status": status,
            "error": data.get("error"),
            "error_reason": data.get("error_reason"),
            "error_traceback": data.get("error_traceback"),
            "bytes": data.get("bytes"),
            "total_bytes": data.get("total_bytes"),
            "model_key": model_key,
            # Timestamps may not be present; leave None by default
        }
        extra = {k: v for k, v in data.items() if k not in {
            "id", "status", "error", "error_reason", "error_traceback", "bytes", "total_bytes", "config_out"
        }}
        return ModelInstJobInfo(**known, extra=extra)

    @staticmethod
    def _to_api_error(e: requests.HTTPError) -> APIRequestError:
        status = e.response.status_code if e.response is not None else None
        payload: Any = None
        try:
            if e.response is not None:
                payload = e.response.json()
        except Exception:
            payload = e.response.text if e.response is not None else None
        return APIRequestError(str(e), status_code=status, payload=payload)
