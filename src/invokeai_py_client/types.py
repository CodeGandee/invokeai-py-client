"""InvokeAI type system for Python client.

This module provides Python representations of InvokeAI's type system,
including primitive types, model references, and complex field types.
All types support validation, serialization, and type conversion.
"""

from typing import Any, Dict, List, Optional, Union, Literal, TypeVar, Generic
from enum import Enum
from pathlib import Path
from abc import ABC, abstractmethod
import json
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]


T = TypeVar('T')


class InvokeAIType(ABC, BaseModel):
    """Abstract base class for all InvokeAI types.
    
    This class provides the common interface for all InvokeAI field types,
    including serialization, validation, and type conversion capabilities.
    
    Attributes
    ----------
    field_name : Optional[str]
        The name of the field in the workflow.
    description : Optional[str]
        Human-readable description of the field.
    required : bool
        Whether this field is required.
    
    Methods
    -------
    to_api_value()
        Convert to InvokeAI API format.
    from_api_value(value)
        Create instance from API response.
    validate_value(value)
        Validate a value against type constraints.
    
    Examples
    --------
    >>> # All InvokeAI types inherit from this base
    >>> class MyType(InvokeAIType):
    ...     def to_api_value(self):
    ...         return {"value": self.value}
    """
    
    field_name: Optional[str] = Field(None, description="Field name in workflow")
    description: Optional[str] = Field(None, description="Field description")
    required: bool = Field(False, description="Whether field is required")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        arbitrary_types_allowed = True
    
    @abstractmethod
    def to_api_value(self) -> Any:
        """Convert this type to InvokeAI API format.
        
        Returns
        -------
        Any
            The value in API-compatible format.
        """
        pass
    
    @classmethod
    @abstractmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIType":
        """Create instance from API response value.
        
        Parameters
        ----------
        value : Any
            The value from API response.
        field_name : Optional[str]
            The field name, if known.
        
        Returns
        -------
        InvokeAIType
            An instance of the appropriate type.
        """
        pass
    
    def validate_value(self, value: Any) -> bool:
        """Validate a value against this type's constraints.
        
        Parameters
        ----------
        value : Any
            The value to validate.
        
        Returns
        -------
        bool
            True if valid, raises ValidationError if not.
        """
        return True


# Primitive Types

class InvokeAIInteger(InvokeAIType):
    """Integer field type for InvokeAI.
    
    Represents an integer value with optional constraints like
    minimum, maximum, and multiple_of requirements.
    
    Attributes
    ----------
    value : int
        The integer value.
    ge : Optional[int]
        Greater than or equal constraint.
    le : Optional[int]
        Less than or equal constraint.
    gt : Optional[int]
        Greater than constraint.
    lt : Optional[int]
        Less than constraint.
    multiple_of : Optional[int]
        Value must be multiple of this.
    
    Examples
    --------
    >>> # Create an integer field for image width
    >>> width = InvokeAIInteger(value=512, ge=64, le=2048, multiple_of=8)
    >>> width.validate_value(1024)  # Valid
    >>> width.validate_value(1023)  # Raises ValidationError (not multiple of 8)
    """
    
    value: int = Field(..., description="The integer value")
    ge: Optional[int] = Field(None, description="Greater than or equal to")
    le: Optional[int] = Field(None, description="Less than or equal to")
    gt: Optional[int] = Field(None, description="Greater than")
    lt: Optional[int] = Field(None, description="Less than")
    multiple_of: Optional[int] = Field(None, description="Must be multiple of")
    
    @validator('value')
    def validate_constraints(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate value against constraints."""
        if 'ge' in values and values['ge'] is not None and v < values['ge']:
            raise ValueError(f"Value {v} must be >= {values['ge']}")
        if 'le' in values and values['le'] is not None and v > values['le']:
            raise ValueError(f"Value {v} must be <= {values['le']}")
        if 'gt' in values and values['gt'] is not None and v <= values['gt']:
            raise ValueError(f"Value {v} must be > {values['gt']}")
        if 'lt' in values and values['lt'] is not None and v >= values['lt']:
            raise ValueError(f"Value {v} must be < {values['lt']}")
        if 'multiple_of' in values and values['multiple_of'] is not None and v % values['multiple_of'] != 0:
            raise ValueError(f"Value {v} must be multiple of {values['multiple_of']}")
        return v
    
    def to_api_value(self) -> int:
        """Convert to API value."""
        return self.value
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIInteger":
        """Create from API value."""
        return cls(
            value=int(value), 
            field_name=field_name,
            description="",
            required=False,
            ge=None,
            le=None,
            gt=None,
            lt=None,
            multiple_of=None
        )


class InvokeAIFloat(InvokeAIType):
    """Float field type for InvokeAI.
    
    Represents a floating-point value with optional constraints.
    
    Attributes
    ----------
    value : float
        The float value.
    ge : Optional[float]
        Greater than or equal constraint.
    le : Optional[float]
        Less than or equal constraint.
    decimal_places : Optional[int]
        Maximum decimal places allowed.
    
    Examples
    --------
    >>> # Create a float field for denoising strength
    >>> strength = InvokeAIFloat(value=0.75, ge=0.0, le=1.0)
    >>> cfg = InvokeAIFloat(value=7.5, ge=1.0, le=30.0)
    """
    
    value: float = Field(..., description="The float value")
    ge: Optional[float] = Field(None, description="Greater than or equal to")
    le: Optional[float] = Field(None, description="Less than or equal to")
    gt: Optional[float] = Field(None, description="Greater than")
    lt: Optional[float] = Field(None, description="Less than")
    decimal_places: Optional[int] = Field(None, description="Max decimal places")
    
    def to_api_value(self) -> float:
        """Convert to API value."""
        if self.decimal_places is not None:
            return round(self.value, self.decimal_places)
        return self.value
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIFloat":
        """Create from API value."""
        return cls(
            value=float(value), 
            field_name=field_name,
            description="",
            required=False,
            ge=None,
            le=None,
            gt=None,
            lt=None,
            decimal_places=None
        )


class InvokeAIBoolean(InvokeAIType):
    """Boolean field type for InvokeAI.
    
    Attributes
    ----------
    value : bool
        The boolean value.
    
    Examples
    --------
    >>> # Create a boolean field
    >>> add_noise = InvokeAIBoolean(value=True)
    >>> seamless = InvokeAIBoolean(value=False)
    """
    
    value: bool = Field(..., description="The boolean value")
    
    def to_api_value(self) -> bool:
        """Convert to API value."""
        return self.value
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIBoolean":
        """Create from API value."""
        return cls(
            value=bool(value), 
            field_name=field_name,
            description="",
            required=False
        )


class InvokeAIString(InvokeAIType):
    """String field type for InvokeAI.
    
    Attributes
    ----------
    value : str
        The string value.
    min_length : Optional[int]
        Minimum string length.
    max_length : Optional[int]
        Maximum string length.
    pattern : Optional[str]
        Regex pattern to match.
    
    Examples
    --------
    >>> # Create a string field for prompt
    >>> prompt = InvokeAIString(value="a beautiful landscape")
    >>> negative = InvokeAIString(value="blurry, low quality", max_length=500)
    """
    
    value: str = Field(..., description="The string value")
    min_length: Optional[int] = Field(None, description="Minimum length")
    max_length: Optional[int] = Field(None, description="Maximum length")
    pattern: Optional[str] = Field(None, description="Regex pattern")
    
    def to_api_value(self) -> str:
        """Convert to API value."""
        return self.value
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIString":
        """Create from API value."""
        return cls(
            value=str(value), 
            field_name=field_name,
            description="",
            required=False,
            min_length=None,
            max_length=None,
            pattern=None
        )


# Resource Reference Types

class InvokeAIImage(InvokeAIType):
    """Image reference type for InvokeAI.
    
    Represents a reference to an image stored on the InvokeAI server.
    Images are uploaded separately and referenced by their UUID.
    
    Attributes
    ----------
    image_name : str
        The UUID filename of the image on the server.
    local_path : Optional[Path]
        Local file path if image was uploaded from disk.
    image_data : Optional[np.ndarray]
        The actual image data as numpy array, if loaded.
    
    Methods
    -------
    from_file(path)
        Create from local image file.
    from_array(array)
        Create from numpy array.
    upload(client)
        Upload image to server and get reference.
    download(client)
        Download image data from server.
    
    Examples
    --------
    >>> # Create image reference from file
    >>> image = InvokeAIImage.from_file("input.png")
    >>> # Upload to server (sets image_name)
    >>> await image.upload(client)
    >>> # Use in workflow
    >>> workflow.set_input("image", image)
    """
    
    image_name: Optional[str] = Field(None, description="Server-side image UUID")
    local_path: Optional[Path] = Field(None, description="Local file path")
    image_data: Optional[Any] = Field(None, description="Image data as numpy array", exclude=True)
    
    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "InvokeAIImage":
        """Create image reference from local file.
        
        Parameters
        ----------
        path : Union[str, Path]
            Path to the image file.
        
        Returns
        -------
        InvokeAIImage
            Image reference ready for upload.
        """
        return cls(local_path=Path(path))
    
    @classmethod
    def from_array(cls, array: np.ndarray) -> "InvokeAIImage":
        """Create image reference from numpy array.
        
        Parameters
        ----------
        array : np.ndarray
            Image data as numpy array.
        
        Returns
        -------
        InvokeAIImage
            Image reference ready for upload.
        """
        return cls(image_data=array)
    
    async def upload(self, client: "InvokeAIClient") -> str:
        """Upload image to InvokeAI server.
        
        Parameters
        ----------
        client : InvokeAIClient
            The client instance to use for upload.
        
        Returns
        -------
        str
            The server-side image UUID.
        """
        # This will be implemented in the actual client
        raise NotImplementedError("Image upload will be implemented in client")
    
    async def download(self, client: "InvokeAIClient") -> np.ndarray:
        """Download image data from server.
        
        Parameters
        ----------
        client : InvokeAIClient
            The client instance to use for download.
        
        Returns
        -------
        np.ndarray
            The image data as numpy array.
        """
        # This will be implemented in the actual client
        raise NotImplementedError("Image download will be implemented in client")
    
    def to_api_value(self) -> Dict[str, str]:
        """Convert to API value."""
        if not self.image_name:
            raise ValueError("Image must be uploaded before use in workflow")
        return {"image_name": self.image_name}
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIImage":
        """Create from API value."""
        if isinstance(value, dict):
            return cls(image_name=value.get("image_name"), field_name=field_name)
        return cls(image_name=str(value), field_name=field_name)


class InvokeAIModelReference(InvokeAIType):
    """Model reference type for InvokeAI.
    
    Represents a reference to a model available on the InvokeAI server.
    
    Attributes
    ----------
    key : str
        The model's unique key/ID.
    hash : Optional[str]
        The model's hash for verification.
    name : Optional[str]
        Human-readable model name.
    base : Optional[str]
        Base model type (e.g., "sdxl", "sd-1", "sd-2").
    type : Optional[str]
        Model type (e.g., "main", "vae", "lora").
    submodel_type : Optional[str]
        Submodel type if applicable.
    
    Examples
    --------
    >>> # Reference a model by key
    >>> model = InvokeAIModelReference(
    ...     key="stable-diffusion-xl-base",
    ...     base="sdxl",
    ...     type="main"
    ... )
    >>> workflow.set_input("model", model)
    """
    
    key: str = Field(..., description="Model key/ID")
    hash: Optional[str] = Field(None, description="Model hash")
    name: Optional[str] = Field(None, description="Model name")
    base: Optional[str] = Field(None, description="Base model type")
    type: Optional[str] = Field(None, description="Model type")
    submodel_type: Optional[str] = Field(None, description="Submodel type")
    
    def to_api_value(self) -> Dict[str, Any]:
        """Convert to API value."""
        result = {"key": self.key}
        if self.hash:
            result["hash"] = self.hash
        if self.name:
            result["name"] = self.name
        if self.base:
            result["base"] = self.base
        if self.type:
            result["type"] = self.type
        if self.submodel_type:
            result["submodel_type"] = self.submodel_type
        return result
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIModelReference":
        """Create from API value."""
        if isinstance(value, dict):
            return cls(**value, field_name=field_name)
        return cls(key=str(value), field_name=field_name)


class InvokeAIBoardReference(InvokeAIType):
    """Board reference type for InvokeAI.
    
    References a board for organizing outputs.
    
    Attributes
    ----------
    board_id : str
        The board's UUID.
    
    Examples
    --------
    >>> # Reference an existing board
    >>> board = InvokeAIBoardReference(board_id="board-uuid-123")
    >>> workflow.set_input("board", board)
    """
    
    board_id: str = Field(..., description="Board UUID")
    
    def to_api_value(self) -> Dict[str, str]:
        """Convert to API value."""
        return {"board_id": self.board_id}
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIBoardReference":
        """Create from API value."""
        if isinstance(value, dict):
            return cls(board_id=value.get("board_id"), field_name=field_name)
        return cls(board_id=str(value), field_name=field_name)


# Enum Types

class SchedulerType(str, Enum):
    """Scheduler types available in InvokeAI.
    
    Examples
    --------
    >>> scheduler = SchedulerType.EULER
    >>> workflow.set_input("scheduler", scheduler)
    """
    
    DDIM = "ddim"
    DDPM = "ddpm"
    DEIS = "deis"
    DPM_2 = "dpm_2"
    DPM_2_ANCESTRAL = "dpm_2_ancestral"
    DPM_MULTI = "dpm_multi"
    DPM_SDE = "dpm_sde"
    DPM_SDE_K = "dpm_sde_k"
    EULER = "euler"
    EULER_ANCESTRAL = "euler_ancestral"
    EULER_K = "euler_k"
    HEUN = "heun"
    LMS = "lms"
    PNDM = "pndm"
    UNIPC = "unipc"


class InvokeAIScheduler(InvokeAIType):
    """Scheduler selection type.
    
    Attributes
    ----------
    value : SchedulerType
        The selected scheduler.
    
    Examples
    --------
    >>> scheduler = InvokeAIScheduler(value=SchedulerType.EULER_ANCESTRAL)
    >>> workflow.set_input("scheduler", scheduler)
    """
    
    value: SchedulerType = Field(..., description="Scheduler type")
    
    def to_api_value(self) -> str:
        """Convert to API value."""
        return self.value.value if isinstance(self.value, SchedulerType) else str(self.value)
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAIScheduler":
        """Create from API value."""
        if isinstance(value, str):
            return cls(value=SchedulerType(value), field_name=field_name)
        return cls(value=value, field_name=field_name)


# Collection Types

class InvokeAICollection(InvokeAIType, Generic[T]):
    """Collection type for multiple values.
    
    Represents a list of values of the same type.
    
    Attributes
    ----------
    items : List[T]
        The collection items.
    item_type : type[T]
        The type of items in the collection.
    
    Examples
    --------
    >>> # Collection of integers
    >>> sizes = InvokeAICollection(
    ...     items=[512, 768, 1024],
    ...     item_type=InvokeAIInteger
    ... )
    >>> # Collection of images
    >>> images = InvokeAICollection(
    ...     items=[img1, img2, img3],
    ...     item_type=InvokeAIImage
    ... )
    """
    
    items: List[Any] = Field(default_factory=list, description="Collection items")
    item_type: type = Field(..., description="Type of items")
    
    def to_api_value(self) -> List[Any]:
        """Convert to API value."""
        result = []
        for item in self.items:
            if hasattr(item, 'to_api_value'):
                result.append(item.to_api_value())
            else:
                result.append(item)
        return result
    
    @classmethod
    def from_api_value(cls, value: Any, field_name: Optional[str] = None) -> "InvokeAICollection":
        """Create from API value."""
        if not isinstance(value, list):
            value = [value]
        return cls(items=value, item_type=type(value[0]) if value else Any, field_name=field_name)


# Type Registry

class TypeRegistry:
    """Registry for mapping field types to Python classes.
    
    This class maintains mappings between InvokeAI field type names
    and their corresponding Python type classes.
    
    Methods
    -------
    register(type_name, type_class)
        Register a type mapping.
    get_type(type_name)
        Get type class for a type name.
    create_from_config(config)
        Create type instance from workflow config.
    
    Examples
    --------
    >>> registry = TypeRegistry()
    >>> registry.register("integer", InvokeAIInteger)
    >>> IntType = registry.get_type("integer")
    """
    
    def __init__(self):
        """Initialize type registry with default mappings."""
        self._types: Dict[str, type] = {
            "integer": InvokeAIInteger,
            "int": InvokeAIInteger,
            "float": InvokeAIFloat,
            "number": InvokeAIFloat,
            "boolean": InvokeAIBoolean,
            "bool": InvokeAIBoolean,
            "string": InvokeAIString,
            "str": InvokeAIString,
            "text": InvokeAIString,
            "image": InvokeAIImage,
            "ImageField": InvokeAIImage,
            "model": InvokeAIModelReference,
            "ModelIdentifierField": InvokeAIModelReference,
            "board": InvokeAIBoardReference,
            "BoardField": InvokeAIBoardReference,
            "scheduler": InvokeAIScheduler,
            "SchedulerField": InvokeAIScheduler,
        }
    
    def register(self, type_name: str, type_class: type) -> None:
        """Register a type mapping.
        
        Parameters
        ----------
        type_name : str
            The InvokeAI type name.
        type_class : type
            The Python type class.
        """
        self._types[type_name] = type_class
    
    def get_type(self, type_name: str) -> Optional[type]:
        """Get type class for a type name.
        
        Parameters
        ----------
        type_name : str
            The InvokeAI type name.
        
        Returns
        -------
        Optional[type]
            The type class, or None if not found.
        """
        # Handle field config types
        if type_name.endswith("-field-config"):
            base_type = type_name.replace("-field-config", "")
            return self._types.get(base_type)
        return self._types.get(type_name)
    
    def create_from_config(self, config: Dict[str, Any]) -> Optional[InvokeAIType]:
        """Create type instance from workflow field config.
        
        Parameters
        ----------
        config : Dict[str, Any]
            The field configuration from workflow.
        
        Returns
        -------
        Optional[InvokeAIType]
            The type instance, or None if type unknown.
        """
        # Extract type from settings
        settings = config.get("settings", {})
        type_name = settings.get("type", "")
        
        type_class = self.get_type(type_name)
        if not type_class:
            return None
        
        # Create instance with field metadata
        field_id = config.get("fieldIdentifier", {})
        return type_class(
            field_name=field_id.get("fieldName"),
            description=config.get("description"),
            required=config.get("required", False)
        )


# Global type registry instance
TYPE_REGISTRY = TypeRegistry()