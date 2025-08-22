# Fields API

Comprehensive reference for the typed field system used by workflow inputs, providing type-safe input handling with Pydantic validation and API format conversion. Key implementations include [`base`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L30){:target="_blank"} classes and mixins, [`primitives`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/primitives.py#L17){:target="_blank"} (string, int, float, bool), [`resources`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/resources.py#L21){:target="_blank"} (image, board, latents), [`models`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/models.py#L18){:target="_blank"} (UNet, CLIP, etc.), [`complex`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/complex.py#L20){:target="_blank"} (color, bbox, collections), and [`enums`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/enums.py#L79){:target="_blank"} (scheduler choices). All field classes are default-constructable; simple fields use a `.value` attribute while structured fields embed configuration directly, with API conversion handled automatically via `.to_api_format()`.

## Field System Architecture

The InvokeAI field system provides type-safe workflow input handling with Pydantic validation and API format conversion.

### Base Class: `IvkField[T]`

```python
class IvkField(Generic[T]):
```

Base class for all InvokeAI field types. This abstract-like base provides common functionality for workflow field types.

**Key Design Principles:**
- **Default Constructability**: ALL field classes must be default-constructable (`field = MyFieldClass()`)
- **Type Safety**: Generic typing with `T` parameter for value types  
- **API Conversion**: Bidirectional conversion between Python objects and InvokeAI API format
- **Validation**: Built-in field validation with Pydantic integration

**Core Methods:**

#### `validate_field()`
```python
def validate_field(self) -> bool:
```
Validate the current field state and values. Returns `True` if valid, `False` otherwise.

#### `to_api_format()`  
```python
def to_api_format(self) -> dict[str, Any]:
```
Convert field to InvokeAI API format for workflow submission. Each field type implements format-specific conversion logic.

#### `from_api_format()`
```python
@classmethod  
def from_api_format(cls, data: dict[str, Any]) -> "IvkField[T]":
```
Create field instance from InvokeAI API response data. Used during workflow discovery and result parsing.

**Source:** [`IvkField`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L30){:target="_blank"}

### Supporting Mixins

#### `PydanticFieldMixin`
Provides Pydantic integration for JSON serialization, validation, and model features.
- Enables `to_json_dict()` and `from_json_dict()` methods
- Integrates with Pydantic's validation system
- Supports model configuration and field constraints

#### `IvkCollectionFieldMixin`
Specialized mixin for collection-type fields with list operations.
- Provides `append()`, `remove()`, `extend()`, `clear()` methods  
- Implements `__len__()`, `__getitem__()`, `__iter__()` for list-like behavior
- Handles collection validation and constraints

**Sources:**
- [`PydanticFieldMixin`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L190){:target="_blank"}  
- [`IvkCollectionFieldMixin`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L294){:target="_blank"}

### Field Categories

Fields are organized into categories based on their data types and usage patterns:

| Category | Purpose | Value Storage |
|----------|---------|---------------|
| **Primitive** | Basic types (string, int, float, bool) | `.value` attribute |
| **Resource** | References (images, boards, latents) | `.value` attribute |  
| **Model** | Model configurations (UNet, CLIP, etc.) | Direct attributes |
| **Complex** | Structured data (color, bbox, collections) | Varies by type |
| **Enum** | Choice fields with predefined options | `.value` attribute |

## Primitive Fields

Primitive fields handle basic data types with optional validation constraints and Pydantic integration.

### `IvkStringField` - Text Input

```python
class IvkStringField(BaseModel, PydanticFieldMixin, IvkField[str]):
```

Text field with optional length constraints and validation.

**Attributes:**
- `value` (str | None): The string value, defaults to None
- `min_length` (int | None): Minimum character length constraint  
- `max_length` (int | None): Maximum character length constraint

**API Format:**
```json
{"value": "example text"}
```

**Example:**
```python
# Basic text field
prompt_field = IvkStringField()
prompt_field.value = "A beautiful landscape painting"

# With constraints  
title_field = IvkStringField(min_length=1, max_length=100)
title_field.value = "My Artwork"

# Validation
assert title_field.validate_field() == True
```

**Source:** [`IvkStringField`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/primitives.py#L17){:target="_blank"}

### `IvkIntegerField` - Numeric Input (Integers)

```python  
class IvkIntegerField(BaseModel, PydanticFieldMixin, IvkField[int]):
```

Integer field with optional range and multiple constraints.

**Attributes:**
- `value` (int | None): The integer value, defaults to None
- `minimum` (int | None): Minimum allowed value
- `maximum` (int | None): Maximum allowed value  
- `multiple_of` (int | None): Value must be multiple of this number

**Example:**
```python
# Step count field with range
steps_field = IvkIntegerField()
steps_field.value = 20
steps_field.minimum = 1
steps_field.maximum = 100

# Seed field
seed_field = IvkIntegerField(minimum=0)
seed_field.value = 42

# Even numbers only
even_field = IvkIntegerField(multiple_of=2)
even_field.value = 16
```

**Source:** [`IvkIntegerField`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/primitives.py#L78){:target="_blank"}

### `IvkFloatField` - Numeric Input (Decimals)

```python
class IvkFloatField(BaseModel, PydanticFieldMixin, IvkField[float]):
```

Float field with optional range constraints for decimal values.

**Attributes:**
- `value` (float | None): The float value, defaults to None
- `minimum` (float | None): Minimum allowed value
- `maximum` (float | None): Maximum allowed value

**Example:**
```python
# CFG scale with typical range
cfg_field = IvkFloatField()
cfg_field.value = 7.5
cfg_field.minimum = 1.0
cfg_field.maximum = 20.0

# Denoise strength for img2img
denoise_field = IvkFloatField(minimum=0.0, maximum=1.0)  
denoise_field.value = 0.8
```

**Source:** [`IvkFloatField`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/primitives.py#L144){:target="_blank"}

### `IvkBooleanField` - True/False Toggle

```python
class IvkBooleanField(BaseModel, PydanticFieldMixin, IvkField[bool]):
```

Boolean field for true/false values, typically used for feature toggles.

**Attributes:**
- `value` (bool | None): The boolean value, defaults to None

**Example:**
```python
# Seamless tiling option
seamless_field = IvkBooleanField()  
seamless_field.value = True

# High-resolution fix
hires_field = IvkBooleanField(value=False)
```

**Source:** [`IvkBooleanField`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/primitives.py#L204){:target="_blank"}

### Validation and API Conversion

**Validation Process:**
- Pydantic validates types and constraints automatically on assignment
- `validate_field()` performs additional field-specific validation
- Constraint violations raise `ValidationError` exceptions

**API Format Conversion:**
- `to_api_format()` converts to InvokeAI server format
- Most primitives use simple `{"value": actual_value}` structure
- Automatic type coercion ensures compatibility

## Resource fields

```python
class IvkImageField(BaseModel, PydanticFieldMixin, IvkField[str], IvkImageFieldMixin]:  # [src/invokeai_py_client/ivk_fields/resources.py:21]
    value: str | None = None            # image name (server) or local path (upload scenarios)
    def to_api_format(self) -> dict[str, Any]:  # {"value": {"image_name": value}, "type": "image"}

class IvkBoardField(..., IvkField[str]):        # [src/invokeai_py_client/ivk_fields/resources.py:106]
    value: str | None = None            # board_id
    def to_api_format(self) -> dict[str, Any]:  # {"value": {"board_id": value}, "type": "board"}

class IvkLatentsField(..., IvkField[dict]):     # [src/invokeai_py_client/ivk_fields/resources.py:171]
    value: str | None = None            # latents_name
    seed: int | None = None
    # {"value": {"latents_name": "...", "seed": ...}, "type": "latents"}

class IvkTensorField(..., IvkField[dict]):      # [src/invokeai_py_client/ivk_fields/resources.py:248]
    value: str | None = None            # tensor_name
    # {"value": {"tensor_name": "..."}, "type": "tensor"}
```

## Model and configuration fields

Model identifier (simple, value-less field where the attributes themselves are the value):
```python
class IvkModelIdentifierField(BaseModel, PydanticFieldMixin, IvkField[dict[str, Any]]):  # [src/invokeai_py_client/ivk_fields/models.py:18]
    key: str = ""
    hash: str = ""
    name: str = ""
    base: BaseDnnModelType = BaseDnnModelType.Any
    type: DnnModelType = DnnModelType.Main
    submodel_type: str | None = None

    def to_api_format(self) -> dict[str, Any]:  # {"key","hash","name","base","type","submodel_type"}
```

Structured configuration fields (they are the value, no .value attribute):
```python
class IvkUNetField(..., IvkField[dict]):        # [src/invokeai_py_client/ivk_fields/models.py:111]
    unet_model: dict[str, str] | None
    scheduler: dict[str, str] | None
    loras: list[dict[str, Any]] = []
    seamless_axes: list[str] = []
    freeu_config: dict[str, Any] | None

class IvkCLIPField(..., IvkField[dict]):        # [src/invokeai_py_client/ivk_fields/models.py:169]
    tokenizer: dict[str, str] | None
    text_encoder: dict[str, str] | None
    skipped_layers: int = 0
    loras: list[dict[str, Any]] = []

class IvkTransformerField(..., IvkField[dict]): # [src/invokeai_py_client/ivk_fields/models.py:223]
    transformer_model: dict[str, str] | None
    loras: list[dict[str, Any]] = []

class IvkLoRAField(..., IvkField[dict]):        # [src/invokeai_py_client/ivk_fields/models.py:269]
    lora_model: dict[str, str] | None
    weight: float = 1.0
```

## Enum and choice fields

General enum field
```python
class IvkEnumField(BaseModel, PydanticFieldMixin, IvkField[str]):  # [src/invokeai_py_client/ivk_fields/enums.py:79]
    value: str | None = None
    choices: list[str] = []
    # Validates that value is one of choices
```

Scheduler field (pre-populated choices matching upstream)
```python
class IvkSchedulerField(IvkEnumField):  # [src/invokeai_py_client/ivk_fields/enums.py:180]
    # choices initialized from SCHEDULER_NAMES
    @staticmethod
    def normalize_alias(name: str) -> str:  # remaps common aliases to canonical names
```

Constants
```python
class SchedulerName(str, Enum): ...            # [src/invokeai_py_client/ivk_fields/enums.py:17]
SCHEDULER_NAMES: list[str] = [...]
```

## Complex fields

Colors
```python
class IvkColorField(..., IvkField[dict[str,int]]):  # [src/invokeai_py_client/ivk_fields/complex.py:20]
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255
    # Helpers: set_rgba(), set_hex(), to_rgba(), to_hex()
```

Bounding box
```python
class IvkBoundingBoxField(..., IvkField[dict]):     # [src/invokeai_py_client/ivk_fields/complex.py:145]
    x_min: int = 0
    x_max: int = 0
    y_min: int = 0
    y_max: int = 0
    score: float | None = None
```

Collections (list wrapper with constraints)
```python
class IvkCollectionField(BaseModel, PydanticFieldMixin, IvkField[list[T]], IvkCollectionFieldMixin[T], Generic[T]:
    value: list[T] = []         # uses Field(default_factory=list) in code
    item_type: type[T] | None = None
    min_length: int | None = None
    max_length: int | None = None
    # append(), remove(), extend(), clear(), __len__(), __getitem__(), etc.
```

## Practical patterns

Type-safe assignment in scripts
```python
from invokeai_py_client.ivk_fields import IvkStringField, IvkIntegerField, IvkSchedulerField

fld = wf.get_input_value(0)  # Returns typed field object
if isinstance(fld, IvkStringField):
    fld.value = "A futuristic city at night"

# Normalize scheduler alias, then assign
sched = wf.get_input_value(7)
if hasattr(sched, "value"):
    from invokeai_py_client.ivk_fields.enums import IvkSchedulerField
    sched.value = IvkSchedulerField.normalize_alias("euler_ancestral")
```

Board/image fields
```python
# Board field (form-exposed output)
board_fld = wf.get_input_value(BOARD_INDEX)
if hasattr(board_fld, "value"):
    board_fld.value = "none"  # uncategorized board_id sentinel
```

Model identifier fields
```python
m = wf.get_input_value(MODEL_INDEX)
# IvkModelIdentifierField stores attributes directly (no .value)
# Set specific attributes if needed:
if hasattr(m, "name"): m.name = "SDXL Base 1.0"
```

## Cross-references

- Inputs and indices: [docs/user-guide/inputs.md](../user-guide/inputs.md)
- Workflows: [docs/api-reference/workflow.md](workflow.md)
- Enums: [docs/api-reference/models.md](models.md)
- Examples: [docs/examples/index.md](../examples/index.md)