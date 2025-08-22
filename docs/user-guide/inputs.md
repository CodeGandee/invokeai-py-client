# Working with Inputs

Master the index-based input system for programmatic workflow control.

## Understanding Inputs

Inputs in the InvokeAI Python Client are fields exposed through the workflow's Form panel. These are the only parameters you can control programmatically.

## Input Discovery

### List All Inputs

```python
# Discover all available inputs
for inp in wf.list_inputs():
    print(f"[{inp.input_index:2d}] {inp.label or inp.field_name}")
    print(f"     Node: {inp.node_name}")
    print(f"     Type: {type(inp.field).__name__}")
    print(f"     Required: {inp.required}")
```

### Input Properties

Each input (IvkWorkflowInput) has:

| Property | Description | Example |
|----------|-------------|---------|
| `input_index` | Unique position number | `0`, `1`, `2` |
| `label` | Display name from Form | `"Positive Prompt"` |
| `field_name` | Technical field name | `"prompt"` |
| `node_name` | Source node name | `"compel_1"` |
| `node_id` | Source node ID | `"abc123"` |
| `field` | Typed field instance | `IvkStringField` |
| `required` | Whether required | `True`/`False` |

## Index-Based Access

### Why Indices?

Indices are the primary way to access inputs because:

1. **Uniqueness**: Always unique (unlike labels/names)
2. **Stability**: Don't change unless Form is restructured
3. **Performance**: Direct array access
4. **Simplicity**: Just numbers, no string matching

### Index Ordering

Indices follow depth-first traversal of the Form:

```
Form Structure:          Index:
├── Prompt               [0]
├── Negative             [1]
├── Container            
│   ├── Width            [2]
│   └── Height           [3]
├── Steps                [4]
└── CFG Scale            [5]
```

### Accessing by Index

```python
# Get field by index
field = wf.get_input_value(0)

# Get input metadata
input_info = wf.get_input(0)
print(f"Label: {input_info.label}")
print(f"Field name: {input_info.field_name}")
```

## Setting Input Values

### Basic Value Setting

```python
# Get field and set value
field = wf.get_input_value(0)
if hasattr(field, 'value'):
    field.value = "New value"
```

### Type-Safe Setting

```python
from invokeai_py_client.ivk_fields import IvkStringField, IvkIntegerField

# String field
prompt = wf.get_input_value(0)
if isinstance(prompt, IvkStringField):
    prompt.value = "A beautiful sunset"

# Integer field
steps = wf.get_input_value(4)
if isinstance(steps, IvkIntegerField):
    steps.value = 30
```

### Batch Setting

```python
# Set multiple values at once
def set_inputs(wf, values_dict):
    """Set multiple inputs by index."""
    for index, value in values_dict.items():
        field = wf.get_input_value(index)
        if hasattr(field, 'value'):
            field.value = value

# Use it
set_inputs(wf, {
    0: "Positive prompt",
    1: "Negative prompt",
    2: 1024,  # width
    3: 1024,  # height
    4: 30,    # steps
})
```

## Input Patterns

### Index Constants Pattern

```python
# Define constants after discovery
IDX_POSITIVE = 0
IDX_NEGATIVE = 1
IDX_WIDTH = 2
IDX_HEIGHT = 3
IDX_STEPS = 4
IDX_CFG = 5
IDX_SEED = 6

# Use throughout your code
wf.get_input_value(IDX_POSITIVE).value = "A castle"
wf.get_input_value(IDX_STEPS).value = 30
```

### Index Mapping Pattern

```python
# Create a mapping for clarity
INPUT_MAP = {
    'positive': 0,
    'negative': 1,
    'width': 2,
    'height': 3,
    'steps': 4,
    'cfg': 5,
    'seed': 6
}

# Access by name
wf.get_input_value(INPUT_MAP['positive']).value = "Landscape"
wf.get_input_value(INPUT_MAP['steps']).value = 25
```

### Dynamic Discovery Pattern

```python
def find_input_index(wf, label=None, field_name=None):
    """Find input index by label or field name."""
    for inp in wf.list_inputs():
        if label and inp.label == label:
            return inp.input_index
        if field_name and inp.field_name == field_name:
            return inp.input_index
    return None

# Find and use
prompt_idx = find_input_index(wf, label="Positive Prompt")
if prompt_idx is not None:
    wf.get_input_value(prompt_idx).value = "New prompt"
```

## Input Validation

### Individual Field Validation

```python
# Validate single field
field = wf.get_input_value(0)
try:
    field.validate_field()
    print("✓ Field is valid")
except ValueError as e:
    print(f"✗ Invalid: {e}")
```

### Workflow-Wide Validation

```python
# Validate all inputs
def validate_all(wf):
    errors = []
    for inp in wf.list_inputs():
        field = wf.get_input_value(inp.input_index)
        try:
            if hasattr(field, 'validate_field'):
                field.validate_field()
        except ValueError as e:
            errors.append(f"[{inp.input_index}] {inp.label}: {e}")
    
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  • {error}")
        return False
    
    print("✓ All inputs valid")
    return True

# Use it
if validate_all(wf):
    wf.submit_sync()
```

### Required Fields Check

```python
def check_required(wf):
    """Ensure all required fields have values."""
    missing = []
    
    for inp in wf.list_inputs():
        if inp.required:
            field = wf.get_input_value(inp.input_index)
            if hasattr(field, 'value') and field.value is None:
                missing.append(f"[{inp.input_index}] {inp.label}")
    
    if missing:
        print("Missing required fields:")
        for field in missing:
            print(f"  • {field}")
        return False
    
    return True
```

## Advanced Input Handling

### Input Snapshots

```python
def snapshot_inputs(wf):
    """Create a snapshot of current input values."""
    snapshot = {}
    for inp in wf.list_inputs():
        field = wf.get_input_value(inp.input_index)
        if hasattr(field, 'value'):
            snapshot[inp.input_index] = {
                'label': inp.label,
                'field_name': inp.field_name,
                'value': field.value,
                'type': type(field).__name__
            }
    return snapshot

# Save and restore
snapshot = snapshot_inputs(wf)

# ... modify inputs ...

# Restore
for index, data in snapshot.items():
    wf.get_input_value(index).value = data['value']
```

### Input Defaults

```python
class WorkflowDefaults:
    """Manage default values for workflow inputs."""
    
    def __init__(self, wf):
        self.wf = wf
        self.defaults = {}
    
    def save_defaults(self):
        """Save current values as defaults."""
        for inp in self.wf.list_inputs():
            field = self.wf.get_input_value(inp.input_index)
            if hasattr(field, 'value'):
                self.defaults[inp.input_index] = field.value
    
    def apply_defaults(self):
        """Apply saved defaults."""
        for index, value in self.defaults.items():
            field = self.wf.get_input_value(index)
            if hasattr(field, 'value'):
                field.value = value
    
    def reset_to_defaults(self):
        """Reset all inputs to defaults."""
        self.apply_defaults()

# Use it
defaults = WorkflowDefaults(wf)
defaults.save_defaults()

# Change values...
wf.get_input_value(0).value = "Different"

# Reset
defaults.reset_to_defaults()
```

### Conditional Inputs

```python
def set_quality_preset(wf, quality='medium'):
    """Set inputs based on quality preset."""
    presets = {
        'low': {'steps': 20, 'width': 512, 'height': 512},
        'medium': {'steps': 30, 'width': 768, 'height': 768},
        'high': {'steps': 50, 'width': 1024, 'height': 1024},
        'ultra': {'steps': 100, 'width': 2048, 'height': 2048}
    }
    
    if quality not in presets:
        raise ValueError(f"Unknown quality: {quality}")
    
    settings = presets[quality]
    
    # Assuming these indices (discover first!)
    wf.get_input_value(4).value = settings['steps']
    wf.get_input_value(2).value = settings['width']
    wf.get_input_value(3).value = settings['height']

# Apply preset
set_quality_preset(wf, 'high')
```

## Input Types Reference

Common field types and their value types:

| Field Class | Value Type | Example |
|-------------|------------|---------|
| `IvkStringField` | `str` | `"prompt text"` |
| `IvkIntegerField` | `int` | `30` |
| `IvkFloatField` | `float` | `7.5` |
| `IvkBooleanField` | `bool` | `True` |
| `IvkImageField` | `str` | `"image_123.png"` |
| `IvkBoardField` | `str` | `"board_id"` |
| `IvkEnumField` | `str` | `"euler"` |

## Debugging Inputs

### Input Inspector

```python
def inspect_input(wf, index):
    """Detailed inspection of an input."""
    try:
        inp = wf.get_input(index)
        field = wf.get_input_value(index)
        
        print(f"=== Input [{index}] ===")
        print(f"Label: {inp.label}")
        print(f"Field name: {inp.field_name}")
        print(f"Node: {inp.node_name} ({inp.node_id})")
        print(f"Type: {type(field).__name__}")
        print(f"Required: {inp.required}")
        
        if hasattr(field, 'value'):
            print(f"Current value: {field.value}")
        
        # Field-specific info
        if hasattr(field, 'min_value'):
            print(f"Min: {field.min_value}")
        if hasattr(field, 'max_value'):
            print(f"Max: {field.max_value}")
        if hasattr(field, 'options'):
            print(f"Options: {field.options}")
            
    except IndexError:
        print(f"No input at index {index}")
```

### Input Comparison

```python
def compare_inputs(wf1, wf2):
    """Compare inputs between two workflows."""
    inputs1 = list(wf1.list_inputs())
    inputs2 = list(wf2.list_inputs())
    
    print(f"Workflow 1: {len(inputs1)} inputs")
    print(f"Workflow 2: {len(inputs2)} inputs")
    
    # Compare by index
    max_idx = max(len(inputs1), len(inputs2))
    for i in range(max_idx):
        inp1 = inputs1[i] if i < len(inputs1) else None
        inp2 = inputs2[i] if i < len(inputs2) else None
        
        if inp1 and inp2:
            if inp1.label == inp2.label:
                print(f"[{i}] ✓ Match: {inp1.label}")
            else:
                print(f"[{i}] ✗ Differ: {inp1.label} vs {inp2.label}")
        elif inp1:
            print(f"[{i}] Only in WF1: {inp1.label}")
        else:
            print(f"[{i}] Only in WF2: {inp2.label}")
```

## Best Practices

### 1. Document Your Indices

```python
"""
Workflow: SDXL Text-to-Image v1.0
Last updated: 2024-01-15

Input Indices:
[0] Positive Prompt (string)
[1] Negative Prompt (string)
[2] Width (integer, 512-2048)
[3] Height (integer, 512-2048)
[4] Steps (integer, 1-150)
[5] CFG Scale (float, 1-20)
[6] Seed (integer)
[7] Scheduler (enum)
"""
```

### 2. Validate Before Submission

```python
# Always validate
try:
    wf.validate_inputs()
    result = wf.submit_sync()
except ValueError as e:
    print(f"Cannot submit: {e}")
```

### 3. Handle Missing Inputs Gracefully

```python
def safe_set_value(wf, index, value):
    """Safely set a value with error handling."""
    try:
        field = wf.get_input_value(index)
        if hasattr(field, 'value'):
            field.value = value
            return True
    except IndexError:
        print(f"Warning: No input at index {index}")
    except ValueError as e:
        print(f"Warning: Invalid value for index {index}: {e}")
    return False
```

## Common Issues

### Index Out of Range

```python
# Check index exists before access
max_index = len(list(wf.list_inputs())) - 1
if index <= max_index:
    field = wf.get_input_value(index)
else:
    print(f"Index {index} out of range (max: {max_index})")
```

### Type Mismatch

```python
# Ensure correct type
field = wf.get_input_value(2)  # Expecting integer
if hasattr(field, 'value'):
    try:
        field.value = int(user_input)  # Convert to expected type
    except (ValueError, TypeError):
        print(f"Cannot convert {user_input} to integer")
```

### Form Changes

When the Form structure changes, indices shift:

```python
def detect_index_changes(old_snapshot, wf):
    """Detect if indices have changed."""
    current = {}
    for inp in wf.list_inputs():
        current[inp.label] = inp.input_index
    
    changes = []
    for label, old_idx in old_snapshot.items():
        new_idx = current.get(label)
        if new_idx != old_idx:
            changes.append(f"{label}: {old_idx} -> {new_idx}")
    
    return changes
```

## Next Steps

- Explore [Field Types](field-types.md) for type-specific features
- Learn about [Board Management](boards.md) for image inputs
- Understand [Execution Modes](execution-modes.md)
- Master [Output Mapping](output-mapping.md)