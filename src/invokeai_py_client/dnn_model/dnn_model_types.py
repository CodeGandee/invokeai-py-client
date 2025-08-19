"""
DNN model data types for the InvokeAI model subsystem.

This module provides the DnnModel class which represents a deep neural network
model (dnn-model) in the InvokeAI system. The term "dnn-model" is used to
differentiate from Pydantic data models and other model concepts.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DnnModelType(str, Enum):
    """DNN model type enum from InvokeAI taxonomy."""
    
    ONNX = "onnx"
    Main = "main"
    VAE = "vae"
    LoRA = "lora"
    ControlLoRa = "control_lora"
    ControlNet = "controlnet"
    TextualInversion = "embedding"
    IPAdapter = "ip_adapter"
    CLIPVision = "clip_vision"
    CLIPEmbed = "clip_embed"
    T2IAdapter = "t2i_adapter"
    T5Encoder = "t5_encoder"
    SpandrelImageToImage = "spandrel_image_to_image"
    SigLIP = "siglip"
    FluxRedux = "flux_redux"
    LlavaOnevision = "llava_onevision"


class BaseDnnModelType(str, Enum):
    """Base DNN model type enum from InvokeAI taxonomy."""
    
    Any = "any"
    StableDiffusion1 = "sd-1"
    StableDiffusion2 = "sd-2"
    StableDiffusion3 = "sd-3"
    StableDiffusionXL = "sdxl"
    StableDiffusionXLRefiner = "sdxl-refiner"
    Flux = "flux"
    CogView4 = "cogview4"
    Imagen3 = "imagen3"
    Imagen4 = "imagen4"
    ChatGPT4o = "chatgpt-4o"
    FluxKontext = "flux-kontext"


class DnnModelFormat(str, Enum):
    """Storage format of DNN model from InvokeAI taxonomy."""
    
    OMI = "omi"
    Diffusers = "diffusers"
    Checkpoint = "checkpoint"
    LyCORIS = "lycoris"
    ONNX = "onnx"
    Olive = "olive"
    EmbeddingFile = "embedding_file"
    EmbeddingFolder = "embedding_folder"
    InvokeAI = "invokeai"
    T5Encoder = "t5_encoder"
    BnbQuantizedLlmInt8b = "bnb_quantized_int8b"
    BnbQuantizednf4b = "bnb_quantized_nf4b"
    GGUFQuantized = "gguf_quantized"
    Api = "api"


class DnnModel(BaseModel):
    """
    InvokeAI deep neural network model representation.

    DNN models are the core components in InvokeAI for generating images,
    controlling generation, and processing data. They include main diffusion models,
    ControlNets, VAEs, text encoders, and other specialized components.

    This matches the model structure from the InvokeAI API v2/models endpoint.
    Models are considered "static" resources - they exist on the system and
    cannot be created/modified through the API (only discovered and used).

    The term "dnn-model" is used to differentiate from Pydantic data models
    and other model concepts in the codebase.

    Parameters
    ----------
    key : str
        Unique identifier for the model.
    name : str
        Human-readable name of the model.
    type : DnnModelType
        Type/category of the model.
    base : BaseDnnModelType
        Base model architecture.
    hash : str
        Blake3 hash for model verification.
    description : str, optional
        Description of the model.
    format : DnnModelFormat
        Storage format of the model.
    path : str
        Path or identifier where model is stored.
    source : str, optional
        Original source of the model.
    file_size : int or None, optional
        File size in bytes.
    variant : str or None, optional
        Model variant (e.g., 'normal', 'inpainting').
    prediction_type : str or None, optional
        Prediction type for main models.

    Examples
    --------
    >>> dnn_model = DnnModel(
    ...     key="abc123",
    ...     name="flux1-dev",
    ...     type=DnnModelType.Main,
    ...     base=BaseDnnModelType.Flux,
    ...     hash="blake3:...",
    ...     format=DnnModelFormat.Checkpoint,
    ...     path="/models/flux1-dev.safetensors"
    ... )
    >>> print(f"{dnn_model.name}: {dnn_model.get_category()}")
    flux1-dev: Primary Diffusion Model
    """

    # Core identification fields
    key: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable name of the model")
    type: DnnModelType = Field(..., description="Type/category of the model")
    base: BaseDnnModelType = Field(..., description="Base model architecture")
    hash: str = Field(..., description="Blake3 hash for model verification")

    # Model metadata
    description: str = Field(default="", description="Description of the model")
    format: DnnModelFormat = Field(..., description="Storage format of the model")
    path: str = Field(..., description="Path or identifier where model is stored")
    source: str = Field(default="", description="Original source of the model")

    # Optional metadata
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    variant: Optional[str] = Field(None, description="Model variant (e.g., 'normal', 'inpainting')")
    prediction_type: Optional[str] = Field(None, description="Prediction type for main models")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> DnnModel:
        """
        Create a DnnModel from API response data.

        Parameters
        ----------
        data : dict[str, Any]
            Raw API response dictionary from /api/v2/models/ endpoint.

        Returns
        -------
        DnnModel
            Parsed dnn-model instance.

        Examples
        --------
        >>> api_data = {"key": "abc123", "name": "flux1-dev", "type": "main", ...}
        >>> dnn_model = DnnModel.from_api_response(api_data)
        """
        return cls(**data)

    def get_category(self) -> str:
        """
        Get human-readable category description for the model.

        Returns
        -------
        str
            Descriptive category name.

        Examples
        --------
        >>> dnn_model.get_category()
        'Primary Diffusion Model'
        """
        categories = {
            DnnModelType.Main: "Primary Diffusion Model",
            DnnModelType.ControlNet: "ControlNet (Guided Generation)",
            DnnModelType.VAE: "Variational Auto-Encoder",
            DnnModelType.CLIPVision: "CLIP Vision Encoder",
            DnnModelType.CLIPEmbed: "CLIP Text Encoder",
            DnnModelType.IPAdapter: "IP-Adapter (Image Prompting)",
            DnnModelType.T5Encoder: "T5 Text Encoder",
            DnnModelType.LoRA: "LoRA (Low-Rank Adaptation)",
            DnnModelType.ControlLoRa: "Control LoRA",
            DnnModelType.TextualInversion: "Textual Inversion (Embedding)",
            DnnModelType.T2IAdapter: "T2I-Adapter",
            DnnModelType.SpandrelImageToImage: "Spandrel Image-to-Image",
            DnnModelType.SigLIP: "SigLIP",
            DnnModelType.FluxRedux: "FLUX Redux",
            DnnModelType.LlavaOnevision: "LLaVA OneVision",
            DnnModelType.ONNX: "ONNX Model"
        }
        return categories.get(self.type, f"Unknown ({self.type.value})")

    def format_file_size(self) -> str:
        """
        Format file size in human-readable format.

        Returns
        -------
        str
            Formatted size string (e.g., "1.5 GB", "256 MB").

        Examples
        --------
        >>> dnn_model.format_file_size()
        '22.17 GB'
        """
        if self.file_size is None:
            return "Unknown"

        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def is_compatible_with_base(self, base_model: BaseDnnModelType) -> bool:
        """
        Check if this dnn-model is compatible with a specific base model.

        Models with base=BaseDnnModelType.Any are compatible with all architectures.

        Parameters
        ----------
        base_model : BaseDnnModelType
            Base model architecture to check compatibility with.

        Returns
        -------
        bool
            True if compatible, False otherwise.

        Examples
        --------
        >>> dnn_model.is_compatible_with_base(BaseDnnModelType.Flux)
        True
        >>> dnn_model.is_compatible_with_base(BaseDnnModelType.StableDiffusionXL)
        False
        """
        return self.base == BaseDnnModelType.Any or self.base == base_model

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns
        -------
        dict[str, Any]
            DNN model data as dictionary.
        """
        return self.model_dump(exclude_none=True)

    def __str__(self) -> str:
        """String representation of the dnn-model."""
        return f"{self.name} ({self.type.value}, {self.base.value}, {self.format_file_size()})"

    def __repr__(self) -> str:
        """Developer representation of the dnn-model."""
        return f"DnnModel(key='{self.key}', name='{self.name}', type='{self.type.value}', base='{self.base.value}')"