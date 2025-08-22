# Field Types

Complete reference for all field types in the InvokeAI Python Client.

## Field Type System

The client uses strongly-typed field classes that provide validation and type safety. All fields inherit from `IvkField[T]` base class.

## Field Categories

### Fields WITH `.value` Property
- Primitive types (String, Integer, Float, Boolean)
- Resource references (Image, Board, Latents, Tensor)
- Collections
- Enumerations

### Fields WITHOUT `.value` Property
- Model fields (use `key`, `hash`, `name`, `base`, `type`)
- Color fields (use `r`, `g`, `b`, `a`)
- BoundingBox fields (use `x_min`, `x_max`, `y_min`, `y_max`)

## Primitive Fields

### IvkStringField

Text input fields for prompts, descriptions, etc.

```python
from invokeai_py_client.ivk_fields import IvkStringField

# Get string field
prompt = wf.get_input_value(0)
if isinstance(prompt, IvkStringField):
    # Set value
    prompt.value = "A beautiful landscape"
    
    # Get value
    text = prompt.value
    
    # Validation
    prompt.min_length = 1
    prompt.max_length = 1000
    prompt.validate_field()
```

### IvkIntegerField

Whole number inputs for steps, dimensions, seeds.

```python
from invokeai_py_client.ivk_fields import IvkIntegerField

# Integer field with constraints
steps = wf.get_input_value(4)
if isinstance(steps, IvkIntegerField):
    # Set value
    steps.value = 30
    
    # Constraints
    steps.min_value = 1
    steps.max_value = 150
    
    # Validation happens automatically
    try:
        steps.value = 200  # Raises ValueError if > max
    except ValueError as e:
        print(f"Invalid: {e}")
```

### IvkFloatField

Decimal number inputs for scales, strengths, ratios.

```python
from invokeai_py_client.ivk_fields import IvkFloatField

# Float field
cfg_scale = wf.get_input_value(5)
if isinstance(cfg_scale, IvkFloatField):
    # Set value
    cfg_scale.value = 7.5
    
    # Constraints
    cfg_scale.min_value = 1.0
    cfg_scale.max_value = 20.0
    
    # Precision
    cfg_scale.value = round(user_input, 2)
```

### IvkBooleanField

True/False checkbox inputs.

```python
from invokeai_py_client.ivk_fields import IvkBooleanField

# Boolean field
enable_hires = wf.get_input_value(8)
if isinstance(enable_hires, IvkBooleanField):
    # Set value
    enable_hires.value = True
    
    # Toggle
    enable_hires.value = not enable_hires.value
```

## Resource Reference Fields

### IvkImageField

References to images by name/ID.

```python
from invokeai_py_client.ivk_fields import IvkImageField

# Image field for image-to-image
source_image = wf.get_input_value(1)
if isinstance(source_image, IvkImageField):
    # Upload image first
    board = client.board_repo.get_board_handle("inputs")
    image_name = board.upload_image_file("source.png")
    
    # Set reference
    source_image.value = image_name
    
    # The value is just the name, not the actual image data
    print(f"Using image: {source_image.value}")
```

### IvkBoardField

Board selection for output routing.

```python
from invokeai_py_client.ivk_fields import IvkBoardField

# Board field
output_board = wf.get_input_value(10)
if isinstance(output_board, IvkBoardField):
    # List available boards
    boards = client.board_repo.list_boards()
    
    # Set by board ID
    output_board.value = "board_abc123"
    
    # Or use uncategorized
    output_board.value = "none"
```

### IvkLatentsField

References to latent tensors (internal use).

```python
from invokeai_py_client.ivk_fields import IvkLatentsField

# Latents field (rarely set directly)
latents = wf.get_input_value(15)
if isinstance(latents, IvkLatentsField):
    # Usually connected internally
    latents.value = "latents_ref_123"
```

### IvkTensorField

References to tensor data (internal use).

```python
from invokeai_py_client.ivk_fields import IvkTensorField

# Tensor field
tensor = wf.get_input_value(16)
if isinstance(tensor, IvkTensorField):
    tensor.value = "tensor_ref_456"
```

## Model Fields

Model fields don't use `.value` property. They have specific attributes.

### IvkModelIdentifierField

Complete model identification.

```python
from invokeai_py_client.ivk_fields import IvkModelIdentifierField

# Model identifier field
model = wf.get_input_value(0)
if isinstance(model, IvkModelIdentifierField):
    # Set model attributes
    model.key = "stable-diffusion-xl-base"
    model.hash = "abc123..."
    model.name = "SDXL Base 1.0"
    model.base = "sdxl"
    model.type = "main"
    
    # Or sync with server
    wf.sync_dnn_model(field_indices=[0])
```

### IvkUNetField

UNet model selection.

```python
from invokeai_py_client.ivk_fields import IvkUNetField

# UNet field
unet = wf.get_input_value(1)
if isinstance(unet, IvkUNetField):
    unet.key = "sdxl-unet"
    unet.name = "SDXL UNet"
```

### IvkCLIPField

CLIP text encoder selection.

```python
from invokeai_py_client.ivk_fields import IvkCLIPField

# CLIP field
clip = wf.get_input_value(2)
if isinstance(clip, IvkCLIPField):
    clip.key = "sdxl-clip"
    clip.name = "SDXL CLIP"
```

### IvkTransformerField

Transformer model selection (FLUX).

```python
from invokeai_py_client.ivk_fields import IvkTransformerField

# Transformer field
transformer = wf.get_input_value(0)
if isinstance(transformer, IvkTransformerField):
    transformer.key = "flux-transformer"
    transformer.name = "FLUX Transformer"
```

### IvkLoRAField

LoRA model selection.

```python
from invokeai_py_client.ivk_fields import IvkLoRAField

# LoRA field
lora = wf.get_input_value(5)
if isinstance(lora, IvkLoRAField):
    lora.key = "my-style-lora"
    lora.name = "My Style LoRA"
    lora.weight = 0.8  # LoRA weight if supported
```

## Complex Fields

### IvkColorField

Color selection (no `.value` property).

```python
from invokeai_py_client.ivk_fields import IvkColorField

# Color field
color = wf.get_input_value(7)
if isinstance(color, IvkColorField):
    # Set RGBA components
    color.r = 255
    color.g = 128
    color.b = 0
    color.a = 255
    
    # From hex
    def set_from_hex(color_field, hex_str):
        hex_str = hex_str.lstrip('#')
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        color_field.r = r
        color_field.g = g
        color_field.b = b
    
    set_from_hex(color, "#FF8000")
```

### IvkBoundingBoxField

Rectangular area definition (no `.value` property).

```python
from invokeai_py_client.ivk_fields import IvkBoundingBoxField

# Bounding box field
bbox = wf.get_input_value(9)
if isinstance(bbox, IvkBoundingBoxField):
    # Set bounds
    bbox.x_min = 100
    bbox.y_min = 100
    bbox.x_max = 400
    bbox.y_max = 300
    
    # Calculate dimensions
    width = bbox.x_max - bbox.x_min
    height = bbox.y_max - bbox.y_min
    print(f"Box size: {width}x{height}")
```

### IvkCollectionField

List/array fields.

```python
from invokeai_py_client.ivk_fields import IvkCollectionField

# Collection field
collection = wf.get_input_value(11)
if isinstance(collection, IvkCollectionField):
    # Set list value
    collection.value = ["item1", "item2", "item3"]
    
    # Append items
    if collection.value is None:
        collection.value = []
    collection.value.append("new_item")
    
    # Get count
    count = len(collection.value)
```

## Enumeration Fields

### IvkEnumField

Predefined option selection.

```python
from invokeai_py_client.ivk_fields import IvkEnumField

# Enum field (e.g., scheduler)
scheduler = wf.get_input_value(7)
if isinstance(scheduler, IvkEnumField):
    # Set from options
    scheduler.value = "euler"
    
    # Get available options
    if hasattr(scheduler, 'options'):
        print(f"Available: {scheduler.options}")
    
    # Validate choice
    if scheduler.value not in scheduler.options:
        print(f"Invalid option: {scheduler.value}")
```

### SchedulerName Enum

Common scheduler enumeration.

```python
from invokeai_py_client.ivk_fields import SchedulerName

# Using scheduler enum
scheduler = wf.get_input_value(7)
if hasattr(scheduler, 'value'):
    # Set using enum
    scheduler.value = SchedulerName.EULER_A.value
    
    # Available schedulers
    for sched in SchedulerName:
        print(f"- {sched.value}")
```

## Field Validation

### Validation Methods

```python
# All fields support validation
field = wf.get_input_value(0)

# Explicit validation
try:
    field.validate_field()
    print("Valid")
except ValueError as e:
    print(f"Invalid: {e}")

# Validation on assignment (automatic)
try:
    field.value = invalid_value
except ValueError as e:
    print(f"Rejected: {e}")
```

### Custom Validation

```python
def validate_prompt(prompt_field):
    """Custom prompt validation."""
    if not isinstance(prompt_field, IvkStringField):
        return False
    
    value = prompt_field.value
    if not value:
        return False
    
    # Check length
    if len(value) < 3:
        raise ValueError("Prompt too short")
    
    # Check for banned words
    banned = ['nsfw', 'explicit']
    for word in banned:
        if word in value.lower():
            raise ValueError(f"Banned word: {word}")
    
    return True
```

## Type Conversion

### Field to API Format

```python
# Convert field to API format
field = wf.get_input_value(0)
api_data = field.to_api_format()
print(f"API format: {api_data}")
```

### Field to JSON

```python
# Serialize field
field = wf.get_input_value(0)
json_data = field.to_json_dict()

# Deserialize
from invokeai_py_client.ivk_fields import IvkStringField
restored = IvkStringField.from_json_dict(json_data)
```

## Working with Unknown Fields

```python
def handle_field(wf, index):
    """Handle any field type."""
    field = wf.get_input_value(index)
    
    # Check for value property
    if hasattr(field, 'value'):
        print(f"Field with value: {field.value}")
        # Safe to use .value
    else:
        # Check for specific attributes
        if hasattr(field, 'key'):
            print(f"Model field: {field.key}")
        elif hasattr(field, 'r'):
            print(f"Color field: rgb({field.r},{field.g},{field.b})")
        elif hasattr(field, 'x_min'):
            print(f"BBox field: ({field.x_min},{field.y_min})")
        else:
            print(f"Unknown field type: {type(field)}")
```

## Field Type Detection

```python
from invokeai_py_client.ivk_fields import (
    IvkStringField, IvkIntegerField, IvkFloatField,
    IvkBooleanField, IvkImageField, IvkModelIdentifierField
)

def detect_field_type(field):
    """Detect and return field type name."""
    type_map = {
        IvkStringField: "String",
        IvkIntegerField: "Integer",
        IvkFloatField: "Float",
        IvkBooleanField: "Boolean",
        IvkImageField: "Image",
        IvkModelIdentifierField: "Model"
    }
    
    for field_class, name in type_map.items():
        if isinstance(field, field_class):
            return name
    
    return "Unknown"

# Use it
for inp in wf.list_inputs():
    field = wf.get_input_value(inp.input_index)
    field_type = detect_field_type(field)
    print(f"[{inp.input_index}] {inp.label}: {field_type}")
```

## Best Practices

### 1. Type Checking

Always check field type before operations:

```python
field = wf.get_input_value(index)
if isinstance(field, IvkIntegerField):
    field.value = 30
elif isinstance(field, IvkStringField):
    field.value = "text"
else:
    print(f"Unexpected type: {type(field)}")
```

### 2. Null Handling

```python
field = wf.get_input_value(index)
if hasattr(field, 'value'):
    # Check for None
    if field.value is None:
        field.value = get_default_value()
```

### 3. Constraint Respect

```python
# Respect field constraints
def safe_set_integer(field, value):
    if not isinstance(field, IvkIntegerField):
        return False
    
    # Clamp to constraints
    if hasattr(field, 'min_value'):
        value = max(value, field.min_value)
    if hasattr(field, 'max_value'):
        value = min(value, field.max_value)
    
    field.value = value
    return True
```

## Field Examples by Use Case

### Text Generation

```python
# Positive prompt
positive = wf.get_input_value(0)
positive.value = "A majestic mountain landscape"

# Negative prompt
negative = wf.get_input_value(1)
negative.value = "blurry, low quality, distorted"
```

### Image Dimensions

```python
# Width and height
width = wf.get_input_value(2)
width.value = 1024

height = wf.get_input_value(3)
height.value = 1024

# Aspect ratio helper
def set_aspect_ratio(wf, width_idx, height_idx, ratio="16:9"):
    ratios = {
        "16:9": (1920, 1080),
        "4:3": (1024, 768),
        "1:1": (1024, 1024),
        "9:16": (1080, 1920)
    }
    w, h = ratios.get(ratio, (1024, 1024))
    wf.get_input_value(width_idx).value = w
    wf.get_input_value(height_idx).value = h
```

### Sampling Parameters

```python
# Steps
steps = wf.get_input_value(4)
steps.value = 30

# CFG Scale
cfg = wf.get_input_value(5)
cfg.value = 7.5

# Seed
seed = wf.get_input_value(6)
seed.value = 42  # Or -1 for random
```

## Next Steps

- Learn about [Board Management](boards.md) for image organization
- Explore [Image Operations](images.md) for upload/download
- Understand [Model Management](models.md)
- Master [Execution Modes](execution-modes.md)