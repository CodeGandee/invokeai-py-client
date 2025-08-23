"""
Workflow handle for managing workflow execution state.

This module provides the WorkflowHandle class which represents the running state
of a workflow and manages input configuration, submission, and result retrieval.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING, Any, Callable, TypedDict
from collections.abc import AsyncGenerator
import json

# JSONPath retained only for backward compatibility (may be phased out after upstream model integration)
# (Legacy JSONPath import removed after upstream model integration)
from pydantic import BaseModel, ConfigDict, PrivateAttr, model_validator

from invokeai_py_client.ivk_fields import (
    IvkBoardField,
    IvkBooleanField,
    IvkEnumField,
    IvkFloatField,
    IvkImageField,
    IvkIntegerField,
    IvkStringField,
)
from invokeai_py_client.ivk_fields.base import IvkField
from invokeai_py_client.workflow import field_plugins
from invokeai_py_client.models import IvkJob
from invokeai_py_client.workflow.upstream_models import (
    load_workflow_json,
    is_field_connected,
)

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient
    from invokeai_py_client.workflow.workflow_model import WorkflowDefinition
    from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField


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
            # Best-effort check for value-style fields
            if isinstance(self.field, (IvkStringField, IvkIntegerField, IvkFloatField, IvkBooleanField, IvkEnumField, IvkBoardField, IvkImageField)):
                if getattr(self.field, 'value', None) is None:
                    raise ValueError(f"Required field '{self.label}' is not set")
        
        # Delegate to field's validation
        return self.field.validate_field()


# Type alias - outputs are board fields exposed in the form
IvkWorkflowOutput = IvkWorkflowInput


class OutputMapping(TypedDict):
    """
    Mapping of output node to generated images.
    
    Attributes
    ----------
    node_id : str
        UUID of the output node.
    board_id : str
        Board ID where images were saved ("none" for uncategorized).
    image_names : list[str]
        List of image filenames generated by this node (list used because a node
        may legitimately yield multiple images in collection/future multi-image
        outputs; most simple workflows produce 0 or 1).
    tier : str
        Evidence tier used to collect images ("results", "legacy", "traversal", "none").
    node_type : str
        Type of the output node (e.g., "save_image").
    input_index : int
        Index in the workflow's list_outputs().
    label : str
        Label of the output node's board field.
    """
    node_id: str
    board_id: str
    image_names: list[str]
    tier: str
    node_type: str
    input_index: int
    label: str


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

        # Upstream workflow root model (forward-compatible structured representation)
        # Loaded from the raw definition dict; mutations applied during conversion only.
        try:
            self._root = load_workflow_json(self.definition.to_dict())
        except Exception:
            # Fail softly; retain legacy path if parsing fails
            self._root = None  # type: ignore[assignment]
        
        # Queue tracking
        self.batch_id: str | None = None
        self.item_id: int | None = None
        self.session_id: str | None = None

        # Initialize inputs from the workflow definition
        self._initialize_inputs()

    def _initialize_inputs(self) -> None:
        """
        Initialize workflow inputs from the definition.

        This parses the form structure and GUI-public fields to create
        the ordered list of IvkWorkflowInput objects.

        Terminology note:
        "GUI-public fields" refers to node input fields that have been intentionally
        surfaced in the workflow "form" tree via a `node-field` element (so they are
        user-configurable in the InvokeAI GUI). This wording avoids confusion with the
        raw workflow JSON property sometimes named `exposedFields` in other contexts;
        here we rely solely on the form element structure to decide what is user facing.
        """
        # Prefer upstream model if available for form elements & nodes
        _root_obj = getattr(self, "_root", None)
        if _root_obj is not None:
            try:
                form_elements = _root_obj.form.elements  # type: ignore[attribute-defined-outside-init]
                nodes = {n.get("id"): n for n in _root_obj.nodes if isinstance(n, dict)}  # type: ignore[attribute-defined-outside-init]
                element_is_model = True
            except Exception:
                form_elements = self.definition.form.get("elements", {})
                nodes = {node["id"]: node for node in self.definition.nodes}
                element_is_model = False
        else:
            form_elements = self.definition.form.get("elements", {})
            nodes = {node["id"]: node for node in self.definition.nodes}
            element_is_model = False

        # Track input index
        input_index = 0

        def traverse_form(elem_id: str) -> None:
            """Traverse form tree and collect node-field elements."""
            nonlocal input_index

            elem = form_elements.get(elem_id)
            if not elem:
                return

            # Support both dict and model element forms
            if element_is_model:
                elem_type = elem.type  # type: ignore[union-attr]
                elem_data = getattr(elem, 'data', None)
                children = (elem_data.children if elem_data and elem_data.children else [])
                field_identifier = getattr(elem_data, 'fieldIdentifier', None)
            else:
                elem_type = elem.get("type")  # type: ignore[assignment]
                elem_data = elem.get("data", {})  # type: ignore[assignment]
                children = elem_data.get("children", [])
                field_identifier = elem_data.get("fieldIdentifier")

            if elem_type == "container":
                # Process children in order
                for child_id in children:
                    traverse_form(child_id)

            elif elem_type == "node-field":
                # Extract field information (upstream model uses same structure)
                field_id = field_identifier
                if not field_id:
                    return
                node_id = field_id["nodeId"]
                field_name = field_id["fieldName"]

                # Get node and field metadata
                node = nodes.get(node_id, {})
                node_data = node.get("data", {})
                node_type = node_data.get("type", "unknown")
                node_label = node_data.get("label", "") or node_type

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
        
        Uses the plugin-based field registry for extensible field type support.
        
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
        # Delegate to plugin system
        return field_plugins.build_field(node_data, field_name, field_info)

    def _detect_field_type(
        self, node_type: str, field_name: str, field_info: dict[str, Any]
    ) -> str:
        """
        Detect the field type based on various hints.
        
        .. deprecated:: 
            This method is deprecated and will be removed in a future version.
            It now delegates to the plugin system via field_plugins.detect_field_type().
            External code should use field_plugins.detect_field_type() directly.
        
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
        # Delegate to plugin system for backward compatibility
        return field_plugins.detect_field_type(node_type, field_name, field_info)

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

    # ------------------------------------------------------------------
    # Index-centric convenience APIs (non-breaking additions)
    # ------------------------------------------------------------------


    def preview(self) -> list[dict[str, Any]]:
        """Return lightweight summary of current inputs (index, label, type, value-preview)."""
        out: list[dict[str, Any]] = []
        for inp in self.inputs:
            field_obj = inp.field
            ftype = type(field_obj).__name__.replace("Ivk", "")
            if hasattr(field_obj, "value"):
                val = field_obj.value  # type: ignore[attr-defined]
            else:
                # Attempt a compact dict preview
                if hasattr(field_obj, "model_dump"):
                    dmp = field_obj.model_dump(exclude_none=True)  # type: ignore[attr-defined]
                    # limit size
                    keys = list(dmp.keys())[:4]
                    val = {k: dmp[k] for k in keys}
                else:
                    val = None
            if isinstance(val, str) and len(val) > 60:
                val = val[:57] + "..."
            out.append({
                "index": inp.input_index,
                "label": inp.label or inp.field_name,
                "type": ftype,
                "value": val,
            })
        return out

    def export_input_index_map(self, path: str | os.PathLike[str]) -> None:
        """Persist current input index mapping (for drift detection)."""
        import datetime
        data = {
            "workflow_id": getattr(self.definition, "id", None),
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "inputs": [
                {
                    "index": inp.input_index,
                    "label": inp.label,
                    "field_name": inp.field_name,
                    "jsonpath": inp.jsonpath,
                }
                for inp in self.inputs
            ],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def verify_input_index_map(self, path: str | os.PathLike[str]) -> dict[str, Any]:
        """Load a previously exported map and report drift.

        Returns dict with keys: unchanged, moved, missing, new.
        """
        import json
        with open(path, encoding="utf-8") as fh:
            recorded = json.load(fh)
        current_by_jsonpath = {inp.jsonpath: inp for inp in self.inputs}
        report = {"unchanged": [], "moved": [], "missing": [], "new": []}
        # Check recorded entries
        for rec in recorded.get("inputs", []):
            jp = rec.get("jsonpath")
            recorded_index = rec.get("index")
            cur = current_by_jsonpath.get(jp)
            if not cur:
                report["missing"].append(rec)
            else:
                if cur.input_index == recorded_index:
                    report["unchanged"].append({"index": cur.input_index, "label": rec.get("label")})
                else:
                    report["moved"].append({
                        "from": recorded_index,
                        "to": cur.input_index,
                        "label": rec.get("label"),
                    })
        # Detect new jsonpaths not in recorded
        recorded_jps = {r.get("jsonpath") for r in recorded.get("inputs", [])}
        for inp in self.inputs:
            if inp.jsonpath not in recorded_jps:
                report["new"].append({"index": inp.input_index, "label": inp.label})
        return report
    
    def list_outputs(self) -> list[IvkWorkflowOutput]:
        """
        List all workflow output nodes.
        
        Output nodes are nodes that:
        1. Have board output capability (save_image, l2i, etc. with WithBoard mixin)
        2. Have their board field exposed in the workflow form
        
        Returns
        -------
        List[IvkWorkflowOutput]
            Ordered list of output nodes (board fields from output-capable nodes).
            
        Notes
        -----
        Output nodes are distinguished from debug nodes by having their board field
        exposed in the form. Debug nodes have board capability but their board field
        is not user-configurable.
        
        Examples
        --------
        >>> outputs = workflow.list_outputs()
        >>> for output in outputs:
        ...     print(f"[{output.input_index}] {output.node_name}: {output.label}")
        ...     # Set the board for this output
        ...     output.field.value = "my-board-id"
        """
        # Node types that have board output capability (WithBoard mixin)
        # These are the types that can save outputs to boards
        output_capable_types = {
            "save_image",
            "l2i",  # Latents to Image
            "flux_vae_decode",
            "flux_vae_encode", 
            "hed_edge_detection"
        }
        
        # Get node type mapping
        node_types = {}
        for node in self.definition.nodes:
            node_id = node.get("id")
            node_data = node.get("data", {})
            node_type = node_data.get("type", "")
            node_types[node_id] = node_type
        
        # Filter inputs to find board fields from output-capable nodes
        outputs = []
        for inp in self.inputs:
            # Check if this is a board field
            if inp.field_name == "board":
                # Check if the node is output-capable
                node_type = node_types.get(inp.node_id, "")
                if node_type in output_capable_types:
                    outputs.append(inp)
        
        return outputs

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
        priority: int = 0,
    ) -> dict[str, Any]:
        """
        Submit the workflow for execution synchronously.

        Parameters
        ----------
        queue_id : str
            The queue to submit to.
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
        api_graph = self._convert_to_api_format()

        # Prepare batch submission
        batch_data = {
            "prepend": priority > 0,  # Higher priority items go to front
            "batch": {
                "graph": api_graph,
                "runs": 1,
            },
        }

        # Optional debug dump
        if os.environ.get("DEBUG_WORKFLOW"):
            try:
                import json
                with open("batch_data_debug.json", "w", encoding="utf-8") as f:
                    json.dump(batch_data, f, indent=2)
                print("\n[DEBUG] Batch data saved to batch_data_debug.json")
            except Exception:
                pass
        
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
            if self.item_id is None:
                raise RuntimeError("Submission did not return an item id")
            queue_item = self._get_queue_item_by_id(queue_id, self.item_id)
            if queue_item:
                self.session_id = queue_item.get("session_id")

            return {
                "batch_id": self.batch_id,
                "item_ids": item_ids,
                "enqueued": len(item_ids),
                "session_id": self.session_id,
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
                    import json as _json  # local alias to satisfy static analyzer
                    with open("tmp/last_failed_submission_detail.json", "w", encoding="utf-8") as fh:
                        _json.dump({"status_code": resp.status_code, "detail": detail_json}, fh, indent=2)
                except Exception:
                    pass
                raise RuntimeError(
                    f"Workflow submission failed ({resp.status_code}): {detail_json}"
                ) from e
            raise RuntimeError(f"Workflow submission failed: {e}") from e

    async def submit(
        self,
        queue_id: str = "default",
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
        api_graph = self._convert_to_api_format()

        # Prepare batch submission
        batch_data = {
            "prepend": priority > 0,
            "batch": {
                "graph": api_graph,
                "runs": 1,
            },
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
            if self.item_id is None:
                raise RuntimeError("Submission did not return an item id")
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
            # Try to get error details from HTTP-like exceptions
            resp = getattr(e, 'response', None)
            if resp is not None:
                try:
                    error_detail = resp.json()
                except Exception:
                    error_detail = getattr(resp, 'text', '')[:500]
                raise RuntimeError(f"Workflow submission failed: {error_detail}") from e
            raise RuntimeError(f"Workflow submission failed: {e}") from e
    
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
        queue_id: str = "default",
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
            
        Examples
        --------
    >>> queue_item = workflow.wait_for_completion_sync()
    >>> # To derive image mappings (if needed):
    >>> mappings = workflow.map_outputs_to_images(queue_item)
    >>> for mapping in mappings:
    ...     print(mapping['image_names'])
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
        queue_id: str = "default",
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
            The completed queue item.

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
        >>> 
    >>> # To derive mappings afterwards:
    >>> queue_item = await workflow.wait_for_completion()
    >>> mappings = workflow.map_outputs_to_images(queue_item)
    >>> for mapping in mappings:
    ...     print(mapping['image_names'])
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
            
        except asyncio.TimeoutError as exc:
            await sio.emit("unsubscribe_queue", {"queue_id": queue_id})
            raise asyncio.TimeoutError(
                f"Workflow execution timed out after {timeout} seconds"
            ) from exc

    async def submit_sync_monitor_async(
        self,
        queue_id: str = "default",
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
    >>> async for event in workflow.submit_sync_monitor_async():
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
            raise RuntimeError(f"Failed to cancel job: {e}") from e
    
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


    def _convert_to_api_format(self) -> dict[str, Any]:
        """
        Convert workflow definition to API graph format.
        
        Uses the original workflow JSON and JSONPath expressions to efficiently 
        update only the fields that have been set through the WorkflowHandle inputs.
        
        Returns
        -------
        dict[str, Any]
            API-formatted graph structure.
        """
        import copy
        
        # Start with a deep copy of the original workflow JSON
        workflow_copy = copy.deepcopy(self.definition.raw_data)

    # (Model synchronization now handled explicitly by sync_dnn_model();
    # no automatic silent replacement is performed here.)

    # NOTE: Previously we auto-filled missing board assignments with a submit-time
    # board_id parameter. This was removed to surface misconfigurations early –
    # users must explicitly set board inputs exposed in the form, or rely on the
    # original workflow JSON defaults. No silent fallback is applied here.
        
    # Update GUI-public (form-surfaced) fields using JSONPath expressions
        for inp in self.inputs:
            # Parse the stored JSONPath expression
            # Legacy JSONPath update replaced by direct mutation via field metadata
            field = inp.field
            api_format = field.to_api_format()
            node_id = inp.node_id
            field_name = inp.field_name

            # Skip mutation if destination field is edge-connected (avoid overriding dynamic input)
            try:
                if self._root is not None and is_field_connected(self._root, node_id, field_name):  # type: ignore[attr-defined]
                    continue
            except Exception:
                pass

            for node in workflow_copy.get("nodes", []):
                if node.get("id") != node_id:
                    continue
                inputs = (node.get("data", {}).get("inputs") or {})
                field_dict = inputs.get(field_name)
                if isinstance(field_dict, dict):
                    # Generic model identifier handling: nested 'value' dict containing a 'key'
                    if 'value' in field_dict and isinstance(field_dict['value'], dict) and 'key' in field_dict['value'] and 'key' in api_format:
                        field_dict['value'] = api_format
                    # Specific legacy field names for model identifiers stored directly
                    elif 'value' in field_dict and field_name in ['model', 'vae', 'unet', 'clip']:
                        field_dict['value'] = api_format
                    else:
                        field_dict.update(api_format)
                else:
                    inputs[field_name] = api_format
                break
        
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
            # (Note: JSONPath-based mutation above already updated GUI-public fields in workflow_copy)
            node_inputs = node_data.get("inputs", {})
            for field_name, field_data in node_inputs.items():
                # Optionally skip connected fields only if pruning explicitly enabled
                if prune_connected and f"{node_id}.{field_name}" in connected_fields:
                    continue
                
                # Get the value from the updated workflow_copy
                field_value = None
                if isinstance(field_data, dict):
                    if "value" in field_data:
                        # Standard fields have a "value" key
                        field_value = field_data["value"]
                    elif field_name == "model" and "key" in field_data:
                        # Model fields don't have a "value" key, they ARE the value
                        # (contains key, hash, name, base, type directly)
                        field_value = field_data
                    elif "key" in field_data and "type" in field_data:
                        # Other model-like fields (VAE, LoRA, etc.)
                        field_value = field_data
                else:
                    # Sometimes the field_data is the value itself (primitives)
                    field_value = field_data
                
                # Only include the field if it has a non-None value
                if field_value is not None:
                    # Normalize image field shape: server expects {'image_name': <filename>} for image inputs
                    if field_name == 'image' and isinstance(field_value, str):
                        field_value = {'image_name': field_value}
                    api_node[field_name] = field_value
            
            # Normalize board field if present and still a raw string like 'auto'
            if "board" in api_node and isinstance(api_node["board"], str):
                existing = api_node["board"]
                if existing == "auto":
                    existing = "none"  # explicit default sentinel
                api_node["board"] = {"board_id": existing}
            
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

    # ------------------------------------------------------------------
    # DNN Model Synchronization
    # ------------------------------------------------------------------
    def sync_dnn_model(self, by_name: bool = True, by_base: bool = False) -> list[tuple[IvkModelIdentifierField, IvkModelIdentifierField]]:
        """Synchronize embedded DNN model references using authoritative installed models.

        Strategy (first match wins):
            1. Exact hash
            2. Name (if by_name=True)
            3. Base model fallback (if by_base=True and base != 'any') preferring same type

        Returns a list of (old_field, new_field) Pydantic ``IvkModelIdentifierField`` pairs
        for each model reference that was updated.
        """
        from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField
        repo = getattr(self.client, 'dnn_model_repo', None)
        if repo is None:
            raise ValueError("DNN model repository not available on client")
        try:
            installed_models = list(repo.list_models())  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover
            raise ValueError(f"Unable to list installed models: {e}") from e

        by_hash: dict[str, Any] = {}
        name_map: dict[str, Any] = {}
        for m in installed_models:
            try:
                by_hash[m.hash] = m
                name_map[m.name] = m
            except Exception:
                continue

        def build_field(m) -> IvkModelIdentifierField:
            return IvkModelIdentifierField(key=m.key, hash=m.hash, name=m.name, base=m.base, type=m.type)

        nodes = self.definition.raw_data.get('nodes', [])
        replacements: list[tuple[IvkModelIdentifierField, IvkModelIdentifierField]] = []
        for node in nodes:
            node_id = node.get('id')
            data = node.get('data', {}) if isinstance(node, dict) else {}
            inputs = data.get('inputs', {}) if isinstance(data, dict) else {}
            for field_name, field_data in list(inputs.items()):
                candidate: dict[str, Any] | None = None
                if isinstance(field_data, dict):
                    if 'value' in field_data and isinstance(field_data['value'], dict) and 'key' in field_data['value'] and 'name' in field_data['value']:
                        candidate = field_data['value']
                    elif 'key' in field_data and 'name' in field_data:
                        candidate = field_data
                if not candidate:
                    continue
                cand_hash = candidate.get('hash') or ''
                cand_name = candidate.get('name') or ''
                cand_base = candidate.get('base') or ''
                cand_type = candidate.get('type') or ''
                match_model = None
                if cand_hash and cand_hash in by_hash:
                    match_model = by_hash[cand_hash]
                elif by_name and cand_name and cand_name in name_map:
                    match_model = name_map[cand_name]
                elif by_base and cand_base and cand_base != 'any':
                    base_candidates = [m for m in installed_models if getattr(m.base, 'value', m.base) == cand_base]
                    if base_candidates:
                        same_type = [m for m in base_candidates if getattr(m.type, 'value', m.type) == cand_type]
                        chosen_pool = same_type if same_type else base_candidates
                        chosen_pool.sort(key=lambda m: getattr(m, 'name', ''))
                        match_model = chosen_pool[0]
                if not match_model:
                    raise ValueError(
                        f"Unrecognized model reference: node='{node_id}' field='{field_name}' name='{cand_name}' hash='{cand_hash}'"
                        f" (strategies tried: hash{', name' if by_name else ''}{', base' if by_base else ''})"
                    )
                new_field = build_field(match_model)
                try:
                    old_field = IvkModelIdentifierField.from_api_format(candidate)
                except Exception:
                    old_field = IvkModelIdentifierField(
                        key=candidate.get('key', ''),
                        hash=candidate.get('hash', ''),
                        name=candidate.get('name', ''),
                        base=candidate.get('base', 'any'),
                        type=candidate.get('type', 'main'),
                    )
                if old_field.to_api_format() != new_field.to_api_format():
                    # Write back updated dict
                    new_dict = new_field.to_api_format()
                    if 'value' in field_data and candidate is field_data.get('value'):
                        field_data['value'] = new_dict
                    else:
                        for k in list(field_data.keys()):
                            if k in {'key','hash','name','base','type'}:
                                field_data.pop(k, None)
                        field_data.update(new_dict)
                    replacements.append((old_field, new_field))

        # Sync parsed root model if present
        if getattr(self, '_root', None) is not None:
            try:
                id_map = {n.get('id'): n for n in nodes if isinstance(n, dict)}
                for rn in self._root.nodes:  # type: ignore[attr-defined]
                    try:
                        rid = rn.get('id')
                        if rid in id_map:
                            updated = id_map[rid]
                            rn.clear()
                            rn.update(updated)  # type: ignore[union-attr]
                    except Exception:
                        continue
            except Exception:
                pass

        # Refresh IvkModelIdentifierField input objects
        from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField as _IMF
        for inp in self.inputs:
            fld = inp.field
            if isinstance(fld, _IMF):
                for node in nodes:
                    if node.get('id') != inp.node_id:  # type: ignore[union-attr]
                        continue
                    nd = node.get('data', {})
                    inps = nd.get('inputs', {})
                    fd = inps.get(inp.field_name)
                    model_ref = None
                    if isinstance(fd, dict):
                        if 'value' in fd and isinstance(fd['value'], dict) and 'key' in fd['value']:
                            model_ref = fd['value']
                        elif 'key' in fd:
                            model_ref = fd
                    if model_ref:
                        try:
                            fld.key = model_ref.get('key', fld.key)
                            fld.hash = model_ref.get('hash', fld.hash)
                            fld.name = model_ref.get('name', fld.name)
                            fld.base = model_ref.get('base', fld.base)
                            fld.type = model_ref.get('type', fld.type)
                        except Exception:
                            pass
                    break

        return replacements
    
    
    def map_outputs_to_images(self, queue_item: dict[str, Any]) -> list[OutputMapping]:
        """
        Map output nodes to their generated image filenames.
        
        Analyzes the completed queue item to determine which images were
        generated by each output node. Uses a tiered approach:
        1. session.results + prepared_source_mapping (authoritative)
        2. Legacy outputs array (fallback)
        3. Descendant traversal through execution graph (heuristic)
        
        Note
        ----
        ``image_names`` is a list because a node can (now or in future) emit
        multiple images (e.g. collection outputs); typical workflows have at
        most one.

        Evidence Tiers
        --------------
        Each mapping's ``tier`` conveys provenance of the collected image names:
        - ``results``: Definitive. Pulled from ``session.results`` via
            ``prepared_source_mapping`` (authoritative prepared→original id link).
        - ``legacy``: From older ``queue_item['outputs']`` structure (kept for
            backward compatibility if server still emits it).
        - ``traversal``: Heuristic DFS over the execution graph collecting any
            downstream node images when direct evidence was absent (best‑effort).
        - ``none``: No images discovered for that node.
        Prefer ``results`` over others when selecting a single canonical image.
        
        Parameters
        ----------
        queue_item : dict[str, Any]
            The completed queue item from wait_for_completion or get_queue_item.
            
        Returns
        -------
        list[OutputMapping]
            List of mappings from output nodes to their generated images.
            Each mapping includes node_id, board_id, image_names, and metadata.
            
        Examples
        --------
        >>> result = workflow.submit_sync()
        >>> queue_item = workflow.wait_for_completion_sync()
        >>> mappings = workflow.map_outputs_to_images(queue_item)
        >>> for mapping in mappings:
        ...     print(f"Node {mapping['node_id']} -> Board {mapping['board_id']}")
        ...     for img_name in mapping['image_names']:
        ...         print(f"  - {img_name}")
        """
        # Get workflow data from queue item
        session = queue_item.get('session', {})
        session_graph = session.get('graph', {})
        graph_nodes: dict[str, Any] = session_graph.get('nodes', {}) or {}
        
        exec_graph = session.get('execution_graph', {})
        exec_nodes: dict[str, Any] = exec_graph.get('nodes', {}) or {}
        exec_edges = exec_graph.get('edges', []) or []
        
        session_results: dict[str, Any] = session.get('results', {}) or {}
        prepared_source_mapping: dict[str, str] = session.get('prepared_source_mapping', {}) or {}
        
        # Build forward adjacency for traversal fallback
        forward: dict[str, list[str]] = {}
        for edge in exec_edges:
            try:
                src = edge.get('source', {}).get('node_id')
                dst = edge.get('destination', {}).get('node_id')
                if src and dst:
                    forward.setdefault(src, []).append(dst)
            except Exception:
                continue
        
        # Tier 1: Collect images from results (prepared -> original)
        results_images: dict[str, list[str]] = {}
        for prepared_id, payload in session_results.items():
            original_id = prepared_source_mapping.get(prepared_id, prepared_id)
            img_obj = (payload or {}).get('image') or {}
            name = img_obj.get('image_name')
            if name:
                results_images.setdefault(original_id, [])
                if name not in results_images[original_id]:
                    results_images[original_id].append(name)
        
        # Tier 2: Legacy outputs array fallback
        legacy_images: dict[str, list[str]] = {}
        for out in queue_item.get('outputs', []) or []:
            node_id = out.get('node_id') or out.get('id')
            img_obj = out.get('image') or {}
            name = img_obj.get('image_name')
            if node_id and name:
                legacy_images.setdefault(node_id, [])
                if name not in legacy_images[node_id]:
                    legacy_images[node_id].append(name)
        
        # Tier 3: Descendant traversal helper
        def descend_collect(start_id: str) -> list[str]:
            seen, stack, found = set(), [start_id], []
            while stack:
                nid = stack.pop()
                if nid in seen:
                    continue
                seen.add(nid)
                node_data = exec_nodes.get(nid, {})
                img_obj = node_data.get('image') or {}
                name = img_obj.get('image_name')
                if name and name not in found:
                    found.append(name)
                for nxt in forward.get(nid, []):
                    if nxt not in seen:
                        stack.append(nxt)
            return found
        
        # Get workflow outputs and create mappings
        outputs_meta: list[OutputMapping] = []
        outputs = self.list_outputs()

        for output in outputs:
            node_id = output.node_id
            node_graph = graph_nodes.get(node_id, {})

            # Extract board ID from the original submission graph
            board_entry = node_graph.get('board', {}) if isinstance(node_graph.get('board'), dict) else {}
            board_id = board_entry.get('board_id') or 'none'

            # Collect images using tiered approach
            images = list(results_images.get(node_id, []))
            tier = 'results' if images else ''

            if not images:
                images = list(legacy_images.get(node_id, []))
                tier = 'legacy' if images else tier

            if not images:
                images = descend_collect(node_id)
                tier = 'traversal' if images else tier or 'none'

            # Create output mapping
            mapping = OutputMapping(
                node_id=node_id,
                board_id=board_id,
                image_names=images,
                tier=tier,
                node_type=node_graph.get('type', 'unknown'),
                input_index=output.input_index,
                label=output.label
            )
            outputs_meta.append(mapping)

        return outputs_meta
    
    def get_output_image_jsonpath_templates(self) -> list[dict[str, str]]:
        """Return best-effort JSONPath templates for locating output image filenames post-run.

        Rationale
        ---------
        Prior to submission we do NOT know the prepared node ids that will appear
        as keys under ``$.session.results`` because the server may expand or
        transform the original graph. Therefore we cannot emit an *exact* JSONPath
        that directly points to ``image.image_name`` for a specific original output
        node ahead of time. We *can* provide:

        1. A stable JSONPath to the original node's board assignment in the
           submission graph (if present).
        2. Wildcard JSONPaths that enumerate all result image filenames.
        3. A lookup path for the prepared→original mapping allowing a resolver
           to filter the wildcard results after the queue item is available.

        Consumers can execute the following resolution algorithm after obtaining
        the completed queue item JSON:

        a. Collect all prepared ids ``p`` where
           ``$.session.prepared_source_mapping[p] == <original_node_id>``.
        b. For each such prepared id, read
           ``$.session.results[<prepared_id>].image.image_name``.
        c. Aggregate unique filenames per original node.

        Returns
        -------
        list[dict[str, str]]
            Each dict contains keys:
              - node_id: original output node id
              - board_jsonpath: path to board id (may yield nothing if board absent)
              - prepared_mapping_jsonpath: root path to prepared_source_mapping object
              - results_wildcard_jsonpath: wildcard path enumerating all image names
              - note: explanatory note about post-run filtering requirement
        """
        templates: list[dict[str, str]] = []
        for out in self.list_outputs():
            node_id = out.node_id
            # Board JSONPath (original submission graph). Using bracket notation to avoid predicate support variance.
            board_jsonpath = f"$.session.graph.nodes['{node_id}'].board.board_id"
            # Prepared mapping root (used for filtering prepared ids by value == original id)
            prepared_mapping_jsonpath = "$.session.prepared_source_mapping"
            # Wildcard over all result image filenames
            results_wildcard_jsonpath = "$.session.results.*.image.image_name"
            note = (
                "Filter prepared ids whose value in prepared_source_mapping equals this node_id; "
                "then read each corresponding $.session.results[prepared_id].image.image_name."
            )
            templates.append({
                "node_id": node_id,
                "board_jsonpath": board_jsonpath,
                "prepared_mapping_jsonpath": prepared_mapping_jsonpath,
                "results_wildcard_jsonpath": results_wildcard_jsonpath,
                "note": note,
            })
        return templates
    
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
