"""
InvokeAI Python Client - Main client interface.

This module provides the primary interface for interacting with an InvokeAI instance.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from invokeai_py_client.models import Board, DnnModel, Image, Job, WorkflowDefinition
from invokeai_py_client.workflow import Workflow


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
    >>> boards = client.list_boards()
    >>> workflow = client.create_workflow(WorkflowDefinition.from_file("workflow.json"))
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9090,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        base_path: str = "/api/v1",
        use_https: bool = False,
        verify_ssl: bool = True,
        max_retries: int = 3,
        **kwargs: Any
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
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Add API key if provided
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # SSL verification
        self.session.verify = self.verify_ssl
        
        # Store any additional kwargs for future use
        self.extra_config = kwargs
    
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
            host=host,
            port=port,
            use_https=use_https,
            base_path=base_path,
            **kwargs
        )
    
    def create_workflow(self, definition: WorkflowDefinition) -> Workflow:
        """
        Create a workflow instance from a workflow definition.
        
        Parameters
        ----------
        definition : WorkflowDefinition
            The workflow definition object loaded from a JSON file.
        
        Returns
        -------
        Workflow
            A workflow object ready for configuration and execution.
        
        Raises
        ------
        ValueError
            If the workflow definition is invalid.
        
        Examples
        --------
        >>> definition = WorkflowDefinition.from_file("workflows/text2img.json")
        >>> workflow = client.create_workflow(definition)
        >>> workflow.set_input("prompt", "A beautiful landscape")
        >>> job = workflow.submit()
        """
        # Validate the workflow definition
        errors = definition.validate_workflow()
        if errors:
            raise ValueError(f"Invalid workflow definition: {'; '.join(errors)}")
        
        # Create and return the workflow instance
        from invokeai_py_client.workflow import Workflow
        return Workflow(client=self, definition=definition)
    
    def list_boards(self, all: bool = True, include_uncategorized: bool = False) -> List[Board]:
        """
        List all available boards in the InvokeAI instance.
        
        Note: The uncategorized board is not included by default as it's system-managed.
        
        Parameters
        ----------
        all : bool, optional
            Whether to fetch all boards or use pagination, by default True.
        include_uncategorized : bool, optional
            Whether to include the uncategorized board in the list, by default False.
        
        Returns
        -------
        List[Board]
            List of board objects containing board metadata.
        
        Examples
        --------
        >>> boards = client.list_boards()
        >>> for board in boards:
        ...     print(f"{board.board_name}: {board.image_count} images")
        
        >>> # Include uncategorized board
        >>> boards = client.list_boards(include_uncategorized=True)
        >>> for board in boards:
        ...     if board.is_uncategorized():
        ...         print(f"Uncategorized: {board.image_count} images")
        """
        params = {'all': all}
        response = self._make_request('GET', '/boards/', params=params)
        
        data = response.json()
        
        # Handle both paginated and non-paginated responses
        if isinstance(data, list):
            # Direct list response when all=True
            boards_data = data
        elif isinstance(data, dict) and 'items' in data:
            # Paginated response
            boards_data = data['items']
        else:
            boards_data = []
        
        # Convert to Board objects
        boards = [Board.from_api_response(board_data) for board_data in boards_data]
        
        # Add uncategorized board if requested
        if include_uncategorized:
            uncategorized_count = self.get_uncategorized_images_count()
            uncategorized_board = Board.uncategorized(image_count=uncategorized_count)
            boards.insert(0, uncategorized_board)  # Add at beginning
        
        return boards
    
    def get_board(self, board_id: str) -> Board:
        """
        Get a specific board by ID.
        
        Parameters
        ----------
        board_id : str
            The unique identifier of the board.
            Use the string "none" (not Python's None) for uncategorized board.
            
            Why "none" instead of None:
            - InvokeAI API uses "none" as a special identifier in URL paths
            - Python's None cannot be used in URL paths (would need string conversion)
            - This follows InvokeAI's established API convention
        
        Returns
        -------
        Board
            The board object with full metadata.
        
        Raises
        ------
        ValueError
            If the board does not exist.
        
        Examples
        --------
        >>> # Get regular board
        >>> board = client.get_board("abc-123")
        
        >>> # Get uncategorized board - must use string "none"
        >>> uncategorized = client.get_board("none")
        """
        # Handle uncategorized board specially
        if board_id == "none" or board_id is None:
            count = self.get_uncategorized_images_count()
            return Board.uncategorized(image_count=count)
        
        try:
            response = self._make_request('GET', f'/boards/{board_id}')
            return Board.from_api_response(response.json())
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Board with ID '{board_id}' does not exist")
            raise
    
    def create_board(self, name: str, is_private: bool = False) -> Board:
        """
        Create a new board.
        
        Note: The "Uncategorized" board is system-managed and cannot be created.
        
        Parameters
        ----------
        name : str
            The name for the new board (max 300 characters).
            Cannot be "Uncategorized" or "uncategorized".
        is_private : bool, optional
            Whether the board should be private, by default False.
        
        Returns
        -------
        Board
            The newly created board object.
        
        Raises
        ------
        ValueError
            If the board name is invalid, reserved, or too long.
        
        Examples
        --------
        >>> board = client.create_board("My Artwork")
        >>> print(f"Created board: {board.board_name} ({board.board_id})")
        """
        # Validate board name
        if name.lower() == "uncategorized":
            raise ValueError("Cannot create board with reserved name 'Uncategorized'")
        
        if len(name) > 300:
            raise ValueError(f"Board name too long: {len(name)} characters (max 300)")
        
        params = {
            'board_name': name,
            'is_private': is_private
        }
        
        response = self._make_request('POST', '/boards/', params=params)
        return Board.from_api_response(response.json())
    
    def get_uncategorized_images_count(self) -> int:
        """
        Get the count of uncategorized images (images not assigned to any board).
        
        This method uses the API endpoint /boards/none/image_names where "none"
        is the special board_id value that InvokeAI uses to represent uncategorized
        items. This is a string literal, not Python's None value.
        
        Returns
        -------
        int
            Number of uncategorized images.
        
        Examples
        --------
        >>> count = client.get_uncategorized_images_count()
        >>> print(f"Uncategorized images: {count}")
        """
        try:
            # Get list of uncategorized image names
            response = self._make_request('GET', '/boards/none/image_names')
            image_names = response.json()
            
            # Return count of images
            if isinstance(image_names, list):
                return len(image_names)
            return 0
        except requests.HTTPError:
            # If endpoint fails, return 0
            return 0
    
    def get_uncategorized_images(self) -> List[str]:
        """
        Get the list of uncategorized image names.
        
        Uses the API endpoint /boards/none/image_names where "none" is InvokeAI's
        special convention for accessing uncategorized items. This must be the
        string "none", not Python's None value, as it's used as a URL path parameter.
        
        Returns
        -------
        List[str]
            List of image names that are not assigned to any board.
        
        Examples
        --------
        >>> images = client.get_uncategorized_images()
        >>> print(f"Found {len(images)} uncategorized images")
        """
        try:
            response = self._make_request('GET', '/boards/none/image_names')
            image_names = response.json()
            
            if isinstance(image_names, list):
                return image_names
            return []
        except requests.HTTPError:
            return []
    
    def delete_board(self, board_id: str, delete_images: bool = False) -> None:
        """
        Delete a board.
        
        Note: The uncategorized board cannot be deleted as it is system-managed.
        We check for both board_id="none" (the API convention) and board_id=None
        (edge case) to prevent deletion attempts.
        
        Parameters
        ----------
        board_id : str
            The ID of the board to delete.
            Cannot be "none" (InvokeAI's identifier for uncategorized board).
        delete_images : bool, optional
            Whether to also delete all images in the board, by default False.
            If False, images are moved to uncategorized.
        
        Raises
        ------
        ValueError
            If trying to delete the uncategorized board or if board doesn't exist.
        
        Examples
        --------
        >>> client.delete_board("abc-123")  # Moves images to uncategorized
        >>> client.delete_board("abc-123", delete_images=True)  # Deletes images too
        """
        # Prevent deletion of system boards
        if board_id == "none" or board_id is None:
            raise ValueError("Cannot delete the uncategorized board (system-managed)")
        
        params = {'delete_board_images': delete_images}
        
        try:
            self._make_request('DELETE', f'/boards/{board_id}', params=params)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Board with ID '{board_id}' does not exist")
            raise
    
    def upload_image(
        self,
        image_path: Union[str, Path],
        board_id: Optional[str] = None,
        category: str = "user"
    ) -> Image:
        """
        Upload an image to the InvokeAI instance.
        
        Parameters
        ----------
        image_path : Union[str, Path]
            Path to the image file to upload.
        board_id : str, optional
            Target board ID. If None, image goes to uncategorized.
        category : str, optional
            Image category, by default "user".
        
        Returns
        -------
        Image
            The uploaded image object with server-assigned metadata.
        
        Raises
        ------
        FileNotFoundError
            If the image file does not exist.
        IOError
            If the upload fails.
        
        Examples
        --------
        >>> image = client.upload_image("input.png", board_id="my-board-id")
        >>> print(f"Uploaded as: {image.name}")
        """
        raise NotImplementedError
    
    def download_image(
        self,
        image_name: str,
        output_path: Optional[Union[str, Path]] = None,
        full_resolution: bool = True
    ) -> Path:
        """
        Download an image from the InvokeAI instance.
        
        Parameters
        ----------
        image_name : str
            The server-side name of the image.
        output_path : Union[str, Path], optional
            Where to save the image. If None, uses temp directory.
        full_resolution : bool, optional
            Whether to download full resolution, by default True.
        
        Returns
        -------
        Path
            Path to the downloaded image file.
        
        Raises
        ------
        ValueError
            If the image does not exist.
        IOError
            If the download fails.
        """
        raise NotImplementedError
    
    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Job]:
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
        List[Job]
            List of job objects.
        """
        raise NotImplementedError
    
    def get_job(self, job_id: str) -> Job:
        """
        Get detailed information about a specific job.
        
        Parameters
        ----------
        job_id : str
            The unique job identifier.
        
        Returns
        -------
        Job
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
    
    def list_models(self, base_model: Optional[str] = None) -> List[DnnModel]:
        """
        List available models on the InvokeAI instance.
        
        Parameters
        ----------
        base_model : str, optional
            Filter by base model type ('sdxl', 'sd-1', 'sd-2', etc.).
        
        Returns
        -------
        List[DnnModel]
            List of model objects.
        """
        raise NotImplementedError
    
    def get_model_info(self, model_key: str) -> DnnModel:
        """
        Get detailed information about a specific model.
        
        Parameters
        ----------
        model_key : str
            The model identifier key.
        
        Returns
        -------
        DnnModel
            DnnModel metadata and configuration.
        
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
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return bool(response.status_code == 200)
        except Exception:
            return False
    
    def close(self) -> None:
        """
        Close the client connection and clean up resources.
        
        This method should be called when the client is no longer needed,
        or used with a context manager.
        """
        if hasattr(self, 'session'):
            self.session.close()
    
    def __enter__(self) -> InvokeAIClient:
        """Context manager entry."""
        return self
    
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Context manager exit."""
        self.close()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any
    ) -> requests.Response:
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
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        # Make the request
        response = self.session.request(method, url, **kwargs)
        
        # Raise for HTTP errors
        response.raise_for_status()
        
        return response