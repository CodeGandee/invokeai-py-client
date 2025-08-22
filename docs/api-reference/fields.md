# Fields API

Type-safe field system for workflow inputs.

## Base Field Class

```python
class IvkField[T](Generic[T], ABC):
    """Abstract base for all field types."""
    
    @abstractmethod
    def validate_field(self) -> bool:
        """Validate field constraints."""
    
    @abstractmethod
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to API format."""
    
    @abstractmethod
    def from_api_format(cls, data: Dict) -> 'IvkField':
        """Create from API data."""
```

## Primitive Fields

```python
class IvkStringField(IvkField[str]):
    value: str
    min_length: Optional[int]
    max_length: Optional[int]

class IvkIntegerField(IvkField[int]):
    value: int
    minimum: Optional[int]
    maximum: Optional[int]

class IvkFloatField(IvkField[float]):
    value: float
    minimum: Optional[float]
    maximum: Optional[float]

class IvkBooleanField(IvkField[bool]):
    value: bool
```

## Resource Fields

```python
class IvkImageField(IvkField[str]):
    value: str  # Image name/ID

class IvkBoardField(IvkField[str]):
    value: str  # Board ID

class IvkLatentsField(IvkField[str]):
    value: str  # Latents reference

class IvkTensorField(IvkField[str]):
    value: str  # Tensor reference
```

## Model Fields

```python
class IvkModelIdentifierField(IvkField):
    key: str
    hash: Optional[str]
    name: Optional[str]
    base: str  # sd-1, sd-2, sdxl, flux
    type: str  # main, vae, lora

class IvkUNetField(IvkField):
    # UNet model reference

class IvkCLIPField(IvkField):
    # CLIP model reference

class IvkTransformerField(IvkField):
    # Transformer model reference

class IvkLoRAField(IvkField):
    key: str
    weight: float
```

## Complex Fields

```python
class IvkColorField(IvkField):
    r: int  # 0-255
    g: int  # 0-255
    b: int  # 0-255
    a: int  # 0-255

class IvkBoundingBoxField(IvkField):
    x_min: int
    x_max: int
    y_min: int
    y_max: int

class IvkCollectionField(IvkField[List]):
    value: List[Any]
    item_type: str
```

## Usage Examples

```python
# String field
prompt = IvkStringField(value="A beautiful landscape")
prompt.max_length = 1000

# Integer field
seed = IvkIntegerField(value=42, minimum=0, maximum=2**32-1)

# Model field
model = IvkModelIdentifierField(
    key="stable-diffusion-xl-base-1.0",
    base="sdxl",
    type="main"
)

# Color field
color = IvkColorField(r=255, g=128, b=0, a=255)

# Collection field
collection = IvkCollectionField(
    value=["item1", "item2"],
    item_type="string"
)
```

See [User Guide](../user-guide/field-types.md) for detailed examples.