"""
DNN model repository for managing DNN model instances using the repository pattern.

This module implements a stateless Repository pattern for dnn-model-related operations,
providing only APIs that call the InvokeAI system directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import requests

from invokeai_py_client.dnn_model.dnn_model_types import DnnModel

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
        # Always fetch fresh from InvokeAI API
        # Use v2 API endpoint for models
        response = self._client._make_request("GET", "/../v2/models/")
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
            # Use v2 API endpoint for model details
            response = self._client._make_request("GET", f"/../v2/models/i/{model_key}")
            return DnnModel.from_api_response(response.json())
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def __repr__(self) -> str:
        """
        String representation of the model repository.

        Returns
        -------
        str
            String representation including the client base URL.
        """
        return f"DnnModelRepository(client={self._client.base_url})"