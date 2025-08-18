"""
Resource reference fields for InvokeAI workflows.

Fields that reference server-side resources like images, boards, latents,
tensors, and other data objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from invokeai_py_client.ivk_fields.base import IvkField, IvkImageFieldMixin, PydanticFieldMixin

if TYPE_CHECKING:
    from invokeai_py_client.client import InvokeAIClient


class IvkImageField(BaseModel, PydanticFieldMixin, IvkField[str], IvkImageFieldMixin):
    """
    Image field for handling image references and uploads.
    
    Handles both local image paths (for upload) and server-side 
    image names (for references).
    
    Examples
    --------
    >>> field = IvkImageField()
    >>> field.value = "path/to/image.png"
    >>> # Or for uploaded images:
    >>> field.value = "image-name-on-server.png"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_uploaded: bool = False

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        is_uploaded = data.pop('is_uploaded', False)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            is_uploaded=is_uploaded,
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
        """Validate the image reference."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": {"image_name": self.value} if self.value else None,
            "type": "image"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkImageField:
        """Create from API data."""
        image_data = data.get("value", {})
        if isinstance(image_data, dict):
            image_name = image_data.get("image_name")
        else:
            image_name = image_data
        
        return cls(
            value=image_name,
            is_uploaded=data.get("is_uploaded", True)
        )


    async def upload(self, client: InvokeAIClient) -> str:
        """Upload the local image to the server."""
        # Placeholder for upload implementation
        raise NotImplementedError

    async def download(self, client: InvokeAIClient, output_path: Optional[Path] = None) -> Path:
        """Download the image from the server."""
        # Placeholder for download implementation
        raise NotImplementedError


class IvkBoardField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Board field for specifying output board destinations.
    
    Examples
    --------
    >>> field = IvkBoardField()
    >>> field.value = "samples"
    >>> print(field.value)
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None
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
        """Validate the board reference."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": {"board_id": self.value} if self.value else None,
            "type": "board"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkBoardField:
        """Create from API data."""
        board_data = data.get("value", {})
        if isinstance(board_data, dict):
            board_id = board_data.get("board_id")
        else:
            board_id = board_data
            
        return cls(value=board_id)



class IvkLatentsField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Latents field for latent space representations.
    
    References latent tensors by UUID with optional seed information.
    
    Examples
    --------
    >>> field = IvkLatentsField()
    >>> field.value = "latents-uuid-here"
    >>> field.seed = 42
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None  # latents_name
    name: Optional[str] = None
    description: Optional[str] = None
    seed: Optional[int] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        seed = data.pop('seed', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            seed=seed,
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
        """Validate latents identifier."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        api_value: dict[str, Any] = {}
        if self.value:
            api_value["latents_name"] = self.value
        if self.seed is not None:
            api_value["seed"] = self.seed
            
        return {
            "value": api_value if api_value else None,
            "type": "latents"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkLatentsField:
        """Create from API data."""
        latents_data = data.get("value", {})
        if isinstance(latents_data, dict):
            return cls(
                value=latents_data.get("latents_name"),
                seed=latents_data.get("seed")
            )
        else:
            return cls(value=latents_data)



class IvkTensorField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Tensor field for generic tensor references.
    
    References tensors by UUID for conditioning and other data.
    
    Examples
    --------
    >>> field = IvkTensorField()
    >>> field.value = "tensor-uuid-here"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None  # tensor_name
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
        """Validate tensor identifier."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": {"tensor_name": self.value} if self.value else None,
            "type": "tensor"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkTensorField:
        """Create from API data."""
        tensor_data = data.get("value", {})
        if isinstance(tensor_data, dict):
            tensor_name = tensor_data.get("tensor_name")
        else:
            tensor_name = tensor_data
            
        return cls(value=tensor_name)



class IvkDenoiseMaskField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    Denoise mask field for inpainting operations.
    
    Contains mask reference and optional masked latents.
    
    Examples
    --------
    >>> field = IvkDenoiseMaskField()
    >>> field.mask_name = "mask-uuid"
    >>> field.gradient = False
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    mask_name: Optional[str] = None
    masked_latents_name: Optional[str] = None
    gradient: bool = False

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        mask_name = data.pop('mask_name', None)
        masked_latents_name = data.pop('masked_latents_name', None)
        gradient = data.pop('gradient', False)

        # Build value dict from components
        if value is None and mask_name:
            value = {
                "mask_name": mask_name,
                "gradient": gradient
            }
            if masked_latents_name:
                value["masked_latents_name"] = masked_latents_name

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            mask_name=mask_name,
            masked_latents_name=masked_latents_name,
            gradient=gradient,
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
        """Validate mask structure."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "denoise_mask"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkDenoiseMaskField:
        """Create from API data."""
        mask_data = data.get("value", {})
        return cls(
            value=mask_data,
            mask_name=mask_data.get("mask_name"),
            masked_latents_name=mask_data.get("masked_latents_name"),
            gradient=mask_data.get("gradient", False)
        )


class IvkMetadataField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    Metadata field for arbitrary key-value pairs.
    
    Stores custom metadata that gets attached to outputs.
    
    Examples
    --------
    >>> field = IvkMetadataField()
    >>> field.value = {"prompt": "landscape", "model": "SDXL"}
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
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
        """Validate metadata structure."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "metadata"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkMetadataField:
        """Create from API data."""
        return cls(value=data.get("value", {}))

