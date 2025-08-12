"""InvokeAI Python Client Library

A Python client library for interacting with InvokeAI as a remote model
inference service. This package provides a user-friendly, Pythonic API for
common tasks like loading workflows exported from the InvokeAI GUI, setting
typed inputs, submitting jobs, tracking status, and retrieving results.

Notes
-----
- Source tree for this package: ``src/invokeai_py_client``
- InvokeAI reference code (for context only): ``context/refcode/InvokeAI``
- Workflow examples (JSON exported from GUI): ``data/workflows``

"""

__version__ = "0.1.0"
__author__ = "CodeGandee"

# Public API surface
from .client import InvokeAIClient
from .workflow import InvokeAIWorkflow
from . import types as invokeai_types
from .models import JobInfo, JobState, AssetInfo, BoardInfo
from .exceptions import (
	InvokeAIClientError,
	InvokeAIConnectionError,
	InvokeAIRequestError,
	InvokeAIWorkflowError,
	InvokeAIValidationError,
)

__all__ = [
	"InvokeAIClient",
	"InvokeAIWorkflow",
	"invokeai_types",
	"JobInfo",
	"JobState",
	"AssetInfo",
	"BoardInfo",
	"InvokeAIClientError",
	"InvokeAIConnectionError",
	"InvokeAIRequestError",
	"InvokeAIWorkflowError",
	"InvokeAIValidationError",
]
