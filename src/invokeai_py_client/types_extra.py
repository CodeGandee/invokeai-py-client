"""Advanced type definitions for InvokeAI Python client.

This module provides TypedDict, Protocol, and other advanced type definitions
that are used throughout the client library for strong typing support.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    TypedDict,
    Union,
    Literal,
    TYPE_CHECKING,
    runtime_checkable,
    Callable,
    Awaitable,
)
from typing_extensions import NotRequired, Required, Final
from datetime import datetime
from pathlib import Path

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt
    import aiohttp
    import requests


# Constants with Literal types
HTTPMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
ImageFormat = Literal["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"]
ModelBase = Literal["sd-1", "sd-2", "sdxl", "sd-3", "flux"]
ModelType = Literal["main", "vae", "lora", "controlnet", "textual_inversion", "ip_adapter"]
NodeStatus = Literal["pending", "in_progress", "completed", "failed", "cancelled"]

# TypedDict definitions for API responses
class ImageResponseDict(TypedDict):
    """Type definition for image API response."""
    image_name: str
    width: int
    height: int
    created_at: str
    updated_at: str
    board_id: NotRequired[str]
    metadata: NotRequired[Dict[str, Any]]
    thumbnail_url: NotRequired[str]
    url: str


class ModelResponseDict(TypedDict):
    """Type definition for model API response."""
    key: str
    hash: str
    name: str
    base: ModelBase
    type: ModelType
    submodel_type: NotRequired[str]
    format: NotRequired[str]
    path: NotRequired[str]
    description: NotRequired[str]
    source: NotRequired[str]
    vae: NotRequired[str]


class BoardResponseDict(TypedDict):
    """Type definition for board API response."""
    board_id: str
    board_name: str
    description: NotRequired[str]
    created_at: str
    updated_at: str
    image_count: int
    cover_image_name: NotRequired[str]


class WorkflowNodeDict(TypedDict):
    """Type definition for workflow node."""
    id: str
    type: str
    data: Dict[str, Any]
    position: NotRequired[Dict[str, float]]
    width: NotRequired[float]
    height: NotRequired[float]


class WorkflowEdgeDict(TypedDict):
    """Type definition for workflow edge."""
    id: str
    source: str
    target: str
    sourceHandle: str
    targetHandle: str
    type: NotRequired[str]


class WorkflowDefinitionDict(TypedDict):
    """Type definition for workflow definition."""
    id: str
    name: str
    version: str
    description: NotRequired[str]
    notes: NotRequired[str]
    tags: NotRequired[List[str]]
    author: NotRequired[str]
    contact: NotRequired[str]
    nodes: List[WorkflowNodeDict]
    edges: List[WorkflowEdgeDict]
    form: NotRequired[Dict[str, Any]]
    meta: NotRequired[Dict[str, Any]]


class JobStatusDict(TypedDict):
    """Type definition for job status response."""
    job_id: str
    batch_id: NotRequired[str]
    status: NodeStatus
    created_at: str
    started_at: NotRequired[str]
    completed_at: NotRequired[str]
    error: NotRequired[str]
    error_type: NotRequired[str]
    error_details: NotRequired[Dict[str, Any]]
    progress: NotRequired[float]
    current_node: NotRequired[str]
    total_nodes: NotRequired[int]
    completed_nodes: NotRequired[int]


class APIErrorDict(TypedDict):
    """Type definition for API error response."""
    detail: NotRequired[str]
    message: NotRequired[str]
    error: NotRequired[str]
    error_code: NotRequired[str]
    status_code: NotRequired[int]
    timestamp: NotRequired[str]
    path: NotRequired[str]
    method: NotRequired[str]


# Protocol definitions for duck typing
@runtime_checkable
class Uploadable(Protocol):
    """Protocol for objects that can be uploaded to InvokeAI."""
    
    async def upload(self, client: Any) -> str:
        """Upload the resource and return its server-side ID."""
        ...
    
    def to_api_value(self) -> Any:
        """Convert to API-compatible value."""
        ...


@runtime_checkable
class Downloadable(Protocol):
    """Protocol for objects that can be downloaded from InvokeAI."""
    
    async def download(self, client: Any) -> Any:
        """Download the resource from server."""
        ...


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to/from JSON."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
        """Create instance from dictionary."""
        ...


@runtime_checkable
class AsyncExecutable(Protocol):
    """Protocol for objects that can be executed asynchronously."""
    
    async def execute(self, timeout: Optional[float] = None) -> Any:
        """Execute the operation asynchronously."""
        ...


# Type aliases for complex types
if TYPE_CHECKING:
    ImageArrayType = Union[npt.NDArray[np.uint8], npt.NDArray[np.float32]]
    HTTPResponse = Union[requests.Response, aiohttp.ClientResponse]
else:
    ImageArrayType = Any
    HTTPResponse = Any

PathLike = Union[str, Path]
ConfigValue = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
Headers = Dict[str, str]
QueryParams = Dict[str, Union[str, int, float, bool, List[str]]]
FormData = Dict[str, Union[str, bytes, Any]]  # aiohttp.FormData
JSONData = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
RequestData = Union[JSONData, FormData, bytes, str]

# Callback type definitions
ProgressCallback = Callable[[float, str], None]
ErrorCallback = Callable[[Exception], None]
CompletionCallback = Callable[[Any], None]
AsyncProgressCallback = Callable[[float, str], Awaitable[None]]
AsyncErrorCallback = Callable[[Exception], Awaitable[None]]
AsyncCompletionCallback = Callable[[Any], Awaitable[None]]

# Response type definitions
APIResponse = Union[Dict[str, Any], List[Any], str, bytes]

# Workflow type definitions
WorkflowInputValue = Union[str, int, float, bool, Dict[str, Any], List[Any]]
WorkflowOutputValue = Union[str, int, float, bool, Dict[str, Any], List[Any], bytes]
NodeFieldConfig = Dict[str, Any]

# Final constants
MAX_RETRIES: Final[int] = 3
DEFAULT_TIMEOUT: Final[float] = 30.0
DEFAULT_POLL_INTERVAL: Final[float] = 1.0
MAX_IMAGE_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
SUPPORTED_IMAGE_FORMATS: Final[tuple[str, ...]] = ("png", "jpg", "jpeg", "webp")
API_VERSION: Final[str] = "v1"

# Type guards
def is_image_response(obj: Any) -> bool:
    """Type guard for ImageResponseDict."""
    return (
        isinstance(obj, dict) 
        and "image_name" in obj 
        and "width" in obj 
        and "height" in obj
    )


def is_model_response(obj: Any) -> bool:
    """Type guard for ModelResponseDict."""
    return (
        isinstance(obj, dict)
        and "key" in obj
        and "hash" in obj
        and "name" in obj
        and "base" in obj
        and "type" in obj
    )


def is_board_response(obj: Any) -> bool:
    """Type guard for BoardResponseDict."""
    return (
        isinstance(obj, dict)
        and "board_id" in obj
        and "board_name" in obj
    )


def is_job_status(obj: Any) -> bool:
    """Type guard for JobStatusDict."""
    return (
        isinstance(obj, dict)
        and "job_id" in obj
        and "status" in obj
    )


def is_api_error(obj: Any) -> bool:
    """Type guard for APIErrorDict."""
    return (
        isinstance(obj, dict)
        and any(key in obj for key in ["detail", "message", "error"])
    )