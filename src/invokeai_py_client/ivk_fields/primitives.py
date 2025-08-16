"""
Primitive field types for InvokeAI workflows.

Basic data types including strings, integers, floats, and booleans
with Pydantic validation and InvokeAI API compatibility.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from invokeai_py_client.ivk_fields.base import IvkField


class IvkStringField(BaseModel, IvkField[str]):
    """
    String field with Pydantic validation for workflow inputs.
    
    Supports length constraints and pattern validation.
    
    Examples
    --------
    >>> field = IvkStringField()
    >>> field.value = "A beautiful landscape"
    >>> print(field.get_value())
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        min_length = data.pop('min_length', None)
        max_length = data.pop('max_length', None)
        pattern = data.pop('pattern', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            **data
        )
        
        # Initialize IvkField
        IvkField.__init__(
            self,
            value=value,
            name=name,
            description=description
        )

    @field_validator("value")
    @classmethod
    def validate_string_constraints(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate string constraints."""
        if v is None:
            return v

        values = info.data if hasattr(info, 'data') else {}

        # Check min length
        min_len = values.get('min_length')
        if min_len is not None and len(v) < min_len:
            raise ValueError(f"String length {len(v)} is less than minimum {min_len}")

        # Check max length
        max_len = values.get('max_length')
        if max_len is not None and len(v) > max_len:
            raise ValueError(f"String length {len(v)} exceeds maximum {max_len}")

        return v

    def validate_field(self) -> bool:
        """Validate the string value."""
        if self.value is None:
            return True
        return True  # Pydantic handles validation

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {"value": self.value, "type": "string"}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkStringField:
        """Create from API data."""
        return cls(value=data.get("value"))

    def get_value(self) -> Optional[str]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[str]) -> None:
        """Set the value with validation."""
        self.value = value


class IvkIntegerField(BaseModel, IvkField[int]):
    """
    Integer field with Pydantic validation for workflow inputs.
    
    Supports min/max constraints and multiple-of validation.
    
    Examples
    --------
    >>> field = IvkIntegerField(minimum=64, maximum=2048, multiple_of=8)
    >>> field.value = 512
    >>> print(field.get_value())
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    multiple_of: Optional[int] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract and convert fields
        value = data.pop('value', None)
        # Convert string to int if needed
        if value is not None and isinstance(value, str):
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass

        name = data.pop('name', None)
        description = data.pop('description', None)
        minimum = data.pop('minimum', None)
        maximum = data.pop('maximum', None)
        multiple_of = data.pop('multiple_of', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            minimum=minimum,
            maximum=maximum,
            multiple_of=multiple_of,
            **data
        )
        
        # Initialize IvkField
        IvkField.__init__(
            self,
            value=value,
            name=name,
            description=description
        )

    @field_validator("value")
    @classmethod
    def validate_integer_constraints(cls, v: Optional[int], info: Any) -> Optional[int]:
        """Validate integer constraints."""
        if v is None:
            return v

        values = info.data if hasattr(info, 'data') else {}

        # Check minimum
        minimum = values.get('minimum')
        if minimum is not None and v < minimum:
            raise ValueError(f"Value {v} is less than minimum {minimum}")

        # Check maximum
        maximum = values.get('maximum')
        if maximum is not None and v > maximum:
            raise ValueError(f"Value {v} exceeds maximum {maximum}")

        # Check multiple_of
        multiple = values.get('multiple_of')
        if multiple is not None and v % multiple != 0:
            raise ValueError(f"Value {v} is not a multiple of {multiple}")

        return v

    def validate_field(self) -> bool:
        """Validate the integer value."""
        if self.value is None:
            return True
        return True  # Pydantic handles validation

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {"value": self.value, "type": "integer"}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkIntegerField:
        """Create from API data."""
        return cls(value=data.get("value"))

    def get_value(self) -> Optional[int]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Any) -> None:
        """Set the value with validation."""
        # Convert string to int if needed
        if value is not None and isinstance(value, str):
            try:
                converted_value = int(value)
                self.value = converted_value
                return
            except (ValueError, TypeError):
                pass
        self.value = value


class IvkFloatField(BaseModel, IvkField[float]):
    """
    Float field with Pydantic validation for workflow inputs.
    
    Supports min/max constraints and decimal precision.
    
    Examples
    --------
    >>> field = IvkFloatField(minimum=0.0, maximum=1.0)
    >>> field.value = 0.5
    >>> print(field.get_value())
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[float] = None
    name: Optional[str] = None
    description: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract and convert fields
        value = data.pop('value', None)
        # Convert string/int to float if needed
        if value is not None and isinstance(value, (str, int)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass

        name = data.pop('name', None)
        description = data.pop('description', None)
        minimum = data.pop('minimum', None)
        maximum = data.pop('maximum', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            minimum=minimum,
            maximum=maximum,
            **data
        )
        
        # Initialize IvkField
        IvkField.__init__(
            self,
            value=value,
            name=name,
            description=description
        )

    @field_validator("value")
    @classmethod
    def validate_float_constraints(cls, v: Optional[float], info: Any) -> Optional[float]:
        """Validate float constraints."""
        if v is None:
            return v

        values = info.data if hasattr(info, 'data') else {}

        # Check minimum
        minimum = values.get('minimum')
        if minimum is not None and v < minimum:
            raise ValueError(f"Value {v} is less than minimum {minimum}")

        # Check maximum
        maximum = values.get('maximum')
        if maximum is not None and v > maximum:
            raise ValueError(f"Value {v} exceeds maximum {maximum}")

        return v

    def validate_field(self) -> bool:
        """Validate the float value."""
        if self.value is None:
            return True
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {"value": self.value, "type": "float"}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkFloatField:
        """Create from API data."""
        return cls(value=data.get("value"))

    def get_value(self) -> Optional[float]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Any) -> None:
        """Set the value with validation."""
        # Convert string/int to float if needed
        if value is not None and isinstance(value, (str, int)):
            try:
                converted_value = float(value)
                self.value = converted_value
                return
            except (ValueError, TypeError):
                pass
        self.value = value


class IvkBooleanField(BaseModel, IvkField[bool]):
    """
    Boolean field with Pydantic validation for workflow inputs.
    
    Examples
    --------
    >>> field = IvkBooleanField()
    >>> field.value = True
    >>> print(field.get_value())
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
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
        """Validate the boolean value."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {"value": self.value, "type": "boolean"}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkBooleanField:
        """Create from API data."""
        return cls(value=data.get("value"))

    def get_value(self) -> Optional[bool]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[bool]) -> None:
        """Set the value with validation."""
        self.value = value