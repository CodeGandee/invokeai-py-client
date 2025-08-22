# Fields API

Focus
- Accurate, to-the-point reference for the typed field system used by workflow inputs.
- Mirrors the current implementation in this repo.

Source locations
- Base and mixins: [`ivk_fields.base`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L30){:target="_blank"}
- Primitive fields: [`ivk_fields.primitives`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/primitives.py#L17){:target="_blank"}
- Resource fields: [`ivk_fields.resources`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/resources.py#L21){:target="_blank"}
- Model fields: [`ivk_fields.models`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/models.py#L18){:target="_blank"}
- Complex fields: [`ivk_fields.complex`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/complex.py#L20){:target="_blank"}
- Enum fields and scheduler: [`ivk_fields.enums`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/enums.py#L79){:target="_blank"}

Usage basics
- All field classes are default-constructable.
- Most simple fields keep a .value attribute you can set directly; structured fields embed their configuration directly (no separate .value).
- Convert to InvokeAI API payload with .to_api_format(); most users don’t call this directly because WorkflowHandle handles conversion.

## Base class and mixins

```python
class IvkField(Generic[T]):  # Source: [`IvkField`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L30){:target="_blank"}
    def validate_field(self) -> bool: ...
    def to_api_format(self) -> dict[str, Any]: ...
    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> "IvkField[T]": ...
```

- PydanticFieldMixin and helper mixins provide JSON conversions and collection/image helpers where applicable:
  - [`PydanticFieldMixin`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L190){:target="_blank"}
  - [`IvkCollectionFieldMixin`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/ivk_fields/base.py#L294){:target="_blank"}

## Primitive fields

```python
class IvkStringField(BaseModel, PydanticFieldMixin, IvkField[str]):  # [src/invokeai_py_client/ivk_fields/primitives.py:17]
    value: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    def to_api_format(self) -> dict[str, Any]:  # {"value": value}
    def validate_field(self) -> bool: ...

class IvkIntegerField(..., IvkField[int]):      # [src/invokeai_py_client/ivk_fields/primitives.py:78]
    value: int | None = None
    minimum: int | None = None
    maximum: int | None = None
    multiple_of: int | None = None

class IvkFloatField(..., IvkField[float]):      # [src/invokeai_py_client/ivk_fields/primitives.py:144]
    value: float | None = None
    minimum: float | None = None
    maximum: float | None = None

class IvkBooleanField(..., IvkField[bool]):     # [src/invokeai_py_client/ivk_fields/primitives.py:204]
    value: bool | None = None
```

Notes
- Validation is enforced via Pydantic validators and validate_field().
- to_api_format() yields the correct shape for the server’s invocation schema.

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