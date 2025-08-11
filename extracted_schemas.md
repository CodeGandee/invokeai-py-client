# Node Schema Extraction Results

## Nodes from example-nodes.json

The following node types were found in the example workflow:
- add
- flux_controlnet  
- flux_denoise
- denoise_latents
- image
- noise

## Extracted Schemas Using jq Commands

### 1. Add Node (Math Operation)
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "add")) | .[0].value' openapi.json
```

**Schema Summary:**
- **Title**: Add Integers
- **Category**: math
- **Version**: 1.0.1
- **Description**: Adds two numbers
- **Input Fields**:
  - `a`: integer (default: 0) - The first number
  - `b`: integer (default: 0) - The second number
- **Output**: IntegerOutput

### 2. FLUX ControlNet Node
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "flux_controlnet")) | .[0].value' openapi.json
```

**Schema Summary:**
- **Title**: FLUX ControlNet
- **Category**: controlnet
- **Version**: 1.0.0
- **Description**: Collect FLUX ControlNet info to pass to other nodes
- **Key Input Fields**:
  - `image`: ImageField - The control image
  - `control_model`: ModelIdentifierField - ControlNet model to load
  - `control_weight`: number/array (default: 1.0, range: -1 to 2) - Weight given to ControlNet
  - `begin_step_percent`: number (default: 0, range: 0-1) - When ControlNet is first applied
  - `end_step_percent`: number (default: 1, range: 0-1) - When ControlNet is last applied
  - `resize_mode`: enum (default: "just_resize") - The resize mode used
  - `instantx_control_mode`: integer (default: -1) - Control mode for InstantX ControlNet union models

### 3. FLUX Denoise Node (Complex)
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "flux_denoise")) | .[0].value' openapi.json
```

**Schema Summary:**
- **Title**: FLUX Denoise
- **Category**: image
- **Version**: 4.1.0
- **Description**: Run denoising process with a FLUX transformer model
- **Input Fields Count**: 21 fields
- **Key Input Fields**:
  - `transformer`: TransformerField (required) - Flux model to load
  - `positive_text_conditioning`: FluxConditioningField (required) - Positive conditioning tensor
  - `negative_text_conditioning`: FluxConditioningField - Negative conditioning tensor
  - `width`: integer (default: 1024, multiple of 16) - Width of generated image
  - `height`: integer (default: 1024, multiple of 16) - Height of generated image
  - `num_steps`: integer (default: 4) - Number of diffusion steps
  - `guidance`: number (default: 4.0) - Guidance strength
  - `cfg_scale`: number/array (default: 1.0) - Classifier-Free Guidance scale
  - `seed`: integer (default: 0) - Randomness seed

### 4. Denoise Latents Node (SD1.5/SDXL)
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "denoise_latents")) | .[0].value' openapi.json
```

**Schema Summary:**
- **Title**: Denoise - SD1.5, SDXL
- **Category**: latents
- **Version**: 1.5.4
- **Description**: Denoises noisy latents to decodable images
- **Input Fields**: 15 fields including:
  - `positive_conditioning`, `negative_conditioning`, `noise`, `steps`, `cfg_scale`, 
  - `denoising_start`, `denoising_end`, `scheduler`, `unet`, `control`, `ip_adapter`, 
  - `t2i_adapter`, `cfg_rescale_multiplier`, `latents`, `denoise_mask`

### 5. Image Primitive Node
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "image")) | .[0].value' openapi.json
```

**Schema Summary:**
- **Title**: Image Primitive
- **Category**: primitives
- **Version**: 1.0.2
- **Description**: An image primitive value
- **Input Fields**:
  - `image`: ImageField (required) - The image to load
- **Output**: ImageOutput

### 6. Noise Generation Node
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "noise")) | .[0].value' openapi.json
```

**Schema Summary:**
- **Title**: Create Latent Noise
- **Category**: latents  
- **Version**: 1.0.3
- **Description**: Generates latent noise
- **Input Fields**:
  - `seed`: integer (default: 0, range: 0-4294967295) - Seed for random number generation
  - `width`: integer (default: 512, multiple of 8) - Width of output (px)
  - `height`: integer (default: 512, multiple of 8) - Height of output (px)
  - `use_cpu`: boolean (default: true) - Use CPU for noise generation
- **Output**: NoiseOutput

## jq Command Patterns Used

### Basic Node Schema Extraction
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value' openapi.json
```

### Extract Only Input Fields
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value | {title, description, category, version, properties: (.properties | with_entries(select(.value.field_kind == "input")))}' openapi.json
```

### Get Input Field Names Only
```bash
jq '.components.schemas | to_entries | map(select(.value.properties.type.default == "NODE_TYPE")) | .[0].value | {title, description, category, version, input_fields: [.properties | to_entries[] | select(.value.field_kind == "input") | .key]}' openapi.json
```

### List All Available Node Types
```bash
jq '.components.schemas | to_entries | map(select(.key | endswith("Invocation"))) | map(.value.properties.type.default)' openapi.json
```

## Field Types Found

The extracted schemas reveal these common field types:
- **Primitive Types**: integer, number, boolean, string
- **Complex Types**: ImageField, ModelIdentifierField, TransformerField, LatentsField
- **Conditioning Types**: FluxConditioningField, ConditioningField
- **Control Types**: FluxControlNetField, ControlLoRAField
- **Array Types**: number[], FluxConditioningField[]

## Usage Notes

1. **Field Constraints**: Many fields have validation constraints (min/max, multiples, enums)
2. **Optional vs Required**: Fields marked with `orig_required: true` are required inputs
3. **Connection Types**: `input: "connection"` means the field expects data from another node
4. **Default Values**: Most fields provide sensible defaults for immediate use
5. **Version Tracking**: Each node schema includes a version for compatibility checking

## Source Code Locations

The following table maps each node to its implementation file in the InvokeAI source code:

| Node Type | Source File | Class Name | Key Features |
|-----------|-------------|------------|--------------|
| `add` | `invokeai/app/invocations/math.py` | `AddInvocation` | Simple integer addition with field validation |
| `flux_controlnet` | `invokeai/app/invocations/flux_controlnet.py` | `FluxControlNetInvocation` | FLUX ControlNet with weight validation and step control |
| `flux_denoise` | `invokeai/app/invocations/flux_denoise.py` | `FluxDenoiseInvocation` | Complex FLUX denoising with 21 input fields |
| `denoise_latents` | `invokeai/app/invocations/denoise_latents.py` | `DenoiseLatentsInvocation` | SD1.5/SDXL denoising with scheduler support |
| `image` | `invokeai/app/invocations/primitives.py` | `ImageInvocation` | Image primitive wrapper for field connections |
| `noise` | `invokeai/app/invocations/noise.py` | `NoiseInvocation` | Latent noise generation with seed control |

### Source Code Analysis

#### 1. Add Node (`math.py`)
```python
@invocation("add", title="Add Integers", tags=["math", "add"], category="math", version="1.0.1")
class AddInvocation(BaseInvocation):
    """Adds two numbers"""
    
    a: int = InputField(default=0, description=FieldDescriptions.num_1)
    b: int = InputField(default=0, description=FieldDescriptions.num_2)
    
    def invoke(self, context: InvocationContext) -> IntegerOutput:
        return IntegerOutput(value=self.a + self.b)
```

**Key Implementation Details:**
- Inherits from `BaseInvocation`
- Uses `InputField` for type validation and defaults
- Returns `IntegerOutput` with computed result
- Simple mathematical operation with no external dependencies

#### 2. FLUX ControlNet Node (`flux_controlnet.py`)
```python
@invocation(
    "flux_controlnet",
    title="FLUX ControlNet", 
    tags=["controlnet", "flux"],
    category="controlnet",
    version="1.0.0",
)
class FluxControlNetInvocation(BaseInvocation):
    """Collect FLUX ControlNet info to pass to other nodes."""
    
    # Complex field validation with custom validators
    @field_validator("control_weight")
    @classmethod
    def validate_control_weight(cls, v: float | list[float]) -> float | list[float]:
        validate_weights(v)
        return v
```

**Key Implementation Details:**
- Custom field validation for control weights
- Supports both single weights and weight arrays
- Step percentage validation with `validate_begin_end_step`
- Uses `ModelIdentifierField` for model selection
- Returns `FluxControlNetField` for downstream connections

#### 3. FLUX Denoise Node (`flux_denoise.py`)
```python
@invocation(
    "flux_denoise",
    title="FLUX Denoise",
    tags=["image", "flux"], 
    category="image",
    version="4.1.0",
)
class FluxDenoiseInvocation(BaseInvocation):
    """Run denoising process with a FLUX transformer model."""
    
    # 21 input fields including complex conditioning
    transformer: TransformerField = InputField(...)
    positive_text_conditioning: FluxConditioningField | list[FluxConditioningField] = InputField(...)
    cfg_scale: float | list[float] = InputField(default=1.0, ...)
```

**Key Implementation Details:**
- Most complex node with 21 input fields
- Supports advanced FLUX features (Redux, Fill, Kontext)
- Complex conditioning field types
- Image-to-image and inpainting support
- Extensive backend integration with FLUX sampling utils

#### 4. Denoise Latents Node (`denoise_latents.py`)
```python
@invocation(
    "denoise_latents",
    title="Denoise - SD1.5, SDXL",
    tags=["latents", "denoise", "txt2img", "t2i", "t2l", "img2img", "i2i", "l2l"],
    category="latents", 
    version="1.5.4",
)
class DenoiseLatentsInvocation(BaseInvocation):
    """Denoises noisy latents to decodable images"""
    
    # Supports both single and list conditioning
    positive_conditioning: Union[ConditioningField, list[ConditioningField]] = InputField(...)
    scheduler: SCHEDULER_NAME_VALUES = InputField(default="euler", ...)
```

**Key Implementation Details:**
- Supports SD 1.5, SD 2.x, and SDXL models
- Complex scheduler integration with validation
- ControlNet and IP-Adapter support
- Extensive CFG scale handling
- Integration with diffusers pipeline

#### 5. Image Primitive Node (`primitives.py`)
```python
@invocation("image", title="Image Primitive", tags=["primitives", "image"], category="primitives", version="1.0.2")
class ImageInvocation(BaseInvocation):
    """An image primitive value"""
    
    image: ImageField = InputField(description="The image to load")
    
    def invoke(self, context: InvocationContext) -> ImageOutput:
        image_dto = context.images.get_dto(self.image.image_name)
        return ImageOutput.build(image_dto=image_dto)
```

**Key Implementation Details:**
- Simple wrapper for image field connections
- Uses context.images service for image retrieval
- Returns `ImageOutput` with image DTO
- Essential for image workflow connectivity

#### 6. Noise Generation Node (`noise.py`)
```python
@invocation(
    "noise",
    title="Create Latent Noise",
    tags=["latents", "noise"],
    category="latents",
    version="1.0.3", 
)
class NoiseInvocation(BaseInvocation):
    """Generates latent noise."""
    
    @field_validator("seed", mode="before")
    def modulo_seed(cls, v):
        """Return the seed modulo (SEED_MAX + 1) to ensure it is within the valid range."""
        return v % (SEED_MAX + 1)
```

**Key Implementation Details:**
- Seed validation with modulo operation
- Cross-platform reproducibility with `use_cpu` option
- Integration with tensor storage via `context.tensors.save`
- Width/height validation with `LATENT_SCALE_FACTOR`
- Uses backend `get_noise` utility function

### Implementation Patterns

All InvokeAI nodes follow consistent patterns:

1. **Decorator Pattern**: `@invocation()` with metadata (type, title, tags, category, version)
2. **Field Validation**: Pydantic `InputField` and `OutputField` with constraints
3. **Context Integration**: Access to services via `InvocationContext`
4. **Type Safety**: Strong typing with Union types for flexibility
5. **Version Management**: Semantic versioning for schema evolution
6. **Service Integration**: Use of context services (images, tensors, models, etc.)

These patterns ensure consistency, maintainability, and extensibility across the entire InvokeAI invocation system.
