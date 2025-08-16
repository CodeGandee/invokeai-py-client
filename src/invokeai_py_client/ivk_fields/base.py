"""
Base classes for InvokeAI field types.

This module provides the foundation for all field types used in workflows,
with Pydantic integration and type safety.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Iterator, TypeVar
from pathlib import Path

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient

T = TypeVar("T")


class IvkField(Generic[T]):
    """
    Base class for all InvokeAI field types.

    This is a non-abstract base class that provides common functionality
    for workflow field types. All concrete field classes should inherit
    from both this class and Pydantic's BaseModel.

    Parameters
    ----------
    value : T, optional
        The initial value for the field.
    name : str, optional
        The field name in the workflow.
    description : str, optional
        Human-readable description of the field.

    Attributes
    ----------
    value : T
        The current value of the field.
    name : str
        The field identifier.
    metadata : Dict[str, Any]
        Additional field metadata.
    """

    def __init__(
        self,
        value: T | None = None,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any
    ) -> None:
        """Initialize the field."""
        self._value = value
        self.name = name
        self.description = description
        self.metadata: dict[str, Any] = {}

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
        """
        return True  # Default implementation

    def to_api_format(self) -> dict[str, Any]:
        """
        Convert the field to InvokeAI API format.

        Returns
        -------
        Dict[str, Any]
            The field in API-compatible format.
        """
        return {"value": self.get_value(), "type": "unknown"}

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
        """
        return cls(value=data.get("value"))

    def set_value(self, value: T | None) -> None:
        """
        Set the field value with validation.

        Parameters
        ----------
        value : T | None
            The new value to set.

        Raises
        ------
        ValueError
            If the value fails validation.
        """
        self._value = value
        if value is not None:
            self.validate_field()

    def get_value(self) -> T | None:
        """
        Get the current field value.

        Returns
        -------
        Optional[T]
            The current value, or None if not set.
        """
        return self._value

    @property
    def value(self) -> T | None:
        """Property for backward compatibility."""
        return self._value

    @value.setter
    def value(self, val: T | None) -> None:
        """Property setter for backward compatibility."""
        self.set_value(val)


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