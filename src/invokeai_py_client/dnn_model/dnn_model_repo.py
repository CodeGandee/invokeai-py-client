"""
DNN model repository for managing DNN model instances and model manager operations.

This module implements a stateless Repository pattern for DNN model discovery
and management operations. Read operations (list/get model) delegate to the
v2 models API. Write operations (install/convert/delete/scan/cache/HF) target
the v2 model_manager endpoints.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import requests

from invokeai_py_client.dnn_model.dnn_model_types import DnnModel
from invokeai_py_client.dnn_model.dnn_model_models import (
    HFLoginStatus,
    InstallJobStatus,
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
        List all available DNN models from the InvokeAI system.

        This method always calls the v2 models API to fetch the current list; no
        client-side caching is performed. Users may filter the returned list locally.

        Returns
        -------
        list[DnnModel]
            List of all DNN model records.

        Raises
        ------
        APIRequestError
            If the API request fails.

        Examples
        --------
        >>> models = dnn_model_repo.list_models()  # Fresh API call
        >>> print(f"Total models: {len(models)}")
        >>>
        >>> # Filter by type
        >>> from invokeai_py_client.dnn_model import DnnModelType
        >>> main_models = [m for m in models if m.type == DnnModelType.Main]
        >>>
        >>> # Filter by base architecture
        >>> from invokeai_py_client.dnn_model import BaseDnnModelType
        >>> flux_models = [m for m in models if m.is_compatible_with_base(BaseDnnModelType.Flux)]
        """
        try:
            response = self._client._make_request_v2("GET", "/models/")
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        data = response.json()

        # Extract models from response
        models_data = data.get("models", [])
        
        # Convert to DnnModel objects
        return [DnnModel.from_api_response(model_data) for model_data in models_data]

    def get_model_by_key(self, model_key: str) -> DnnModel | None:
        """
        Get a specific DNN model by its unique key.

        Parameters
        ----------
        model_key : str
            The unique model key identifier.

        Returns
        -------
        DnnModel or None
            The model object if found, otherwise ``None`` (404).

        Raises
        ------
        APIRequestError
            If the API request fails (non-404 errors).

        Examples
        --------
        >>> model = dnn_model_repo.get_model_by_key("4ea8c1b5-e56c-47c0-949e-3805d06c1301")
        >>> if model:
        ...     print(f"Found: {model.name} ({model.type.value})")
        ...     from invokeai_py_client.dnn_model import BaseDnnModelType
        ...     print(f"Compatible with FLUX: {model.is_compatible_with_base(BaseDnnModelType.Flux)}")
        >>> # Not found
        >>> print(dnn_model_repo.get_model_by_key("nonexistent-key"))
        None
        """
        try:
            response = self._client._make_request_v2("GET", f"/models/i/{model_key}")
            return DnnModel.from_api_response(response.json())
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise self._to_api_error(e) from e

    # -------------------- Model install jobs --------------------
    def install_model(
        self,
        source: str,
        *,
        config: ModelInstallConfig | dict | None = None,
        inplace: bool | None = None,
        access_token: str | None = None,
    ) -> ModelInstJobHandle:
        """
        Start a model install job and return its handle.

        Parameters
        ----------
        source : str
            Model source to install. May be a local file/folder path, a direct URL to
            a model file, or a Hugging Face `repo_id` (e.g., "org/name").
        config : ModelInstallConfig or dict, optional
            Optional overrides for model metadata (name, type, base, prediction_type, etc.).
            When provided as a dict, it is sent as-is to the server's `ModelRecordChanges`.
        inplace : bool, optional
            For local paths only. If True, installs the model "in place" without moving
            it into the InvokeAI-managed models directory. Defaults to False server-side
            if not provided.
        access_token : str, optional
            Optional access token for protected URLs or HF repos.

        Returns
        -------
        ModelInstJobHandle
            A handle for the created (or resolved) installation job. Use this handle to
            monitor progress, wait for completion, or cancel.

        Outcome Detection
        -----------------
        - Success
          Call ``handle.wait_until(timeout=None)`` to wait until terminal. On success,
          it returns a ``ModelInstJobInfo`` whose ``status`` is ``COMPLETED`` and may
          include a ``model_key`` in the job info.

        - Already Installed (Skipped)
          If the server reports the model already exists (HTTP 409), this function
          returns a handle whose info is in a synthetic terminal state:
          ``status=COMPLETED`` and ``info.extra['reason'] == 'already_installed'``.
          You can detect a skip with::

              info = handle.info or handle.refresh()
              skipped = getattr(info, 'extra', {}).get('reason') == 'already_installed'

        - Failure
          - Job creation fails (e.g., bad request): raises ``ModelInstallStartError``.
          - Job fails during processing: ``handle.wait_until(...)`` raises
            ``ModelInstallJobFailed``; inspect ``e.info`` for details.
          - Transport/API errors: raises ``APIRequestError``.

        Notes
        -----
        - ``wait_until(timeout=None)`` waits indefinitely once the job is being
          processed by the server.
        - You may also poll manually and use ``handle.raise_if_failed()`` to convert a
          failed/cancelled status into a ``ModelInstallJobFailed`` exception.

        Examples
        --------
        >>> h = client.dnn_model_repo.install_model("/mnt/models/foo.safetensors")
        >>> try:
        ...     info = h.wait_until(timeout=None)
        ...     print("installed", getattr(info, "model_key", None))
        ... except ModelInstallJobFailed as e:
        ...     print("failed", getattr(e.info, "error", None))
        """
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
            # If already exists (409), treat as a non-fatal skip and return a synthetic completed handle
            if e.response is not None and e.response.status_code == 409:
                h = ModelInstJobHandle.from_client_and_id(self._client, -1)
                h._info = ModelInstJobInfo(id=-1, status=InstallJobStatus.COMPLETED, extra={"reason": "already_installed"})  # type: ignore[arg-type]
                return h
            # Wrap other failures as start error
            raise ModelInstallStartError(str(self._to_api_error(e))) from e
        data = resp.json()
        job_id = int(data.get("id", 0))
        handle = ModelInstJobHandle.from_client_and_id(self._client, job_id)
        handle._info = self._parse_job_info(data)  # type: ignore[attr-defined]
        return handle

    def list_install_jobs(self) -> list[ModelInstJobHandle]:
        """
        List all model install jobs.

        Returns
        -------
        list[ModelInstJobHandle]
            A list of handles with preloaded job info (no additional request
            required to access initial state).

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.INSTALL_BASE)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
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

    def get_install_job(self, id: int | str) -> ModelInstJobHandle | None:
        """
        Get a handle for a single install job.

        Parameters
        ----------
        id : int or str
            The install job identifier.

        Returns
        -------
        ModelInstJobHandle or None
            A handle for the job if found, otherwise ``None`` (404).

        Raises
        ------
        APIRequestError
            If the API request fails (non-404 errors).
        """
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
            raise self._to_api_error(e) from e
        data = resp.json()
        h = ModelInstJobHandle.from_client_and_id(self._client, jid)
        h._info = self._parse_job_info(data)  # type: ignore[attr-defined]
        return h

    def prune_install_jobs(self) -> bool:
        """
        Prune completed and errored install jobs from the server list.

        Returns
        -------
        bool
            ``True`` if the server acknowledged the prune request.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("DELETE", _V2Endpoint.INSTALL_BASE)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        return bool(resp.status_code in (200, 204))

    def install_huggingface(
        self,
        repo_id: str,
        *,
        config: ModelInstallConfig | dict | None = None,
        access_token: str | None = None,
    ) -> ModelInstJobHandle:
        """
        Convenience wrapper to install a model from a Hugging Face repo id.

        Parameters
        ----------
        repo_id : str
            The Hugging Face repository id (e.g., "org/name").
        config : ModelInstallConfig or dict, optional
            Optional overrides for model metadata.
        access_token : str, optional
            Optional HF token.

        Returns
        -------
        ModelInstJobHandle
            A handle to the created or resolved job; semantics match ``install_model``.
        """
        return self.install_model(source=repo_id, config=config, access_token=access_token)

    # -------------------- Mutations --------------------
    def convert_model(self, key: str) -> DnnModel:
        """
        Convert a model to diffusers format.

        Parameters
        ----------
        key : str
            The unique model key to convert.

        Returns
        -------
        DnnModel
            The updated model configuration after conversion.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("PUT", _V2Endpoint.CONVERT.format(key=key))
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        data = resp.json()
        return DnnModel.from_api_response(data)

    def delete_model(self, key: str) -> bool:
        """
        Delete a model by key.

        Parameters
        ----------
        key : str
            The unique model key to delete.

        Returns
        -------
        bool
            ``True`` if the model was deleted (200/204), else ``False``.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("DELETE", _V2Endpoint.MODEL_BY_KEY.format(key=key))
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        return bool(resp.status_code in (200, 204))

    def delete_all_models(self) -> dict[str, Any]:
        """
        Delete all DNN models from the InvokeAI system.

        Performs a best-effort batch delete:
        - Retrieves current list of models
        - Attempts to delete each by key
        - Continues on errors and returns a summary

        Returns
        -------
        dict[str, Any]
            Summary: ``{"total": int, "deleted": int, "failed": int, "errors": list}``.
            Each item in ``errors`` is a dict with ``key``, ``message``, and optional ``status_code``.
        """
        models = self.list_models()
        total = len(models)
        deleted = 0
        failures: list[dict[str, Any]] = []

        for m in models:
            key = getattr(m, "key", None)
            if not key:
                failures.append({"key": None, "message": "missing model key"})
                continue
            try:
                ok = self.delete_model(key)
                if ok:
                    deleted += 1
                else:
                    failures.append({"key": key, "message": "delete returned False"})
            except requests.HTTPError as e:  # Should be wrapped by delete_model, but guard anyway
                api_err = self._to_api_error(e)
                failures.append(
                    {
                        "key": key,
                        "message": str(api_err),
                        "status_code": getattr(api_err, "status_code", None),
                    }
                )
            except Exception as e:  # pragma: no cover - unexpected
                failures.append({"key": key, "message": str(e)})

        return {
            "total": total,
            "deleted": deleted,
            "failed": len(failures),
            "errors": failures,
        }

    # -------------------- Cache & Stats --------------------
    def empty_model_cache(self) -> bool:
        """
        Empty the model RAM/VRAM cache on the server.

        Returns
        -------
        bool
            ``True`` if the request was acknowledged.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("POST", _V2Endpoint.EMPTY_CACHE)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        return bool(resp.status_code in (200, 204))

    def get_stats(self) -> ModelManagerStats | None:
        """
        Retrieve model manager cache statistics.

        Returns
        -------
        ModelManagerStats or None
            Cache stats if available, otherwise ``None`` when no models have been loaded.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.STATS)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        if resp.status_code == 200 and resp.content:
            data = resp.json()
            if data is None:
                return None
            return self._parse_stats(data)
        return None

    # -------------------- Scan folder --------------------
    def scan_folder(self, scan_path: str | None = None) -> list[FoundModel] | dict[str, Any]:
        """
        Scan a folder for models and report paths and install status.

        Parameters
        ----------
        scan_path : str, optional
            Absolute path to scan. If omitted, server may require this parameter.

        Returns
        -------
        list[FoundModel] or dict
            A list of FoundModel entries (``path``, ``is_installed``). Some servers may
            return a raw response dict on error.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        params: dict[str, Any] = {}
        if scan_path is not None:
            params["scan_path"] = scan_path
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.SCAN_FOLDER, params=params)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        data = resp.json()
        if isinstance(data, list):
            return [self._parse_found_model(it) for it in data]
        return data

    # -------------------- Hugging Face helpers --------------------
    def hf_status(self) -> HFLoginStatus:
        """
        Get the Hugging Face login token status from the server.

        Returns
        -------
        HFLoginStatus
            One of: VALID, INVALID, UNKNOWN.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("GET", _V2Endpoint.HF_LOGIN)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        status_raw = str(resp.json())
        try:
            return HFLoginStatus(status_raw)
        except Exception:
            return HFLoginStatus.UNKNOWN

    def hf_login(self, token: str) -> bool:
        """
        Log in to Hugging Face using the provided token.

        Parameters
        ----------
        token : str
            Hugging Face access token.

        Returns
        -------
        bool
            ``True`` if the token was accepted.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("POST", _V2Endpoint.HF_LOGIN, json={"token": token})
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
        return bool(resp.status_code == 200)

    def hf_logout(self) -> bool:
        """
        Log out from Hugging Face (clear token on server).

        Returns
        -------
        bool
            ``True`` if the token was cleared.

        Raises
        ------
        APIRequestError
            If the API request fails.
        """
        try:
            resp = self._client._make_request_v2("DELETE", _V2Endpoint.HF_LOGIN)
        except requests.HTTPError as e:
            raise self._to_api_error(e) from e
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
