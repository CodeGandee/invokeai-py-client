"""
Model reference fields for InvokeAI workflows.

Fields that reference AI models including main models, VAEs, LoRAs,
and model configurations for different architectures.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from invokeai_py_client.ivk_fields.base import IvkField


class IvkModelIdentifierField(BaseModel, IvkField[dict[str, str]]):
    """
    Model identifier field for DNN model references.
    
    Handles model references with key, name, base, and type attributes.
    
    Examples
    --------
    >>> field = IvkModelIdentifierField()
    >>> field.value = {
    ...     "key": "sdxl-model-key",
    ...     "name": "SDXL 1.0",
    ...     "base": "sdxl",
    ...     "type": "main"
    ... }
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, str]] = None
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

    @field_validator("value")
    @classmethod
    def validate_model_structure(cls, v: Optional[dict[str, str]], info: Any) -> Optional[dict[str, str]]:
        """Validate model reference structure."""
        if v is None:
            return v

        # Required fields for model reference
        required = ["key", "name", "base", "type"]
        missing = [f for f in required if f not in v]
        if missing:
            # Allow partial model info during initialization
            pass

        return v

    def validate_field(self) -> bool:
        """Validate the model reference."""
        if self.value is None:
            return True
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        if self.value is None:
            return {"value": None, "type": "model"}
        return {"value": self.value, "type": "model"}

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkModelIdentifierField:
        """Create from API data."""
        return cls(value=data.get("value"))


class IvkUNetField(BaseModel, IvkField[dict[str, Any]]):
    """
    UNet field with configuration for SD models.
    
    Corresponds to InvokeAI's UNetField model type.
    
    This field represents a complete UNet configuration including the model,
    scheduler, LoRAs, and other settings. The field itself IS the value - it
    doesn't contain a separate value field.
    
    Examples
    --------
    >>> field = IvkUNetField(
    ...     unet_model={"key": "unet-key", "base": "sdxl", "type": "main"},
    ...     scheduler={"key": "scheduler-key", "base": "any", "type": "scheduler"}
    ... )
    >>> field.loras.append({"lora": {...}, "weight": 0.8})
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # UNet configuration fields - these ARE the value
    unet_model: Optional[dict[str, str]] = None
    scheduler: Optional[dict[str, str]] = None
    loras: list[dict[str, Any]] = []
    seamless_axes: list[str] = []
    freeu_config: Optional[dict[str, Any]] = None

    def validate_field(self) -> bool:
        """Validate UNet configuration."""
        # Could add validation for required fields here
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI UNetField."""
        api_dict: dict[str, Any] = {}
        if self.unet_model:
            api_dict["unet"] = self.unet_model
        if self.scheduler:
            api_dict["scheduler"] = self.scheduler
        api_dict["loras"] = self.loras
        api_dict["seamless_axes"] = self.seamless_axes
        if self.freeu_config:
            api_dict["freeu_config"] = self.freeu_config
        return api_dict

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkUNetField:
        """Create from API data."""
        return cls(
            unet_model=data.get("unet"),
            scheduler=data.get("scheduler"),
            loras=data.get("loras", []),
            seamless_axes=data.get("seamless_axes", []),
            freeu_config=data.get("freeu_config")
        )


class IvkCLIPField(BaseModel, IvkField[dict[str, Any]]):
    """
    CLIP field with text encoder configuration.
    
    Corresponds to InvokeAI's CLIPField model type.
    
    This field represents a complete CLIP configuration including tokenizer,
    text encoder, and LoRA settings. The field itself IS the value - it doesn't
    contain a separate value field.
    
    Examples
    --------
    >>> field = IvkCLIPField(
    ...     tokenizer={"key": "tokenizer-key", "base": "sdxl", "type": "clip"},
    ...     text_encoder={"key": "encoder-key", "base": "sdxl", "type": "text_encoder"}
    ... )
    >>> field.skipped_layers = 2
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # CLIP configuration fields - these ARE the value
    tokenizer: Optional[dict[str, str]] = None
    text_encoder: Optional[dict[str, str]] = None
    skipped_layers: int = 0
    loras: list[dict[str, Any]] = []

    def validate_field(self) -> bool:
        """Validate CLIP configuration."""
        # Could add validation for required fields here
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI CLIPField."""
        api_dict: dict[str, Any] = {}
        if self.tokenizer:
            api_dict["tokenizer"] = self.tokenizer
        if self.text_encoder:
            api_dict["text_encoder"] = self.text_encoder
        api_dict["skipped_layers"] = self.skipped_layers
        api_dict["loras"] = self.loras
        return api_dict

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkCLIPField:
        """Create from API data."""
        return cls(
            tokenizer=data.get("tokenizer"),
            text_encoder=data.get("text_encoder"),
            skipped_layers=data.get("skipped_layers", 0),
            loras=data.get("loras", [])
        )


class IvkTransformerField(BaseModel, IvkField[dict[str, Any]]):
    """
    Transformer field for FLUX models.
    
    Corresponds to InvokeAI's TransformerField type.
    
    This field represents a transformer configuration directly through its attributes.
    The field itself IS the value - it doesn't contain a separate value field.
    
    Examples
    --------
    >>> field = IvkTransformerField(
    ...     transformer_model={"key": "flux-key", "base": "flux", "type": "main"}
    ... )
    >>> field.loras.append({"lora": {...}, "weight": 0.8})
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Transformer configuration fields - these ARE the value
    transformer_model: Optional[dict[str, str]] = None
    loras: list[dict[str, Any]] = []

    def validate_field(self) -> bool:
        """Validate Transformer configuration."""
        # Could add validation for required fields here
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI TransformerField."""
        api_dict: dict[str, Any] = {}
        if self.transformer_model:
            api_dict["transformer"] = self.transformer_model
        api_dict["loras"] = self.loras
        return api_dict

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkTransformerField:
        """Create from API data."""
        return cls(
            transformer_model=data.get("transformer"),
            loras=data.get("loras", [])
        )



class IvkLoRAField(BaseModel, IvkField[dict[str, Any]]):
    """
    LoRA field with model and weight configuration.
    
    Corresponds to InvokeAI's LoRAField type.
    
    This field represents a LoRA configuration directly through its attributes.
    The field itself IS the value - it doesn't contain a separate value field.
    
    Examples
    --------
    >>> field = IvkLoRAField(
    ...     lora_model={"key": "lora-key", "base": "sdxl", "type": "lora"},
    ...     weight=0.8
    ... )
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # LoRA configuration fields - these ARE the value
    lora_model: Optional[dict[str, str]] = None
    weight: float = 1.0

    def validate_field(self) -> bool:
        """Validate LoRA configuration."""
        # Could add validation for required fields here
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI LoRAField."""
        api_dict: dict[str, Any] = {}
        if self.lora_model:
            api_dict["lora"] = self.lora_model
        api_dict["weight"] = self.weight
        return api_dict

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkLoRAField:
        """Create from API data."""
        return cls(
            lora_model=data.get("lora"),
            weight=data.get("weight", 1.0)
        )


# Create aliases for common model field types
IvkSDXLModelField = IvkModelIdentifierField
IvkFluxModelField = IvkModelIdentifierField
IvkT5EncoderField = IvkModelIdentifierField
IvkCLIPEmbedField = IvkModelIdentifierField
IvkVAEModelField = IvkModelIdentifierField