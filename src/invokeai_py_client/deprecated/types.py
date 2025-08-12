"""Client-side wrappers for InvokeAI primitive types ("invokeai-types").

These types are used for workflow inputs and outputs within the client API.
Each type performs minimal validation and type-safe value access. During
implementation, these can be extended to include server-side schema details
as needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .exceptions import InvokeAIValidationError


@dataclass
class BaseField:
    """Base class for all client-side typed fields.

    Parameters
    ----------
    name : str
        The unique workflow input/output field name. Required for inputs.
    value : Any, optional
        The field value. Type must conform to the specific field subclass.

    Notes
    -----
    A field may represent either a workflow input or output. For outputs,
    ``name`` may be absent, but is retained in the type for symmetry and
    diagnostics.
    """

    name: Optional[str] = None
    value: Any = None

    def set(self, value: Any) -> None:
        """Set the field value with validation.

        Parameters
        ----------
        value : Any
            The value to assign.
        """

        self._validate(value)
        self.value = value

    def get(self) -> Any:
        """Return the field value."""

        return self.value

    def _validate(self, value: Any) -> None:  # pragma: no cover - placeholder
        """Validate a value for this field.

        Subclasses should raise ``InvokeAIValidationError`` when validation
        fails.
        """

        raise NotImplementedError


@dataclass
class InvokeAIIntegerField(BaseField):
    """Integer field wrapper.

    Accepts Python ``int`` values.
    """

    def _validate(self, value: Any) -> None:
        if not isinstance(value, int):
            raise InvokeAIValidationError("Expected int for InvokeAIIntegerField")


@dataclass
class InvokeAIFloatField(BaseField):
    """Float field wrapper.

    Accepts Python ``float`` values.
    """

    def _validate(self, value: Any) -> None:
        if not isinstance(value, (float, int)):
            raise InvokeAIValidationError("Expected float for InvokeAIFloatField")


@dataclass
class InvokeAIStringField(BaseField):
    """String field wrapper.

    Accepts Python ``str`` values.
    """

    def _validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise InvokeAIValidationError("Expected str for InvokeAIStringField")


@dataclass
class InvokeAIBooleanField(BaseField):
    """Boolean field wrapper.

    Accepts Python ``bool`` values.
    """

    def _validate(self, value: Any) -> None:
        if not isinstance(value, bool):
            raise InvokeAIValidationError("Expected bool for InvokeAIBooleanField")


@dataclass
class InvokeAIImageRefField(BaseField):
    """Image reference field wrapper.

    Represents a reference to an image asset stored in the backend. The value
    is the server-side asset name (str). Client code is expected to upload
    images first and then set this value to the server-assigned name.
    """

    def _validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise InvokeAIValidationError("Expected str (asset name) for InvokeAIImageRefField")
