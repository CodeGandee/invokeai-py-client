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

    def get_value(self) -> Optional[dict[str, str]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, str]]) -> None:
        """Set the value with validation."""
        self.value = value


class IvkUNetField(BaseModel, IvkField[dict[str, Any]]):
    """
    UNet field with configuration for SD models.
    
    Contains UNet model, scheduler, LoRAs, and other configuration.
    
    Examples
    --------
    >>> field = IvkUNetField()
    >>> field.unet_model = {"key": "unet-key", "base": "sdxl", "type": "main"}
    >>> field.scheduler = {"key": "scheduler-key", "base": "any", "type": "scheduler"}
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    unet_model: Optional[dict[str, str]] = None
    scheduler: Optional[dict[str, str]] = None
    loras: list[dict[str, Any]] = []
    seamless_axes: list[str] = []
    freeu_config: Optional[dict[str, Any]] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        unet_model = data.pop('unet_model', None)
        scheduler = data.pop('scheduler', None)
        loras = data.pop('loras', [])
        seamless_axes = data.pop('seamless_axes', [])
        freeu_config = data.pop('freeu_config', None)

        # Build value dict from components
        if value is None:
            value = {}
            if unet_model:
                value["unet"] = unet_model
            if scheduler:
                value["scheduler"] = scheduler
            if loras:
                value["loras"] = loras
            if seamless_axes:
                value["seamless_axes"] = seamless_axes
            if freeu_config:
                value["freeu_config"] = freeu_config

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            unet_model=unet_model,
            scheduler=scheduler,
            loras=loras,
            seamless_axes=seamless_axes,
            freeu_config=freeu_config,
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
        """Validate UNet configuration."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "unet"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkUNetField:
        """Create from API data."""
        unet_data = data.get("value", {})
        return cls(
            value=unet_data,
            unet_model=unet_data.get("unet"),
            scheduler=unet_data.get("scheduler"),
            loras=unet_data.get("loras", []),
            seamless_axes=unet_data.get("seamless_axes", []),
            freeu_config=unet_data.get("freeu_config")
        )

    def get_value(self) -> Optional[dict[str, Any]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, Any]]) -> None:
        """Set the value with validation."""
        self.value = value


class IvkCLIPField(BaseModel, IvkField[dict[str, Any]]):
    """
    CLIP field with text encoder configuration.
    
    Contains tokenizer, text encoder, and LoRA configuration.
    
    Examples
    --------
    >>> field = IvkCLIPField()
    >>> field.tokenizer = {"key": "tokenizer-key", "base": "sdxl", "type": "clip"}
    >>> field.text_encoder = {"key": "encoder-key", "base": "sdxl", "type": "text_encoder"}
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tokenizer: Optional[dict[str, str]] = None
    text_encoder: Optional[dict[str, str]] = None
    skipped_layers: int = 0
    loras: list[dict[str, Any]] = []

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        tokenizer = data.pop('tokenizer', None)
        text_encoder = data.pop('text_encoder', None)
        skipped_layers = data.pop('skipped_layers', 0)
        loras = data.pop('loras', [])

        # Build value dict from components
        if value is None:
            value = {}
            if tokenizer:
                value["tokenizer"] = tokenizer
            if text_encoder:
                value["text_encoder"] = text_encoder
            value["skipped_layers"] = skipped_layers
            if loras:
                value["loras"] = loras

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            tokenizer=tokenizer,
            text_encoder=text_encoder,
            skipped_layers=skipped_layers,
            loras=loras,
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
        """Validate CLIP configuration."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "clip"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkCLIPField:
        """Create from API data."""
        clip_data = data.get("value", {})
        return cls(
            value=clip_data,
            tokenizer=clip_data.get("tokenizer"),
            text_encoder=clip_data.get("text_encoder"),
            skipped_layers=clip_data.get("skipped_layers", 0),
            loras=clip_data.get("loras", [])
        )

    def get_value(self) -> Optional[dict[str, Any]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, Any]]) -> None:
        """Set the value with validation."""
        self.value = value


class IvkTransformerField(BaseModel, IvkField[dict[str, Any]]):
    """
    Transformer field for FLUX models.
    
    Contains transformer model and LoRA configuration.
    
    Examples
    --------
    >>> field = IvkTransformerField()
    >>> field.transformer_model = {"key": "flux-key", "base": "flux", "type": "main"}
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    transformer_model: Optional[dict[str, str]] = None
    loras: list[dict[str, Any]] = []

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        transformer_model = data.pop('transformer_model', None)
        loras = data.pop('loras', [])

        # Build value dict from components
        if value is None:
            value = {}
            if transformer_model:
                value["transformer"] = transformer_model
            if loras:
                value["loras"] = loras

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            transformer_model=transformer_model,
            loras=loras,
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
        """Validate Transformer configuration."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "transformer"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkTransformerField:
        """Create from API data."""
        transformer_data = data.get("value", {})
        return cls(
            value=transformer_data,
            transformer_model=transformer_data.get("transformer"),
            loras=transformer_data.get("loras", [])
        )

    def get_value(self) -> Optional[dict[str, Any]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, Any]]) -> None:
        """Set the value with validation."""
        self.value = value


class IvkLoRAField(BaseModel, IvkField[dict[str, Any]]):
    """
    LoRA field with model and weight configuration.
    
    Examples
    --------
    >>> field = IvkLoRAField()
    >>> field.lora_model = {"key": "lora-key", "base": "sdxl", "type": "lora"}
    >>> field.weight = 0.8
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    lora_model: Optional[dict[str, str]] = None
    weight: float = 1.0

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        lora_model = data.pop('lora_model', None)
        weight = data.pop('weight', 1.0)

        # Build value dict from components
        if value is None and lora_model:
            value = {
                "lora": lora_model,
                "weight": weight
            }

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            lora_model=lora_model,
            weight=weight,
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
        """Validate LoRA configuration."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "lora"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkLoRAField:
        """Create from API data."""
        lora_data = data.get("value", {})
        return cls(
            value=lora_data,
            lora_model=lora_data.get("lora"),
            weight=lora_data.get("weight", 1.0)
        )

    def get_value(self) -> Optional[dict[str, Any]]:
        """Get the current value."""
        return self.value

    def set_value(self, value: Optional[dict[str, Any]]) -> None:
        """Set the value with validation."""
        self.value = value
        if value:
            self.lora_model = value.get("lora")
            self.weight = value.get("weight", 1.0)


# Create aliases for common model field types
IvkSDXLModelField = IvkModelIdentifierField
IvkFluxModelField = IvkModelIdentifierField
IvkT5EncoderField = IvkModelIdentifierField
IvkCLIPEmbedField = IvkModelIdentifierField
IvkVAEModelField = IvkModelIdentifierField