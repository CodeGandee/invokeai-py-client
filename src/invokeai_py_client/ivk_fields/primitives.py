"""
Primitive field types for InvokeAI workflows.

Basic data types including strings, integers, floats, and booleans
with Pydantic validation and InvokeAI API compatibility.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from invokeai_py_client.ivk_fields.base import IvkField, PydanticFieldMixin


class IvkStringField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    String field with Pydantic validation for workflow inputs.
    
    Corresponds to InvokeAI's StringField primitive type.
    
    Supports length constraints and pattern validation.
    Primitive string fields keep a `value` field to store the actual string data.
    
    Examples
    --------
    >>> field = IvkStringField(value="A beautiful landscape")
    >>> field.value = "Updated prompt"
    >>> print(field.value)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Primitive types keep the value field
    value: Optional[str] = None
    # Optional metadata fields
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None

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
        # Pydantic handles validation through field_validator
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI StringInvocation."""
        return {"value": self.value}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkStringField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkIntegerField(BaseModel, PydanticFieldMixin, IvkField[int]):
    """
    Integer field with Pydantic validation for workflow inputs.
    
    Corresponds to InvokeAI's IntegerField primitive type.
    
    Supports min/max constraints and multiple-of validation.
    Primitive integer fields keep a `value` field to store the actual integer data.
    
    Examples
    --------
    >>> field = IvkIntegerField(value=512, minimum=64, maximum=2048, multiple_of=8)
    >>> field.value = 1024
    >>> print(field.value)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Primitive types keep the value field
    value: Optional[int] = None
    # Optional constraint fields
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    multiple_of: Optional[int] = None

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
        # Pydantic handles validation through field_validator
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI IntegerInvocation."""
        return {"value": self.value}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkIntegerField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkFloatField(BaseModel, PydanticFieldMixin, IvkField[float]):
    """
    Float field with Pydantic validation for workflow inputs.
    
    Corresponds to InvokeAI's FloatField primitive type.
    
    Supports min/max constraints and decimal precision.
    Primitive float fields keep a `value` field to store the actual float data.
    
    Examples
    --------
    >>> field = IvkFloatField(value=0.5, minimum=0.0, maximum=1.0)
    >>> field.value = 0.75
    >>> print(field.value)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Primitive types keep the value field
    value: Optional[float] = None
    # Optional constraint fields
    minimum: Optional[float] = None
    maximum: Optional[float] = None

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
        # Pydantic handles validation through field_validator
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI FloatInvocation."""
        return {"value": self.value}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkFloatField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkBooleanField(BaseModel, PydanticFieldMixin, IvkField[bool]):
    """
    Boolean field with Pydantic validation for workflow inputs.
    
    Corresponds to InvokeAI's BooleanField primitive type.
    
    Primitive boolean fields keep a `value` field to store the actual boolean data.
    
    Examples
    --------
    >>> field = IvkBooleanField(value=True)
    >>> field.value = False
    >>> print(field.value)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Primitive types keep the value field  
    value: Optional[bool] = None

    def validate_field(self) -> bool:
        """Validate the boolean value."""
        # Pydantic handles validation
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI BooleanInvocation."""
        return {"value": self.value}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkBooleanField:
        """Create from API data."""
        return cls(value=data.get("value"))