"""
Base classes for InvokeAI field types.

This module provides the foundation for all field types used in workflows,
with Pydantic integration and type safety.

CRITICAL DESIGN REQUIREMENT
---------------------------
ALL IvkField SUBCLASSES MUST BE DEFAULT-CONSTRUCTABLE!

Every field class must be able to be created with no arguments:
    field = MyFieldClass()  # This MUST work!

This is non-negotiable for proper workflow system operation.
See IvkField class documentation for detailed requirements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar
from collections.abc import Iterator
from pathlib import Path

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient

T = TypeVar("T")


class IvkField(Generic[T]):
    """
    Base class for all InvokeAI field types.

    This is an abstract-like base class that provides common functionality
    for workflow field types. All concrete field classes should inherit
    from both this class and Pydantic's BaseModel.
    
    IMPORTANT: Default Constructability Requirement
    ------------------------------------------------
    ALL SUBCLASSES MUST BE DEFAULT-CONSTRUCTABLE!
    
    Every IvkField subclass MUST be able to be instantiated without any
    required arguments: `field = MyFieldClass()`. This is essential for:
    - Workflow initialization and discovery
    - Automatic field creation from workflow definitions
    - Type inspection and validation
    - Testing and debugging
    
    Use Pydantic's Field(default=...) or Field(default_factory=...) for
    all field attributes to ensure default constructability.
    
    Example:
    --------
    >>> # GOOD - Default constructable
    >>> class MyField(BaseModel, IvkField[str]):
    ...     value: Optional[str] = None  # Has default
    ...     items: list[str] = Field(default_factory=list)  # Factory for mutable
    ...
    >>> # BAD - Not default constructable
    >>> class BadField(BaseModel, IvkField[str]):
    ...     value: str  # No default - will fail!
    ...     items: list[str] = []  # Mutable default - dangerous!
    
    Subclasses are responsible for:
    - Being default-constructable (no required __init__ parameters)
    - Storing their own data (e.g., value, name, description) 
    - Implementing abstract methods like validate_field, to_api_format, etc.
    - Using proper Pydantic patterns for defaults and validation

    Notes
    -----
    This base class does not use ABC/abstractmethod decorators.
    Instead, it raises NotImplementedError for methods that must be 
    implemented by subclasses.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the field.
        
        This is a placeholder initialization that subclasses can override.
        The base class doesn't store any data itself.
        
        IMPORTANT: Subclasses MUST remain default-constructable!
        If you override __init__, ensure it can still be called without
        any required arguments. Use default values for all parameters:
        
        def __init__(self, value: Optional[str] = None, **kwargs):
            super().__init__(**kwargs)
            self.value = value
        """
        pass  # Base class has no member fields

    def validate_field(self) -> bool:
        """
        Validate the current field value.

        Returns
        -------
        bool
            True if the value is valid, False otherwise.

        Raises
        ------
        ValueError
            If validation fails with details about the error.
        NotImplementedError
            If the subclass hasn't implemented this method.
        """
        raise NotImplementedError("Subclass must implement validate_field()")

    def to_api_format(self) -> dict[str, Any]:
        """
        Convert the field to InvokeAI API format.

        Returns
        -------
        Dict[str, Any]
            The field in API-compatible format.
            
        Raises
        ------
        NotImplementedError
            If the subclass hasn't implemented this method.
        """
        raise NotImplementedError("Subclass must implement to_api_format()")

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkField[T]:
        """
        Create a field instance from API response data.

        Parameters
        ----------
        data : Dict[str, Any]
            The API response data.

        Returns
        -------
        IvkField[T]
            A new field instance with the parsed value.
            
        Raises
        ------
        NotImplementedError
            If the subclass hasn't implemented this method.
        """
        raise NotImplementedError("Subclass must implement from_api_format()")

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> IvkField[T]:
        """
        Create a field instance from a JSON-like dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            The JSON-like dictionary containing field data.

        Returns
        -------
        IvkField[T]
            A new field instance created from the dictionary.
            
        Raises
        ------
        NotImplementedError
            If the subclass hasn't implemented this method.
        """
        raise NotImplementedError("Subclass must implement from_json_dict()")

    def to_json_dict(self) -> dict[str, Any]:
        """
        Serialize the field to a JSON-like dictionary.

        Returns
        -------
        Dict[str, Any]
            The field data as a JSON-serializable dictionary.
            
        Raises
        ------
        NotImplementedError
            If the subclass hasn't implemented this method.
        """
        raise NotImplementedError("Subclass must implement to_json_dict()")



class PydanticFieldMixin:
    """
    Mixin for IvkField subclasses that are also Pydantic models.
    
    Provides JSON conversion methods leveraging Pydantic's built-in serialization.
    This mixin avoids code duplication across all Pydantic-based field classes.
    """
    
    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Any:
        """
        Create a field instance from a JSON-like dictionary.
        
        Uses Pydantic's model_validate to handle the conversion.
        
        Parameters
        ----------
        data : Dict[str, Any]
            The JSON-like dictionary containing field data.
        
        Returns
        -------
        IvkField
            A new field instance created from the dictionary.
        """
        # Leverage Pydantic's model_validate for proper deserialization
        from pydantic import BaseModel
        if issubclass(cls, BaseModel):
            return cls.model_validate(data)
        else:
            # Fallback to regular constructor for non-Pydantic classes
            return cls(**data)
    
    def to_json_dict(self) -> dict[str, Any]:
        """
        Serialize the field to a JSON-like dictionary.
        
        Uses Pydantic's model_dump for Pydantic models.
        
        Returns
        -------
        Dict[str, Any]
            The field data as a JSON-serializable dictionary.
        """
        from pydantic import BaseModel
        if isinstance(self, BaseModel):
            # Use model_dump for Pydantic models
            return self.model_dump(exclude_none=False)
        else:
            # Fallback for non-Pydantic classes
            return self.__dict__.copy()


class IvkImageFieldMixin:
    """
    Mixin for fields that handle image upload/download operations.
    
    Provides common image handling methods for ImageField and related types.
    """

    async def upload(self, client: InvokeAIClient) -> str:
        """
        Upload the local image to the server.

        Parameters
        ----------
        client : InvokeAIClient
            The client instance for uploading.

        Returns
        -------
        str
            The server-side image name.

        Raises
        ------
        FileNotFoundError
            If the local image doesn't exist.
        IOError
            If upload fails.
        """
        raise NotImplementedError

    async def download(
        self, client: InvokeAIClient, output_path: Path | None = None
    ) -> Path:
        """
        Download the image from the server.

        Parameters
        ----------
        client : InvokeAIClient
            The client instance for downloading.
        output_path : Path, optional
            Where to save the image.

        Returns
        -------
        Path
            Path to the downloaded image.
        """
        raise NotImplementedError


class IvkCollectionFieldMixin(Generic[T]):
    """
    Mixin for fields that handle collections (lists) of values.
    
    Provides common collection manipulation methods.
    """

    def append(self, item: T) -> None:
        """
        Add an item to the collection.

        Parameters
        ----------
        item : T
            The item to add.

        Raises
        ------
        ValueError
            If adding would exceed max_length.
        TypeError
            If item type doesn't match.
        """
        raise NotImplementedError

    def remove(self, item: T) -> None:
        """
        Remove an item from the collection.

        Parameters
        ----------
        item : T
            The item to remove.

        Raises
        ------
        ValueError
            If item not in collection or would go below min_length.
        """
        raise NotImplementedError

    def clear(self) -> None:
        """Clear all items from the collection."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Get the number of items in the collection."""
        raise NotImplementedError

    def iter_items(self) -> Iterator[T]:
        """Iterate over items in the collection."""
        raise NotImplementedError