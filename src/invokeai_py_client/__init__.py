"""InvokeAI Python Client Library.

A Pythonic, task-oriented client library for interacting with InvokeAI instances.
This library provides high-level abstractions for managing workflows, images, and
models without requiring deep knowledge of the underlying REST API.

Basic Usage
-----------
>>> from invokeai_py_client import InvokeAIClient, ClientWorkflow
>>> 
>>> # Initialize client
>>> client = InvokeAIClient("http://localhost:9090")
>>> 
>>> # Load and execute a workflow
>>> workflow = client.create_workflow("text-to-image.json")
>>> workflow.set_input("prompt", "a beautiful landscape")
>>> workflow.set_input("width", 1024)
>>> workflow.set_input("height", 768)
>>> 
>>> # Execute workflow
>>> result = await workflow.execute()
>>> 
>>> # Get generated images
>>> images = result.get_images()
>>> for image in images:
>>>     data = await client.images.download(image.image_name)

Key Components
--------------
InvokeAIClient : Main client class
    Primary interface for connecting to and interacting with InvokeAI.
    
ClientWorkflow : Workflow management
    Load, configure, and execute workflows from JSON definitions.
    
InvokeAI Types : Type system
    Strongly-typed representations of InvokeAI field types.
    
Resource Managers : Images, Models, Boards
    High-level interfaces for managing InvokeAI resources.

Environment Variables
---------------------
INVOKEAI_API_KEY : str
    API key for authentication (optional).

Version Information
-------------------
The current version is available as `invokeai_py_client.__version__`.
"""

from typing import Final

__version__: Final[str] = "0.1.0"
__author__: Final[str] = "InvokeAI Python Client Contributors"
__license__: Final[str] = "MIT"

# Core client
from .client import (
    InvokeAIClient,
    ClientConfig,
    ImageManager,
    ModelManager,
    BoardManager,
)

# Workflow management
from .workflow import (
    ClientWorkflow,
    WorkflowStatus,
    WorkflowInput,
    WorkflowOutput,
    WorkflowResult,
)

# Type system
from .types import (
    # Base type
    InvokeAIType,
    
    # Primitive types
    InvokeAIInteger,
    InvokeAIFloat,
    InvokeAIBoolean,
    InvokeAIString,
    
    # Resource types
    InvokeAIImage,
    InvokeAIModelReference,
    InvokeAIBoardReference,
    
    # Enum types
    SchedulerType,
    InvokeAIScheduler,
    
    # Collection type
    InvokeAICollection,
    
    # Type registry
    TypeRegistry,
    TYPE_REGISTRY,
)

# Exceptions
from .exceptions import (
    # Base exception
    InvokeAIError,
    
    # Connection and auth
    ConnectionError,
    AuthenticationError,
    
    # Validation
    ValidationError,
    TypeConversionError,
    
    # Workflow errors
    WorkflowError,
    WorkflowLoadError,
    WorkflowExecutionError,
    
    # Resource errors
    ResourceNotFoundError,
    
    # Operation errors
    TimeoutError,
    APIError,
    ConfigurationError,
)

# Public API
__all__: Final[list[str]] = [
    # Version
    "__version__",
    
    # Client
    "InvokeAIClient",
    "ClientConfig",
    "ImageManager",
    "ModelManager",
    "BoardManager",
    
    # Workflow
    "ClientWorkflow",
    "WorkflowStatus",
    "WorkflowInput",
    "WorkflowOutput",
    "WorkflowResult",
    
    # Types - Base
    "InvokeAIType",
    
    # Types - Primitives
    "InvokeAIInteger",
    "InvokeAIFloat",
    "InvokeAIBoolean",
    "InvokeAIString",
    
    # Types - Resources
    "InvokeAIImage",
    "InvokeAIModelReference",
    "InvokeAIBoardReference",
    
    # Types - Enums
    "SchedulerType",
    "InvokeAIScheduler",
    
    # Types - Collections
    "InvokeAICollection",
    
    # Types - Registry
    "TypeRegistry",
    "TYPE_REGISTRY",
    
    # Exceptions
    "InvokeAIError",
    "ConnectionError",
    "AuthenticationError",
    "ValidationError",
    "TypeConversionError",
    "WorkflowError",
    "WorkflowLoadError",
    "WorkflowExecutionError",
    "ResourceNotFoundError",
    "TimeoutError",
    "APIError",
    "ConfigurationError",
]


def get_version() -> str:
    """Get the current version of the InvokeAI Python client.
    
    Returns
    -------
    str
        Version string in format "major.minor.patch".
    
    Examples
    --------
    >>> import invokeai_py_client
    >>> print(invokeai_py_client.get_version())
    0.1.0
    """
    return __version__


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for the InvokeAI client.
    
    Parameters
    ----------
    level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    
    Examples
    --------
    >>> import invokeai_py_client
    >>> invokeai_py_client.configure_logging("DEBUG")
    """
    import logging
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set specific loggers
    logging.getLogger("invokeai_py_client").setLevel(level)
    logging.getLogger("aiohttp").setLevel("WARNING")
    logging.getLogger("requests").setLevel("WARNING")
    logging.getLogger("urllib3").setLevel("WARNING")