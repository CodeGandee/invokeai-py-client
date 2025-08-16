"""
Field types for InvokeAI workflow inputs and outputs.

This module provides Python wrapper classes for InvokeAI primitive types,
handling validation, type conversion, and data management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient

T = TypeVar("T")


class IvkField(ABC, Generic[T]):
    """
    Abstract base class for all InvokeAI field types.

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
    ) -> None:
        """Initialize the field."""
        self._value = value
        self.name = name
        self.description = description
        self.metadata: dict[str, Any] = {}

    def validate(self) -> bool:
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

    @abstractmethod
    def to_api_format(self) -> dict[str, Any]:
        """
        Convert the field to InvokeAI API format.

        Returns
        -------
        Dict[str, Any]
            The field in API-compatible format.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
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
        raise NotImplementedError

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
            self.validate()

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


class IntegerField(IvkField[int]):
    """
    Integer field type with optional constraints.

    Parameters
    ----------
    value : int, optional
        The integer value.
    minimum : int, optional
        Minimum allowed value.
    maximum : int, optional
        Maximum allowed value.
    multiple_of : int, optional
        Value must be a multiple of this number.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = IntegerField(value=512, minimum=64, maximum=2048, multiple_of=8)
    >>> field.validate()
    True
    """

    def __init__(
        self,
        value: int | None = None,
        minimum: int | None = None,
        maximum: int | None = None,
        multiple_of: int | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the integer field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate integer constraints."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IntegerField:
        """Create from API data."""
        raise NotImplementedError


class FloatField(IvkField[float]):
    """
    Float field type with optional constraints.

    Parameters
    ----------
    value : float, optional
        The float value.
    minimum : float, optional
        Minimum allowed value.
    maximum : float, optional
        Maximum allowed value.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = FloatField(value=7.5, minimum=0.0, maximum=10.0)
    >>> field.validate()
    True
    """

    def __init__(
        self,
        value: float | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the float field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate float constraints."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> FloatField:
        """Create from API data."""
        raise NotImplementedError


class StringField(IvkField[str]):
    """
    String field type with optional constraints.

    Parameters
    ----------
    value : str, optional
        The string value.
    min_length : int, optional
        Minimum string length.
    max_length : int, optional
        Maximum string length.
    pattern : str, optional
        Regex pattern for validation.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = StringField(value="prompt text", min_length=1, max_length=1000)
    >>> field.validate()
    True
    """

    def __init__(
        self,
        value: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the string field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate string constraints."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> StringField:
        """Create from API data."""
        raise NotImplementedError


class BooleanField(IvkField[bool]):
    """
    Boolean field type.

    Parameters
    ----------
    value : bool, optional
        The boolean value.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = BooleanField(value=True, name="enable_hires")
    >>> field.get_value()
    True
    """

    def __init__(
        self,
        value: bool | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the boolean field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate boolean value."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> BooleanField:
        """Create from API data."""
        raise NotImplementedError


class ImageField(IvkField[Union[str, Path]]):
    """
    Image field for handling image references and uploads.

    This field handles both local image paths (for upload) and
    server-side image names (for references).

    Parameters
    ----------
    value : Union[str, Path], optional
        Local path to image or server-side image name.
    is_uploaded : bool, optional
        Whether the image is already on the server.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Attributes
    ----------
    image_name : str
        Server-side image identifier after upload.
    local_path : Path
        Local file path before upload.

    Examples
    --------
    >>> field = ImageField(value="input.png")
    >>> await field.upload(client)
    >>> print(field.image_name)
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890.png"
    """

    def __init__(
        self,
        value: str | Path | None = None,
        is_uploaded: bool = False,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the image field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate image path or name."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format with image_name."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> ImageField:
        """Create from API data."""
        raise NotImplementedError

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


class LatentsField(IvkField[str]):
    """
    Latents field for latent space representations.

    Parameters
    ----------
    value : str, optional
        The latents identifier.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.
    """

    def __init__(
        self,
        value: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the latents field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate latents identifier."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> LatentsField:
        """Create from API data."""
        raise NotImplementedError


class ModelField(IvkField[dict[str, str]]):
    """
    DnnModel reference field.

    Parameters
    ----------
    model_key : str, optional
        The model identifier key.
    model_name : str, optional
        Human-readable model name.
    base_model : str, optional
        Base model type ('sdxl', 'sd-1', etc.).
    model_type : str, optional
        DnnModel type ('main', 'vae', 'lora', etc.).
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = ModelField(
    ...     model_key="stable-diffusion-xl-base-1.0",
    ...     base_model="sdxl",
    ...     model_type="main"
    ... )
    """

    def __init__(
        self,
        model_key: str | None = None,
        model_name: str | None = None,
        base_model: str | None = None,
        model_type: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the model field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate model reference."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> ModelField:
        """Create from API data."""
        raise NotImplementedError


class EnumField(IvkField[str]):
    """
    Enum field with predefined choices.

    Parameters
    ----------
    value : str, optional
        The selected choice.
    choices : List[str]
        Available options.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = EnumField(
    ...     value="euler",
    ...     choices=["euler", "euler_a", "dpm++", "ddim"]
    ... )
    """

    def __init__(
        self,
        value: str | None = None,
        choices: list[str] | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the enum field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate value is in choices."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> EnumField:
        """Create from API data."""
        raise NotImplementedError


class ColorField(IvkField[str]):
    """
    Color field for RGBA color values.

    Parameters
    ----------
    value : str, optional
        Color in hex format (#RRGGBB or #RRGGBBAA).
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = ColorField(value="#FF5733")
    >>> field.to_rgba()
    (255, 87, 51, 255)
    """

    def __init__(
        self,
        value: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the color field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate color format."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> ColorField:
        """Create from API data."""
        raise NotImplementedError

    def to_rgba(self) -> tuple[int, int, int, int]:
        """
        Convert to RGBA tuple.

        Returns
        -------
        Tuple[int, int, int, int]
            (red, green, blue, alpha) values 0-255.
        """
        raise NotImplementedError


class ConditioningField(IvkField[dict[str, Any]]):
    """
    Conditioning field for prompt embeddings.

    Parameters
    ----------
    value : Dict[str, Any], optional
        Conditioning data structure.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.
    """

    def __init__(
        self,
        value: dict[str, Any] | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the conditioning field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate conditioning structure."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> ConditioningField:
        """Create from API data."""
        raise NotImplementedError


class CollectionField(IvkField[list[T]], Generic[T]):
    """
    Collection field for lists of values.

    Parameters
    ----------
    value : List[T], optional
        List of items.
    item_type : type
        Type of items in the collection.
    min_length : int, optional
        Minimum number of items.
    max_length : int, optional
        Maximum number of items.
    name : str, optional
        Field identifier.
    description : str, optional
        Field description.

    Examples
    --------
    >>> field = CollectionField(
    ...     value=[1, 2, 3],
    ...     item_type=int,
    ...     min_length=1,
    ...     max_length=10
    ... )
    """

    def __init__(
        self,
        value: list[T] | None = None,
        item_type: type[T] | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize the collection field."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate collection constraints."""
        raise NotImplementedError

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        raise NotImplementedError

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> CollectionField[T]:
        """Create from API data."""
        raise NotImplementedError

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
