"""
Complex field types for InvokeAI workflows.

Advanced field types including colors, bounding boxes, collections,
and other structured data types.
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar
from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field, field_validator

from invokeai_py_client.ivk_fields.base import IvkField, IvkCollectionFieldMixin, PydanticFieldMixin

T = TypeVar("T")


class IvkColorField(BaseModel, PydanticFieldMixin, IvkField[dict[str, int]]):
    """
    Color field for RGBA color values.
    
    Corresponds to InvokeAI's ColorField type.
    
    This field represents color values directly through its RGBA components.
    The field itself IS the color value.
    
    Examples
    --------
    >>> field = IvkColorField(r=255, g=128, b=0, a=255)  # Orange
    >>> field.set_rgba(255, 128, 0, 255)
    >>> field.set_hex("#FF8000")
    >>> print(field.to_rgba())
    (255, 128, 0, 255)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Color components ARE the value
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255

    @field_validator("r", "g", "b", "a")
    @classmethod
    def validate_color_component(cls, v: int) -> int:
        """Validate color component is in valid range."""
        if not (0 <= v <= 255):
            raise ValueError(f"Color component {v} must be between 0 and 255")
        return v

    def validate_field(self) -> bool:
        """Validate color format."""
        # Validation is handled by field_validator
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI ColorField."""
        return {
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "a": self.a
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkColorField:
        """Create from API data."""
        return cls(
            r=data.get("r", 0),
            g=data.get("g", 0),
            b=data.get("b", 0),
            a=data.get("a", 255)
        )

    def set_rgba(self, r: int, g: int, b: int, a: int = 255) -> None:
        """Set color from RGBA components."""
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def set_hex(self, hex_color: str) -> None:
        """
        Set color from hex string.
        
        Parameters
        ----------
        hex_color : str
            Hex color string like "#FF8000" or "#FF8000FF"
        """
        # Remove # if present
        hex_color = hex_color.lstrip("#")
        
        if len(hex_color) == 6:
            # RGB format
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = 255
        elif len(hex_color) == 8:
            # RGBA format
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = int(hex_color[6:8], 16)
        else:
            raise ValueError(f"Invalid hex color format: {hex_color}")
        
        self.set_rgba(r, g, b, a)

    def to_rgba(self) -> tuple[int, int, int, int]:
        """
        Convert to RGBA tuple.
        
        Returns
        -------
        Tuple[int, int, int, int]
            (red, green, blue, alpha) values 0-255.
        """
        return (self.r, self.g, self.b, self.a)

    def to_hex(self, include_alpha: bool = False) -> str:
        """
        Convert to hex string.
        
        Parameters
        ----------
        include_alpha : bool
            Whether to include alpha channel in hex string.
            
        Returns
        -------
        str
            Hex color string like "#FF8000" or "#FF8000FF"
        """
        if include_alpha:
            return f"#{self.r:02X}{self.g:02X}{self.b:02X}{self.a:02X}"
        else:
            return f"#{self.r:02X}{self.g:02X}{self.b:02X}"


class IvkBoundingBoxField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    Bounding box field for region specifications.
    
    Corresponds to InvokeAI's BoundingBoxField type.
    
    This field represents a rectangular region directly through its coordinates.
    The field itself IS the bounding box value.
    
    Examples
    --------
    >>> field = IvkBoundingBoxField(x_min=100, x_max=400, y_min=50, y_max=300, score=0.95)
    >>> field.set_box(100, 400, 50, 300, 0.95)
    >>> print(field.get_box())
    (100, 400, 50, 300, 0.95)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Bounding box components ARE the value
    x_min: int = 0
    x_max: int = 0
    y_min: int = 0
    y_max: int = 0
    score: Optional[float] = None

    def validate_field(self) -> bool:
        """Validate bounding box coordinates."""
        if self.x_max <= self.x_min:
            raise ValueError(f"x_max ({self.x_max}) must be greater than x_min ({self.x_min})")
        if self.y_max <= self.y_min:
            raise ValueError(f"y_max ({self.y_max}) must be greater than y_min ({self.y_min})")
        if self.score is not None and not (0.0 <= self.score <= 1.0):
            raise ValueError(f"Score {self.score} must be between 0.0 and 1.0")
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI BoundingBoxField."""
        result: dict[str, Any] = {
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_min": self.y_min,
            "y_max": self.y_max
        }
        if self.score is not None:
            result["score"] = self.score
        return result

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkBoundingBoxField:
        """Create from API data."""
        return cls(
            x_min=data.get("x_min", 0),
            x_max=data.get("x_max", 0),
            y_min=data.get("y_min", 0),
            y_max=data.get("y_max", 0),
            score=data.get("score")
        )

    def set_box(self, x_min: int, x_max: int, y_min: int, y_max: int, score: Optional[float] = None) -> None:
        """Set bounding box coordinates."""
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.score = score

    def get_box(self) -> tuple[int, int, int, int, Optional[float]]:
        """Get bounding box as tuple."""
        return (self.x_min, self.x_max, self.y_min, self.y_max, self.score)

    def get_width(self) -> int:
        """Get bounding box width."""
        return self.x_max - self.x_min

    def get_height(self) -> int:
        """Get bounding box height."""
        return self.y_max - self.y_min

    def get_area(self) -> int:
        """Get bounding box area."""
        return self.get_width() * self.get_height()


class IvkCollectionField(BaseModel, PydanticFieldMixin, IvkField[list[T]], IvkCollectionFieldMixin[T], Generic[T]):
    """
    Collection field for lists of values.
    
    Corresponds to InvokeAI's collection types (e.g., list[ImageField], list[int]).
    
    Collections are primitive-like and keep a value field containing the list.
    Supports type validation and length constraints.
    
    Examples
    --------
    >>> field = IvkCollectionField[int](value=[])
    >>> field.append(1)
    >>> field.append(2) 
    >>> field.extend([3, 4, 5])
    >>> print(field.value)
    [1, 2, 3, 4, 5]
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Collections keep the value field since they wrap a list
    value: list[T] = Field(default_factory=list)
    item_type: Optional[type[T]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    def validate_field(self) -> bool:
        """Validate collection constraints."""
        # Check length constraints
        length = len(self.value)
        if self.min_length is not None and length < self.min_length:
            raise ValueError(f"Collection length {length} is less than minimum {self.min_length}")
        if self.max_length is not None and length > self.max_length:
            raise ValueError(f"Collection length {length} exceeds maximum {self.max_length}")
            
        # Check item types if specified
        if self.item_type and self.value:
            for i, item in enumerate(self.value):
                if not isinstance(item, self.item_type):
                    raise TypeError(f"Item at index {i} is {type(item)}, expected {self.item_type}")
                    
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI collection types."""
        return {"value": self.value}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkCollectionField[T]:
        """Create from API data."""
        return cls(value=data.get("value", []))

    def append(self, item: T) -> None:
        """Add an item to the collection."""
        # Check max length
        if self.max_length is not None and len(self.value) >= self.max_length:
            raise ValueError(f"Cannot add item: would exceed maximum length {self.max_length}")
            
        # Check item type
        if self.item_type and not isinstance(item, self.item_type):
            raise TypeError(f"Item is {type(item)}, expected {self.item_type}")
            
        self.value.append(item)

    def remove(self, item: T) -> None:
        """Remove an item from the collection."""
        # Check min length
        if self.min_length is not None and len(self.value) <= self.min_length:
            raise ValueError(f"Cannot remove item: would go below minimum length {self.min_length}")
            
        if item not in self.value:
            raise ValueError("Item not in collection")
            
        self.value.remove(item)

    def clear(self) -> None:
        """Clear all items from the collection."""
        if self.min_length is not None and self.min_length > 0:
            raise ValueError(f"Cannot clear collection: minimum length is {self.min_length}")
        self.value = []

    def extend(self, items: list[T]) -> None:
        """Add multiple items to the collection."""
        for item in items:
            self.append(item)

    def __len__(self) -> int:
        """Get the number of items in the collection."""
        return len(self.value) if self.value else 0

    def iter_items(self) -> Iterator[T]:
        """Iterate over items in the collection."""
        return iter(self.value) if self.value else iter([])

    def __getitem__(self, index: int) -> T:
        """Get item by index."""
        if self.value is None:
            raise IndexError("Collection is empty")
        return self.value[index]

    def __setitem__(self, index: int, value: T) -> None:
        """Set item by index."""
        if self.value is None:
            raise IndexError("Collection is empty")
        if self.item_type and not isinstance(value, self.item_type):
            raise TypeError(f"Item is {type(value)}, expected {self.item_type}")
        self.value[index] = value