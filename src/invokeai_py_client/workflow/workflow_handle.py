"""
Workflow handle for managing workflow execution state.

This module provides the WorkflowHandle class which represents the running state
of a workflow and manages input configuration, submission, and result retrieval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pydantic import BaseModel, ConfigDict

from invokeai_py_client.fields import Field
from invokeai_py_client.models import IvkJob

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient
    from invokeai_py_client.workflow.workflow_model import WorkflowDefinition


class InkWorkflowInput(BaseModel):
    """
    Represents a single workflow input with metadata and typed field.

    Attributes
    ----------
    label : str
        User-facing field label (e.g., "Positive Prompt").
    node_name : str
        Node's display name from label field or type.
    node_id : str
        UUID of the workflow node.
    field_name : str
        Name of the field in the node.
    field : Field
        The actual typed field instance.
    required : bool
        Whether this input must be provided.
    input_index : int
        0-based index from form tree traversal.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    label: str
    node_name: str
    node_id: str
    field_name: str
    field: Field[Any]
    required: bool
    input_index: int


class WorkflowHandle:
    """
    Manages the running state of a workflow instance.

    This class handles workflow configuration, submission, execution tracking,
    and result retrieval. It provides a pythonic interface for interacting
    with workflows exported from the InvokeAI GUI.

    Parameters
    ----------
    client : InvokeAIClient
        The client instance for API communication.
    definition : WorkflowDefinition
        The parsed workflow definition.

    Attributes
    ----------
    client : InvokeAIClient
        Reference to the parent client.
    definition : WorkflowDefinition
        The workflow structure and metadata.
    inputs : List[InkWorkflowInput]
        Ordered list of workflow inputs.
    job : Optional[IvkJob]
        Current or last job execution.
    uploaded_assets : List[str]
        Names of assets uploaded for this workflow.

    Examples
    --------
    >>> # Created by WorkflowRepository
    >>> workflow = repo.create_workflow(definition)
    >>> inputs = workflow.list_inputs()
    >>> workflow.get_input(0).field.value = "A beautiful landscape"
    >>> job = workflow.submit_sync()
    """

    def __init__(self, client: InvokeAIClient, definition: WorkflowDefinition) -> None:
        """Initialize the workflow handle."""
        self.client = client
        self.definition = definition
        self.inputs: list[InkWorkflowInput] = []
        self.job: IvkJob | None = None
        self.uploaded_assets: list[str] = []

        # Initialize inputs from the workflow definition
        self._initialize_inputs()

    def _initialize_inputs(self) -> None:
        """
        Initialize workflow inputs from the definition.

        This parses the form structure and exposed fields to create
        the ordered list of InkWorkflowInput objects.
        """
        # This is a placeholder - full implementation would parse
        # the form structure and create InkWorkflowInput instances
        # based on the exposed fields and their types
        pass

    def list_inputs(self) -> list[InkWorkflowInput]:
        """
        List all available workflow inputs.

        Returns
        -------
        List[InkWorkflowInput]
            Ordered list of input definitions.

        Examples
        --------
        >>> inputs = workflow.list_inputs()
        >>> for inp in inputs:
        ...     print(f"[{inp.input_index}] {inp.label}")
        """
        return self.inputs.copy()

    def get_input(self, index: int) -> InkWorkflowInput:
        """
        Get a workflow input by index.

        Parameters
        ----------
        index : int
            The 0-based input index.

        Returns
        -------
        InkWorkflowInput
            The input at the specified index.

        Raises
        ------
        IndexError
            If the index is out of range.

        Examples
        --------
        >>> prompt_input = workflow.get_input(0)
        >>> prompt_input.field.value = "A sunset"
        """
        if index < 0 or index >= len(self.inputs):
            raise IndexError(
                f"Input index {index} out of range (0-{len(self.inputs) - 1})"
            )
        return self.inputs[index]

    def get_all_inputs(self) -> list[InkWorkflowInput]:
        """
        Get all inputs as an indexed list.

        Returns
        -------
        List[InkWorkflowInput]
            All inputs where index matches input-index.
        """
        return self.inputs.copy()

    def get_missing_required_input_indices(self) -> list[int]:
        """
        Get indices of required inputs that have no value set.

        Returns
        -------
        List[int]
            List of indices for missing required inputs.

        Examples
        --------
        >>> missing = workflow.get_missing_required_input_indices()
        >>> if missing:
        ...     print(f"Missing inputs at indices: {missing}")
        """
        missing = []
        for inp in self.inputs:
            if inp.required and inp.field.get_value() is None:
                missing.append(inp.input_index)
        return missing

    def validate_inputs(self) -> dict[int, list[str]]:
        """
        Validate all configured inputs.

        Returns
        -------
        Dict[int, List[str]]
            Dictionary of input indices to validation errors.
            Empty dict means all inputs are valid.

        Examples
        --------
        >>> errors = workflow.validate_inputs()
        >>> if errors:
        ...     for idx, msgs in errors.items():
        ...         print(f"[{idx}]: {', '.join(msgs)}")
        """
        errors: dict[int, list[str]] = {}

        # Check required inputs
        for inp in self.inputs:
            if inp.required and inp.field.get_value() is None:
                if inp.input_index not in errors:
                    errors[inp.input_index] = []
                errors[inp.input_index].append("Required field is not set")

        # Additional validation would go here
        # (field-specific validation, inter-field dependencies, etc.)

        return errors

    def submit_sync(
        self,
        queue_id: str = "default",
        board_id: str | None = None,
        priority: int = 0,
    ) -> Any:  # Would return EnqueueBatchResult
        """
        Submit the workflow for execution synchronously.

        Parameters
        ----------
        queue_id : str
            The queue to submit to.
        board_id : str, optional
            Default board for outputs.
        priority : int
            Job priority (higher = more priority).

        Returns
        -------
        EnqueueBatchResult
            The submission result with batch and item IDs.

        Raises
        ------
        ValueError
            If validation fails or required inputs are missing.
        RuntimeError
            If submission fails.
        """
        raise NotImplementedError

    async def submit(
        self,
        queue_id: str = "default",
        board_id: str | None = None,
        priority: int = 0,
        subscribe_events: bool = False,
        on_invocation_started: Callable[[dict[str, Any]], None] | None = None,
        on_invocation_progress: Callable[[dict[str, Any]], None] | None = None,
        on_invocation_complete: Callable[[dict[str, Any]], None] | None = None,
        on_invocation_error: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any:  # Would return EnqueueBatchResult
        """
        Submit the workflow for execution asynchronously.

        Parameters
        ----------
        queue_id : str
            The queue to submit to.
        board_id : str, optional
            Default board for outputs.
        priority : int
            Job priority.
        subscribe_events : bool
            Whether to subscribe to Socket.IO events.
        on_invocation_started : Callable, optional
            Callback for node start events.
        on_invocation_progress : Callable, optional
            Callback for progress events.
        on_invocation_complete : Callable, optional
            Callback for node completion events.
        on_invocation_error : Callable, optional
            Callback for error events.

        Returns
        -------
        EnqueueBatchResult
            The submission result.
        """
        raise NotImplementedError

    def wait_for_completion_sync(
        self,
        poll_interval: float = 0.5,
        timeout: float = 60.0,
        progress_callback: Callable[[IvkJob], None] | None = None,
    ) -> IvkJob:
        """
        Wait for workflow completion synchronously.

        Parameters
        ----------
        poll_interval : float
            How often to check status in seconds.
        timeout : float
            Maximum time to wait in seconds.
        progress_callback : Callable, optional
            Callback for progress updates.

        Returns
        -------
        IvkJob
            The completed job.

        Raises
        ------
        TimeoutError
            If timeout is exceeded.
        RuntimeError
            If the job fails.
        """
        raise NotImplementedError

    async def wait_for_completion(self, timeout: float | None = None) -> IvkJob:
        """
        Wait for workflow completion asynchronously.

        Parameters
        ----------
        timeout : float, optional
            Maximum time to wait in seconds.

        Returns
        -------
        IvkJob
            The completed job.

        Raises
        ------
        asyncio.TimeoutError
            If timeout is exceeded.
        RuntimeError
            If the job fails.
        """
        raise NotImplementedError

    def get_queue_item(self) -> Any | None:  # Would return SessionQueueItem
        """
        Get the current queue item for tracking.

        Returns
        -------
        Optional[SessionQueueItem]
            The queue item if submitted, None otherwise.
        """
        raise NotImplementedError

    def cancel(self) -> bool:
        """
        Cancel the current workflow execution.

        Returns
        -------
        bool
            True if cancellation was successful.

        Raises
        ------
        RuntimeError
            If no job is running or cancellation fails.
        """
        raise NotImplementedError

    def get_outputs(self) -> Any:  # Would return WorkflowOutput
        """
        Get workflow outputs after completion.

        Returns
        -------
        WorkflowOutput
            Container with all workflow outputs.

        Raises
        ------
        RuntimeError
            If workflow hasn't completed successfully.
        """
        raise NotImplementedError

    def get_uploaded_assets(self) -> list[str]:
        """
        Get list of assets uploaded for this workflow.

        Returns
        -------
        List[str]
            Names of uploaded assets.
        """
        return self.uploaded_assets.copy()

    def cleanup_inputs(self) -> Any:  # Would return CleanupResult
        """
        Clean up uploaded input assets.

        Returns
        -------
        CleanupResult
            Result with deleted count and any failures.
        """
        raise NotImplementedError

    def cleanup_outputs(
        self, delete_from_board: bool = True, delete_images: bool = True
    ) -> Any:  # Would return CleanupResult
        """
        Clean up generated outputs.

        Parameters
        ----------
        delete_from_board : bool
            Whether to remove from boards.
        delete_images : bool
            Whether to delete image files.

        Returns
        -------
        CleanupResult
            Result with deleted count and any failures.
        """
        raise NotImplementedError

    def cleanup_queue_items(self) -> Any:  # Would return CleanupResult
        """
        Clean up completed queue items.

        Returns
        -------
        CleanupResult
            Result with pruned count.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """
        Reset the workflow to initial state.

        Clears all inputs, outputs, and job information,
        allowing the workflow to be reconfigured and rerun.
        """
        # Reset all input values
        for inp in self.inputs:
            inp.field.set_value(None)

        # Clear job and assets
        self.job = None
        self.uploaded_assets.clear()

    def clone(self) -> WorkflowHandle:
        """
        Create a copy of this workflow handle.

        Returns
        -------
        WorkflowHandle
            A new workflow instance with the same definition
            but cleared inputs/outputs.
        """
        # Create new instance with same definition
        new_handle = WorkflowHandle(self.client, self.definition)
        return new_handle

    def to_dict(self) -> dict[str, Any]:
        """
        Export the workflow configuration with current input values.

        Returns
        -------
        Dict[str, Any]
            Workflow definition with current input values.
        """
        # Get base definition
        data = self.definition.to_dict()

        # Update with current input values
        # This would map the input values back to the nodes
        # Placeholder for now

        return data

    def __repr__(self) -> str:
        """String representation of the workflow handle."""
        return (
            f"WorkflowHandle(name='{self.definition.name}', "
            f"inputs={len(self.inputs)}, "
            f"job={'pending' if self.job else 'none'})"
        )
