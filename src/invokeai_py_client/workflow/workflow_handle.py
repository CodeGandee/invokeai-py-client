"""
Workflow handle for managing workflow execution state.

This module provides the WorkflowHandle class which represents the running state
of a workflow and manages input configuration, submission, and result retrieval.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable

from jsonpath_ng.ext import parse as parse_jsonpath  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, PrivateAttr, model_validator

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
    jsonpath : str
        JSONPath expression to locate this field in the workflow JSON.

    Field Type Immutability
    -----------------------
    After the model is first instantiated, the concrete Python class of the
    `.field` attribute is locked. Any subsequent reassignment of `.field` must
    be an instance of the exact same class (not just a subclass). Attempting to
    assign a different concrete field type raises ``TypeError``. This ensures
    stable downstream logic that may rely on the original field interface.
    """

    # Enable arbitrary types and assignment validation so our model_validator runs on re-assignment.
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    label: str
    node_name: str
    node_id: str
    field_name: str
    field: IvkField[Any]  # Base class for all field types
    required: bool
    input_index: int
    jsonpath: str  # JSONPath expression for efficient field location

    # Private attribute to remember the concrete type of `field` after first initialization.
    _field_type: type[IvkField[Any]] | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _lock_field_type(self) -> IvkWorkflowInput:
        """Capture the initial concrete type of `field` and enforce exact-type reassignments.

        Runs after model creation and again on any assignment (validate_assignment=True).
        """
        if self.field is not None:
            if self._field_type is None:
                self._field_type = type(self.field)
            else:
                if type(self.field) is not self._field_type:
                    raise TypeError(
                        "Cannot reassign 'field' with different type: "
                        f"expected {self._field_type.__name__}, got {type(self.field).__name__}"
                    )
        return self

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
        
        # Queue tracking
        self.batch_id: str | None = None
        self.item_id: int | None = None
        self.session_id: str | None = None

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
                # description currently unused, keep retrieval if needed later
                # field_description = field_info.get("description", "")  # noqa: F841

                # Determine if required
                required = field_info.get("required", False)

                # Create appropriate field instance based on type
                field_instance = self._create_field_from_node(
                    node_data, field_name, field_info
                )

                # Calculate JSONPath expression for this field
                # Points to the entire field dict object (not just .value)
                # We'll merge to_api_format() results with this dict
                jsonpath_expr = f"$.nodes[?(@.id='{node_id}')].data.inputs.{field_name}"

                # Create IvkWorkflowInput
                workflow_input = IvkWorkflowInput(
                    label=field_label,
                    node_name=node_label,
                    node_id=node_id,
                    field_name=field_name,
                    field=field_instance,
                    required=required,
                    input_index=input_index,
                    jsonpath=jsonpath_expr
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
            # Extract model properties from field_value dict
            if isinstance(field_value, dict):
                return IvkModelIdentifierField(
                    key=field_value.get("key", ""),
                    hash=field_value.get("hash", ""),
                    name=field_value.get("name", ""),
                    base=field_value.get("base", "any"),
                    type=field_value.get("type", "main"),
                    submodel_type=field_value.get("submodel_type")
                )
            else:
                # Handle case where field_value is not a dict
                return IvkModelIdentifierField(
                    key="",
                    hash="",
                    name=str(field_value) if field_value else "",
                    base="any",
                    type="main"
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

    def get_input_value(self, index: int) -> IvkField[Any]:
        """
        Get the field instance for a workflow input by index.

        This method provides direct access to the IvkField instance,
        allowing users to inspect and modify field properties directly.

        Parameters
        ----------
        index : int
            The 0-based input index.

        Returns
        -------
        IvkField[Any]
            The field instance at the specified index.

        Raises
        ------
        IndexError
            If the index is out of range.

        Examples
        --------
        >>> field = workflow.get_input_value(0)
        >>> if hasattr(field, 'value'):
        ...     print(f"Current value: {field.value}")
        >>> field.value = "New value"
        """
        if index < 0 or index >= len(self.inputs):
            raise IndexError(
                f"Input index {index} out of range (0-{len(self.inputs) - 1})"
            )
        return self.inputs[index].field

    def set_input_value(self, index: int, value: IvkField[Any]) -> None:
        """
        Update the field instance for a workflow input by index.

        This method replaces the entire field instance, ensuring type
        consistency and validating the result. The new field must be
        of the exact same type as the original field.

        Parameters
        ----------
        index : int
            The 0-based input index.
        value : IvkField[Any]
            The new field instance to set.

        Raises
        ------
        IndexError
            If the index is out of range.
        TypeError
            If the field type doesn't match the original field type.
        ValueError
            If the field validation fails after setting.

        Examples
        --------
        >>> # Get the original field to understand its type
        >>> original_field = workflow.get_input_value(0)
        >>> # Create a new field of the same type
        >>> new_field = type(original_field)(value="New value")
        >>> # Set the new field
        >>> workflow.set_input_value(0, new_field)
        """
        if index < 0 or index >= len(self.inputs):
            raise IndexError(
                f"Input index {index} out of range (0-{len(self.inputs) - 1})"
            )
        
        workflow_input = self.inputs[index]
        
        # Validate type consistency - use the field type locking mechanism
        expected_type = workflow_input._field_type
        if expected_type is not None and type(value) is not expected_type:
            raise TypeError(
                f"Field type mismatch: expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        
        # Set the new field value
        workflow_input.field = value
        
        # Validate the input after setting
        workflow_input.validate_input()

    def submit_sync(
        self,
        queue_id: str = "default",
        board_id: str | None = None,
        priority: int = 0,
    ) -> dict[str, Any]:
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
        dict[str, Any]
            The submission result with batch_id, item_ids, and enqueued count.

        Raises
        ------
        ValueError
            If validation fails or required inputs are missing.
        RuntimeError
            If submission fails.
        """
        # Validate inputs first
        validation_errors = self.validate_inputs()
        if validation_errors:
            error_msgs = []
            for idx, errors in validation_errors.items():
                input_info = self.inputs[idx]
                error_msgs.append(f"[{idx}] {input_info.label}: {', '.join(errors)}")
            raise ValueError(f"Input validation failed: {'; '.join(error_msgs)}")
        
        # Convert workflow to API format
        api_graph = self._convert_to_api_format(board_id)
        
        # Prepare batch submission
        batch_data = {
            "prepend": priority > 0,  # Higher priority items go to front
            "batch": {
                "graph": api_graph,
                "runs": 1
            }
        }
        
        # Debug: Print a sample of the batch data (only in debug mode)
        import os
        if os.environ.get("DEBUG_WORKFLOW"):
            import json
            # Save full batch data to file for inspection
            with open("batch_data_debug.json", "w") as f:
                json.dump(batch_data, f, indent=2)
            print("\n[DEBUG] Batch data saved to batch_data_debug.json")
            print("[DEBUG] Sample of batch data:")
            print(json.dumps(batch_data, indent=2)[:1000])
        
        # Submit to queue
        url = f"/queue/{queue_id}/enqueue_batch"
        try:
            response = self.client._make_request("POST", url, json=batch_data)
            result = response.json()
            
            # Extract batch information
            batch_info = result.get("batch", {})
            self.batch_id = batch_info.get("batch_id")
            item_ids = result.get("item_ids", [])
            
            if not self.batch_id or not item_ids:
                raise RuntimeError(f"Invalid submission response: {result}")
            
            # Store first item ID for tracking
            self.item_id = item_ids[0]
            
            # Get session ID from queue item
            queue_item = self._get_queue_item_by_id(queue_id, self.item_id)
            if queue_item:
                self.session_id = queue_item.get("session_id")
            
            return {
                "batch_id": self.batch_id,
                "item_ids": item_ids,
                "enqueued": len(item_ids),
                "session_id": self.session_id
            }
            
        except Exception as e:
            # Surface server validation errors (422) with as much context as possible
            resp = getattr(e, 'response', None)
            if resp is not None:
                try:
                    detail_json = resp.json()
                except Exception:  # pragma: no cover - fallback to text
                    detail_json = {"non_json_response": resp.text[:2000]}
                # Persist for offline diffing
                try:
                    with open("tmp/last_failed_submission_detail.json", "w", encoding="utf-8") as fh:
                        json.dump({"status_code": resp.status_code, "detail": detail_json}, fh, indent=2)
                except Exception:
                    pass
                raise RuntimeError(
                    f"Workflow submission failed ({resp.status_code}): {detail_json}"
                ) from e
            raise RuntimeError(f"Workflow submission failed: {e}") from e

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
    ) -> dict[str, Any]:
        """
        Submit the workflow for execution asynchronously with real-time events.

        This method provides non-blocking submission with optional Socket.IO event 
        streaming for real-time progress monitoring. It's best suited for interactive 
        applications, dashboards, and concurrent workflow execution.

        Parameters
        ----------
        queue_id : str, optional
            The queue to submit to (default: "default").
        board_id : str, optional
            Default board for output images.
        priority : int, optional
            Job priority (higher values = higher priority).
        subscribe_events : bool, optional
            Whether to subscribe to Socket.IO events for real-time updates.
        on_invocation_started : Callable, optional
            Callback when a node starts executing. Receives event dict with:
            - node_id: str
            - node_type: str
            - session_id: str
        on_invocation_progress : Callable, optional
            Callback for progress updates during node execution. Receives event dict with:
            - node_id: str
            - progress: float (0.0 to 1.0)
            - message: str (optional progress message)
        on_invocation_complete : Callable, optional
            Callback when a node completes successfully. Receives event dict with:
            - node_id: str
            - outputs: dict (node output data)
        on_invocation_error : Callable, optional
            Callback when a node encounters an error. Receives event dict with:
            - node_id: str
            - error: str (error message)

        Returns
        -------
        dict[str, Any]
            Submission result with:
            - batch_id: str
            - session_id: str
            - item_ids: List[int]
            - enqueued: int (number of items enqueued)

        Raises
        ------
        ValueError
            If validation fails or required inputs are missing.
        RuntimeError
            If submission fails.

        Examples
        --------
        >>> async def on_progress(event):
        ...     print(f"Progress: {event['progress']*100:.0f}%")
        >>> 
        >>> result = await workflow.submit(
        ...     board_id="my-outputs",
        ...     subscribe_events=True,
        ...     on_invocation_progress=on_progress
        ... )
        >>> print(f"Submitted: {result['batch_id']}")
        """
        # Validate inputs first
        validation_errors = self.validate_inputs()
        if validation_errors:
            error_msgs = []
            for idx, errors in validation_errors.items():
                input_info = self.inputs[idx]
                error_msgs.append(f"[{idx}] {input_info.label}: {', '.join(errors)}")
            raise ValueError(f"Input validation failed: {'; '.join(error_msgs)}")
        
        # Convert workflow to API format
        api_graph = self._convert_to_api_format(board_id)
        
        # Prepare batch submission
        batch_data = {
            "prepend": priority > 0,  # Higher priority items go to front
            "batch": {
                "graph": api_graph,
                "runs": 1
            }
        }
        
        # Submit to queue asynchronously (still uses sync API endpoint)
        url = f"/queue/{queue_id}/enqueue_batch"
        try:
            # Use sync request for submission (API doesn't have async endpoint)
            response = self.client._make_request("POST", url, json=batch_data)
            result = response.json()
            
            # Extract batch information
            batch_info = result.get("batch", {})
            self.batch_id = batch_info.get("batch_id")
            item_ids = result.get("item_ids", [])
            
            if not self.batch_id or not item_ids:
                raise RuntimeError(f"Invalid submission response: {result}")
            
            # Store first item ID for tracking
            self.item_id = item_ids[0]
            
            # Get session ID from queue item
            queue_item = self._get_queue_item_by_id(queue_id, self.item_id)
            if queue_item:
                self.session_id = queue_item.get("session_id")
            
            # Set up Socket.IO event subscriptions if requested
            if subscribe_events and self.session_id:
                await self._setup_event_subscriptions(
                    queue_id,
                    on_invocation_started,
                    on_invocation_progress,
                    on_invocation_complete,
                    on_invocation_error
                )
            
            return {
                "batch_id": self.batch_id,
                "session_id": self.session_id,
                "item_ids": item_ids,
                "enqueued": len(item_ids)
            }
            
        except Exception as e:
            # Try to get error details from response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    raise RuntimeError(f"Workflow submission failed: {error_detail}")
                except:
                    pass
            raise RuntimeError(f"Workflow submission failed: {e}")
    
    async def _setup_event_subscriptions(
        self,
        queue_id: str,
        on_invocation_started: Callable[[dict[str, Any]], None] | None = None,
        on_invocation_progress: Callable[[dict[str, Any]], None] | None = None,
        on_invocation_complete: Callable[[dict[str, Any]], None] | None = None,
        on_invocation_error: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """
        Set up Socket.IO event subscriptions for workflow monitoring.
        
        Parameters
        ----------
        queue_id : str
            The queue ID to subscribe to.
        on_invocation_started : Callable, optional
            Callback for node start events.
        on_invocation_progress : Callable, optional
            Callback for progress events.
        on_invocation_complete : Callable, optional
            Callback for node completion events.
        on_invocation_error : Callable, optional
            Callback for error events.
        """
        # Connect to Socket.IO
        sio = await self.client.connect_socketio()
        
        # Subscribe to queue room
        await sio.emit("subscribe_queue", {"queue_id": queue_id})
        
        # Register event handlers based on InvokeAI's event types
        if on_invocation_started:
            @sio.on("invocation_started")  # type: ignore[misc]
            async def handle_started(data: dict[str, Any]) -> None:
                # Filter for our session
                if data.get("session_id") == self.session_id:
                    on_invocation_started(data)
        
        if on_invocation_progress:
            @sio.on("invocation_progress")  # type: ignore[misc]
            async def handle_progress(data: dict[str, Any]) -> None:
                if data.get("session_id") == self.session_id:
                    on_invocation_progress(data)
        
        if on_invocation_complete:
            @sio.on("invocation_complete")  # type: ignore[misc]
            async def handle_complete(data: dict[str, Any]) -> None:
                if data.get("session_id") == self.session_id:
                    on_invocation_complete(data)
        
        if on_invocation_error:
            @sio.on("invocation_error")  # type: ignore[misc]
            async def handle_error(data: dict[str, Any]) -> None:
                if data.get("session_id") == self.session_id:
                    on_invocation_error(data)

    def wait_for_completion_sync(
        self,
        poll_interval: float = 0.5,
        timeout: float = 60.0,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        queue_id: str = "default"
    ) -> dict[str, Any]:
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
        queue_id : str
            The queue ID to poll.

        Returns
        -------
        dict[str, Any]
            The completed queue item.

        Raises
        ------
        TimeoutError
            If timeout is exceeded.
        RuntimeError
            If the job fails.
        """
        if not self.item_id:
            raise RuntimeError("No job submitted to wait for")
        
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            # Get current queue item status
            queue_item = self._get_queue_item_by_id(queue_id, self.item_id)
            
            if not queue_item:
                raise RuntimeError(f"Queue item {self.item_id} not found")
            
            current_status = queue_item.get("status")
            
            # Call progress callback if status changed
            if current_status != last_status:
                if progress_callback:
                    progress_callback(queue_item)
                last_status = current_status
            
            # Check if completed
            if current_status == "completed":
                return queue_item
            elif current_status == "failed":
                error_msg = queue_item.get("error", "Unknown error")
                raise RuntimeError(f"Workflow execution failed: {error_msg}")
            elif current_status == "canceled":
                raise RuntimeError("Workflow execution was canceled")
            
            # Wait before next poll
            time.sleep(poll_interval)
        
        # Timeout reached
        raise TimeoutError(f"Workflow execution timed out after {timeout} seconds")

    async def wait_for_completion(
        self, 
        timeout: float | None = None,
        queue_id: str = "default"
    ) -> dict[str, Any]:
        """
        Wait for workflow completion asynchronously with real-time events.

        This method monitors the workflow execution via Socket.IO events,
        providing real-time updates without polling overhead.

        Parameters
        ----------
        timeout : float, optional
            Maximum time to wait in seconds. None for no timeout.
        queue_id : str, optional
            The queue ID to monitor (default: "default").

        Returns
        -------
        dict[str, Any]
            The completed queue item with status and results.

        Raises
        ------
        asyncio.TimeoutError
            If timeout is exceeded.
        RuntimeError
            If the job fails or no job is submitted.

        Examples
        --------
        >>> result = await workflow.submit(subscribe_events=True)
        >>> completed_item = await workflow.wait_for_completion(timeout=60.0)
        >>> print(f"Status: {completed_item['status']}")
        """
        if not self.session_id:
            raise RuntimeError("No job submitted to wait for")
        
        # Connect to Socket.IO and subscribe
        sio = await self.client.connect_socketio()
        await sio.emit("subscribe_queue", {"queue_id": queue_id})
        
        # Create a future to wait for completion
        completion_future: asyncio.Future[dict[str, Any]] = asyncio.Future()
        
        # Handler for queue item status changes
        @sio.on("queue_item_status_changed")  # type: ignore[misc]
        async def handle_status_change(data: dict[str, Any]) -> None:
            if data.get("session_id") != self.session_id:
                return
                
            status = data.get("status")
            if status == "completed":
                # Get full queue item data
                if self.item_id is not None:
                    queue_item = self._get_queue_item_by_id(queue_id, self.item_id)
                    if queue_item and not completion_future.done():
                        completion_future.set_result(queue_item)
            elif status == "failed":
                error_msg = data.get("error", "Unknown error")
                if not completion_future.done():
                    completion_future.set_exception(
                        RuntimeError(f"Workflow execution failed: {error_msg}")
                    )
            elif status == "canceled":
                if not completion_future.done():
                    completion_future.set_exception(
                        RuntimeError("Workflow execution was canceled")
                    )
        
        # Also handle graph completion event as backup
        @sio.on("graph_complete")  # type: ignore[misc]
        async def handle_graph_complete(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                if self.item_id is not None:
                    queue_item = self._get_queue_item_by_id(queue_id, self.item_id)
                    if queue_item and not completion_future.done():
                        completion_future.set_result(queue_item)
        
        # Wait with timeout
        try:
            if timeout:
                result = await asyncio.wait_for(completion_future, timeout=timeout)
            else:
                result = await completion_future
            
            # Unsubscribe from queue
            await sio.emit("unsubscribe_queue", {"queue_id": queue_id})
            return result
            
        except asyncio.TimeoutError:
            await sio.emit("unsubscribe_queue", {"queue_id": queue_id})
            raise asyncio.TimeoutError(
                f"Workflow execution timed out after {timeout} seconds"
            )

    async def submit_sync_monitor_async(
        self,
        queue_id: str = "default",
        board_id: str | None = None,
        priority: int = 0,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Hybrid approach: Submit synchronously but monitor with async events.
        
        This method combines simple blocking submission with async event monitoring,
        ideal for applications wanting simple submission APIs but rich monitoring 
        capabilities, or transitioning from sync to async patterns.
        
        Parameters
        ----------
        queue_id : str, optional
            The queue to submit to (default: "default").
        board_id : str, optional
            Default board for output images.
        priority : int, optional
            Job priority (higher values = higher priority).
            
        Yields
        ------
        dict[str, Any]
            Event dictionaries as workflow executes:
            - First yield: Submission result with batch_id, session_id
            - Subsequent yields: Real-time events (invocation_started, progress, complete, error)
            - Final yield: Completion event with final status
            
        Raises
        ------
        ValueError
            If validation fails or required inputs are missing.
        RuntimeError
            If submission fails.
            
        Examples
        --------
        >>> async for event in workflow.submit_sync_monitor_async(board_id="outputs"):
        ...     event_type = event.get("event_type")
        ...     if event_type == "submission":
        ...         print(f"Submitted: {event['batch_id']}")
        ...     elif event_type == "invocation_started":
        ...         print(f"Started: {event['node_type']}")
        ...     elif event_type == "invocation_complete":
        ...         print(f"Completed: {event['node_type']}")
        ...     elif event_type == "graph_complete":
        ...         print("Workflow finished!")
        """
        # Submit synchronously (simpler API)
        batch_result = self.submit_sync(
            queue_id=queue_id,
            board_id=board_id,
            priority=priority
        )
        
        # Yield submission result first
        yield {
            "event_type": "submission",
            "batch_id": batch_result["batch_id"],
            "session_id": batch_result["session_id"],
            "item_ids": batch_result["item_ids"],
            "enqueued": batch_result["enqueued"]
        }
        
        # Connect to Socket.IO for real-time monitoring
        sio = await self.client.connect_socketio()
        await sio.emit("subscribe_queue", {"queue_id": queue_id})
        
        # Track completion
        is_complete = False
        
        # Set up event handlers that yield events
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        
        @sio.on("invocation_started")  # type: ignore[misc]
        async def handle_started(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                await event_queue.put({
                    "event_type": "invocation_started",
                    **data
                })
        
        @sio.on("invocation_progress")  # type: ignore[misc]
        async def handle_progress(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                await event_queue.put({
                    "event_type": "invocation_progress",
                    **data
                })
        
        @sio.on("invocation_complete")  # type: ignore[misc]
        async def handle_complete(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                await event_queue.put({
                    "event_type": "invocation_complete",
                    **data
                })
        
        @sio.on("invocation_error")  # type: ignore[misc]
        async def handle_error(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                await event_queue.put({
                    "event_type": "invocation_error",
                    **data
                })
                # Mark as complete on error
                nonlocal is_complete
                is_complete = True
        
        @sio.on("graph_complete")  # type: ignore[misc]
        async def handle_graph_complete(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                await event_queue.put({
                    "event_type": "graph_complete",
                    **data
                })
                # Mark as complete
                nonlocal is_complete
                is_complete = True
        
        @sio.on("queue_item_status_changed")  # type: ignore[misc]
        async def handle_status_change(data: dict[str, Any]) -> None:
            if data.get("session_id") == self.session_id:
                status = data.get("status")
                if status in ["completed", "failed", "canceled"]:
                    await event_queue.put({
                        "event_type": "queue_item_status_changed",
                        **data
                    })
                    nonlocal is_complete
                    is_complete = True
        
        # Yield events as they come in
        try:
            while not is_complete:
                try:
                    # Wait for next event with a short timeout to check completion
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                    yield event
                except asyncio.TimeoutError:
                    # Check if we should continue waiting
                    continue
            
            # Drain any remaining events
            while not event_queue.empty():
                try:
                    event = event_queue.get_nowait()
                    yield event
                except asyncio.QueueEmpty:
                    break
                    
        finally:
            # Clean up - unsubscribe from queue
            await sio.emit("unsubscribe_queue", {"queue_id": queue_id})
    
    def get_queue_item(self, queue_id: str = "default") -> dict[str, Any] | None:
        """
        Get the current queue item for tracking.

        Parameters
        ----------
        queue_id : str
            The queue ID to query.

        Returns
        -------
        Optional[dict[str, Any]]
            The queue item if submitted, None otherwise.
        """
        if not self.item_id:
            return None
        
        return self._get_queue_item_by_id(queue_id, self.item_id)

    def cancel(self, queue_id: str = "default") -> bool:
        """
        Cancel the current workflow execution synchronously.

        Parameters
        ----------
        queue_id : str
            The queue ID.

        Returns
        -------
        bool
            True if cancellation was successful.

        Raises
        ------
        RuntimeError
            If no job is running or cancellation fails.
        """
        if not self.item_id:
            raise RuntimeError("No job to cancel")
        
        url = f"/queue/{queue_id}/i/{self.item_id}/cancel"
        try:
            response = self.client._make_request("DELETE", url)
            return bool(response.status_code == 200)
        except Exception as e:
            raise RuntimeError(f"Failed to cancel job: {e}")
    
    async def cancel_async(self, queue_id: str = "default") -> bool:
        """
        Cancel the current workflow execution asynchronously.

        Parameters
        ----------
        queue_id : str
            The queue ID.

        Returns
        -------
        bool
            True if cancellation was successful.

        Raises
        ------
        RuntimeError
            If no job is running or cancellation fails.
        """
        # Just wrap the sync version in an async executor
        return await asyncio.get_event_loop().run_in_executor(
            None, self.cancel, queue_id
        )

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

    def _convert_to_api_format(self, board_id: str | None = None) -> dict[str, Any]:
        """
        Convert workflow definition to API graph format.
        
        Uses the original workflow JSON and JSONPath expressions to efficiently 
        update only the fields that have been set through the WorkflowHandle inputs.
        
        Parameters
        ----------
        board_id : str, optional
            Default board for outputs.
        
        Returns
        -------
        dict[str, Any]
            API-formatted graph structure.
        """
        import copy
        
        # Start with a deep copy of the original workflow JSON
        workflow_copy = copy.deepcopy(self.definition.raw_data)
        
        # Update exposed fields using JSONPath expressions
        for inp in self.inputs:
            # Parse the stored JSONPath expression
            jsonpath_expr = parse_jsonpath(inp.jsonpath)
            
            # Get the field's API format
            field = inp.field
            api_format = field.to_api_format()
            
            # Find the target field dict in the workflow
            matches = jsonpath_expr.find(workflow_copy)
            for match in matches:
                # Get the existing field dict
                existing_dict = match.value
                if not isinstance(existing_dict, dict):
                    existing_dict = {}
                
                # Merge the API format data with existing dict
                # This preserves keys like 'name', 'label', 'description'
                # while updating/adding the 'value' and other keys from to_api_format()
                merged_dict = {**existing_dict, **api_format}
                
                # Update the field dict in the workflow
                match.full_path.update(workflow_copy, merged_dict)
        
        # Build a set of fields that are connected via edges.
        # Historically we attempted to REMOVE these fields from the serialized
        # API graph under the assumption that an edge-supplied value should not
        # also appear inline on the destination node. However, the canonical
        # GUI-generated payloads DO include these (eg. width/height/seed even
        # when an edge provides a value). The server's pydantic schema also
        # expects required parameters to be present – omitting them causes 422s.
        #
        # We therefore keep the set only for optional diagnostics and retain
        # all fields (connected or not) when building the node payload. An env
        # var can restore the pruning behaviour for experiments.
        connected_fields: set[str] = set()
        for edge in workflow_copy.get("edges", []):
            target_node = edge.get("target")
            target_field = edge.get("targetHandle")
            if target_node and target_field:
                connected_fields.add(f"{target_node}.{target_field}")
        prune_connected = os.environ.get("INVOKEAI_PRUNE_CONNECTED_FIELDS") == "1"
        
        # Convert nodes to API format
        api_nodes = {}
        for node in workflow_copy.get("nodes", []):
            node_id = node.get("id")
            if not node_id:
                continue  # Skip nodes without ID
            
            node_data = node.get("data", {})
            node_type = node_data.get("type")

            # Skip non-executable/GUI-only helper nodes that the server schema doesn't accept
            if node_type in {"notes"}:
                continue
            
            # Create API node with basic fields
            api_node = {
                "id": node_id,
                "type": node_type,
                "is_intermediate": node_data.get("isIntermediate", True),
                "use_cache": node_data.get("useCache", True)
            }
            
            # Process inputs - only include fields with values
            # (Note: JSONPath has already updated exposed fields in workflow_copy)
            node_inputs = node_data.get("inputs", {})
            for field_name, field_data in node_inputs.items():
                # Optionally skip connected fields only if pruning explicitly enabled
                if prune_connected and f"{node_id}.{field_name}" in connected_fields:
                    continue
                
                # Get the value from the updated workflow_copy
                field_value = None
                if isinstance(field_data, dict) and "value" in field_data:
                    field_value = field_data["value"]
                elif not isinstance(field_data, dict):
                    # Sometimes the field_data is the value itself
                    field_value = field_data
                
                # Only include the field if it has a non-None value
                if field_value is not None:
                    api_node[field_name] = field_value
            
            # Special handling for specific node types
            # Normalize existing board field (GUI uses string like "auto" or board_id)
            if "board" in api_node and isinstance(api_node["board"], str):
                existing = api_node["board"]
                # If GUI default 'auto', replace with provided board_id if any, else 'none'
                normalized = board_id if (existing == "auto" and board_id) else existing
                if normalized == "auto":  # still auto with no board_id provided
                    normalized = "none"
                api_node["board"] = {"board_id": normalized}

            if board_id:
                # Apply/override board_id to standard output/image decode nodes where absent
                if node_type in ["save_image", "l2i", "flux_vae_decode", "flux_vae_encode", "hed_edge_detection"]:
                    if "board" not in api_node or not isinstance(api_node["board"], dict):
                        api_node["board"] = {"board_id": board_id}
            
            api_nodes[node_id] = api_node
        
        # Convert edges to API format
        api_edges = []
        for edge in workflow_copy.get("edges", []):
            api_edge = {
                "source": {
                    "node_id": edge.get("source"),
                    "field": edge.get("sourceHandle")
                },
                "destination": {
                    "node_id": edge.get("target"),
                    "field": edge.get("targetHandle")
                }
            }
            api_edges.append(api_edge)
        
        return {
            "id": "workflow",  # Default workflow ID
            "nodes": api_nodes,
            "edges": api_edges
        }
    
    
    def _get_queue_item_by_id(self, queue_id: str, item_id: int) -> dict[str, Any] | None:
        """
        Get a specific queue item by ID.
        
        Parameters
        ----------
        queue_id : str
            The queue ID.
        item_id : int
            The item ID.
        
        Returns
        -------
        Optional[dict[str, Any]]
            The queue item data or None if not found.
        """
        url = f"/queue/{queue_id}/i/{item_id}"
        try:
            response = self.client._make_request("GET", url)
            result: dict[str, Any] = response.json()
            return result
        except Exception:
            return None
    
    def __repr__(self) -> str:
        """String representation of the workflow handle."""
        status = "none"
        if self.batch_id:
            status = "submitted"
        elif self.job:
            status = "pending"
        
        return (
            f"WorkflowHandle(name='{self.definition.name}', "
            f"inputs={len(self.inputs)}, "
            f"status={status})"
        )
