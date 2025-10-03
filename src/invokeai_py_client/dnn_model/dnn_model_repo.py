"""
DNN model repository for managing DNN model instances and model manager operations.

This module implements a stateless Repository pattern for DNN model discovery
and management operations. Read operations (list/get model) delegate to the
v2 models API. Write operations (install/convert/delete/scan/cache/HF) target
the v2 model_manager endpoints.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING, Optional

import requests

from invokeai_py_client.dnn_model.dnn_model_types import DnnModel
from invokeai_py_client.dnn_model.dnn_model_models import (
    HFLoginStatus,
    ModelInstallConfig,
    ModelInstJobInfo,
    ModelManagerStats,
    FoundModel,
    _V2Endpoint,
)
from invokeai_py_client.dnn_model.model_inst_job_handle import ModelInstJobHandle
from invokeai_py_client.dnn_model.dnn_model_exceptions import (
    APIRequestError,
    ModelInstallStartError,
)

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class DnnModelRepository:
    """
    Repository for DNN model discovery from the InvokeAI system.

    This class provides a stateless model repository following the Repository
    pattern. It only provides operations that call the InvokeAI API directly.
    No caching is performed - each call hits the API.

    Since dnn-models are considered "static" resources in the current version,
    it only provides read operations - no create, update, or delete operations.

    Attributes
    ----------
    _client : InvokeAIClient
        Reference to the InvokeAI client for API calls.

    Examples
    --------
    >>> client = InvokeAIClient.from_url("http://localhost:9090")
    >>> dnn_model_repo = client.dnn_model_repo
    >>>
    >>> # Get all models (always fresh from API)
    >>> models = dnn_model_repo.list_models()
    >>>
    >>> # Get specific model
    >>> model = dnn_model_repo.get_model_by_key("model-key-123")
    """

    def __init__(self, client: InvokeAIClient) -> None:
        """
        Initialize the DnnModelRepository.

        Parameters
        ----------
        client : InvokeAIClient
            The InvokeAI client instance to use for API calls.
        """
        self._client = client

    def list_models(self) -> list[DnnModel]:
        """
        List all available dnn-models from the InvokeAI system.

        This method always calls the InvokeAI API to fetch the current list of models.
        No caching is performed - each call gets fresh data from the system.

        Users can perform their own filtering on the returned model list.

        Returns
        -------
        list[DnnModel]
            List of all dnn-model objects from the InvokeAI system.

        Raises
        ------
        requests.HTTPError
            If the API request fails.

        Examples
        --------
        >>> models = dnn_model_repo.list_models()  # Fresh API call
        >>> print(f"Total models: {len(models)}")
        >>>
        >>> # User filters by type
        >>> from invokeai_py_client.dnn_model import DnnModelType
        >>> main_models = [m for m in models if m.type == DnnModelType.Main]
        >>>
        >>> # User filters by base architecture
        >>> from invokeai_py_client.dnn_model import BaseDnnModelType
        >>> flux_models = [m for m in models if m.is_compatible_with_base(BaseDnnModelType.Flux)]
        """
        try:
            response = self._client._make_request_v2("GET", "/models/")
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        data = response.json()

        # Extract models from response
        models_data = data.get("models", [])
        
        # Convert to DnnModel objects
        return [DnnModel.from_api_response(model_data) for model_data in models_data]

    def get_model_by_key(self, model_key: str) -> Optional[DnnModel]:
        """
        Get a specific dnn-model by its unique key from the InvokeAI system.

        This method always calls the InvokeAI API to fetch the model details.
        No caching is performed.

        Parameters
        ----------
        model_key : str
            The unique model key identifier.

        Returns
        -------
        DnnModel or None
            The dnn-model object if found, None if not found.

        Raises
        ------
        requests.HTTPError
            If the API request fails (except for 404 errors).

        Examples
        --------
        >>> model = dnn_model_repo.get_model_by_key("4ea8c1b5-e56c-47c0-949e-3805d06c1301")
        >>> if model:
        ...     print(f"Found: {model.name} ({model.type.value})")
        ...     from invokeai_py_client.dnn_model import BaseDnnModelType
        ...     print(f"Compatible with FLUX: {model.is_compatible_with_base(BaseDnnModelType.Flux)}")
        
        >>> # Model not found
        >>> missing = dnn_model_repo.get_model_by_key("nonexistent-key")
        >>> print(missing)  # None
        """
        try:
            response = self._client._make_request_v2("GET", f"/models/i/{model_key}")
            return DnnModel.from_api_response(response.json())
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise self._to_api_error(e)

    # -------------------- Model install jobs --------------------
    def install_model(
        self,
        source: str,
        *,
        config: ModelInstallConfig | dict | None = None,
        inplace: bool | None = None,
        access_token: str | None = None,
    ) -> ModelInstJobHandle:
        """Start a model install job and return a job handle."""
        params: dict[str, Any] = {"source": source}
        if inplace is not None:
            params["inplace"] = inplace
        if access_token is not None:
            params["access_token"] = access_token

        body: dict[str, Any]
        if config is None:
            body = {}
        elif isinstance(config, ModelInstallConfig):
            body = config.to_record_changes()
        else:
            body = dict(config)

        try:
            resp = self._client._make_request_v2("POST", _V2Endpoint.INSTALL_BASE, params=params, json=body)
        except requests.HTTPError as e:
            # Wrap rejection as a start error
            raise ModelInstallStartError(str(self._to_api_error(e)))
        data = resp.json()
        job_id = int(data.get("id", 0))
        handle = ModelInstJobHandle.from_client_and_id(self._client, job_id)
        handle._info = self._parse_job_info(data)  # type: ignore[attr-defined]
        return handle

    def list_install_jobs(self) -> list[ModelInstJobHandle]:
        """List all install jobs as handles (with preloaded info)."""
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.INSTALL_BASE)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        items = resp.json() or []
        handles: list[ModelInstJobHandle] = []
        for it in items:
            try:
                jid = int(it.get("id", 0))
            except Exception:
                continue
            h = ModelInstJobHandle.from_client_and_id(self._client, jid)
            h._info = self._parse_job_info(it)  # type: ignore[attr-defined]
            handles.append(h)
        return handles

    def get_install_job(self, id: int | str) -> Optional[ModelInstJobHandle]:
        """Get a handle for a single install job. Returns None if not found."""
        try:
            jid = int(id)
        except Exception:
            return None
        url = _V2Endpoint.INSTALL_BY_ID.format(id=jid)
        try:
            resp = self._client._make_request_v2("GET", url)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise self._to_api_error(e)
        data = resp.json()
        h = ModelInstJobHandle.from_client_and_id(self._client, jid)
        h._info = self._parse_job_info(data)  # type: ignore[attr-defined]
        return h

    def prune_install_jobs(self) -> bool:
        """Prune completed and errored jobs from install list."""
        try:
            resp = self._client._make_request_v2("DELETE", _V2Endpoint.INSTALL_BASE)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        return bool(resp.status_code in (200, 204))

    def install_huggingface(
        self,
        repo_id: str,
        *,
        config: ModelInstallConfig | dict | None = None,
        access_token: str | None = None,
    ) -> ModelInstJobHandle:
        """Convenience wrapper to install from a Hugging Face repo id."""
        return self.install_model(source=repo_id, config=config, access_token=access_token)

    # -------------------- Mutations --------------------
    def convert_model(self, key: str) -> DnnModel:
        """Convert a safetensors model to diffusers format."""
        try:
            resp = self._client._make_request_v2("PUT", _V2Endpoint.CONVERT.format(key=key))
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        data = resp.json()
        return DnnModel.from_api_response(data)

    def delete_model(self, key: str) -> bool:
        """Delete a model by key."""
        try:
            resp = self._client._make_request_v2("DELETE", _V2Endpoint.MODEL_BY_KEY.format(key=key))
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        return bool(resp.status_code in (200, 204))

    # -------------------- Cache & Stats --------------------
    def empty_model_cache(self) -> bool:
        try:
            resp = self._client._make_request_v2("POST", _V2Endpoint.EMPTY_CACHE)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        return bool(resp.status_code in (200, 204))

    def get_stats(self) -> Optional[ModelManagerStats]:
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.STATS)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        if resp.status_code == 200 and resp.content:
            data = resp.json()
            if data is None:
                return None
            return self._parse_stats(data)
        return None

    # -------------------- Scan folder --------------------
    def scan_folder(self, scan_path: str | None = None) -> list[FoundModel] | dict[str, Any]:
        params: dict[str, Any] = {}
        if scan_path is not None:
            params["scan_path"] = scan_path
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.SCAN_FOLDER, params=params)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        data = resp.json()
        if isinstance(data, list):
            return [self._parse_found_model(it) for it in data]
        return data

    # -------------------- Hugging Face helpers --------------------
    def hf_status(self) -> HFLoginStatus:
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.HF_LOGIN)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        status_raw = str(resp.json())
        try:
            return HFLoginStatus(status_raw)
        except Exception:
            return HFLoginStatus.UNKNOWN

    def hf_login(self, token: str) -> bool:
        try:
            resp = self._client._make_request_v2("POST", _V2Endpoint.HF_LOGIN, json={"token": token})
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        return bool(resp.status_code == 200)

    def hf_logout(self) -> bool:
        try:
            resp = self._client._make_request_v2("DELETE", _V2Endpoint.HF_LOGIN)
        except requests.HTTPError as e:
            raise self._to_api_error(e)
        return bool(resp.status_code == 200)

    # -------------------- Parsing helpers --------------------
    @staticmethod
    def _parse_job_info(data: dict[str, Any]) -> ModelInstJobInfo:
        from invokeai_py_client.dnn_model.model_inst_job_handle import ModelInstJobHandle as _H

        return _H._parse_job_info(data)  # type: ignore[attr-defined]

    @staticmethod
    def _parse_stats(data: dict[str, Any]) -> ModelManagerStats:
        known_keys = {
            "hit_rate",
            "miss_rate",
            "ram_used_mb",
            "ram_capacity_mb",
            "loads",
            "evictions",
        }
        known: dict[str, Any] = {k: data.get(k) for k in known_keys}
        extra = {k: v for k, v in data.items() if k not in known_keys}
        return ModelManagerStats(**known, extra=extra)

    @staticmethod
    def _parse_found_model(data: dict[str, Any]) -> FoundModel:
        known = {
            "path": data.get("path", ""),
            "is_installed": bool(data.get("is_installed", False)),
        }
        extra = {k: v for k, v in data.items() if k not in {"path", "is_installed"}}
        return FoundModel(**known, extra=extra)

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

    def __repr__(self) -> str:
        """
        String representation of the model repository.

        Returns
        -------
        str
            String representation including the client base URL.
        """
        return f"DnnModelRepository(client={self._client.base_url})"
