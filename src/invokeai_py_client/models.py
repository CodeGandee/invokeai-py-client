"""
Data models for InvokeAI API responses and entities.

This module provides Pydantic models for type-safe handling of
InvokeAI API data structures.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Enumeration of job execution states."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageCategory(str, Enum):
    """Enumeration of image categories."""
    
    USER = "user"
    GENERATED = "generated"
    CONTROL = "control"
    MASK = "mask"
    OTHER = "other"


class BaseModelEnum(str, Enum):
    """Enumeration of base model architectures."""
    
    SD1 = "sd-1"
    SD2 = "sd-2"
    SDXL = "sdxl"
    SDXL_REFINER = "sdxl-refiner"
    FLUX = "flux"
    FLUX_SCHNELL = "flux-schnell"


class Board(BaseModel):
    """
    Represents an InvokeAI board for organizing images.
    
    This matches the BoardDTO structure from the InvokeAI API.
    Supports both regular boards and the special "uncategorized" board.
    
    The uncategorized board is a system-managed board that:
    - Cannot be created or deleted by users
    - Always exists in the system
    - Uses "none" as its board_id in API calls
    - Holds all images not assigned to any board
    
    Examples
    --------
    >>> board = Board(board_id="abc123", board_name="Landscapes")
    >>> print(f"{board.board_name}: {board.image_count} images")
    
    >>> uncategorized = Board.uncategorized(image_count=10)
    >>> print(f"Uncategorized: {uncategorized.image_count} images")
    >>> print(f"Is system board: {uncategorized.is_system_board()}")
    """
    
    board_id: Optional[str] = Field(None, description="The unique ID of the board (None for uncategorized)")
    board_name: Optional[str] = Field(None, description="The name of the board (None for uncategorized)")
    created_at: Optional[Union[datetime, str]] = Field(None, description="The created timestamp of the board")
    updated_at: Optional[Union[datetime, str]] = Field(None, description="The updated timestamp of the board")
    deleted_at: Optional[Union[datetime, str]] = Field(None, description="The deleted timestamp of the board")
    cover_image_name: Optional[str] = Field(None, description="The name of the board's cover image")
    archived: bool = Field(False, description="Whether or not the board is archived")
    is_private: Optional[bool] = Field(None, description="Whether the board is private")
    image_count: int = Field(0, ge=0, description="The number of images in the board")
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> Board:
        """
        Create a Board from API response data.
        
        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.
        
        Returns
        -------
        Board
            Parsed board instance.
        """
        return cls(**data)
    
    @classmethod
    def uncategorized(cls, image_count: int = 0) -> Board:
        """
        Create a special uncategorized board instance.
        
        The uncategorized board represents images not assigned to any board.
        
        Important: We use the string "none" as board_id rather than Python's None
        because:
        - InvokeAI API expects the literal string "none" in URL paths
        - API endpoint: /api/v1/boards/none/image_names requires "none" as a path parameter
        - Python's None would serialize to null in JSON, which cannot be used in URL paths
        - "none" is InvokeAI's established convention for uncategorized items
        
        Parameters
        ----------
        image_count : int
            Number of uncategorized images.
        
        Returns
        -------
        Board
            Uncategorized board instance with board_id="none".
        """
        from datetime import datetime
        now = datetime.now().isoformat()
        return cls(
            board_id="none",
            board_name="Uncategorized",
            created_at=now,
            updated_at=now,
            deleted_at=None,
            cover_image_name=None,
            image_count=image_count,
            archived=False,
            is_private=False
        )
    
    def is_uncategorized(self) -> bool:
        """
        Check if this is the uncategorized board.
        
        We check for both "none" (the API convention) and Python's None
        (for edge cases) to handle different scenarios:
        - board_id == "none": Standard uncategorized board from API
        - board_id is None: Fallback for edge cases or uninitialized boards
        
        Returns
        -------
        bool
            True if this is the uncategorized board.
        """
        return self.board_id == "none" or self.board_id is None
    
    def is_system_board(self) -> bool:
        """
        Check if this is a system-managed board.
        
        System boards cannot be created or deleted by users.
        Currently only the uncategorized board is a system board.
        
        Returns
        -------
        bool
            True if this is a system-managed board.
        """
        return self.is_uncategorized()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns
        -------
        Dict[str, Any]
            Board data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class Image(BaseModel):
    """
    Represents an image in the InvokeAI system.
    
    This matches the ImageDTO structure from the InvokeAI API.
    
    Examples
    --------
    >>> image = Image(image_name="abc-123.png", width=1024, height=768)
    >>> print(f"Image: {image.image_name} ({image.width}x{image.height})")
    """
    
    image_name: str = Field(..., description="Server-side image identifier")
    board_id: Optional[str] = Field(None, description="Associated board ID (None for uncategorized)")
    image_category: ImageCategory = Field(ImageCategory.GENERATED, description="Image category type")
    width: Optional[int] = Field(None, gt=0, description="Image width in pixels")
    height: Optional[int] = Field(None, gt=0, description="Image height in pixels")
    created_at: Optional[Union[datetime, str]] = Field(None, description="Creation timestamp")
    updated_at: Optional[Union[datetime, str]] = Field(None, description="Last modification timestamp")
    starred: bool = Field(False, description="Whether the image is starred")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Generation metadata")
    thumbnail_url: Optional[str] = Field(None, description="URL for thumbnail version")
    image_url: Optional[str] = Field(None, description="URL for full resolution image")
    is_intermediate: bool = Field(False, description="Whether this is an intermediate image")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    node_id: Optional[str] = Field(None, description="Associated node ID")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> Image:
        """
        Create an Image from API response data.
        
        Handles field mapping from API response to model fields.
        
        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.
        
        Returns
        -------
        Image
            Parsed image instance.
        """
        # Map image_category string to enum if needed
        if 'image_category' in data and isinstance(data['image_category'], str):
            try:
                data['image_category'] = ImageCategory(data['image_category'])
            except ValueError:
                # If unknown category, default to OTHER
                data['image_category'] = ImageCategory.OTHER
        
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns
        -------
        Dict[str, Any]
            Image data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class Job(BaseModel):
    """
    Represents a workflow execution job.
    
    Examples
    --------
    >>> job = Job(id="job-123", status=JobStatus.RUNNING, progress=0.5)
    >>> print(f"Job {job.id}: {job.status} ({job.progress*100:.0f}%)")
    """
    
    id: str = Field(..., description="Unique job identifier")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    status: JobStatus = Field(JobStatus.PENDING, description="Current job status")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Completion progress (0.0 to 1.0)")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Job output data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional job metadata")
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> Job:
        """
        Create a Job from API response data.
        
        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.
        
        Returns
        -------
        Job
            Parsed job instance.
        """
        return cls(**data)
    
    def is_complete(self) -> bool:
        """
        Check if the job has finished execution.
        
        Returns
        -------
        bool
            True if completed, failed, or cancelled.
        """
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    def is_successful(self) -> bool:
        """
        Check if the job completed successfully.
        
        Returns
        -------
        bool
            True if status is COMPLETED.
        """
        return self.status == JobStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns
        -------
        Dict[str, Any]
            Job data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class WorkflowDefinition(BaseModel):
    """
    Represents a workflow definition from InvokeAI.
    
    Examples
    --------
    >>> definition = WorkflowDefinition.from_file("workflow.json")
    >>> print(f"Workflow: {definition.name} v{definition.version}")
    >>> print(f"Inputs: {len(definition.get_input_fields())}")
    """
    
    id: Optional[str] = Field(None, description="Workflow identifier")
    name: Optional[str] = Field(None, description="Workflow display name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: str = Field("3.0.0", description="Workflow schema version")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow node definitions")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Node connections")
    form: Dict[str, Any] = Field(default_factory=dict, description="Public input definitions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow metadata")
    
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> WorkflowDefinition:
        """
        Load a workflow definition from a JSON file.
        
        Parameters
        ----------
        path : Union[str, Path]
            Path to the workflow JSON file.
        
        Returns
        -------
        WorkflowDefinition
            Parsed workflow definition.
        
        Raises
        ------
        FileNotFoundError
            If the file doesn't exist.
        ValueError
            If the JSON is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in workflow file: {e}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowDefinition:
        """
        Create a workflow definition from a dictionary.
        
        Parameters
        ----------
        data : Dict[str, Any]
            Workflow data dictionary.
        
        Returns
        -------
        WorkflowDefinition
            Parsed workflow definition.
        """
        # Extract meta information if present
        meta = data.get('meta', {})
        if 'version' in meta and 'version' not in data:
            data['version'] = meta['version']
        
        # Extract name from meta if not in root
        if 'name' not in data and 'name' in meta:
            data['name'] = meta['name']
        
        # Extract description from meta if not in root
        if 'description' not in data and 'description' in meta:
            data['description'] = meta['description']
        
        return cls(**data)
    
    def get_input_fields(self) -> List[Dict[str, Any]]:
        """
        Get all public input field definitions.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of input field specifications.
        """
        # Extract input fields from the form section
        form_data = self.form or {}
        inputs = []
        
        # The form structure contains node-field-* entries for inputs
        for key, value in form_data.items():
            if key.startswith('node-field-') and isinstance(value, dict):
                field_data = value.get('data', {})
                field_identifier = field_data.get('fieldIdentifier', {})
                settings = field_data.get('settings', {})
                
                input_field = {
                    'id': key,
                    'node_id': field_identifier.get('nodeId'),
                    'field_name': field_identifier.get('fieldName'),
                    'type': settings.get('type'),
                    'component': settings.get('component'),
                    'show_description': field_data.get('showDescription', False),
                    'data': field_data
                }
                inputs.append(input_field)
        
        return inputs
    
    def get_output_fields(self) -> List[Dict[str, Any]]:
        """
        Get all output field definitions.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of output field specifications.
        """
        # Extract output fields from nodes
        outputs = []
        for node in self.nodes:
            if node.get('type') == 'output':
                node_data = node.get('data', {})
                outputs.append({
                    'id': node.get('id'),
                    'type': node_data.get('type'),
                    'data': node_data
                })
        return outputs
    
    def validate_workflow(self) -> List[str]:
        """
        Validate the workflow definition structure.
        
        Returns
        -------
        List[str]
            List of validation errors, empty if valid.
        """
        errors = []
        
        # Check required fields
        if not self.nodes:
            errors.append("Workflow must have at least one node")
        
        # Check version compatibility
        if self.version and not self.version.startswith(('2.', '3.')):
            errors.append(f"Unsupported workflow version: {self.version}")
        
        # Check node structure
        for i, node in enumerate(self.nodes):
            if 'id' not in node:
                errors.append(f"Node {i} missing 'id' field")
            if 'type' not in node:
                errors.append(f"Node {i} missing 'type' field")
        
        # Check edge structure
        for i, edge in enumerate(self.edges):
            if 'source' not in edge:
                errors.append(f"Edge {i} missing 'source' field")
            if 'target' not in edge:
                errors.append(f"Edge {i} missing 'target' field")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns
        -------
        Dict[str, Any]
            Workflow data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class DnnModel(BaseModel):
    """
    Represents a DNN (Deep Neural Network) model in InvokeAI.
    
    Examples
    --------
    >>> model = DnnModel(
    ...     key="sdxl-base",
    ...     name="Stable Diffusion XL Base",
    ...     base=BaseModelEnum.SDXL,
    ...     type="main"
    ... )
    """
    
    key: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Model display name")
    base: BaseModelEnum = Field(..., description="Base architecture type")
    type: str = Field(..., description="Model type (main, vae, lora, etc.)")
    hash: Optional[str] = Field(None, description="Model file hash")
    path: Optional[str] = Field(None, description="Model file path")
    description: Optional[str] = Field(None, description="Model description")
    format: Optional[str] = Field(None, description="Model format (diffusers, checkpoint, etc.)")
    variant: Optional[str] = Field(None, description="Model variant (fp16, fp32, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional model metadata")
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> DnnModel:
        """
        Create a DnnModel from API response data.
        
        Parameters
        ----------
        data : Dict[str, Any]
            Raw API response dictionary.
        
        Returns
        -------
        DnnModel
            Parsed model instance.
        """
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns
        -------
        Dict[str, Any]
            Model data as dictionary.
        """
        return self.model_dump(exclude_none=True)


class SessionEvent(BaseModel):
    """
    Represents a real-time session event from WebSocket.
    
    Examples
    --------
    >>> event = SessionEvent(
    ...     event_type="generation_progress",
    ...     data={"step": 10, "total": 30}
    ... )
    """
    
    event_type: str = Field(..., description="Event type identifier")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")
    
    @classmethod
    def from_websocket_message(cls, message: Dict[str, Any]) -> SessionEvent:
        """
        Create an event from a WebSocket message.
        
        Parameters
        ----------
        message : Dict[str, Any]
            Raw WebSocket message.
        
        Returns
        -------
        SessionEvent
            Parsed event instance.
        """
        return cls(**message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns
        -------
        Dict[str, Any]
            Event data as dictionary.
        """
        return self.model_dump(exclude_none=True)