"""
Conditioning fields for different AI model architectures.

Supports conditioning systems for SD, FLUX, SD3, CogView4, and other
generative AI model architectures.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from invokeai_py_client.ivk_fields.base import IvkField, PydanticFieldMixin


class IvkConditioningField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Standard conditioning field for SD models.
    
    References conditioning tensors with optional mask support.
    
    Examples
    --------
    >>> field = IvkConditioningField()
    >>> field.value = "conditioning-uuid-here"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None  # conditioning_name
    name: Optional[str] = None
    description: Optional[str] = None
    mask: Optional[str] = None  # Optional tensor field for masked conditioning

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        mask = data.pop('mask', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            mask=mask,
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
        """Validate conditioning reference."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        api_value: dict[str, Any] = {}
        if self.value:
            api_value["conditioning_name"] = self.value
        if self.mask:
            api_value["mask"] = {"tensor_name": self.mask}
            
        return {
            "value": api_value if api_value else None,
            "type": "conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkConditioningField:
        """Create from API data."""
        conditioning_data = data.get("value", {})
        mask_data = conditioning_data.get("mask", {})
        mask_name = mask_data.get("tensor_name") if isinstance(mask_data, dict) else None
        
        return cls(
            value=conditioning_data.get("conditioning_name"),
            mask=mask_name
        )



class IvkFluxConditioningField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    FLUX conditioning field for FLUX models.
    
    Similar to standard conditioning but for FLUX architecture.
    
    Examples
    --------
    >>> field = IvkFluxConditioningField()
    >>> field.value = "flux-conditioning-uuid"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None  # conditioning_name
    name: Optional[str] = None
    description: Optional[str] = None
    mask: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        mask = data.pop('mask', None)

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            mask=mask,
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
        """Validate FLUX conditioning reference."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        api_value: dict[str, Any] = {}
        if self.value:
            api_value["conditioning_name"] = self.value
        if self.mask:
            api_value["mask"] = {"tensor_name": self.mask}
            
        return {
            "value": api_value if api_value else None,
            "type": "flux_conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkFluxConditioningField:
        """Create from API data."""
        conditioning_data = data.get("value", {})
        mask_data = conditioning_data.get("mask", {})
        mask_name = mask_data.get("tensor_name") if isinstance(mask_data, dict) else None
        
        return cls(
            value=conditioning_data.get("conditioning_name"),
            mask=mask_name
        )



class IvkFluxReduxConditioningField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    FLUX Redux conditioning field.
    
    Contains conditioning tensor and optional mask.
    
    Examples
    --------
    >>> field = IvkFluxReduxConditioningField()
    >>> field.conditioning = "conditioning-tensor-uuid"
    >>> field.mask = "mask-tensor-uuid"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    conditioning: Optional[str] = None  # TensorField reference
    mask: Optional[str] = None  # Optional TensorField reference

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        conditioning = data.pop('conditioning', None)
        mask = data.pop('mask', None)

        # Build value dict from components
        if value is None:
            value = {}
            if conditioning:
                value["conditioning"] = {"tensor_name": conditioning}
            if mask:
                value["mask"] = {"tensor_name": mask}

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            conditioning=conditioning,
            mask=mask,
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
        """Validate FLUX Redux conditioning."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "flux_redux_conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkFluxReduxConditioningField:
        """Create from API data."""
        redux_data = data.get("value", {})
        conditioning_data = redux_data.get("conditioning", {})
        mask_data = redux_data.get("mask", {})
        
        return cls(
            value=redux_data,
            conditioning=conditioning_data.get("tensor_name") if isinstance(conditioning_data, dict) else None,
            mask=mask_data.get("tensor_name") if isinstance(mask_data, dict) else None
        )



class IvkFluxFillConditioningField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    FLUX Fill conditioning field for inpainting.
    
    Contains image reference and mask tensor.
    
    Examples
    --------
    >>> field = IvkFluxFillConditioningField()
    >>> field.image = "image-uuid"
    >>> field.mask = "mask-tensor-uuid"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None  # ImageField reference
    mask: Optional[str] = None  # TensorField reference

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        image = data.pop('image', None)
        mask = data.pop('mask', None)

        # Build value dict from components
        if value is None:
            value = {}
            if image:
                value["image"] = {"image_name": image}
            if mask:
                value["mask"] = {"tensor_name": mask}

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            image=image,
            mask=mask,
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
        """Validate FLUX Fill conditioning."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "flux_fill_conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkFluxFillConditioningField:
        """Create from API data."""
        fill_data = data.get("value", {})
        image_data = fill_data.get("image", {})
        mask_data = fill_data.get("mask", {})
        
        return cls(
            value=fill_data,
            image=image_data.get("image_name") if isinstance(image_data, dict) else None,
            mask=mask_data.get("tensor_name") if isinstance(mask_data, dict) else None
        )



class IvkFluxKontextConditioningField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):
    """
    FLUX Kontext conditioning field.
    
    Contains reference image for Kontext conditioning.
    
    Examples
    --------
    >>> field = IvkFluxKontextConditioningField()
    >>> field.image = "reference-image-uuid"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[dict[str, Any]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None  # ImageField reference

    def __init__(self, **data: Any) -> None:
        """Initialize with Pydantic validation."""
        # Extract fields
        value = data.pop('value', None)
        name = data.pop('name', None)
        description = data.pop('description', None)
        image = data.pop('image', None)

        # Build value dict from components
        if value is None and image:
            value = {"image": {"image_name": image}}

        # Initialize BaseModel
        BaseModel.__init__(
            self,
            value=value,
            name=name,
            description=description,
            image=image,
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
        """Validate FLUX Kontext conditioning."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": self.value,
            "type": "flux_kontext_conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkFluxKontextConditioningField:
        """Create from API data."""
        kontext_data = data.get("value", {})
        image_data = kontext_data.get("image", {})
        
        return cls(
            value=kontext_data,
            image=image_data.get("image_name") if isinstance(image_data, dict) else None
        )



class IvkSD3ConditioningField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Stable Diffusion 3 conditioning field.
    
    Simplified conditioning for SD3 architecture.
    
    Examples
    --------
    >>> field = IvkSD3ConditioningField()
    >>> field.value = "sd3-conditioning-uuid"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None  # conditioning_name
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
        """Validate SD3 conditioning reference."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": {"conditioning_name": self.value} if self.value else None,
            "type": "sd3_conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkSD3ConditioningField:
        """Create from API data."""
        conditioning_data = data.get("value", {})
        return cls(value=conditioning_data.get("conditioning_name"))



class IvkCogView4ConditioningField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    CogView4 conditioning field.
    
    Conditioning for CogView4 architecture.
    
    Examples
    --------
    >>> field = IvkCogView4ConditioningField()
    >>> field.value = "cogview4-conditioning-uuid"
    """

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    value: Optional[str] = None  # conditioning_name
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
        """Validate CogView4 conditioning reference."""
        return True

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format."""
        return {
            "value": {"conditioning_name": self.value} if self.value else None,
            "type": "cogview4_conditioning"
        }

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> IvkCogView4ConditioningField:
        """Create from API data."""
        conditioning_data = data.get("value", {})
        return cls(value=conditioning_data.get("conditioning_name"))

