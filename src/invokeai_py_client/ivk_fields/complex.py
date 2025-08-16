"""
Complex field types for InvokeAI workflows.

Advanced field types including colors, bounding boxes, collections,
and other structured data types.
"""

from __future__ import annotations

import re
from typing import Any, Generic, Iterator, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from invokeai_py_client.ivk_fields.base import IvkField, IvkCollectionFieldMixin

T = TypeVar("T")


class IvkColorField(BaseModel, IvkField[dict[str, int]]):
    """
    Color field for RGBA color values.
    
    Supports RGB and RGBA color formats with validation.
    
    Examples
    --------
    >>> field = IvkColorField()
    >>> field.set_rgba(255, 128, 0, 255)  # Orange
    >>> field.set_hex("#FF8000")
    >>> print(field.to_rgba())
    (255, 128, 0, 255)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, int]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        r = data.pop('r', 0)
        g = data.pop('g', 0)
        b = data.pop('b', 0)
        a = data.pop('a', 255)

        # Build value dict from components
        if value is None:
            value = {"r": r, "g": g, "b": b, "a": a}

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            r=r,
            g=g,
            b=b,
            a=a,
            **data
        )
        
        # Initialize IvkField
        IvkField.__init__(
            self,
            value=value,
            name=name,
            description=description
        )

    @field_validator("r", "g", "b", "a")
    @classmethod
    def validate_color_component(cls, v: int) -> int:
        """Validate color component is in valid range."""
        if not (0 <= v <= 255):
            raise ValueError(f"Color component {v} must be between 0 and 255")
        return v

    def validate_field(self) -> bool:
        """Validate color format."""
        if self.value:
            for component in ["r", "g", "b", "a"]:
                if component in self.value:
                    val = self.value[component]
                    if not (0 <= val <= 255):
                        raise ValueError(f"Color component {component}={val} must be between 0 and 255")
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "color"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkColorField:
        """Create from API data."""
        color_data = data.get("value", {})
        return cls(
            value=color_data,
            r=color_data.get("r", 0),
            g=color_data.get("g", 0),
            b=color_data.get("b", 0),
            a=color_data.get("a", 255)
        )

    def get_value(self) -> Optional[dict[str, int]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, int]]) -> None:
        """Set the value with validation."""
        self.value = value
        if value:
            self.r = value.get("r", 0)
            self.g = value.get("g", 0)
            self.b = value.get("b", 0)
            self.a = value.get("a", 255)

    def set_rgba(self, r: int, g: int, b: int, a: int = 255) -> None:
        """Set color from RGBA components."""
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        self.value = {"r": r, "g": g, "b": b, "a": a}

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


class IvkBoundingBoxField(BaseModel, IvkField[dict[str, Any]]):
    """
    Bounding box field for region specifications.
    
    Defines rectangular regions with optional confidence scores.
    
    Examples
    --------
    >>> field = IvkBoundingBoxField()
    >>> field.set_box(100, 400, 50, 300, 0.95)
    >>> print(field.get_box())
    (100, 400, 50, 300, 0.95)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    x_min: int = 0
    x_max: int = 0
    y_min: int = 0
    y_max: int = 0
    score: Optional[float] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        x_min = data.pop('x_min', 0)
        x_max = data.pop('x_max', 0)
        y_min = data.pop('y_min', 0)
        y_max = data.pop('y_max', 0)
        score = data.pop('score', None)

        # Build value dict from components
        if value is None:
            value = {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max
            }
            if score is not None:
                value["score"] = score

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            score=score,
            **data
        )
        
        # Initialize IvkField
        IvkField.__init__(
            self,
            value=value,
            name=name,
            description=description
        )

    def validate_field(self) -> bool:
        """Validate bounding box coordinates."""
        if self.value:
            x_min = self.value.get("x_min", 0)
            x_max = self.value.get("x_max", 0)
            y_min = self.value.get("y_min", 0)
            y_max = self.value.get("y_max", 0)
            
            if x_max <= x_min:
                raise ValueError(f"x_max ({x_max}) must be greater than x_min ({x_min})")
            if y_max <= y_min:
                raise ValueError(f"y_max ({y_max}) must be greater than y_min ({y_min})")
                
            score = self.value.get("score")
            if score is not None and not (0.0 <= score <= 1.0):
                raise ValueError(f"Score {score} must be between 0.0 and 1.0")
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "bounding_box"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkBoundingBoxField:
        """Create from API data."""
        bbox_data = data.get("value", {})
        return cls(
            value=bbox_data,
            x_min=bbox_data.get("x_min", 0),
            x_max=bbox_data.get("x_max", 0),
            y_min=bbox_data.get("y_min", 0),
            y_max=bbox_data.get("y_max", 0),
            score=bbox_data.get("score")
        )

    def get_value(self) -> Optional[dict[str, Any]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, Any]]) -> None:
        """Set the value with validation."""
        self.value = value
        if value:
            self.x_min = value.get("x_min", 0)
            self.x_max = value.get("x_max", 0)
            self.y_min = value.get("y_min", 0)
            self.y_max = value.get("y_max", 0)
            self.score = value.get("score")

    def set_box(self, x_min: int, x_max: int, y_min: int, y_max: int, score: Optional[float] = None) -> None:
        """Set bounding box coordinates."""
        box_data: dict[str, Any] = {
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max
        }
        if score is not None:
            box_data["score"] = score
            
        self.set_value(box_data)

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


class IvkCollectionField(BaseModel, IvkField[list[T]], IvkCollectionFieldMixin[T], Generic[T]):
    """
    Collection field for lists of values.
    
    Supports collections with type validation and length constraints.
    
    Examples
    --------
    >>> field = IvkCollectionField[int]()
    >>> field.append(1)
    >>> field.append(2) 
    >>> field.extend([3, 4, 5])
    >>> print(field.get_value())
    [1, 2, 3, 4, 5]
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[list[T]] = Field(default_factory=list)
    name: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[type[T]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', [])
        name = data.pop('name', None)
        description = data.pop('description', None)
        item_type = data.pop('item_type', None)
        min_length = data.pop('min_length', None)
        max_length = data.pop('max_length', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            item_type=item_type,
            min_length=min_length,
            max_length=max_length,
            **data
        )
        
        # Initialize IvkField
        IvkField.__init__(
            self,
            value=value,
            name=name,
            description=description
        )

    def validate_field(self) -> bool:
        """Validate collection constraints."""
        if self.value is None:
            return True
            
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
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "collection"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkCollectionField[T]:
        """Create from API data."""
        return cls(value=data.get("value", []))

    def get_value(self) -> Optional[list[T]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[list[T]]) -> None:
        """Set the value with validation."""
        self.value = value or []

    def append(self, item: T) -> None:
        """Add an item to the collection."""
        if self.value is None:
            self.value = []
            
        # Check max length
        if self.max_length is not None and len(self.value) >= self.max_length:
            raise ValueError(f"Cannot add item: would exceed maximum length {self.max_length}")
            
        # Check item type
        if self.item_type and not isinstance(item, self.item_type):
            raise TypeError(f"Item is {type(item)}, expected {self.item_type}")
            
        self.value.append(item)

    def remove(self, item: T) -> None:
        """Remove an item from the collection."""
        if self.value is None:
            raise ValueError("Cannot remove from empty collection")
            
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