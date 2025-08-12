"""Main InvokeAI Python client implementation.

This module provides the InvokeAIClient class, the primary interface for
interacting with InvokeAI instances. It manages connections, authentication,
and provides high-level operations for workflows, images, and models.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Tuple, TypeVar, Generic,
    TYPE_CHECKING, cast, overload, Final, Literal
)
from typing_extensions import TypeAlias, Self
from urllib.parse import urlparse, urljoin
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import BaseModel, Field, validator
import json
import base64
from io import BytesIO
try:
    import numpy as np
    import numpy.typing as npt
except ImportError:
    np = None  # type: ignore[assignment]
    npt = None  # type: ignore[assignment]
try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]

from .workflow import ClientWorkflow, WorkflowResult, WorkflowOutput
from .types import InvokeAIImage, InvokeAIModelReference
from .exceptions import (
    ConnectionError, AuthenticationError, APIError,
    ConfigurationError, ResourceNotFoundError,
    WorkflowExecutionError, TimeoutError
)
from .types_extra import (
    HTTPMethod, ImageResponseDict, ModelResponseDict, BoardResponseDict,
    JobStatusDict, APIErrorDict, PathLike, Headers, QueryParams,
    FormData, JSONData, RequestData, HTTPResponse, APIResponse,
    MAX_RETRIES, DEFAULT_TIMEOUT, DEFAULT_POLL_INTERVAL,
    is_image_response, is_model_response, is_board_response,
    is_job_status, is_api_error
)
from .utils import (
    ensure_dict_response, ensure_list_response, get_dict_value,
    is_dict_response, is_list_response
)

if TYPE_CHECKING:
    from types import TracebackType


logger: Final[logging.Logger] = logging.getLogger(__name__)

# Type variables for generic resource managers
T = TypeVar('T')
ResourceType = TypeVar('ResourceType', bound=BaseModel)


class ClientConfig(BaseModel):
    """Configuration for InvokeAI client.
    
    Attributes
    ----------
    base_url : str
        Base URL of the InvokeAI instance.
    api_key : Optional[str]
        API key for authentication.
    timeout : float
        Default timeout for requests in seconds.
    max_retries : int
        Maximum number of retry attempts.
    retry_backoff : float
        Backoff factor for retries.
    verify_ssl : bool
        Whether to verify SSL certificates.
    connection_pool_size : int
        Size of the connection pool.
    enable_cache : bool
        Whether to enable response caching.
    cache_ttl : int
        Cache time-to-live in seconds.
    
    Examples
    --------
    >>> config = ClientConfig(
    ...     base_url="http://localhost:9090",
    ...     timeout=30.0,
    ...     max_retries=3
    ... )
    """
    
    base_url: str = Field(..., description="InvokeAI base URL")
    api_key: Optional[str] = Field(None, description="API key for auth")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Max retry attempts")
    retry_backoff: float = Field(0.3, description="Retry backoff factor")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    connection_pool_size: int = Field(10, description="Connection pool size")
    enable_cache: bool = Field(True, description="Enable response caching")
    cache_ttl: int = Field(300, description="Cache TTL in seconds")
    
    @validator('base_url')
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        # Ensure URL has scheme
        if not v.startswith(('http://', 'https://')):
            v = f'http://{v}'
        
        # Remove trailing slash
        v = v.rstrip('/')
        
        # Parse to validate
        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError(f"Invalid base URL: {v}")
        
        return v


class ResourceManager(Generic[ResourceType]):
    """Base class for resource managers (images, models, etc.).
    
    Provides common functionality for resource operations like
    listing, getting, uploading, and downloading.
    
    Attributes
    ----------
    client : InvokeAIClient
        The parent client instance.
    resource_type : str
        Type of resource managed.
    """
    
    def __init__(self, client: "InvokeAIClient", resource_type: str) -> None:
        """Initialize resource manager.
        
        Parameters
        ----------
        client : InvokeAIClient
            The parent client instance.
        resource_type : str
            Type of resource (e.g., "image", "model").
        """
        self.client = client
        self.resource_type = resource_type
    
    async def list(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """List resources.
        
        Parameters
        ----------
        **kwargs
            Query parameters for filtering.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of resource records.
        """
        raise NotImplementedError
    
    async def get(self, resource_id: str) -> Dict[str, Any]:
        """Get a specific resource.
        
        Parameters
        ----------
        resource_id : str
            The resource ID.
        
        Returns
        -------
        Dict[str, Any]
            The resource record.
        """
        raise NotImplementedError


class ImageManager(ResourceManager):
    """Manager for image operations.
    
    Handles uploading, downloading, and managing images on the
    InvokeAI server.
    
    Methods
    -------
    upload(image, board_id=None)
        Upload an image to the server.
    download(image_name)
        Download an image from the server.
    list(board_id=None, limit=100)
        List available images.
    delete(image_name)
        Delete an image.
    
    Examples
    --------
    >>> # Upload an image
    >>> image = await client.images.upload("input.png")
    >>> 
    >>> # Download an image
    >>> data = await client.images.download(image.image_name)
    >>> 
    >>> # List images
    >>> images = await client.images.list(limit=10)
    """
    
    def __init__(self, client: "InvokeAIClient") -> None:
        """Initialize image manager."""
        super().__init__(client, "image")
    
    async def upload(
        self,
        image: Union[PathLike, npt.NDArray[np.uint8], InvokeAIImage],
        board_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> InvokeAIImage:
        """Upload an image to the server.
        
        Parameters
        ----------
        image : Union[str, Path, np.ndarray, InvokeAIImage]
            The image to upload. Can be file path, numpy array, or InvokeAIImage.
        board_id : Optional[str]
            Board to add the image to.
        metadata : Optional[Dict[str, Any]]
            Additional metadata for the image.
        
        Returns
        -------
        InvokeAIImage
            The uploaded image reference.
        
        Raises
        ------
        APIError
            If upload fails.
        
        Examples
        --------
        >>> # Upload from file
        >>> image = await client.images.upload("input.png")
        >>> 
        >>> # Upload numpy array
        >>> array = np.zeros((512, 512, 3), dtype=np.uint8)
        >>> image = await client.images.upload(array)
        """
        # Convert to InvokeAIImage if needed
        if isinstance(image, (str, Path)):
            image_obj = InvokeAIImage.from_file(image)
        elif isinstance(image, np.ndarray):
            image_obj = InvokeAIImage.from_array(image)
        elif isinstance(image, InvokeAIImage):
            image_obj = image
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
        
        # Prepare upload
        if image_obj.local_path:
            # Load from file
            with open(image_obj.local_path, 'rb') as f:
                image_data = f.read()
            filename = image_obj.local_path.name
        elif image_obj.image_data is not None:
            # Convert numpy array to bytes
            pil_image = Image.fromarray(image_obj.image_data)
            buffer = BytesIO()
            pil_image.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            filename = "upload.png"
        else:
            raise ValueError("Image has no data to upload")
        
        # Upload to server
        url = f"/api/v1/images/upload"
        
        data = aiohttp.FormData()
        data.add_field('file', image_data, filename=filename, content_type='image/png')
        if board_id:
            data.add_field('board_id', board_id)
        if metadata:
            data.add_field('metadata', json.dumps(metadata))
        
        response = await self.client._request_async('POST', url, data=data)
        response_dict = ensure_dict_response(response, url)
        
        # Update image object with server reference
        image_obj.image_name = response_dict.get('image_name')
        
        logger.info(f"Uploaded image: {image_obj.image_name}")
        return image_obj
    
    async def download(
        self,
        image_name: str,
        as_array: bool = True
    ) -> Union[npt.NDArray[np.uint8], bytes]:
        """Download an image from the server.
        
        Parameters
        ----------
        image_name : str
            The image UUID/name on the server.
        as_array : bool
            If True, return as numpy array. Otherwise return raw bytes.
        
        Returns
        -------
        Union[np.ndarray, bytes]
            The image data.
        
        Raises
        ------
        ResourceNotFoundError
            If image not found.
        
        Examples
        --------
        >>> # Download as numpy array
        >>> array = await client.images.download("image-uuid")
        >>> 
        >>> # Download as bytes
        >>> data = await client.images.download("image-uuid", as_array=False)
        """
        url = f"/api/v1/images/i/{image_name}"
        
        try:
            response = await self.client._request_async('GET', url, raw_response=True)
            image_data = await response.read()
        except APIError as e:
            if e.status_code == 404:
                raise ResourceNotFoundError("image", image_name)
            raise
        
        if as_array:
            # Convert to numpy array
            pil_image = Image.open(BytesIO(image_data))
            return np.array(pil_image)
        
        return image_data
    
    async def list(
        self,
        board_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List images on the server.
        
        Parameters
        ----------
        board_id : Optional[str]
            Filter by board ID.
        limit : int
            Maximum number of images to return.
        offset : int
            Offset for pagination.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of image records.
        
        Examples
        --------
        >>> images = await client.images.list(limit=10)
        >>> for img in images:
        ...     print(f"Image: {img['image_name']}")
        """
        params = {"limit": limit, "offset": offset}
        if board_id:
            params["board_id"] = board_id
        
        response = await self.client._request_async('GET', "/api/v1/images", params=params)
        response_dict = ensure_dict_response(response, "/api/v1/images")
        return response_dict.get("items", [])
    
    async def delete(self, image_name: str) -> bool:
        """Delete an image from the server.
        
        Parameters
        ----------
        image_name : str
            The image UUID/name to delete.
        
        Returns
        -------
        bool
            True if deleted successfully.
        
        Examples
        --------
        >>> success = await client.images.delete("image-uuid")
        >>> if success:
        ...     print("Image deleted")
        """
        url = f"/api/v1/images/i/{image_name}"
        
        try:
            await self.client._request_async('DELETE', url)
            logger.info(f"Deleted image: {image_name}")
            return True
        except APIError as e:
            if e.status_code == 404:
                raise ResourceNotFoundError("image", image_name)
            raise


class ModelManager(ResourceManager):
    """Manager for model operations.
    
    Handles listing and managing models available on the InvokeAI server.
    
    Methods
    -------
    list(base=None, type=None)
        List available models.
    get(model_key)
        Get model details.
    
    Examples
    --------
    >>> # List all models
    >>> models = await client.models.list()
    >>> 
    >>> # List SDXL models
    >>> sdxl_models = await client.models.list(base="sdxl")
    """
    
    def __init__(self, client: "InvokeAIClient") -> None:
        """Initialize model manager."""
        super().__init__(client, "model")
    
    async def list(
        self,
        base: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[InvokeAIModelReference]:
        """List available models.
        
        Parameters
        ----------
        base : Optional[str]
            Filter by base model type (e.g., "sdxl", "sd-1", "sd-2").
        type : Optional[str]
            Filter by model type (e.g., "main", "vae", "lora").
        
        Returns
        -------
        List[InvokeAIModelReference]
            List of model references.
        
        Examples
        --------
        >>> # List all SDXL main models
        >>> models = await client.models.list(base="sdxl", type="main")
        >>> for model in models:
        ...     print(f"Model: {model.name} ({model.key})")
        """
        params = {}
        if base:
            params["base"] = base
        if type:
            params["type"] = type
        
        response = await self.client._request_async('GET', "/api/v2/models", params=params)
        response_dict = ensure_dict_response(response, "/api/v2/models")
        
        models = []
        for model_data in response_dict.get("models", []):
            models.append(InvokeAIModelReference(
                key=model_data.get("key", ""),
                hash=model_data.get("hash"),
                name=model_data.get("name"),
                base=model_data.get("base"),
                type=model_data.get("type"),
                submodel_type=model_data.get("submodel_type"),
                field_name=None,
                description="",
                required=False
            ))
        
        return models
    
    async def get(self, model_key: str) -> InvokeAIModelReference:
        """Get model details.
        
        Parameters
        ----------
        model_key : str
            The model key/ID.
        
        Returns
        -------
        InvokeAIModelReference
            The model reference.
        
        Raises
        ------
        ResourceNotFoundError
            If model not found.
        
        Examples
        --------
        >>> model = await client.models.get("stable-diffusion-xl-base")
        >>> print(f"Model: {model.name}")
        """
        url = f"/api/v2/models/i/{model_key}"
        
        try:
            response = await self.client._request_async('GET', url)
        except APIError as e:
            if e.status_code == 404:
                raise ResourceNotFoundError("model", model_key)
            raise
        
        response_dict = ensure_dict_response(response, url)
        return InvokeAIModelReference(
            key=response_dict.get("key", ""),
            hash=response_dict.get("hash"),
            name=response_dict.get("name"),
            base=response_dict.get("base"),
            type=response_dict.get("type"),
            submodel_type=response_dict.get("submodel_type"),
            field_name=None,
            description="",
            required=False
        )


class BoardManager(ResourceManager[Dict[str, Any]]):
    """Manager for board operations.
    
    Handles creating and managing boards for organizing outputs.
    
    Methods
    -------
    create(name, description=None)
        Create a new board.
    list()
        List available boards.
    delete(board_id)
        Delete a board.
    
    Examples
    --------
    >>> # Create a board
    >>> board = await client.boards.create("My Project")
    >>> 
    >>> # List boards
    >>> boards = await client.boards.list()
    """
    
    def __init__(self, client: "InvokeAIClient") -> None:
        """Initialize board manager."""
        super().__init__(client, "board")
    
    async def create(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new board.
        
        Parameters
        ----------
        name : str
            Board name.
        description : Optional[str]
            Board description.
        
        Returns
        -------
        Dict[str, Any]
            The created board record.
        
        Examples
        --------
        >>> board = await client.boards.create(
        ...     "Project X",
        ...     description="Images for Project X"
        ... )
        >>> board_id = board["board_id"]
        """
        data = {"board_name": name}
        if description:
            data["description"] = description
        
        response = await self.client._request_async('POST', "/api/v1/boards", json=data)
        response_dict = ensure_dict_response(response, "/api/v1/boards")
        logger.info(f"Created board: {name} ({response_dict.get('board_id')})")
        return response_dict
    
    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List boards.
        
        Parameters
        ----------
        limit : int
            Maximum number of boards to return.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of board records.
        
        Examples
        --------
        >>> boards = await client.boards.list()
        >>> for board in boards:
        ...     print(f"Board: {board['board_name']}")
        """
        params = {"limit": limit}
        response = await self.client._request_async('GET', "/api/v1/boards", params=params)
        response_dict = ensure_dict_response(response, "/api/v1/boards")
        return response_dict.get("items", [])
    
    async def delete(self, board_id: str) -> bool:
        """Delete a board.
        
        Parameters
        ----------
        board_id : str
            The board ID to delete.
        
        Returns
        -------
        bool
            True if deleted successfully.
        
        Examples
        --------
        >>> success = await client.boards.delete("board-id")
        """
        url = f"/api/v1/boards/{board_id}"
        
        try:
            await self.client._request_async('DELETE', url)
            logger.info(f"Deleted board: {board_id}")
            return True
        except APIError as e:
            if e.status_code == 404:
                raise ResourceNotFoundError("board", board_id)
            raise


class InvokeAIClient:
    """Main client for interacting with InvokeAI.
    
    This is the primary interface for the InvokeAI Python client library.
    It manages connections, authentication, and provides access to all
    InvokeAI functionality through resource managers and workflow operations.
    
    Attributes
    ----------
    config : ClientConfig
        Client configuration.
    images : ImageManager
        Manager for image operations.
    models : ModelManager
        Manager for model operations.
    boards : BoardManager
        Manager for board operations.
    
    Methods
    -------
    create_workflow(path)
        Create a workflow from JSON file.
    submit_workflow(workflow)
        Submit a workflow for execution.
    get_job_status(job_id)
        Get status of a running job.
    close()
        Close client connections.
    
    Examples
    --------
    >>> # Initialize client
    >>> client = InvokeAIClient("http://localhost:9090")
    >>> 
    >>> # Load and execute workflow
    >>> workflow = client.create_workflow("text-to-image.json")
    >>> workflow.set_input("prompt", "a beautiful landscape")
    >>> result = await workflow.execute()
    >>> 
    >>> # Work with resources
    >>> models = await client.models.list(base="sdxl")
    >>> images = await client.images.list(limit=10)
    >>> 
    >>> # Clean up
    >>> await client.close()
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        **config_kwargs: Any
    ) -> None:
        """Initialize InvokeAI client.
        
        Parameters
        ----------
        base_url : str
            Base URL of the InvokeAI instance (e.g., "http://localhost:9090").
        api_key : Optional[str]
            API key for authentication, if required.
        **config_kwargs
            Additional configuration options (timeout, retries, etc.).
        
        Raises
        ------
        ConfigurationError
            If configuration is invalid.
        ConnectionError
            If unable to connect to InvokeAI.
        
        Examples
        --------
        >>> # Basic initialization
        >>> client = InvokeAIClient("http://localhost:9090")
        >>> 
        >>> # With authentication
        >>> client = InvokeAIClient(
        ...     "https://invoke.example.com",
        ...     api_key="your-api-key"
        ... )
        >>> 
        >>> # With custom configuration
        >>> client = InvokeAIClient(
        ...     "http://localhost:9090",
        ...     timeout=60.0,
        ...     max_retries=5
        ... )
        """
        # Initialize configuration
        self.config = ClientConfig(
            base_url=base_url,
            api_key=api_key or os.environ.get("INVOKEAI_API_KEY"),
            **config_kwargs
        )
        
        # Parse base URL
        parsed = urlparse(self.config.base_url)
        self.host: str = parsed.hostname or "localhost"
        self.port: int = parsed.port or (443 if parsed.scheme == "https" else 80)
        
        # Initialize session for sync requests
        self._session: requests.Session = self._create_session()
        
        # Initialize async session (created on first use)
        self._async_session: Optional[aiohttp.ClientSession] = None
        
        # Initialize resource managers
        self.images: ImageManager = ImageManager(self)
        self.models: ModelManager = ModelManager(self)
        self.boards: BoardManager = BoardManager(self)
        
        # Response cache
        self._cache: Dict[str, Tuple[APIResponse, datetime]] = {}
        
        # Test connection
        self._test_connection()
        
        logger.info(f"Initialized InvokeAI client for {self.config.base_url}")
    
    def _create_session(self) -> requests.Session:
        """Create configured requests session.
        
        Returns
        -------
        requests.Session
            Configured session with retries and adapters.
        """
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_backoff,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_maxsize=self.config.connection_pool_size
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            "User-Agent": "InvokeAI-Python-Client/0.1.0",
            "Accept": "application/json"
        })
        
        # Add auth if configured
        if self.config.api_key:
            session.headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        return session
    
    async def _get_async_session(self) -> aiohttp.ClientSession:
        """Get or create async session.
        
        Returns
        -------
        aiohttp.ClientSession
            The async HTTP session.
        """
        if not self._async_session:
            headers = {
                "User-Agent": "InvokeAI-Python-Client/0.1.0",
                "Accept": "application/json"
            }
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            self._async_session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    limit=self.config.connection_pool_size,
                    ssl=self.config.verify_ssl
                )
            )
        
        return self._async_session
    
    def _test_connection(self) -> None:
        """Test connection to InvokeAI instance.
        
        Raises
        ------
        ConnectionError
            If unable to connect.
        AuthenticationError
            If authentication fails.
        """
        try:
            response = self._request('GET', "/api/v1/app/version")
            logger.info(f"Connected to InvokeAI version {response.get('version', 'unknown')}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                self.host,
                self.port,
                cause=e
            )
        except APIError as e:
            if e.status_code in [401, 403]:
                raise AuthenticationError(
                    "Authentication failed",
                    auth_method="api_key" if self.config.api_key else "none",
                    status_code=e.status_code,
                    cause=e
                )
            raise
    
    def _request(
        self,
        method: Union[HTTPMethod, str],
        path: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Make synchronous HTTP request.
        
        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.).
        path : str
            API path.
        **kwargs
            Additional request arguments.
        
        Returns
        -------
        Dict[str, Any]
            Response data.
        
        Raises
        ------
        APIError
            If request fails.
        """
        url = urljoin(self.config.base_url, path)
        
        # Check cache for GET requests
        if method == "GET" and self.config.enable_cache:
            cache_key = f"{method}:{url}:{kwargs.get('params')}"
            if cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                if (datetime.now() - cached_time).seconds < self.config.cache_ttl:
                    logger.debug(f"Cache hit for {cache_key}")
                    # Return cached data if it's a dict
                    if is_dict_response(cached_data):
                        return cached_data
                    # Otherwise, try to convert it
                    return ensure_dict_response(cached_data, path)
        
        # Make request
        kwargs.setdefault('timeout', self.config.timeout)
        kwargs.setdefault('verify', self.config.verify_ssl)
        
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise APIError.from_response(e.response)
        except requests.exceptions.RequestException as e:
            raise APIError(
                str(e),
                status_code=0,
                request_method=method,
                request_url=url,
                cause=e
            )
        
        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"text": response.text}
        
        # Update cache
        if method == "GET" and self.config.enable_cache:
            self._cache[cache_key] = (data, datetime.now())
        
        return data
    
    @overload
    async def _request_async(
        self,
        method: Union[HTTPMethod, str],
        path: str,
        raw_response: Literal[False] = False,
        **kwargs: Any
    ) -> APIResponse: ...
    
    @overload
    async def _request_async(
        self,
        method: Union[HTTPMethod, str],
        path: str,
        raw_response: Literal[True],
        **kwargs: Any
    ) -> aiohttp.ClientResponse: ...
    
    async def _request_async(
        self,
        method: Union[HTTPMethod, str],
        path: str,
        raw_response: bool = False,
        **kwargs: Any
    ) -> Union[APIResponse, aiohttp.ClientResponse]:
        """Make asynchronous HTTP request.
        
        Parameters
        ----------
        method : str
            HTTP method.
        path : str
            API path.
        raw_response : bool
            If True, return raw response object.
        **kwargs
            Additional request arguments.
        
        Returns
        -------
        Any
            Response data or raw response.
        
        Raises
        ------
        APIError
            If request fails.
        """
        session = await self._get_async_session()
        url = urljoin(self.config.base_url, path)
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if raw_response:
                    return response
                
                response.raise_for_status()
                
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return await response.read()
                    
        except aiohttp.ClientResponseError as e:
            raise APIError(
                e.message,
                status_code=e.status,
                request_method=method,
                request_url=url,
                cause=e
            )
        except aiohttp.ClientError as e:
            raise APIError(
                str(e),
                status_code=0,
                request_method=method,
                request_url=url,
                cause=e
            )
    
    def create_workflow(
        self,
        path: Union[PathLike, Dict[str, Any]]
    ) -> ClientWorkflow:
        """Create a workflow instance.
        
        Parameters
        ----------
        path : Union[str, Path, Dict[str, Any]]
            Path to workflow JSON file or workflow definition dict.
        
        Returns
        -------
        ClientWorkflow
            The workflow instance.
        
        Examples
        --------
        >>> # From file
        >>> workflow = client.create_workflow("workflows/text-to-image.json")
        >>> 
        >>> # From dict
        >>> definition = {"name": "my-workflow", ...}
        >>> workflow = client.create_workflow(definition)
        """
        if isinstance(path, dict):
            return ClientWorkflow.from_dict(path, client=self)
        else:
            return ClientWorkflow.from_file(path, client=self)
    
    async def submit_workflow(self, workflow: ClientWorkflow) -> str:
        """Submit a workflow for execution.
        
        Parameters
        ----------
        workflow : ClientWorkflow
            The workflow to submit.
        
        Returns
        -------
        str
            The job ID for tracking execution.
        
        Raises
        ------
        WorkflowExecutionError
            If submission fails.
        
        Examples
        --------
        >>> job_id = await client.submit_workflow(workflow)
        >>> print(f"Submitted as job {job_id}")
        """
        # Prepare batch for submission
        batch = {
            "workflow": workflow.to_dict(),
            "prepend": False
        }
        
        # Submit to queue
        response = await self._request_async(
            'POST',
            "/api/v1/queue/default/enqueue_batch",
            json={"batch": batch}
        )
        
        # Extract job ID from response
        job_id = get_dict_value(response, "batch_id") or get_dict_value(response, "job_id")
        if not job_id:
            raise WorkflowExecutionError(
                "No job ID returned from submission",
                workflow_id=workflow.id
            )
        
        logger.info(f"Submitted workflow '{workflow.name}' as job {job_id}")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a running job.
        
        Parameters
        ----------
        job_id : str
            The job ID to check.
        
        Returns
        -------
        Dict[str, Any]
            Job status information.
        
        Examples
        --------
        >>> status = await client.get_job_status("job-123")
        >>> print(f"Job status: {status['status']}")
        """
        response = await self._request_async(
            'GET',
            f"/api/v1/queue/default/status/{job_id}"
        )
        return ensure_dict_response(response, f"/api/v1/queue/default/status/{job_id}")
    
    async def get_job_outputs(self, job_id: str) -> List[WorkflowOutput]:
        """Get outputs from a completed job.
        
        Parameters
        ----------
        job_id : str
            The job ID.
        
        Returns
        -------
        List[WorkflowOutput]
            List of job outputs.
        
        Examples
        --------
        >>> outputs = await client.get_job_outputs("job-123")
        >>> for output in outputs:
        ...     print(f"Output: {output.field_name}")
        """
        response = await self._request_async(
            'GET',
            f"/api/v1/queue/default/results/{job_id}"
        )
        
        response_dict = ensure_dict_response(response, f"/api/v1/queue/default/results/{job_id}")
        outputs = []
        for result in response_dict.get("results", []):
            outputs.append(WorkflowOutput(
                node_id=result.get("node_id"),
                field_name=result.get("field_name"),
                value=result.get("value"),
                type_name=result.get("type")
            ))
        
        return outputs
    
    async def close(self) -> None:
        """Close client connections.
        
        Examples
        --------
        >>> await client.close()
        """
        if self._async_session:
            await self._async_session.close()
            self._async_session = None
        
        if self._session:
            self._session.close()
        
        logger.info("Closed InvokeAI client connections")
    
    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self
    
    async def __aexit__(
        self, 
        exc_type: Optional[type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional["TracebackType"]
    ) -> None:
        """Async context manager exit."""
        await self.close()
    
    def __enter__(self) -> Self:
        """Context manager entry."""
        return self
    
    def __exit__(
        self, 
        exc_type: Optional[type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional["TracebackType"]
    ) -> None:
        """Context manager exit."""
        if self._session:
            self._session.close()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"InvokeAIClient(base_url='{self.config.base_url}')"