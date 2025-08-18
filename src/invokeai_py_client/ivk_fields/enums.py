"""
Enum and choice fields for InvokeAI workflows.

Fields that provide enumerated choices including schedulers,
interpolation modes, and other predefined option sets.
"""

from __future__ import annotations

from typing import Any, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from invokeai_py_client.ivk_fields.base import IvkField, PydanticFieldMixin

# Scheduler options from InvokeAI
SCHEDULER_NAMES = [
    "ddim",
    "ddpm", 
    "deis",
    "dpm_2",
    "dpm_2_ancestral",
    "dpm_multi", 
    "dpm_sde",
    "dpm_sde_k",
    "euler",
    "euler_ancestral",
    "euler_k",
    "heun",
    "lms",
    "pndm",
    "unipc"
]

# Interpolation modes
INTERPOLATION_MODES = [
    "nearest",
    "linear", 
    "bilinear",
    "bicubic",
    "trilinear",
    "area"
]

# Color modes
COLOR_MODES = [
    "RGB",
    "RGBA",
    "L",
    "LA",
    "CMYK",
    "HSV"
]


class IvkEnumField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Enum field with predefined choices for workflow inputs.
    
    Examples
    --------
    >>> field = IvkEnumField(choices=["euler", "dpm++", "ddim"])
    >>> field.value = "euler"
    >>> print(field.value)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    choices: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        choices = data.pop('choices', [])

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            choices=choices,
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
    def validate_enum_choice(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate value is in choices."""
        if v is None:
            return v

        values = info.data if hasattr(info, 'data') else {}
        choices = values.get('choices', [])

        if choices and v not in choices:
            raise ValueError(f"Value '{v}' is not in choices: {choices}")

        return v

    def validate_field(self) -> bool:
        """Validate the enum value."""
        if self.value is None:
            return True
        if self.choices and self.value not in self.choices:
            raise ValueError(f"Value '{self.value}' not in choices: {self.choices}")
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value, 
            "type": "enum", 
            "choices": self.choices
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkEnumField:
        """Create from API data."""
        return cls(
            value=data.get("value"), 
            choices=data.get("choices", [])
        )

    def get_choices(self) -> list[str]:
        """Get available choices."""
        return self.choices.copy()

    def add_choice(self, choice: str) -> None:
        """Add a new choice option."""
        if choice not in self.choices:
            self.choices.append(choice)

    def remove_choice(self, choice: str) -> None:
        """Remove a choice option."""
        if choice in self.choices:
            self.choices.remove(choice)
            # Reset value if it's no longer valid
            if self.value == choice:
                self.value = None


class IvkSchedulerField(IvkEnumField):
    """
    Scheduler field with predefined InvokeAI scheduler options.
    
    Examples
    --------
    >>> field = IvkSchedulerField()
    >>> field.value = "euler"
    >>> print(field.get_choices())
    ['ddim', 'ddpm', 'deis', ...]
    """

    def __init__(self, **data: Any) -> None:
        """Initialize with InvokeAI scheduler choices."""
        if 'choices' not in data:
            data['choices'] = SCHEDULER_NAMES.copy()
        super().__init__(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "scheduler"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkSchedulerField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkInterpolationField(IvkEnumField):
    """
    Interpolation mode field for image operations.
    
    Examples
    --------
    >>> field = IvkInterpolationField()
    >>> field.value = "bilinear"
    >>> print(field.get_choices())
    ['nearest', 'linear', 'bilinear', ...]
    """

    def __init__(self, **data: Any) -> None:
        """Initialize with interpolation mode choices."""
        if 'choices' not in data:
            data['choices'] = INTERPOLATION_MODES.copy()
        super().__init__(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "interpolation"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkInterpolationField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkColorModeField(IvkEnumField):
    """
    Color mode field for image format specifications.
    
    Examples
    --------
    >>> field = IvkColorModeField()
    >>> field.value = "RGBA"
    >>> print(field.get_choices())
    ['RGB', 'RGBA', 'L', ...]
    """

    def __init__(self, **data: Any) -> None:
        """Initialize with color mode choices."""
        if 'choices' not in data:
            data['choices'] = COLOR_MODES.copy()
        super().__init__(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "color_mode"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkColorModeField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkLiteralField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Literal field for compile-time constant choices.
    
    Similar to enum but with TypeScript-style literal types.
    
    Examples
    --------
    >>> field = IvkLiteralField(literals=["RGB", "RGBA"])
    >>> field.value = "RGB"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    literals: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        literals = data.pop('literals', [])

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            literals=literals,
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
    def validate_literal_choice(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate value is in literals."""
        if v is None:
            return v

        values = info.data if hasattr(info, 'data') else {}
        literals = values.get('literals', [])

        if literals and v not in literals:
            raise ValueError(f"Value '{v}' is not in literals: {literals}")

        return v

    def validate_field(self) -> bool:
        """Validate the literal value."""
        if self.value is None:
            return True
        if self.literals and self.value not in self.literals:
            raise ValueError(f"Value '{self.value}' not in literals: {self.literals}")
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "literal",
            "literals": self.literals
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkLiteralField:
        """Create from API data."""
        return cls(
            value=data.get("value"),
            literals=data.get("literals", [])
        )

    def get_literals(self) -> list[str]:
        """Get available literal values."""
        return self.literals.copy()


# Convenient type aliases for common enum patterns
IvkSchedulerField = IvkSchedulerField  # Explicit alias for clarity