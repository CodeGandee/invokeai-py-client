"""
InvokeAI field types for workflow construction.

This module provides a comprehensive set of field types for building
InvokeAI workflows with type safety and validation.

The field system is organized into several categories:

Base Classes
------------
- IvkField: Base class for all field types
- IvkImageFieldMixin: Mixin for image upload/download operations
- IvkCollectionFieldMixin: Mixin for collection manipulation

Primitive Types
---------------
- IvkStringField: String values with length/pattern validation
- IvkIntegerField: Integer values with range/multiple constraints
- IvkFloatField: Float values with range constraints
- IvkBooleanField: Boolean true/false values

Resource References
-------------------
- IvkImageField: Image references and uploads
- IvkBoardField: Board destinations for outputs
- IvkLatentsField: Latent tensor references
- IvkTensorField: Generic tensor references
- IvkDenoiseMaskField: Inpainting mask configurations
- IvkMetadataField: Arbitrary metadata key-value pairs

Model References
----------------
- IvkModelIdentifierField: Generic model references
- IvkUNetField: UNet model with configuration
- IvkCLIPField: CLIP text encoder configuration
- IvkTransformerField: Transformer model (FLUX)
- IvkLoRAField: LoRA model with weight

Model Aliases
-------------
- IvkSDXLModelField: SDXL main model alias
- IvkFluxModelField: FLUX main model alias
- IvkT5EncoderField: T5 text encoder alias
- IvkCLIPEmbedField: CLIP embedding alias
- IvkVAEModelField: VAE model alias

Conditioning Types
------------------
- IvkConditioningField: Standard SD conditioning
- IvkFluxConditioningField: FLUX conditioning
- IvkFluxReduxConditioningField: FLUX Redux conditioning
- IvkFluxFillConditioningField: FLUX Fill/inpainting
- IvkFluxKontextConditioningField: FLUX Kontext reference
- IvkSD3ConditioningField: Stable Diffusion 3 conditioning
- IvkCogView4ConditioningField: CogView4 conditioning

Complex Types
-------------
- IvkColorField: RGBA color with hex/component access
- IvkBoundingBoxField: Rectangular regions with confidence
- IvkCollectionField: Typed collections with constraints

Enum & Choice Types
-------------------
- IvkEnumField: Generic enum with custom choices
- IvkSchedulerField: InvokeAI scheduler selection
- IvkInterpolationField: Image interpolation modes
- IvkColorModeField: Image color mode selection
- IvkLiteralField: Compile-time literal choices

Examples
--------
>>> from invokeai_py_client.ivk_fields import IvkStringField, IvkIntegerField
>>> 
>>> # Create a string field with validation
>>> prompt_field = IvkStringField(min_length=1, max_length=1000)
>>> prompt_field.value = "A beautiful landscape"
>>> 
>>> # Create an integer field with constraints
>>> width_field = IvkIntegerField(minimum=64, maximum=2048, multiple_of=8)
>>> width_field.value = 1024
>>> 
>>> # Use in workflow construction
>>> workflow_inputs = [
>>>     {"field": prompt_field, "index": 0},
>>>     {"field": width_field, "index": 1}
>>> ]
"""

# Base classes
from invokeai_py_client.ivk_fields.base import (
    IvkField,
    IvkImageFieldMixin,
    IvkCollectionFieldMixin,
)

# Primitive types
from invokeai_py_client.ivk_fields.primitives import (
    IvkStringField,
    IvkIntegerField,
    IvkFloatField,
    IvkBooleanField,
)

# Resource reference types
from invokeai_py_client.ivk_fields.resources import (
    IvkImageField,
    IvkBoardField,
    IvkLatentsField,
    IvkTensorField,
    IvkDenoiseMaskField,
    IvkMetadataField,
)

# Model reference types
from invokeai_py_client.ivk_fields.models import (
    IvkModelIdentifierField,
    IvkUNetField,
    IvkCLIPField,
    IvkTransformerField,
    IvkLoRAField,
    # Model aliases
    IvkSDXLModelField,
    IvkFluxModelField,
    IvkT5EncoderField,
    IvkCLIPEmbedField,
    IvkVAEModelField,
)

# Conditioning types
from invokeai_py_client.ivk_fields.conditioning import (
    IvkConditioningField,
    IvkFluxConditioningField,
    IvkFluxReduxConditioningField,
    IvkFluxFillConditioningField,
    IvkFluxKontextConditioningField,
    IvkSD3ConditioningField,
    IvkCogView4ConditioningField,
)

# Complex types
from invokeai_py_client.ivk_fields.complex import (
    IvkColorField,
    IvkBoundingBoxField,
    IvkCollectionField,
)

# Enum and choice types
from invokeai_py_client.ivk_fields.enums import (
    IvkEnumField,
    IvkSchedulerField,
    IvkInterpolationField,
    IvkColorModeField,
    IvkLiteralField,
    # Constants
    SchedulerName,
    SCHEDULER_NAMES,
    INTERPOLATION_MODES,
    COLOR_MODES,
)

# Explicit __all__ for controlled public API
__all__ = [
    # Base classes
    "IvkField",
    "IvkImageFieldMixin", 
    "IvkCollectionFieldMixin",
    
    # Primitive types
    "IvkStringField",
    "IvkIntegerField", 
    "IvkFloatField",
    "IvkBooleanField",
    
    # Resource reference types
    "IvkImageField",
    "IvkBoardField",
    "IvkLatentsField",
    "IvkTensorField",
    "IvkDenoiseMaskField", 
    "IvkMetadataField",
    
    # Model reference types
    "IvkModelIdentifierField",
    "IvkUNetField",
    "IvkCLIPField",
    "IvkTransformerField",
    "IvkLoRAField",
    
    # Model aliases
    "IvkSDXLModelField",
    "IvkFluxModelField",
    "IvkT5EncoderField",
    "IvkCLIPEmbedField",
    "IvkVAEModelField",
    
    # Conditioning types
    "IvkConditioningField",
    "IvkFluxConditioningField",
    "IvkFluxReduxConditioningField",
    "IvkFluxFillConditioningField",
    "IvkFluxKontextConditioningField",
    "IvkSD3ConditioningField", 
    "IvkCogView4ConditioningField",
    
    # Complex types
    "IvkColorField",
    "IvkBoundingBoxField",
    "IvkCollectionField",
    
    # Enum and choice types
    "IvkEnumField",
    "IvkSchedulerField",
    "IvkInterpolationField",
    "IvkColorModeField",
    "IvkLiteralField",
    
    # Constants
    "SchedulerName",
    "SCHEDULER_NAMES",
    "INTERPOLATION_MODES",
    "COLOR_MODES",
]