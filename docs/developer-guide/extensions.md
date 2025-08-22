# Field Type Extensions

Guide for extending the InvokeAI Python Client with custom typed fields for workflow inputs. This page explains the field type system architecture, implementation requirements, and best practices for adding new field types.

## Overview

The field type system provides strongly-typed, validated input handling for InvokeAI workflows. Custom field types enable precise control over GUI Form inputs with automatic validation and API format conversion.

### Why Create Custom Field Types?

- **Type Safety**: Provide stronger typing and validation for specific GUI Form inputs
- **Wire Format Control**: Normalize values and produce the exact format expected by the InvokeAI server
- **Developer Experience**: Improve ergonomics with autocompletion, constraints, and safer assignment
- **Domain Modeling**: Express business logic and constraints directly in the type system

## Field Architecture

The client discovers Form inputs and instantiates concrete field classes that implement a common contract through base classes and mixins.

### Core Principles

#### 1. Default Constructability
All field classes must support no-argument initialization to enable deserialization and discovery:
```python
field = MyFieldClass()  # Must work without arguments
```

#### 2. Clear Assignment Semantics
Fields follow two patterns based on their complexity:

- **Simple fields** expose `.value` attribute (primitives, resources, enums)
- **Structured fields** store attributes directly without `.value` (models, configs)

#### 3. Explicit Conversion Boundaries
Each field implements standard conversion methods:

- `validate_field()` - Per-field validation checks
- `to_api_format()` - Convert to server wire format
- `from_api_format()` - Parse server responses

## Implementation Guide

### Step 1: Choose Your Field Category

Determine which pattern your field should follow:

| Category | Pattern | Examples |
|----------|---------|----------|
| **Primitive-like** | Has `.value` attribute | String, Integer, Float, Boolean, Percent |
| **Resource-like** | Has `.value` with nested wire format | Image, Board, Latents, Mask |
| **Structured** | Direct attributes, no `.value` | ModelIdentifier, UNetConfig, Collections |

### Step 2: Create the Field Class

#### Example: Primitive Field with Constraints

```python
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field, ValidationError
from invokeai_py_client.ivk_fields.base import PydanticFieldMixin
from invokeai_py_client.ivk_fields import IvkField

class IvkPercentField(BaseModel, PydanticFieldMixin, IvkField[float]):
    """
    Percentage value constrained to 0.0-1.0 range.
    Used for opacity, strength, and probability inputs.
    """
    value: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0,
        description="Normalized percentage value"
    )

    def validate_field(self) -> bool:
        """Validate the field has a valid value."""
        try:
            self.model_dump()  # Trigger Pydantic validation
            return self.value is not None
        except ValidationError:
            return False

    def to_api_format(self) -> Dict[str, Any]:
        """Convert to InvokeAI API format."""
        return {"value": self.value}

    @classmethod
    def from_api_format(cls, data: Dict[str, Any]) -> "IvkPercentField":
        """Parse from API response."""
        return cls(value=(data or {}).get("value"))
```

#### Example: Resource Field with Nested Structure

```python
from typing import Any, Optional, Dict
from pydantic import BaseModel
from invokeai_py_client.ivk_fields.base import PydanticFieldMixin
from invokeai_py_client.ivk_fields import IvkField

class IvkMaskField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """
    Reference to a mask image on the server.
    Expands to nested object in wire format.
    """
    value: Optional[str] = None  # image_name on server
    
    def validate_field(self) -> bool:
        """Ensure mask reference is provided."""
        return bool(self.value)
    
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to API format with nested structure."""
        return {
            "value": {"image_name": self.value},
            "type": "mask"
        }
    
    @classmethod
    def from_api_format(cls, data: Dict[str, Any]) -> "IvkMaskField":
        """Extract mask reference from API response."""
        value_obj = (data or {}).get("value", {})
        return cls(value=value_obj.get("image_name"))
```

### Step 3: Register with Discovery System

Add detection rules to map workflow inputs to your field class:

```python
# In discovery layer (contributors add this)
def detect_field_type(node_type: str, field_name: str, metadata: dict):
    """Map node/field combinations to field classes."""
    
    # Specific node + field detection
    if node_type == "opacity_node" and field_name == "alpha":
        return IvkPercentField
    
    # Metadata-based detection
    if metadata.get("field_type") == "percentage":
        return IvkPercentField
    
    # Default to existing rules...
```

### Step 4: Validation and Conversion

Ensure proper validation and wire format conversion:

```python
# Pre-submission validation
errors = wf.validate_inputs()
if errors:
    for idx, msgs in errors.items():
        print(f"Input [{idx}]: {', '.join(msgs)}")

# Automatic format conversion happens during submission
submission = wf.submit_sync()  # Calls to_api_format() internally
```

### Step 5: Testing Strategy

#### Unit Tests
```python
def test_percent_field_constraints():
    """Test boundary values and constraints."""
    field = IvkPercentField()
    
    # Valid values
    field.value = 0.0  # Minimum
    assert field.validate_field()
    
    field.value = 1.0  # Maximum
    assert field.validate_field()
    
    # Invalid values (should raise)
    with pytest.raises(ValidationError):
        field.value = 1.1  # Above maximum

def test_api_round_trip():
    """Test serialization round-trip."""
    original = IvkPercentField(value=0.75)
    api_format = original.to_api_format()
    restored = IvkPercentField.from_api_format(api_format)
    assert restored.value == original.value
```

#### Integration Tests
```python
def test_workflow_with_percent_field(client, workflow_json):
    """Test discovery and submission with custom field."""
    wf = client.workflow_repo.create_workflow(
        WorkflowDefinition.from_file(workflow_json)
    )
    
    # Verify field discovery
    percent_inputs = [
        inp for inp in wf.list_inputs() 
        if isinstance(inp.field, IvkPercentField)
    ]
    assert len(percent_inputs) > 0
    
    # Set value and submit
    percent_field = wf.get_input_value(percent_inputs[0].input_index)
    percent_field.value = 0.5
    
    submission = wf.submit_sync()
    assert submission is not None
```

## Usage Example

After implementing and registering your field:

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# Initialize client
client = InvokeAIClient.from_url("http://localhost:9090")

# Load workflow that uses your custom field
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflows/with-percent.json")
)

# Discover and identify your field
for inp in wf.list_inputs():
    if isinstance(inp.field, IvkPercentField):
        print(f"Found percent field at index {inp.input_index}")
        
        # Set value with type safety
        inp.field.value = 0.75
        
        # Validation happens automatically
        if inp.field.validate_field():
            print("Field is valid")

# Submit workflow (conversion happens automatically)
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=180)

# Process results
for mapping in wf.map_outputs_to_images(result):
    print(f"Generated: {mapping.get('image_names', [])}")
```

## Design Guidelines

### Best Practices

#### ✅ DO
- **Default constructability**: Always support zero-argument creation
- **Clear semantics**: Use `.value` for simple fields, attributes for structured
- **Validation messages**: Provide helpful error messages for constraint violations
- **Wire format accuracy**: Match server expectations exactly
- **Type stability**: Keep field types consistent after discovery
- **Narrow detection**: Use precise rules to avoid unintended matches

#### ❌ DON'T
- **Runtime type swapping**: Never change field type after discovery
- **Workflow mutation**: Only set values, never modify graph structure
- **Broad detection**: Avoid overly general matching rules
- **Missing validation**: Always implement `validate_field()`
- **Asymmetric conversion**: Implement both `to_api_format()` and `from_api_format()`

### Common Pitfalls and Solutions

| Problem | Solution |
|---------|----------|
| **Field not discovered** | Check detection rule specificity and order |
| **Validation always fails** | Ensure default values satisfy constraints |
| **API format mismatch** | Compare with server OpenAPI spec |
| **Type confusion** | Use isinstance() checks, not string comparison |
| **Serialization errors** | Implement proper Pydantic field configuration |

## Advanced Patterns

### Composite Fields with Multiple Values

```python
class IvkRangeField(BaseModel, PydanticFieldMixin, IvkField[dict]):
    """Range with min/max values."""
    min_value: float = Field(default=0.0)
    max_value: float = Field(default=1.0)
    
    @validator('max_value')
    def validate_range(cls, v, values):
        if 'min_value' in values and v < values['min_value']:
            raise ValueError('max_value must be >= min_value')
        return v
    
    def to_api_format(self) -> Dict[str, Any]:
        return {
            "min": self.min_value,
            "max": self.max_value
        }
```

### Fields with Dynamic Validation

```python
class IvkDependentField(BaseModel, PydanticFieldMixin, IvkField[str]):
    """Field that validates based on other inputs."""
    value: Optional[str] = None
    depends_on: Optional[str] = None
    
    def validate_field(self, context: dict = None) -> bool:
        if not self.value:
            return False
        
        # Dynamic validation based on context
        if context and self.depends_on:
            dependency = context.get(self.depends_on)
            if dependency and not self._is_compatible(dependency):
                return False
        
        return True
```

## Cross-References

- **Field System Overview**: [Fields API](../api-reference/fields.md) - Complete field type reference
- **Workflow Integration**: [Workflow API](../api-reference/workflow.md) - Input discovery and management
- **Validation Utilities**: [Utilities](../api-reference/utilities.md) - Helper functions and patterns
- **Type Examples**: [Developer Guide](index.md) - Additional implementation examples

## Further Reading

- [Pydantic Documentation](https://docs.pydantic.dev/) - Validation framework
- [InvokeAI API Documentation](https://invoke-ai.github.io/InvokeAI/) - Official InvokeAI documentation
- [Contributing Guide](contributing.md) - Contribution guidelines