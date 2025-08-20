"""
Workflow subsystem for InvokeAI client using repository pattern.

This package provides workflow management functionality following the repository pattern:
- WorkflowDefinition: Pydantic model for workflow JSON structure
- WorkflowHandle: Manages the running state of a workflow
- WorkflowRepository: Creates and manages workflow instances
"""

from invokeai_py_client.workflow.workflow_handle import (
    WorkflowHandle, 
    IvkWorkflowInput, 
    IvkWorkflowOutput,
    OutputMapping
)
from invokeai_py_client.workflow.workflow_model import WorkflowDefinition
from invokeai_py_client.workflow.workflow_repo import WorkflowRepository

__all__ = [
    "WorkflowDefinition",
    "WorkflowHandle",
    "WorkflowRepository",
    "IvkWorkflowInput",
    "IvkWorkflowOutput",
    "OutputMapping",
]
