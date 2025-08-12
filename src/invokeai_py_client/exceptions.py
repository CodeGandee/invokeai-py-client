"""Custom exceptions for InvokeAI Python client.

This module defines a hierarchy of exceptions for the InvokeAI client library,
providing semantic error handling for various failure scenarios.
"""

from typing import Optional, Any, Dict, TYPE_CHECKING, Final
from typing_extensions import Self
import requests

if TYPE_CHECKING:
    from .types_extra import APIErrorDict


class InvokeAIError(Exception):
    """Base exception for all InvokeAI client errors.
    
    This is the root exception class that all other InvokeAI exceptions inherit from.
    It provides common functionality for error context preservation and debugging.
    
    Attributes
    ----------
    message : str
        Human-readable error message.
    cause : Optional[Exception]
        The underlying exception that caused this error, if any.
    context : Dict[str, Any]
        Additional context information for debugging.
    
    Examples
    --------
    >>> try:
    ...     # Some InvokeAI operation
    ...     client.workflows.submit(wf)
    ... except InvokeAIError as e:
    ...     print(f"InvokeAI operation failed: {e}")
    ...     if e.cause:
    ...         print(f"Caused by: {e.cause}")
    """
    
    def __init__(
        self, 
        message: str, 
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize InvokeAI error.
        
        Parameters
        ----------
        message : str
            The error message.
        cause : Optional[Exception]
            The underlying exception that caused this error.
        context : Optional[Dict[str, Any]]
            Additional context information for debugging.
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class ConnectionError(InvokeAIError):
    """Raised when unable to connect to InvokeAI instance.
    
    This exception indicates network-level connection failures such as
    host unreachable, connection refused, or timeout errors.
    
    Attributes
    ----------
    host : str
        The host that failed to connect.
    port : int
        The port number attempted.
    timeout : Optional[float]
        The connection timeout in seconds, if specified.
    
    Examples
    --------
    >>> try:
    ...     client = InvokeAIClient("http://invalid-host:9090")
    ... except ConnectionError as e:
    ...     print(f"Failed to connect to {e.host}:{e.port}")
    """
    
    def __init__(
        self, 
        host: str, 
        port: int, 
        message: Optional[str] = None,
        cause: Optional[Exception] = None,
        timeout: Optional[float] = None
    ) -> None:
        """Initialize connection error."""
        msg = message or f"Failed to connect to InvokeAI at {host}:{port}"
        super().__init__(msg, cause)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context.update({"host": host, "port": port, "timeout": timeout})


class AuthenticationError(InvokeAIError):
    """Raised when authentication with InvokeAI fails.
    
    This exception indicates authentication failures such as invalid
    API keys, expired tokens, or insufficient permissions.
    
    Attributes
    ----------
    auth_method : str
        The authentication method attempted (e.g., "api_key", "token").
    status_code : Optional[int]
        HTTP status code if from HTTP response.
    
    Examples
    --------
    >>> try:
    ...     client = InvokeAIClient("http://localhost:9090", api_key="invalid")
    ... except AuthenticationError as e:
    ...     print(f"Authentication failed: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        auth_method: str = "unknown",
        status_code: Optional[int] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize authentication error."""
        super().__init__(message, cause)
        self.auth_method = auth_method
        self.status_code = status_code
        self.context.update({"auth_method": auth_method, "status_code": status_code})


class ValidationError(InvokeAIError):
    """Raised when input validation fails.
    
    This exception indicates that provided inputs don't meet the
    requirements or constraints of the InvokeAI API or workflow.
    
    Attributes
    ----------
    field : Optional[str]
        The field that failed validation, if applicable.
    value : Any
        The value that failed validation.
    constraints : Optional[Dict[str, Any]]
        The constraints that were violated.
    
    Examples
    --------
    >>> try:
    ...     workflow.set_input("width", -100)  # Invalid negative width
    ... except ValidationError as e:
    ...     print(f"Invalid {e.field}: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        constraints: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize validation error."""
        super().__init__(message, cause)
        self.field = field
        self.value = value
        self.constraints = constraints or {}
        self.context.update({
            "field": field,
            "value": value,
            "constraints": constraints
        })


class WorkflowError(InvokeAIError):
    """Base class for workflow-related errors.
    
    This exception represents errors specific to workflow operations
    such as loading, validation, or execution failures.
    
    Attributes
    ----------
    workflow_id : Optional[str]
        The ID of the workflow involved, if available.
    workflow_name : Optional[str]
        The name of the workflow, if available.
    """
    
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize workflow error."""
        super().__init__(message, cause)
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.context.update({
            "workflow_id": workflow_id,
            "workflow_name": workflow_name
        })


class WorkflowLoadError(WorkflowError):
    """Raised when a workflow fails to load.
    
    This exception indicates failures in loading workflow definitions
    from JSON files or parsing workflow structure.
    
    Attributes
    ----------
    file_path : Optional[str]
        Path to the workflow file that failed to load.
    parse_error : Optional[str]
        Specific parsing error message, if applicable.
    
    Examples
    --------
    >>> try:
    ...     workflow = ClientWorkflow.from_file("invalid.json")
    ... except WorkflowLoadError as e:
    ...     print(f"Failed to load workflow from {e.file_path}")
    """
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        parse_error: Optional[str] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize workflow load error."""
        super().__init__(message, cause=cause)
        self.file_path = file_path
        self.parse_error = parse_error
        self.context.update({
            "file_path": file_path,
            "parse_error": parse_error
        })


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails.
    
    This exception indicates failures during workflow execution on
    the InvokeAI server, including node failures or processing errors.
    
    Attributes
    ----------
    job_id : Optional[str]
        The job ID of the failed execution.
    node_id : Optional[str]
        The ID of the node that failed, if applicable.
    error_details : Optional[Dict[str, Any]]
        Detailed error information from the server.
    
    Examples
    --------
    >>> try:
    ...     result = await workflow.execute()
    ... except WorkflowExecutionError as e:
    ...     print(f"Workflow execution failed at node {e.node_id}")
    """
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        node_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize workflow execution error."""
        super().__init__(message, workflow_id=workflow_id, cause=cause)
        self.job_id = job_id
        self.node_id = node_id
        self.error_details = error_details or {}
        self.context.update({
            "job_id": job_id,
            "node_id": node_id,
            "error_details": error_details
        })


class ResourceNotFoundError(InvokeAIError):
    """Raised when a requested resource is not found.
    
    This exception indicates that a requested resource (workflow, image,
    model, etc.) does not exist on the InvokeAI server.
    
    Attributes
    ----------
    resource_type : str
        Type of resource (e.g., "workflow", "image", "model").
    resource_id : str
        The identifier of the missing resource.
    
    Examples
    --------
    >>> try:
    ...     image = client.images.get("non-existent-id")
    ... except ResourceNotFoundError as e:
    ...     print(f"{e.resource_type} with ID {e.resource_id} not found")
    """
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize resource not found error."""
        msg = message or f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(msg, cause)
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.context.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })


class TimeoutError(InvokeAIError):
    """Raised when an operation times out.
    
    This exception indicates that an operation exceeded its time limit,
    such as waiting for a workflow to complete or a connection attempt.
    
    Attributes
    ----------
    operation : str
        Description of the operation that timed out.
    timeout_seconds : float
        The timeout duration in seconds.
    
    Examples
    --------
    >>> try:
    ...     result = workflow.execute(timeout=30)
    ... except TimeoutError as e:
    ...     print(f"Operation '{e.operation}' timed out after {e.timeout_seconds}s")
    """
    
    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        message: Optional[str] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize timeout error."""
        msg = message or f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        super().__init__(msg, cause)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.context.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })


class APIError(InvokeAIError):
    """Raised when the InvokeAI API returns an error.
    
    This exception wraps HTTP errors from the InvokeAI REST API,
    providing access to status codes and response details.
    
    Attributes
    ----------
    status_code : int
        HTTP status code from the API response.
    response_body : Optional[Dict[str, Any]]
        The response body, if available.
    request_method : str
        The HTTP method used (GET, POST, etc.).
    request_url : str
        The URL that was requested.
    
    Examples
    --------
    >>> try:
    ...     response = client._request("POST", "/invalid-endpoint")
    ... except APIError as e:
    ...     print(f"API returned {e.status_code}: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        status_code: int,
        request_method: str,
        request_url: str,
        response_body: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize API error."""
        super().__init__(message, cause)
        self.status_code = status_code
        self.response_body = response_body
        self.request_method = request_method
        self.request_url = request_url
        self.context.update({
            "status_code": status_code,
            "response_body": response_body,
            "request_method": request_method,
            "request_url": request_url
        })
    
    @classmethod
    def from_response(cls, response: requests.Response) -> Self:
        """Create APIError from requests Response object.
        
        Parameters
        ----------
        response : requests.Response
            The response object from requests library.
        
        Returns
        -------
        APIError
            An APIError instance with details from the response.
        """
        try:
            body = response.json()
            message = body.get("detail", body.get("message", response.reason))
        except Exception:
            body = None
            message = response.reason or f"HTTP {response.status_code} error"
        
        return cls(
            message=message,
            status_code=response.status_code,
            request_method=getattr(response.request, 'method', 'UNKNOWN'),
            request_url=str(getattr(response.request, 'url', '')),
            response_body=body
        )


class ConfigurationError(InvokeAIError):
    """Raised when client configuration is invalid.
    
    This exception indicates problems with client configuration such as
    invalid base URLs, missing required settings, or incompatible options.
    
    Attributes
    ----------
    config_key : Optional[str]
        The configuration key that has an issue.
    config_value : Any
        The problematic configuration value.
    
    Examples
    --------
    >>> try:
    ...     client = InvokeAIClient(base_url="not-a-url")
    ... except ConfigurationError as e:
    ...     print(f"Invalid configuration: {e.message}")
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Any = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize configuration error."""
        super().__init__(message, cause)
        self.config_key = config_key
        self.config_value = config_value
        self.context.update({
            "config_key": config_key,
            "config_value": config_value
        })


class TypeConversionError(InvokeAIError):
    """Raised when type conversion fails.
    
    This exception indicates failures in converting between Python types
    and InvokeAI field types, or when type constraints are violated.
    
    Attributes
    ----------
    from_type : str
        The source type name.
    to_type : str
        The target type name.
    value : Any
        The value that failed to convert.
    
    Examples
    --------
    >>> try:
    ...     int_field = InvokeAIInteger.from_value("not-a-number")
    ... except TypeConversionError as e:
    ...     print(f"Cannot convert {e.value} from {e.from_type} to {e.to_type}")
    """
    
    def __init__(
        self,
        message: str,
        from_type: str,
        to_type: str,
        value: Any = None,
        cause: Optional[Exception] = None
    ) -> None:
        """Initialize type conversion error."""
        super().__init__(message, cause)
        self.from_type = from_type
        self.to_type = to_type
        self.value = value
        self.context.update({
            "from_type": from_type,
            "to_type": to_type,
            "value": value
        })