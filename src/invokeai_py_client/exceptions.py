"""
Exception classes for InvokeAI Python client.

This module defines a hierarchy of exceptions for error handling
in the InvokeAI client library.
"""

from typing import Any, Optional


class InvokeAIError(Exception):
    """
    Base exception for all InvokeAI client errors.

    Parameters
    ----------
    message : str
        Error message.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    message : str
        The error message.
    details : Dict[str, Any]
        Additional context about the error.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the exception."""
        raise NotImplementedError


class ConnectionError(InvokeAIError):
    """
    Raised when connection to InvokeAI server fails.

    Parameters
    ----------
    message : str
        Error message.
    host : str, optional
        Server hostname.
    port : int, optional
        Server port.
    details : Dict[str, Any], optional
        Additional error details.

    Examples
    --------
    >>> raise ConnectionError(
    ...     "Failed to connect to InvokeAI server",
    ...     host="localhost",
    ...     port=9090
    ... )
    """

    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the connection error."""
        raise NotImplementedError


class AuthenticationError(InvokeAIError):
    """
    Raised when authentication with the server fails.

    Parameters
    ----------
    message : str
        Error message.
    details : Dict[str, Any], optional
        Additional error details.

    Examples
    --------
    >>> raise AuthenticationError("Invalid API key provided")
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the authentication error."""
        raise NotImplementedError


class APIError(InvokeAIError):
    """
    Raised when the InvokeAI API returns an error.

    Parameters
    ----------
    message : str
        Error message.
    status_code : int, optional
        HTTP status code.
    response_body : Any, optional
        Raw response body.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    status_code : int
        The HTTP status code from the API.
    response_body : Any
        The raw response body.

    Examples
    --------
    >>> raise APIError(
    ...     "Resource not found",
    ...     status_code=404,
    ...     response_body={"error": "Board does not exist"}
    ... )
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the API error."""
        raise NotImplementedError


class ValidationError(InvokeAIError):
    """
    Raised when input validation fails.

    Parameters
    ----------
    message : str
        Error message.
    field_name : str, optional
        Name of the invalid field.
    field_value : Any, optional
        The invalid value.
    constraints : Dict[str, Any], optional
        Validation constraints that were violated.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    field_name : str
        The field that failed validation.
    field_value : Any
        The value that was invalid.
    constraints : Dict[str, Any]
        The constraints that were violated.

    Examples
    --------
    >>> raise ValidationError(
    ...     "Width must be between 64 and 2048",
    ...     field_name="width",
    ...     field_value=50,
    ...     constraints={"minimum": 64, "maximum": 2048}
    ... )
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        constraints: Optional[dict[str, Any]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the validation error."""
        raise NotImplementedError


class WorkflowError(InvokeAIError):
    """
    Raised when workflow operations fail.

    Parameters
    ----------
    message : str
        Error message.
    workflow_id : str, optional
        Workflow identifier.
    workflow_name : str, optional
        Workflow name.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    workflow_id : str
        The workflow that caused the error.
    workflow_name : str
        The workflow display name.

    Examples
    --------
    >>> raise WorkflowError(
    ...     "Missing required input: prompt",
    ...     workflow_name="text2img",
    ...     details={"missing_inputs": ["prompt", "seed"]}
    ... )
    """

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the workflow error."""
        raise NotImplementedError


class JobError(InvokeAIError):
    """
    Raised when job execution fails.

    Parameters
    ----------
    message : str
        Error message.
    job_id : str, optional
        Job identifier.
    status : str, optional
        Job status when error occurred.
    error_details : str, optional
        Detailed error from the job.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    job_id : str
        The job that failed.
    status : str
        The job status.
    error_details : str
        Detailed error message from the server.

    Examples
    --------
    >>> raise JobError(
    ...     "Job execution failed",
    ...     job_id="job-123",
    ...     status="failed",
    ...     error_details="Out of memory during generation"
    ... )
    """

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        error_details: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the job error."""
        raise NotImplementedError


class ResourceNotFoundError(APIError):
    """
    Raised when a requested resource doesn't exist.

    Parameters
    ----------
    resource_type : str
        Type of resource (board, image, model, etc.).
    resource_id : str
        Resource identifier.
    message : str, optional
        Error message.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    resource_type : str
        The type of resource not found.
    resource_id : str
        The identifier of the missing resource.

    Examples
    --------
    >>> raise ResourceNotFoundError(
    ...     resource_type="board",
    ...     resource_id="abc-123"
    ... )
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the resource not found error."""
        raise NotImplementedError


class TimeoutError(InvokeAIError):
    """
    Raised when an operation times out.

    Parameters
    ----------
    message : str
        Error message.
    operation : str, optional
        The operation that timed out.
    timeout : float, optional
        Timeout duration in seconds.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    operation : str
        The operation that timed out.
    timeout : float
        The timeout duration.

    Examples
    --------
    >>> raise TimeoutError(
    ...     "Job execution timed out",
    ...     operation="wait_for_completion",
    ...     timeout=60.0
    ... )
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the timeout error."""
        raise NotImplementedError


class FileError(InvokeAIError):
    """
    Raised when file operations fail.

    Parameters
    ----------
    message : str
        Error message.
    file_path : str, optional
        Path to the problematic file.
    operation : str, optional
        The file operation that failed.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    file_path : str
        The file that caused the error.
    operation : str
        The operation that failed (upload, download, read, write).

    Examples
    --------
    >>> raise FileError(
    ...     "Failed to upload image",
    ...     file_path="/path/to/image.png",
    ...     operation="upload"
    ... )
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the file error."""
        raise NotImplementedError


class ConfigurationError(InvokeAIError):
    """
    Raised when client configuration is invalid.

    Parameters
    ----------
    message : str
        Error message.
    config_key : str, optional
        The configuration key that's invalid.
    config_value : Any, optional
        The invalid configuration value.
    details : Dict[str, Any], optional
        Additional error details.

    Attributes
    ----------
    config_key : str
        The configuration parameter.
    config_value : Any
        The invalid value.

    Examples
    --------
    >>> raise ConfigurationError(
    ...     "Invalid port number",
    ...     config_key="port",
    ...     config_value=-1
    ... )
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize the configuration error."""
        raise NotImplementedError
