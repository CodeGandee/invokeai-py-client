# InvokeAI Workflow Input Types Reference

A comprehensive guide to all input field types available in InvokeAI workflows for developers building Python clients and custom nodes.

## Overview

InvokeAI uses a strongly-typed field system built on Pydantic for workflow nodes. Each field type has specific validation rules, connection requirements, and serialization formats that Python clients must understand to properly construct and execute workflows.

## Primitive Input Types

### Basic Types

These fundamental types use Python's built-in types with pydantic validation via `InputField()`:

**Integer Fields**
```python
width: int = InputField(default=512, ge=64, le=2048, description="Width of image")
steps: int = InputField(default=50, gt=0, le=100, description="Number of steps")
```
- **Constraints**: `ge` (≥), `le` (≤), `gt` (>), `lt` (<), `multiple_of`
- **JSON Format**: `{"width": 1024, "steps": 25}`

**Float Fields**
```python
strength: float = InputField(default=0.8, ge=0.0, le=1.0, description="Denoising strength")
scale: float = InputField(default=1.0, gt=0.0, description="Scale factor")
```
- **Constraints**: Same as integers, plus `decimal_places`
- **JSON Format**: `{"strength": 0.75, "scale": 2.5}`

**Boolean Fields**
```python
add_noise: bool = InputField(default=True, description="Add noise based on denoising start")
crop: bool = InputField(default=False, description="Crop to base image dimensions")
```
- **JSON Format**: `{"add_noise": true, "crop": false}`

**String Fields**
```python
prompt: str = InputField(default="", description="Text prompt")
label: str = InputField(max_length=255, description="Node label")
```
- **Constraints**: `min_length`, `max_length`, `pattern` (regex)
- **JSON Format**: `{"prompt": "a beautiful landscape", "label": "my-node"}`

### Complex Primitive Types

**ColorField**
```python
color: ColorField = InputField(default=ColorField(r=0, g=0, b=0, a=255), description="RGBA color")
```
- **Structure**: `{"r": int, "g": int, "b": int, "a": int}` (0-255 range)
- **JSON Format**: `{"color": {"r": 255, "g": 128, "b": 0, "a": 255}}`

**BoundingBoxField**
```python
bbox: BoundingBoxField = InputField(description="Region of interest")
```
- **Structure**: `{"x_min": int, "x_max": int, "y_min": int, "y_max": int, "score": Optional[float]}`
- **JSON Format**: `{"bbox": {"x_min": 100, "x_max": 400, "y_min": 50, "y_max": 300, "score": 0.95}}`

## Resource Reference Types

### Image and Data Fields

**ImageField**
```python
image: ImageField = InputField(description="Input image")
mask: Optional[ImageField] = InputField(default=None, description="Optional mask")
```
- **Structure**: `{"image_name": str}` - References image by UUID filename
- **JSON Format**: `{"image": {"image_name": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv.png"}}`

**LatentsField**
```python
latents: LatentsField = InputField(description="Latent tensor")
```
- **Structure**: `{"latents_name": str, "seed": Optional[int]}`
- **JSON Format**: `{"latents": {"latents_name": "latents_uuid", "seed": 42}}`

**TensorField**
```python
conditioning: TensorField = InputField(description="Conditioning tensor")
```
- **Structure**: `{"tensor_name": str}` - References tensor by UUID
- **JSON Format**: `{"conditioning": {"tensor_name": "tensor_uuid"}}`

**DenoiseMaskField**
```python
denoise_mask: DenoiseMaskField = InputField(description="Inpainting mask")
```
- **Structure**: `{"mask_name": str, "masked_latents_name": Optional[str], "gradient": bool}`
- **JSON Format**: `{"denoise_mask": {"mask_name": "mask_uuid", "gradient": false}}`

**BoardField**
```python
board: BoardField = InputField(description="Board to save to")
```
- **Structure**: `{"board_id": str}` - References board by UUID
- **JSON Format**: `{"board": {"board_id": "board-uuid-here"}}`

## Model Reference Types

InvokeAI uses sophisticated model reference fields that include model identification, configuration, and dependencies:

**ModelIdentifierField**
```python
model: ModelIdentifierField = InputField(description="Any model reference")
```
- **Structure**: `{"key": str, "hash": str, "name": str, "base": BaseModelType, "type": ModelType, "submodel_type": Optional[SubModelType]}`
- **JSON Format**: 
```json
{
  "model": {
    "key": "sdxl-base-1.0",
    "hash": "abc123def456...",
    "name": "Stable Diffusion XL Base 1.0",
    "base": "sdxl",
    "type": "main",
    "submodel_type": null
  }
}
```

**UNetField**
```python
unet: UNetField = InputField(description="UNet model with configuration")
```
- **Structure**: Includes UNet model, scheduler, LoRAs, seamless axes, FreeU config
- **JSON Format**:
```json
{
  "unet": {
    "unet": {"key": "...", "hash": "...", "name": "...", "base": "sdxl", "type": "main"},
    "scheduler": {"key": "...", "hash": "...", "name": "...", "base": "any", "type": "scheduler"},
    "loras": [{"lora": {...}, "weight": 0.8}],
    "seamless_axes": ["x", "y"],
    "freeu_config": null
  }
}
```

**CLIPField**
```python
clip: CLIPField = InputField(description="CLIP model with configuration")
```
- **Structure**: Tokenizer, text encoder, skipped layers, LoRAs
- **JSON Format**:
```json
{
  "clip": {
    "tokenizer": {...},
    "text_encoder": {...},
    "skipped_layers": 0,
    "loras": []
  }
}
```

**TransformerField**
```python
transformer: TransformerField = InputField(description="FLUX Transformer model")
```
- **Structure**: `{"transformer": ModelIdentifierField, "loras": List[LoRAField]}`

## Conditioning Types

InvokeAI supports multiple conditioning systems for different model architectures:

**ConditioningField** (Standard SD)
```python
positive_conditioning: ConditioningField = InputField(description="Positive conditioning")
```
- **Structure**: `{"conditioning_name": str, "mask": Optional[TensorField]}`
- **JSON Format**: `{"conditioning": {"conditioning_name": "conditioning_uuid", "mask": null}}`

**FluxConditioningField** (FLUX Models)
```python
positive_text_conditioning: FluxConditioningField = InputField(description="FLUX text conditioning")
```
- **Structure**: Same as ConditioningField but for FLUX architecture
- **JSON Format**: `{"conditioning": {"conditioning_name": "flux_conditioning_uuid", "mask": null}}`

**FluxReduxConditioningField** (FLUX Redux)
```python
redux_conditioning: FluxReduxConditioningField = InputField(description="FLUX Redux conditioning")
```
- **Structure**: `{"conditioning": TensorField, "mask": Optional[TensorField]}`

**FluxFillConditioningField** (FLUX Fill/Inpainting)
```python
fill_conditioning: FluxFillConditioningField = InputField(description="FLUX Fill conditioning")
```
- **Structure**: `{"image": ImageField, "mask": TensorField}`

**FluxKontextConditioningField** (FLUX Kontext)
```python
kontext_conditioning: FluxKontextConditioningField = InputField(description="FLUX Kontext reference")
```
- **Structure**: `{"image": ImageField}` - Reference image for Kontext

**SD3ConditioningField** (Stable Diffusion 3)
```python
sd3_conditioning: SD3ConditioningField = InputField(description="SD3 conditioning")
```
- **Structure**: `{"conditioning_name": str}` - Simplified for SD3

**CogView4ConditioningField** (CogView4)
```python
cogview4_conditioning: CogView4ConditioningField = InputField(description="CogView4 conditioning")
```
- **Structure**: `{"conditioning_name": str}` - CogView4 specific

## Collection Types

InvokeAI supports collections (lists) of most field types:

**Primitive Collections**
```python
values: list[int] = InputField(default=[], description="Collection of integers")
labels: list[str] = InputField(default=[], description="Collection of strings")
flags: list[bool] = InputField(default=[], description="Collection of booleans")
```

**Object Collections**
```python
images: list[ImageField] = InputField(default=[], description="Multiple images")
loras: list[LoRAField] = InputField(default=[], description="Multiple LoRAs")
conditioning: list[FluxConditioningField] = InputField(description="Multiple conditioning")
```
- **JSON Format**: `{"images": [{"image_name": "img1.png"}, {"image_name": "img2.png"}]}`

## Enum and Choice Types

**Literal Types**
```python
mode: Literal["RGB", "RGBA"] = InputField(default="RGB", description="Color mode")
interpolation: Literal["nearest", "linear", "bilinear", "bicubic"] = InputField(default="bilinear")
```
- **JSON Format**: `{"mode": "RGBA", "interpolation": "bicubic"}`

**Scheduler Enums**
```python
scheduler: SCHEDULER_NAME_VALUES = InputField(default="euler", ui_type=UIType.Scheduler)
```
- **Values**: `"ddim", "ddpm", "deis", "dpm_2", "dpm_2_ancestral", "dpm_multi", "dpm_sde", "dpm_sde_k", "euler", "euler_ancestral", "euler_k", "heun", "lms", "pndm", "unipc"`

## Advanced Field Features

### Connection Types

Fields can specify how they receive values:

```python
# Must be provided directly in workflow JSON
direct_field: int = InputField(default=512, input=Input.Direct)

# Must be connected from another node's output
connected_field: ImageField = InputField(input=Input.Connection)

# Can be either direct or connected (default)
flexible_field: float = InputField(default=0.8, input=Input.Any)
```

### UI Hints

**UI Type Hints**
```python
model: ModelIdentifierField = InputField(ui_type=UIType.SDXLMainModel)
scheduler: SCHEDULER_NAME_VALUES = InputField(ui_type=UIType.Scheduler)
```

**UI Components**
```python
prompt: str = InputField(ui_component=UIComponent.Textarea)
value: float = InputField(ui_component=UIComponent.Slider)
```

**UI Ordering**
```python
width: int = InputField(ui_order=1)
height: int = InputField(ui_order=2)
```

### Validation Constraints

**Numeric Constraints**
```python
width: int = InputField(ge=64, le=4096, multiple_of=8)  # 64 ≤ width ≤ 4096, divisible by 8
strength: float = InputField(gt=0.0, lt=1.0, decimal_places=3)  # 0 < strength < 1, max 3 decimals
```

**String Constraints**
```python
name: str = InputField(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
```

## Metadata and Board Integration

**WithMetadata Mixin**
```python
class MyInvocation(BaseInvocation, WithMetadata):
    # Automatically adds metadata: Optional[MetadataField] field
```
- **Structure**: `{"metadata": {"key": "value", ...}}` - Arbitrary key-value pairs

**WithBoard Mixin**
```python
class MyInvocation(BaseInvocation, WithBoard):
    # Automatically adds board: Optional[BoardField] field
```

## Special Field Types

**MetadataField**
```python
metadata: MetadataField = InputField(description="Custom metadata")
```
- **Structure**: `dict[str, Any]` - Arbitrary JSON object
- **JSON Format**: `{"metadata": {"custom_field": "value", "another": 42}}`

**Union Types**
```python
conditioning: FluxConditioningField | list[FluxConditioningField] = InputField(
    description="Single or multiple conditioning"
)
```

## Node Definition Patterns

**Basic Input Node**
```python
@invocation("my_node", title="My Node", tags=["custom"], category="custom", version="1.0.0")
class MyNodeInvocation(BaseInvocation):
    # Required input
    image: ImageField = InputField(description="Input image")
    
    # Optional with default
    strength: float = InputField(default=0.8, ge=0.0, le=1.0)
    
    # Connection-only input
    latents: LatentsField = InputField(input=Input.Connection)
    
    def invoke(self, context: InvocationContext) -> MyNodeOutput:
        # Implementation here
        pass
```

**With Mixins**
```python
@invocation("save_node", title="Save Node", category="image", version="1.0.0")
class SaveNodeInvocation(BaseInvocation, WithMetadata, WithBoard):
    image: ImageField = InputField(description="Image to save")
    # metadata and board fields automatically added
```

## Best Practices for Python Clients

1. **Type Safety**: Use proper type hints matching InvokeAI's field definitions
2. **Validation**: Implement client-side validation using pydantic constraints
3. **Connection Graph**: Track field dependencies when building workflow graphs
4. **Resource Management**: Handle image/tensor/model references properly
5. **Error Handling**: Validate field constraints before sending to InvokeAI API

## OpenAPI Integration

All these field types are reflected in InvokeAI's OpenAPI schema. For dynamic client generation:

```python
# Get schema for specific node
schema = requests.get("http://localhost:9090/openapi.json").json()
node_schema = schema["components"]["schemas"]["FluxDenoiseInvocation"]

# Extract input fields
for field_name, field_def in node_schema["properties"].items():
    if field_def.get("field_kind") == "input":
        # Process field definition for client generation
        pass
```

## Source References

- **Field Definitions**: `invokeai/app/invocations/fields.py`
- **Base Classes**: `invokeai/app/invocations/baseinvocation.py`
- **Primitive Types**: `invokeai/app/invocations/primitives.py`
- **Model Types**: `invokeai/app/invocations/model.py`
- **Usage Examples**: All `*.py` files in `invokeai/app/invocations/`

This comprehensive reference covers all input types available in InvokeAI workflows as of version 3.x and above, providing Python client developers with the complete type system specification needed for proper workflow construction and execution.