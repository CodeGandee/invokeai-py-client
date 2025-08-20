"""
Model reference fields for InvokeAI workflows.

Fields that reference AI models including main models, VAEs, LoRAs,
and model configurations for different architectures.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from invokeai_py_client.ivk_fields.base import IvkField, PydanticFieldMixin
from invokeai_py_client.dnn_model.dnn_model_types import BaseDnnModelType, DnnModelType


class IvkModelIdentifierField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    Model identifier field for DNN model references.
    
    Corresponds to InvokeAI's ModelIdentifierField.
    
    This field directly contains the model identification attributes
    (key, hash, name, base, type) without a separate 'value' property.
    
    Examples
    --------
    >>> field = IvkModelIdentifierField(
    ...     key="sdxl-model-key",
    ...     hash="blake3:abc123...",
    ...     name="SDXL 1.0",
    ...     base="sdxl",
    ...     type="main"
    ... )
    >>> print(field.name)
    SDXL 1.0
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    # Direct fields matching InvokeAI's ModelIdentifierField
    key: str = Field(default="", description="The model's unique key")
    hash: str = Field(default="", description="The model's BLAKE3 hash")
    name: str = Field(default="", description="The model's name")
    base: BaseDnnModelType = Field(default=BaseDnnModelType.Any, description="The model's base model enum (e.g., sdxl, flux, sd-1, sd-2)")
    type: DnnModelType = Field(default=DnnModelType.Main, description="The model's type enum (e.g., main, vae, lora, controlnet)")
    submodel_type: Optional[str] = Field(
        default=None,
        description="The submodel to load, if this is a main model"
    )

    def validate_field(self) -> bool:
        """Validate the model reference has all required fields."""
        # All required fields are enforced by Pydantic
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for InvokeAI ModelIdentifierField."""
        return {
            "key": self.key,
            "hash": self.hash,
            "name": self.name,
            "base": getattr(self.base, 'value', self.base),
            "type": getattr(self.type, 'value', self.type),
            "submodel_type": self.submodel_type
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkModelIdentifierField:
        """Create from API data, coercing base to enum."""
        base_val = data.get("base", BaseDnnModelType.Any)
        try:
            base_enum = base_val if isinstance(base_val, BaseDnnModelType) else BaseDnnModelType(str(base_val))
        except Exception:
            base_enum = BaseDnnModelType.Any
        return cls(
            key=data.get("key", ""),
            hash=data.get("hash", ""),
            name=data.get("name", ""),
            base=base_enum,
            type=cls._coerce_type(data.get("type", DnnModelType.Main)),
            submodel_type=data.get("submodel_type")
        )

    @field_validator("base", mode="before")
    @classmethod
    def _coerce_base(cls, v: Any) -> BaseDnnModelType:
        if isinstance(v, BaseDnnModelType):
            return v
        try:
            return BaseDnnModelType(str(v))
        except Exception:
            return BaseDnnModelType.Any

    @staticmethod
    def _coerce_type(v: Any) -> DnnModelType:
        if isinstance(v, DnnModelType):
            return v
        try:
            return DnnModelType(str(v))
        except Exception:
            return DnnModelType.Main

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> DnnModelType:
        return cls._coerce_type(v)


class IvkUNetField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
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
    loras: list[dict[str, Any]] = Field(default_factory=list)
    seamless_axes: list[str] = Field(default_factory=list)
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


class IvkCLIPField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
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
    loras: list[dict[str, Any]] = Field(default_factory=list)

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


class IvkTransformerField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
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
    loras: list[dict[str, Any]] = Field(default_factory=list)

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



class IvkLoRAField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
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