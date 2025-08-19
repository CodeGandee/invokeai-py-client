"""
InvokeAI Python Client - Main client interface.

This module provides the primary interface for interacting with an InvokeAI instance.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import requests
import socketio  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from invokeai_py_client.board import BoardRepository
from invokeai_py_client.dnn_model import DnnModelRepository
from invokeai_py_client.models import (
    IvkDnnModel,
    IvkJob,
)
from invokeai_py_client.workflow import (
    WorkflowDefinition,
    WorkflowHandle,
    WorkflowRepository,
)


class InvokeAIClient:
    """
    Primary client for interacting with an InvokeAI instance.

    This class represents a connection to an InvokeAI server and provides
    high-level operations for workflow execution, asset management, and job tracking.

    Parameters
    ----------
    host : str
        The hostname or IP address of the InvokeAI server.
    port : int
        The port number of the InvokeAI server.
    api_key : Optional[str]
        API key for authentication, if required.
    timeout : float
        Request timeout in seconds.
    base_path : str
        Base path for API endpoints.
    use_https : bool
        Whether to use HTTPS for connections.
    verify_ssl : bool
        Whether to verify SSL certificates.
    max_retries : int
        Maximum number of retry attempts for failed requests.

    Attributes
    ----------
    host : str
        The InvokeAI server hostname.
    port : int
        The InvokeAI server port.
    base_url : str
        The base URL for API requests.
    session : requests.Session
        HTTP session for making requests.

    Examples
    --------
    >>> client = InvokeAIClient.from_url("http://localhost:9090")
    >>> boards = client.board_repo.list_boards()
    >>> workflow = client.create_workflow(WorkflowDefinition.from_file("workflow.json"))
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9090,
        api_key: str | None = None,
        timeout: float = 30.0,
        base_path: str = "/api/v1",
        use_https: bool = False,
        verify_ssl: bool = True,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        """Initialize the InvokeAI client with all member variables."""
        # Store configuration
        self.host = host
        self.port = port
        self.api_key = api_key
        self.timeout = timeout
        self.base_path = base_path
        self.use_https = use_https
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries

        # Build base URL
        scheme = "https" if self.use_https else "http"
        self.base_url = f"{scheme}://{self.host}:{self.port}{self.base_path}"

        # Initialize HTTP session with retry strategy
        self.session = requests.Session()

        # Configure retry strategy
        retry = Retry(
            total=self.max_retries,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        # Add API key if provided
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

        # SSL verification
        self.session.verify = self.verify_ssl

        # Store any additional kwargs for future use
        self.extra_config = kwargs

        # Initialize repositories
        self._board_repo: BoardRepository | None = None
        self._workflow_repo: WorkflowRepository | None = None
        self._dnn_model_repo: DnnModelRepository | None = None
        
        # Initialize Socket.IO client for async operations
        self._sio: socketio.AsyncClient | None = None  # type: ignore[no-any-unimported]
        self._sio_connected: bool = False

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> InvokeAIClient:
        """
        Create an InvokeAI client from a URL.

        Parameters
        ----------
        url : str
            The URL of the InvokeAI instance (e.g., "http://localhost:9090").
        **kwargs : Any
            Additional keyword arguments to pass to the constructor.

        Returns
        -------
        InvokeAIClient
            A configured client instance.

        Examples
        --------
        >>> client = InvokeAIClient.from_url("http://localhost:9090")
        >>> client = InvokeAIClient.from_url("https://my-invoke.ai:8080/api/v1")
        """
        # Parse the URL
        parsed = urlparse(url)

        # Extract components
        host = parsed.hostname or "localhost"
        port = parsed.port
        use_https = parsed.scheme == "https"
        base_path = parsed.path if parsed.path and parsed.path != "/" else "/api/v1"

        # Determine default port if not specified
        if port is None:
            port = 443 if use_https else 80

        # Create and return the client
        return cls(
            host=host, port=port, use_https=use_https, base_path=base_path, **kwargs
        )

    def create_workflow(self, definition: WorkflowDefinition) -> WorkflowHandle:
        """
        Create a workflow instance from a workflow definition.

        This method delegates to the workflow repository for creating
        workflow handles with proper validation and error handling.

        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow definition object loaded from a JSON file.

        Returns
        -------
        WorkflowHandle
            A workflow handle ready for configuration and execution.

        Raises
        ------
        ValueError
            If the workflow definition is invalid.

        Examples
        --------
        >>> definition = WorkflowDefinition.from_file("workflows/text2img.json")
        >>> workflow = client.create_workflow(definition)
        >>> workflow.get_input(0).field.value = "A beautiful landscape"
        >>> job = workflow.submit_sync()
        """
        # Delegate to workflow repository
        return self.workflow_repo.create_workflow(definition)

    @property
    def board_repo(self) -> BoardRepository:
        """
        Get the board repository instance for board-related operations.

        The BoardRepository provides all board management functionality including:
        - Listing, creating, and deleting boards
        - Creating BoardHandle instances for board operations
        - Managing the board lifecycle

        Returns
        -------
        BoardRepository
            The board repository instance.

        Examples
        --------
        >>> # List all boards
        >>> boards = client.board_repo.list_boards()

        >>> # Create a new board and get its handle
        >>> board_handle = client.board_repo.create_board("My Artwork")
        >>> board_handle.upload_image("photo.png")

        >>> # Get handle for existing board
        >>> board_handle = client.board_repo.get_board_handle("board-id-123")
        >>> images = board_handle.list_images()

        >>> # Get uncategorized board handle
        >>> uncategorized = client.board_repo.get_uncategorized_handle()
        >>> uncategorized.upload_image("new.png")
        """
        if self._board_repo is None:
            self._board_repo = BoardRepository(self)
        return self._board_repo

    @property
    def workflow_repo(self) -> WorkflowRepository:
        """
        Get the workflow repository instance for workflow-related operations.

        The WorkflowRepository provides all workflow management functionality including:
        - Creating workflow handles from definitions
        - Validating and fixing workflow compatibility issues
        - Managing workflow uploads and downloads

        Returns
        -------
        WorkflowRepository
            The workflow repository instance.

        Examples
        --------
        >>> # Create workflow from file
        >>> workflow = client.workflow_repo.create_workflow_from_file("workflow.json")

        >>> # List workflow inputs
        >>> inputs = workflow.list_inputs()

        >>> # Set inputs and submit
        >>> workflow.get_input(0).field.value = "A beautiful landscape"
        >>> job = workflow.submit_sync()
        """
        if self._workflow_repo is None:
            self._workflow_repo = WorkflowRepository(self)
        return self._workflow_repo

    @property
    def dnn_model_repo(self) -> DnnModelRepository:
        """
        Get the DNN model repository instance for dnn-model operations.

        The DnnModelRepository provides read-only access to DNN models:
        - List all available models from InvokeAI system
        - Get specific model details by key
        - Stateless design - no caching, always fresh API calls

        Returns
        -------
        DnnModelRepository
            The DNN model repository instance.

        Examples
        --------
        >>> # List all models (fresh API call)
        >>> models = client.dnn_model_repo.list_models()
        >>> print(f"Total models: {len(models)}")

        >>> # User filters models by type
        >>> from invokeai_py_client.dnn_model import DnnModelType
        >>> main_models = [m for m in models if m.type == DnnModelType.Main]

        >>> # Get specific model by key
        >>> model = client.dnn_model_repo.get_model_by_key("model-key-123")
        >>> if model:
        ...     print(f"Found: {model.name} ({model.type.value})")
        """
        if self._dnn_model_repo is None:
            self._dnn_model_repo = DnnModelRepository(self)
        return self._dnn_model_repo

    def list_jobs(self, status: str | None = None, limit: int = 100) -> list[IvkJob]:
        """
        List jobs with optional status filtering.

        Parameters
        ----------
        status : str, optional
            Filter by job status ('pending', 'running', 'completed', 'failed').
        limit : int, optional
            Maximum number of jobs to return, by default 100.

        Returns
        -------
        List[IvkJob]
            List of job objects.
        """
        raise NotImplementedError

    def get_job(self, job_id: str) -> IvkJob:
        """
        Get detailed information about a specific job.

        Parameters
        ----------
        job_id : str
            The unique job identifier.

        Returns
        -------
        IvkJob
            The job object with current status and results.

        Raises
        ------
        ValueError
            If the job does not exist.
        """
        raise NotImplementedError

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Parameters
        ----------
        job_id : str
            The job to cancel.

        Returns
        -------
        bool
            True if cancellation was successful.

        Raises
        ------
        ValueError
            If the job cannot be cancelled.
        """
        raise NotImplementedError

    def list_models(self, base_model: str | None = None) -> list[IvkDnnModel]:
        """
        List available models on the InvokeAI instance.

        Parameters
        ----------
        base_model : str, optional
            Filter by base model type ('sdxl', 'sd-1', 'sd-2', etc.).

        Returns
        -------
        List[IvkDnnModel]
            List of model objects.
        """
        raise NotImplementedError

    def get_model_info(self, model_key: str) -> IvkDnnModel:
        """
        Get detailed information about a specific model.

        Parameters
        ----------
        model_key : str
            The model identifier key.

        Returns
        -------
        IvkDnnModel
            IvkDnnModel metadata and configuration.

        Raises
        ------
        ValueError
            If the model does not exist.
        """
        raise NotImplementedError

    def health_check(self) -> bool:
        """
        Check if the InvokeAI instance is healthy and reachable.

        Returns
        -------
        bool
            True if the instance is healthy, False otherwise.
        """
        try:
            # Try to reach the health endpoint
            response = self.session.get(f"{self.base_url}/health", timeout=5.0)
            return bool(response.status_code == 200)
        except Exception:
            return False

    async def connect_socketio(self) -> socketio.AsyncClient:  # type: ignore[no-any-unimported]
        """
        Connect to the InvokeAI Socket.IO server.
        
        Returns
        -------
        socketio.AsyncClient
            The connected Socket.IO client.
            
        Raises
        ------
        RuntimeError
            If connection fails.
        """
        if self._sio is None:
            self._sio = socketio.AsyncClient()
        
        if not self._sio_connected:
            # Build Socket.IO URL
            scheme = "wss" if self.use_https else "ws"
            socketio_url = f"{scheme}://{self.host}:{self.port}"
            
            try:
                await self._sio.connect(
                    socketio_url, 
                    socketio_path="/ws/socket.io",
                    transports=["websocket", "polling"]
                )
                self._sio_connected = True
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Socket.IO: {e}")
        
        return self._sio
    
    async def disconnect_socketio(self) -> None:
        """
        Disconnect from the Socket.IO server.
        """
        if self._sio and self._sio_connected:
            await self._sio.disconnect()
            self._sio_connected = False
    
    @asynccontextmanager
    async def socketio_session(self) -> AsyncGenerator[socketio.AsyncClient, None]:  # type: ignore[no-any-unimported]
        """
        Context manager for Socket.IO connections.
        
        Yields
        ------
        socketio.AsyncClient
            The connected Socket.IO client.
            
        Examples
        --------
        >>> async with client.socketio_session() as sio:
        ...     await sio.emit("subscribe_queue", {"queue_id": "default"})
        """
        sio = await self.connect_socketio()
        try:
            yield sio
        finally:
            # Keep connection alive for reuse - don't disconnect here
            # User can manually disconnect if needed
            pass
    
    def close(self) -> None:
        """
        Close the client connection and clean up resources.

        This method should be called when the client is no longer needed,
        or used with a context manager.
        """
        if hasattr(self, "session"):
            self.session.close()
        
        # Close Socket.IO if connected
        if self._sio and self._sio_connected:
            # Use asyncio.run if not in async context
            try:
                asyncio.run(self.disconnect_socketio())
            except RuntimeError:
                # Already in async context or loop is running
                pass

    def __enter__(self) -> InvokeAIClient:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """
        Make an HTTP request to the API.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.).
        endpoint : str
            API endpoint path.
        **kwargs : Any
            Additional arguments to pass to requests.

        Returns
        -------
        requests.Response
            The response object.

        Raises
        ------
        requests.RequestException
            If the request fails.
        """
        url = f"{self.base_url}{endpoint}"

        # Set timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        # Make the request
        response = self.session.request(method, url, **kwargs)

        # Raise for HTTP errors
        response.raise_for_status()

        return response
