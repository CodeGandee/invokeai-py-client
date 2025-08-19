"""
Model conversion utilities using Protocol for type-safe conversions.

This module provides conversion between different model representations
(DnnModel, IvkModelIdentifierField) without coupling them directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from invokeai_py_client.ivk_fields.models import IvkModelIdentifierField


@runtime_checkable
class ModelLike(Protocol):
    """
    Protocol defining the interface for model-like objects.
    
    Both DnnModel and IvkModelIdentifierField implement this interface,
    allowing for type-safe conversions between them.
    """
    
    @property
    def key(self) -> str:
        """Model's unique key."""
        ...
    
    @property
    def hash(self) -> str:
        """Model's BLAKE3 hash."""
        ...
    
    @property
    def name(self) -> str:
        """Model's display name."""
        ...
    
    @property
    def base(self) -> str:
        """Model's base architecture (e.g., 'sdxl', 'flux', 'sd-1')."""
        ...
    
    @property
    def type(self) -> str:
        """Model's type (e.g., 'main', 'vae', 'lora')."""
        ...


def to_ivk_model_field(model: ModelLike) -> IvkModelIdentifierField:
    """
    Convert any ModelLike object to IvkModelIdentifierField.
    
    This factory method converts DnnModel or any other ModelLike
    object to the IvkModelIdentifierField used in workflows.
    
    Parameters
    ----------
    model : ModelLike
        Any object implementing the ModelLike protocol.
    
    Returns
    -------
    IvkModelIdentifierField
        Field instance for use in workflows.
    
    Examples
    --------
    >>> from invokeai_py_client.dnn_model import DnnModelRepository
    >>> repo = DnnModelRepository(client)
    >>> dnn_model = repo.get_model_by_key("model-key")
    >>> 
    >>> # Convert to field
    >>> field = to_ivk_model_field(dnn_model)
    >>> 
    >>> # Use in workflow
    >>> workflow.get_input(0).field = field
    """
    # Handle base and type that might be enums
    base_value = model.base.value if hasattr(model.base, 'value') else str(model.base)
    type_value = model.type.value if hasattr(model.type, 'value') else str(model.type)
    
    return IvkModelIdentifierField(
        key=model.key,
        hash=model.hash,
        name=model.name,
        base=base_value,
        type=type_value,
        submodel_type=None  # Usually not needed for main models
    )


def from_ivk_model_field(field: IvkModelIdentifierField) -> dict[str, str]:
    """
    Convert IvkModelIdentifierField to a model dictionary.
    
    This is useful when you need model information from a field
    but don't have access to the full DnnModel object.
    
    Parameters
    ----------
    field : IvkModelIdentifierField
        The field to convert.
    
    Returns
    -------
    dict[str, str]
        Dictionary with model properties.
    
    Examples
    --------
    >>> field = workflow.get_input(0).field
    >>> if isinstance(field, IvkModelIdentifierField):
    ...     model_info = from_ivk_model_field(field)
    ...     print(f"Using model: {model_info['name']}")
    """
    return {
        "key": field.key,
        "hash": field.hash,
        "name": field.name,
        "base": field.base,
        "type": field.type,
    }


def is_model_compatible(model: ModelLike, base_type: str, model_type: str | None = None) -> bool:
    """
    Check if a model is compatible with specified requirements.
    
    Parameters
    ----------
    model : ModelLike
        The model to check.
    base_type : str
        Required base architecture (e.g., 'sdxl', 'flux').
    model_type : str, optional
        Required model type (e.g., 'main', 'vae'). If None, any type is accepted.
    
    Returns
    -------
    bool
        True if the model matches the requirements.
    
    Examples
    --------
    >>> # Check if model is SDXL main model
    >>> if is_model_compatible(model, 'sdxl', 'main'):
    ...     field = to_ivk_model_field(model)
    ...     workflow.get_input(0).field = field
    """
    # Handle enum values
    model_base = model.base.value if hasattr(model.base, 'value') else str(model.base)
    
    if model_base != base_type:
        return False
    
    if model_type is not None:
        model_type_value = model.type.value if hasattr(model.type, 'value') else str(model.type)
        if model_type_value != model_type:
            return False
    
    return True