"""
ModelInstJobHandle: handle for a single model install job.

Provides refresh, status helpers, cancel, and wait-for-completion.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

import requests

from invokeai_py_client.dnn_model.dnn_model_models import (
    InstallJobStatus,
    ModelInstJobInfo,
    _V2Endpoint,
)

if TYPE_CHECKING:  # pragma: no cover
    from invokeai_py_client.client import InvokeAIClient


class ModelInstJobHandle:
    """
    Handle for a single model install job.

    Construct via repository methods; do not instantiate directly.
    """

    def __init__(self) -> None:
        self._client: Optional["InvokeAIClient"] = None
        self._job_id: Optional[int] = None
        self._info: Optional[ModelInstJobInfo] = None

    @classmethod
    def from_client_and_id(cls, client: "InvokeAIClient", job_id: int) -> "ModelInstJobHandle":
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
    def info(self) -> Optional[ModelInstJobInfo]:
        return self._info

    # -------------------- API helpers --------------------
    def refresh(self) -> ModelInstJobInfo:
        """Fetch latest job info and cache it."""
        url = _V2Endpoint.INSTALL_BY_ID.format(id=self.job_id)
        resp = self._client_v2("GET", url)
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

    def progress(self) -> Optional[float]:
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
            raise

    def wait(self, timeout: float = 600.0, poll_interval: float = 2.0) -> ModelInstJobInfo:
        """Wait until the job reaches a terminal state or timeout elapses."""
        deadline = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < deadline:
            info = self.refresh()
            if info.status in {InstallJobStatus.COMPLETED, InstallJobStatus.ERROR, InstallJobStatus.CANCELLED}:
                return info
            import time

            time.sleep(poll_interval)
        return self.refresh()

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

        model_key: Optional[str] = None
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

