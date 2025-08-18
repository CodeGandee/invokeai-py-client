"""
Workflow handle for managing workflow execution state.

This module provides the WorkflowHandle class which represents the running state
of a workflow and manages input configuration, submission, and result retrieval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pydantic import BaseModel, ConfigDict

from invokeai_py_client.ivk_fields import (
    IvkBoardField,
    IvkBooleanField,
    IvkEnumField,
    IvkFloatField,
    IvkImageField,
    IvkIntegerField,
    IvkModelIdentifierField,
    IvkStringField,
)
from invokeai_py_client.ivk_fields.base import IvkField
from invokeai_py_client.models import IvkJob

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient
    from invokeai_py_client.workflow.workflow_model import WorkflowDefinition


class IvkWorkflowInput(BaseModel):
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
    field : IvkField
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
    field: IvkField[Any]  # Base class for all field types
    required: bool
    input_index: int

    def validate_input(self) -> bool:
        """
        Validate the workflow input by delegating to the field's validate_field method.
        
        Returns
        -------
        bool
            True if the field is valid, False otherwise.
            
        Raises
        ------
        ValueError
            If the field validation fails with specific error details.
            
        Notes
        -----
        This method delegates validation to the underlying IvkField instance.
        Required fields with None values will raise a ValueError.
        """
        # Check if required field has value
        if self.required:
            if hasattr(self.field, 'value') and self.field.value is None:
                raise ValueError(f"Required field '{self.label}' is not set")
        
        # Delegate to field's validation
        return self.field.validate_field()


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
    inputs : List[IvkWorkflowInput]
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
        self.inputs: list[IvkWorkflowInput] = []
        self.job: IvkJob | None = None
        self.uploaded_assets: list[str] = []

        # Initialize inputs from the workflow definition
        self._initialize_inputs()

    def _initialize_inputs(self) -> None:
        """
        Initialize workflow inputs from the definition.

        This parses the form structure and exposed fields to create
        the ordered list of IvkWorkflowInput objects.
        """
        # Get form elements and nodes for reference
        form_elements = self.definition.form.get("elements", {})
        nodes = {node["id"]: node for node in self.definition.nodes}

        # Track input index
        input_index = 0

        def traverse_form(elem_id: str) -> None:
            """Traverse form tree and collect node-field elements."""
            nonlocal input_index

            elem = form_elements.get(elem_id)
            if not elem:
                return

            elem_type = elem.get("type")

            if elem_type == "container":
                # Process children in order
                for child_id in elem.get("data", {}).get("children", []):
                    traverse_form(child_id)

            elif elem_type == "node-field":
                # Extract field information
                field_id = elem["data"]["fieldIdentifier"]
                node_id = field_id["nodeId"]
                field_name = field_id["fieldName"]

                # Get node and field metadata
                node = nodes.get(node_id, {})
                node_data = node.get("data", {})
                node_type = node_data.get("type", "unknown")

                # Get labels
                node_label = node_data.get("label", "")
                if not node_label:
                    # Use node type as fallback
                    node_label = node_type

                # Get field info from node inputs
                field_info = node_data.get("inputs", {}).get(field_name, {})
                field_label = field_info.get("label", field_name)
                field_description = field_info.get("description", "")

                # Determine if required
                required = field_info.get("required", False)

                # Create appropriate field instance based on type
                field_instance = self._create_field_from_node(
                    node_data, field_name, field_info
                )

                # Create IvkWorkflowInput
                workflow_input = IvkWorkflowInput(
                    label=field_label,
                    node_name=node_label,
                    node_id=node_id,
                    field_name=field_name,
                    field=field_instance,
                    required=required,
                    input_index=input_index
                )

                self.inputs.append(workflow_input)
                input_index += 1

        # Start traversal from root
        traverse_form("root")

    def _create_field_from_node(
        self, node_data: dict[str, Any], field_name: str, field_info: dict[str, Any]
    ) -> IvkField[Any]:
        """
        Create appropriate field instance based on node and field information.
        
        Parameters
        ----------
        node_data : Dict[str, Any]
            The node's data section
        field_name : str
            The field name within the node
        field_info : Dict[str, Any]
            The field's metadata from node.inputs[field_name]
        
        Returns
        -------
        IvkField[Any]
            Appropriate Ivk*Field instance (IvkStringField, IvkIntegerField, etc.)
        """
        # Get node type for context
        node_type = node_data.get("type", "")

        # Get field value if exists
        field_value = field_info.get("value")

        # Detect field type based on various hints
        field_type = self._detect_field_type(node_type, field_name, field_info)

        # Create field instance based on detected type
        if field_type == "string":
            return IvkStringField(
                value=field_value
            )

        elif field_type == "integer":
            return IvkIntegerField(
                value=field_value,
                minimum=field_info.get("minimum"),
                maximum=field_info.get("maximum")
            )

        elif field_type == "float":
            return IvkFloatField(
                value=field_value,
                minimum=field_info.get("minimum"),
                maximum=field_info.get("maximum")
            )

        elif field_type == "boolean":
            return IvkBooleanField(
                value=field_value
            )

        elif field_type == "model":
            return IvkModelIdentifierField(
                value=field_value
            )

        elif field_type == "board":
            # Board values can be dict with board_id or string
            board_value = field_value
            if isinstance(field_value, dict) and "board_id" in field_value:
                board_value = field_value["board_id"]
            return IvkBoardField(
                value=board_value
            )

        elif field_type == "image":
            return IvkImageField(
                value=field_value
            )

        elif field_type == "enum":
            # Get choices from options or ui_choices
            choices = field_info.get("options", [])
            if not choices:
                ui_choices = field_info.get("ui_choices", [])
                if ui_choices:
                    choices = ui_choices

            return IvkEnumField(
                value=field_value,
                choices=choices
            )

        else:
            # Default to string field for unknown types
            return IvkStringField(
                value=field_value
            )

    def _detect_field_type(
        self, node_type: str, field_name: str, field_info: dict[str, Any]
    ) -> str:
        """
        Detect the field type based on various hints.
        
        Parameters
        ----------
        node_type : str
            The type of the node (e.g., "string", "integer", "save_image")
        field_name : str
            The field name (e.g., "value", "model", "board")
        field_info : Dict[str, Any]
            The field metadata
        
        Returns
        -------
        str
            Detected field type identifier
        """
        # Check explicit type hint in field info
        if "type" in field_info:
            return str(field_info["type"])

        # Check by field name patterns
        if field_name == "board":
            return "board"
        elif field_name == "model" or field_name.endswith("_model"):
            return "model"
        elif field_name == "image":
            return "image"
        elif field_name == "scheduler":
            return "enum"

        # Check by node type for primitive nodes
        if node_type == "string":
            return "string"
        elif node_type == "integer":
            return "integer"
        elif node_type == "float" or node_type == "float_math":
            return "float"
        elif node_type == "boolean":
            return "boolean"

        # Check value type if present
        value = field_info.get("value")
        if value is not None:
            if isinstance(value, bool):
                return "boolean"
            elif isinstance(value, int) and not isinstance(value, bool):
                return "integer"
            elif isinstance(value, float):
                return "float"
            elif isinstance(value, dict):
                # Model fields have dict values with key/name/base/type
                if "key" in value and "base" in value:
                    return "model"
            elif isinstance(value, str):
                return "string"

        # Check for enum fields by presence of options/choices
        if "options" in field_info or "ui_choices" in field_info:
            return "enum"

        # Check for numeric constraints
        if "minimum" in field_info or "maximum" in field_info:
            if "multiple_of" in field_info:
                return "integer"
            return "float"

        # Default to string
        return "string"

    def list_inputs(self) -> list[IvkWorkflowInput]:
        """
        List all available workflow inputs.

        Returns
        -------
        List[IvkWorkflowInput]
            Ordered list of input definitions.

        Examples
        --------
        >>> inputs = workflow.list_inputs()
        >>> for inp in inputs:
        ...     print(f"[{inp.input_index}] {inp.label}")
        """
        return self.inputs.copy()

    def get_input(self, index: int) -> IvkWorkflowInput:
        """
        Get a workflow input by index.

        Parameters
        ----------
        index : int
            The 0-based input index.

        Returns
        -------
        IvkWorkflowInput
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

    def validate_inputs(self) -> dict[int, list[str]]:
        """
        Validate all configured inputs.

        Delegates validation to each IvkWorkflowInput's validate() method.

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

        # Validate each input using its validate_input() method
        for inp in self.inputs:
            try:
                inp.validate_input()
            except ValueError as e:
                if inp.input_index not in errors:
                    errors[inp.input_index] = []
                errors[inp.input_index].append(str(e))
            except Exception as e:
                # Catch any other validation errors
                if inp.input_index not in errors:
                    errors[inp.input_index] = []
                errors[inp.input_index].append(f"Validation error: {str(e)}")

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
            if hasattr(inp.field, 'value'):
                # Primitive fields have a value attribute
                inp.field.value = None
            else:
                # Complex fields - reset individual attributes
                # This would need field-specific logic
                pass

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
