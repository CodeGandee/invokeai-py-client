"""Workflow management for InvokeAI Python client.

This module provides the ClientWorkflow class for loading, configuring,
and executing InvokeAI workflows from JSON definitions.
"""

import json
import asyncio
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Union, Set, Tuple, TYPE_CHECKING,
    Final, Literal, TypeVar, cast, overload
)
from typing_extensions import TypeAlias, Self
from enum import Enum
from datetime import datetime
import logging
from pydantic import BaseModel, Field, validator

from .types import (
    InvokeAIType, InvokeAIImage, InvokeAIModelReference,
    TYPE_REGISTRY, TypeRegistry
)
from .exceptions import (
    WorkflowLoadError, WorkflowExecutionError, ValidationError,
    ResourceNotFoundError, TimeoutError
)
from .types_extra import (
    WorkflowDefinitionDict, WorkflowNodeDict, WorkflowEdgeDict,
    JobStatusDict, NodeStatus, WorkflowInputValue, WorkflowOutputValue,
    PathLike, DEFAULT_POLL_INTERVAL
)

if TYPE_CHECKING:
    from .client import InvokeAIClient


logger: Final[logging.Logger] = logging.getLogger(__name__)

# Type alias for workflow data
WorkflowData: TypeAlias = Dict[str, Any]


class WorkflowStatus(str, Enum):
    """Workflow execution status.
    
    Attributes
    ----------
    PENDING : str
        Workflow is queued but not started.
    IN_PROGRESS : str
        Workflow is currently executing.
    COMPLETED : str
        Workflow completed successfully.
    FAILED : str
        Workflow execution failed.
    CANCELLED : str
        Workflow was cancelled.
    """
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowInput(BaseModel):
    """Represents a single workflow input field.
    
    Attributes
    ----------
    name : str
        The user-friendly name of the input.
    field_id : str
        The internal field identifier.
    node_id : str
        The node this input belongs to.
    field_name : str
        The field name within the node.
    type_config : Dict[str, Any]
        Type configuration from workflow.
    value : Optional[Any]
        The current value of the input.
    type_instance : Optional[InvokeAIType]
        The type instance for this input.
    """
    
    name: str = Field(..., description="User-friendly input name")
    field_id: str = Field(..., description="Internal field ID")
    node_id: str = Field(..., description="Node ID")
    field_name: str = Field(..., description="Field name in node")
    type_config: Dict[str, Any] = Field(default_factory=dict, description="Type configuration")
    value: Optional[Any] = Field(None, description="Current value")
    type_instance: Optional[InvokeAIType] = Field(None, description="Type instance")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class WorkflowOutput(BaseModel):
    """Represents a workflow output.
    
    Attributes
    ----------
    node_id : str
        The node that produced this output.
    field_name : str
        The output field name.
    value : Any
        The output value.
    type_name : Optional[str]
        The type of the output.
    """
    
    node_id: str = Field(..., description="Source node ID")
    field_name: str = Field(..., description="Output field name")
    value: Any = Field(..., description="Output value")
    type_name: Optional[str] = Field(None, description="Output type")


class WorkflowResult(BaseModel):
    """Result of workflow execution.
    
    Attributes
    ----------
    workflow_id : str
        The workflow ID.
    job_id : str
        The execution job ID.
    status : WorkflowStatus
        Final execution status.
    outputs : List[WorkflowOutput]
        List of workflow outputs.
    error : Optional[str]
        Error message if failed.
    started_at : datetime
        When execution started.
    completed_at : Optional[datetime]
        When execution completed.
    execution_time : Optional[float]
        Total execution time in seconds.
    """
    
    workflow_id: str = Field(..., description="Workflow ID")
    job_id: str = Field(..., description="Job ID")
    status: WorkflowStatus = Field(..., description="Execution status")
    outputs: List[WorkflowOutput] = Field(default_factory=list, description="Outputs")
    error: Optional[str] = Field(None, description="Error message")
    started_at: datetime = Field(..., description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    
    def get_output(self, name: str) -> Optional["WorkflowOutput"]:
        """Get output by name.
        
        Parameters
        ----------
        name : str
            The output name or node_id.field_name.
        
        Returns
        -------
        Optional[WorkflowOutput]
            The output if found, None otherwise.
        """
        for output in self.outputs:
            if output.field_name == name:
                return output
            if f"{output.node_id}.{output.field_name}" == name:
                return output
        return None
    
    def get_images(self) -> List[InvokeAIImage]:
        """Get all image outputs.
        
        Returns
        -------
        List[InvokeAIImage]
            List of image outputs.
        """
        images = []
        for output in self.outputs:
            if output.type_name in ["image", "ImageField"]:
                if isinstance(output.value, InvokeAIImage):
                    images.append(output.value)
                else:
                    images.append(InvokeAIImage.from_api_value(output.value))
        return images


class ClientWorkflow:
    """Manages a workflow instance for execution.
    
    This class represents a workflow loaded from a JSON definition file.
    It handles input configuration, validation, submission, and result retrieval.
    
    Attributes
    ----------
    definition : Dict[str, Any]
        The full workflow definition.
    name : str
        Workflow name.
    id : str
        Workflow ID.
    inputs : Dict[str, WorkflowInput]
        Available workflow inputs by name.
    client : Optional[InvokeAIClient]
        Associated client instance.
    
    Methods
    -------
    from_file(path, client=None)
        Load workflow from JSON file.
    from_dict(definition, client=None)
        Load workflow from dictionary.
    set_input(name, value)
        Set an input value.
    get_input(name)
        Get current input value.
    validate()
        Validate all required inputs are set.
    execute(timeout=None)
        Execute the workflow.
    
    Examples
    --------
    >>> # Load workflow from file
    >>> workflow = ClientWorkflow.from_file("text-to-image.json", client)
    >>> 
    >>> # Set inputs
    >>> workflow.set_input("prompt", "a beautiful landscape")
    >>> workflow.set_input("width", 1024)
    >>> workflow.set_input("height", 768)
    >>> 
    >>> # Execute and get results
    >>> result = await workflow.execute()
    >>> images = result.get_images()
    """
    
    def __init__(
        self,
        definition: Dict[str, Any],
        client: Optional["InvokeAIClient"] = None
    ) -> None:
        """Initialize workflow from definition.
        
        Parameters
        ----------
        definition : Dict[str, Any]
            The workflow definition dictionary.
        client : Optional[InvokeAIClient]
            The client instance to use for execution.
        
        Raises
        ------
        WorkflowLoadError
            If the workflow definition is invalid.
        """
        self.definition = definition
        self.client = client
        self._type_registry = TYPE_REGISTRY
        
        # Extract basic metadata
        self.name: str = definition.get("name", "unnamed")
        self.id: str = definition.get("id", "")
        self.description: str = definition.get("description", "")
        self.version: str = definition.get("version", "")
        
        # Parse workflow structure
        self.nodes: Dict[str, WorkflowNodeDict] = self._parse_nodes(definition.get("nodes", []))
        self.edges: List[WorkflowEdgeDict] = self._parse_edges(definition.get("edges", []))
        self.form: Dict[str, Any] = definition.get("form", {})
        
        # Extract workflow inputs from form
        self.inputs: Dict[str, WorkflowInput] = self._extract_inputs()
        
        # Track execution state
        self._job_id: Optional[str] = None
        self._status: WorkflowStatus = WorkflowStatus.PENDING
        
        logger.info(f"Loaded workflow '{self.name}' with {len(self.inputs)} inputs")
    
    @classmethod
    def from_file(
        cls,
        path: PathLike,
        client: Optional["InvokeAIClient"] = None
    ) -> Self:
        """Load workflow from JSON file.
        
        Parameters
        ----------
        path : Union[str, Path]
            Path to the workflow JSON file.
        client : Optional[InvokeAIClient]
            The client instance to use.
        
        Returns
        -------
        ClientWorkflow
            The loaded workflow instance.
        
        Raises
        ------
        WorkflowLoadError
            If the file cannot be loaded or parsed.
        
        Examples
        --------
        >>> workflow = ClientWorkflow.from_file("workflows/text-to-image.json")
        >>> print(f"Loaded: {workflow.name}")
        """
        path = Path(path)
        if not path.exists():
            raise WorkflowLoadError(
                f"Workflow file not found: {path}",
                file_path=str(path)
            )
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                definition = json.load(f)
        except json.JSONDecodeError as e:
            raise WorkflowLoadError(
                f"Invalid JSON in workflow file: {path}",
                file_path=str(path),
                parse_error=str(e),
                cause=e
            )
        except Exception as e:
            raise WorkflowLoadError(
                f"Failed to read workflow file: {path}",
                file_path=str(path),
                cause=e
            )
        
        return cls(definition, client)
    
    @classmethod
    def from_dict(
        cls,
        definition: Dict[str, Any],
        client: Optional["InvokeAIClient"] = None
    ) -> Self:
        """Load workflow from dictionary.
        
        Parameters
        ----------
        definition : Dict[str, Any]
            The workflow definition dictionary.
        client : Optional[InvokeAIClient]
            The client instance to use.
        
        Returns
        -------
        ClientWorkflow
            The loaded workflow instance.
        
        Examples
        --------
        >>> definition = {"name": "my-workflow", "nodes": [...], ...}
        >>> workflow = ClientWorkflow.from_dict(definition)
        """
        return cls(definition, client)
    
    def _parse_nodes(self, nodes: List[WorkflowNodeDict]) -> Dict[str, WorkflowNodeDict]:
        """Parse workflow nodes.
        
        Parameters
        ----------
        nodes : List[Dict[str, Any]]
            List of node definitions.
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Nodes indexed by ID.
        """
        result: Dict[str, WorkflowNodeDict] = {}
        for node in nodes:
            node_id = node.get("id", "")
            if node_id:
                result[node_id] = node
        return result
    
    def _parse_edges(self, edges: List[WorkflowEdgeDict]) -> List[WorkflowEdgeDict]:
        """Parse workflow edges.
        
        Parameters
        ----------
        edges : List[Dict[str, Any]]
            List of edge definitions.
        
        Returns
        -------
        List[Dict[str, Any]]
            Parsed edges.
        """
        return edges
    
    def _extract_inputs(self) -> Dict[str, WorkflowInput]:
        """Extract workflow inputs from form definition.
        
        Returns
        -------
        Dict[str, WorkflowInput]
            Workflow inputs indexed by name.
        """
        inputs: Dict[str, WorkflowInput] = {}
        
        if not self.form:
            return inputs
        
        elements = self.form.get("elements", {})
        
        for element_id, element in elements.items():
            if element.get("type") != "node-field":
                continue
            
            data = element.get("data", {})
            field_id = data.get("fieldIdentifier", {})
            settings = data.get("settings", {})
            
            node_id = field_id.get("nodeId", "")
            field_name = field_id.get("fieldName", "")
            
            if not node_id or not field_name:
                continue
            
            # Find the node to get the field's current value and label
            node = self.nodes.get(node_id, {})
            node_data = node.get("data", {})
            node_inputs = node_data.get("inputs", {})
            field_data = node_inputs.get(field_name, {})
            
            # Use field label if available, otherwise use field name
            input_name = field_data.get("label", "").strip()
            if not input_name:
                input_name = field_data.get("description", "").strip()
            if not input_name:
                input_name = field_name
            
            # Create type instance from settings
            type_instance = self._type_registry.create_from_config(data)
            
            workflow_input = WorkflowInput(
                name=input_name,
                field_id=element_id,
                node_id=node_id,
                field_name=field_name,
                type_config=settings,
                value=field_data.get("value"),
                type_instance=type_instance
            )
            
            inputs[input_name] = workflow_input
            
            logger.debug(f"Found input '{input_name}' ({node_id}.{field_name})")
        
        return inputs
    
    def set_input(self, name: str, value: WorkflowInputValue) -> None:
        """Set a workflow input value.
        
        Parameters
        ----------
        name : str
            The input name (as shown in GUI).
        value : Any
            The value to set. Can be raw value or InvokeAIType instance.
        
        Raises
        ------
        ValidationError
            If the input name is not found or value is invalid.
        
        Examples
        --------
        >>> # Set primitive values
        >>> workflow.set_input("prompt", "a landscape")
        >>> workflow.set_input("width", 1024)
        >>> 
        >>> # Set typed values
        >>> image = InvokeAIImage.from_file("input.png")
        >>> workflow.set_input("image", image)
        """
        if name not in self.inputs:
            available = list(self.inputs.keys())
            raise ValidationError(
                f"Input '{name}' not found in workflow",
                field=name,
                constraints={"available_inputs": available}
            )
        
        input_field = self.inputs[name]
        
        # Validate and convert value if needed
        if isinstance(value, InvokeAIType):
            # Already a typed value
            input_field.value = value
        else:
            # Convert raw value to appropriate type
            if input_field.type_instance:
                try:
                    input_field.type_instance.validate_value(value)
                except Exception as e:
                    raise ValidationError(
                        f"Invalid value for input '{name}'",
                        field=name,
                        value=value,
                        cause=e
                    )
            input_field.value = value
        
        # Update the node's input value in the definition
        node = self.nodes.get(input_field.node_id, {})
        if node:
            node_data = node.get("data", {})
            node_inputs = node_data.get("inputs", {})
            field_data = node_inputs.get(input_field.field_name, {})
            
            # Convert to API format if needed
            if isinstance(value, InvokeAIType):
                field_data["value"] = value.to_api_value()
            else:
                field_data["value"] = value
        
        logger.debug(f"Set input '{name}' = {value}")
    
    def get_input(self, name: str) -> Optional[WorkflowInputValue]:
        """Get current input value.
        
        Parameters
        ----------
        name : str
            The input name.
        
        Returns
        -------
        Any
            The current input value, or None if not set.
        
        Raises
        ------
        ValidationError
            If the input name is not found.
        
        Examples
        --------
        >>> prompt = workflow.get_input("prompt")
        >>> print(f"Current prompt: {prompt}")
        """
        if name not in self.inputs:
            raise ValidationError(
                f"Input '{name}' not found in workflow",
                field=name
            )
        
        return self.inputs[name].value
    
    def list_inputs(self) -> List[str]:
        """List all available input names.
        
        Returns
        -------
        List[str]
            List of input names.
        
        Examples
        --------
        >>> inputs = workflow.list_inputs()
        >>> print(f"Available inputs: {inputs}")
        """
        return list(self.inputs.keys())
    
    def get_required_inputs(self) -> List[str]:
        """Get list of required inputs that are not yet set.
        
        Returns
        -------
        List[str]
            List of required input names without values.
        
        Examples
        --------
        >>> missing = workflow.get_required_inputs()
        >>> if missing:
        ...     print(f"Please set: {missing}")
        """
        required = []
        for name, input_field in self.inputs.items():
            if input_field.value is None:
                # Check if this input is truly required
                node = self.nodes.get(input_field.node_id, {})
                node_data = node.get("data", {})
                node_inputs = node_data.get("inputs", {})
                field_data = node_inputs.get(input_field.field_name, {})
                
                # If there's no default value and no connection, it's required
                if "value" not in field_data:
                    required.append(name)
        
        return required
    
    def validate(self) -> bool:
        """Validate workflow is ready for execution.
        
        Checks that all required inputs have values and meet constraints.
        
        Returns
        -------
        bool
            True if valid, raises exception if not.
        
        Raises
        ------
        ValidationError
            If validation fails.
        
        Examples
        --------
        >>> try:
        ...     workflow.validate()
        ...     print("Workflow is ready")
        ... except ValidationError as e:
        ...     print(f"Validation failed: {e}")
        """
        # Check required inputs
        missing = self.get_required_inputs()
        if missing:
            raise ValidationError(
                f"Required inputs not set: {', '.join(missing)}",
                constraints={"missing_inputs": missing}
            )
        
        # Validate each input value
        for name, input_field in self.inputs.items():
            if input_field.value is not None and input_field.type_instance:
                try:
                    input_field.type_instance.validate_value(input_field.value)
                except Exception as e:
                    raise ValidationError(
                        f"Invalid value for input '{name}'",
                        field=name,
                        value=input_field.value,
                        cause=e
                    )
        
        return True
    
    async def _upload_resources(self) -> None:
        """Upload any resources (images, etc.) before execution.
        
        Raises
        ------
        WorkflowExecutionError
            If resource upload fails.
        """
        if not self.client:
            return
        
        for name, input_field in self.inputs.items():
            value = input_field.value
            
            # Upload images
            if isinstance(value, InvokeAIImage) and not value.image_name:
                try:
                    await value.upload(self.client)
                    # Update the node's input with the uploaded reference
                    self.set_input(name, value)
                except Exception as e:
                    raise WorkflowExecutionError(
                        f"Failed to upload image for input '{name}'",
                        workflow_id=self.id,
                        cause=e
                    )
    
    async def execute(
        self,
        timeout: Optional[float] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL
    ) -> WorkflowResult:
        """Execute the workflow.
        
        Submits the workflow for execution and waits for completion.
        
        Parameters
        ----------
        timeout : Optional[float]
            Maximum time to wait for completion in seconds.
        poll_interval : float
            How often to check status in seconds.
        
        Returns
        -------
        WorkflowResult
            The execution result with outputs.
        
        Raises
        ------
        ValidationError
            If workflow validation fails.
        WorkflowExecutionError
            If execution fails.
        TimeoutError
            If execution times out.
        
        Examples
        --------
        >>> # Execute with timeout
        >>> result = await workflow.execute(timeout=60)
        >>> if result.status == WorkflowStatus.COMPLETED:
        ...     images = result.get_images()
        ...     for img in images:
        ...         await img.download(client)
        """
        if not self.client:
            raise WorkflowExecutionError(
                "No client attached to workflow",
                workflow_id=self.id
            )
        
        # Validate inputs
        self.validate()
        
        # Upload resources
        await self._upload_resources()
        
        # Submit workflow
        started_at = datetime.now()
        try:
            self._job_id = await self.client.submit_workflow(self)
            self._status = WorkflowStatus.PENDING
        except Exception as e:
            raise WorkflowExecutionError(
                "Failed to submit workflow",
                workflow_id=self.id,
                cause=e
            )
        
        # Wait for completion
        elapsed: float = 0.0
        error: Optional[str] = None
        status_info: JobStatusDict = {"job_id": self._job_id, "status": "pending"}  # type: ignore
        
        while True:
            # Check timeout
            if timeout and elapsed >= timeout:
                raise TimeoutError(
                    operation=f"workflow execution ({self.name})",
                    timeout_seconds=timeout
                )
            
            # Check status
            try:
                status_info = cast(JobStatusDict, await self.client.get_job_status(self._job_id))
                self._status = WorkflowStatus(status_info.get("status", "pending"))
                
                if self._status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                    break
                
            except Exception as e:
                logger.warning(f"Failed to check job status: {e}")
            
            # Wait before next check
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        completed_at = datetime.now()
        execution_time = (completed_at - started_at).total_seconds()
        
        # Get results
        if self._status == WorkflowStatus.COMPLETED:
            try:
                outputs = await self.client.get_job_outputs(self._job_id)
            except Exception as e:
                raise WorkflowExecutionError(
                    "Failed to retrieve workflow outputs",
                    workflow_id=self.id,
                    job_id=self._job_id,
                    cause=e
                )
        else:
            outputs = []
            error = status_info.get("error", "Workflow execution failed")
        
        return WorkflowResult(
            workflow_id=self.id,
            job_id=self._job_id,
            status=self._status,
            outputs=outputs,
            error=error if self._status == WorkflowStatus.FAILED else None,
            started_at=started_at,
            completed_at=completed_at,
            execution_time=execution_time
        )
    
    def get_status(self) -> WorkflowStatus:
        """Get current workflow execution status.
        
        Returns
        -------
        WorkflowStatus
            The current status.
        
        Examples
        --------
        >>> status = workflow.get_status()
        >>> print(f"Workflow is {status.value}")
        """
        return self._status
    
    def get_job_id(self) -> Optional[str]:
        """Get current job ID if executing.
        
        Returns
        -------
        Optional[str]
            The job ID, or None if not executing.
        
        Examples
        --------
        >>> job_id = workflow.get_job_id()
        >>> if job_id:
        ...     print(f"Running as job {job_id}")
        """
        return self._job_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Export workflow definition with current input values.
        
        Returns
        -------
        Dict[str, Any]
            The complete workflow definition.
        
        Examples
        --------
        >>> # Export modified workflow
        >>> definition = workflow.to_dict()
        >>> with open("modified.json", "w") as f:
        ...     json.dump(definition, f)
        """
        return self.definition.copy()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ClientWorkflow(name='{self.name}', inputs={len(self.inputs)}, status={self._status.value})"