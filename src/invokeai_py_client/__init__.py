"""
InvokeAI Python Client Library.

A pythonic client library for interacting with InvokeAI instances,
providing high-level abstractions for workflow execution, asset management,
and AI image generation tasks.

Examples
--------
Basic usage:

>>> from invokeai_py_client import InvokeAIClient
>>> 
>>> # Connect to InvokeAI instance
>>> client = InvokeAIClient("localhost", 9090)
>>> 
>>> # Load and configure a workflow
>>> workflow = client.create_workflow("text2img.json")
>>> workflow.set_input("prompt", "A beautiful landscape")
>>> workflow.set_input("width", 1024)
>>> workflow.set_input("height", 768)
>>> 
>>> # Submit and wait for results
>>> job = workflow.submit_sync()
>>> results = workflow.wait_for_completion_sync()
>>> 
>>> # Download generated image
>>> image = results["output_image"]
>>> client.download_image(image.get_value(), "output.png")

Context manager usage:

>>> with InvokeAIClient("localhost", 9090) as client:
...     boards = client.list_boards()
...     for board in boards:
...         print(f"{board.name}: {board.image_count} images")
"""

__version__ = "0.1.0"
__author__ = "InvokeAI Python Client Contributors"

# Core client
from invokeai_py_client.client import InvokeAIClient

# Repositories
from invokeai_py_client.repositories import BoardRepository

# Workflow management
from invokeai_py_client.workflow import Workflow

# Field types - TODO: Implement these modules
# from invokeai_py_client.fields import (
#     Field,
#     IntegerField,
#     FloatField,
#     StringField,
#     BooleanField,
#     ImageField,
#     LatentsField,
#     ModelField,
#     EnumField,
#     ColorField,
#     ConditioningField,
#     CollectionField,
# )

# Data models
from invokeai_py_client.models import (
    Board,
    IvkImage,
    IvkJob,
    WorkflowDefinition,
    IvkDnnModel,
    SessionEvent,
    JobStatus,
    ImageCategory,
    BaseModelEnum,
)

# Exceptions - TODO: Implement these modules
# from invokeai_py_client.exceptions import (
#     InvokeAIError,
#     ConnectionError,
#     AuthenticationError,
#     APIError,
#     ValidationError,
#     WorkflowError,
#     JobError,
#     ResourceNotFoundError,
#     TimeoutError,
#     FileError,
#     ConfigurationError,
# )

# Utilities - TODO: Implement these modules
# from invokeai_py_client.utils import (
#     AssetManager,
#     BoardManager,
#     TypeConverter,
#     ProgressTracker,
# )

__all__ = [
    # Version
    "__version__",
    
    # Core
    "InvokeAIClient",
    "BoardRepository",
    "Workflow",
    
    # Models
    "Board",
    "IvkImage",
    "IvkJob",
    "WorkflowDefinition",
    "IvkDnnModel",
    "SessionEvent",
    "JobStatus",
    "ImageCategory",
    "BaseModelEnum",
]