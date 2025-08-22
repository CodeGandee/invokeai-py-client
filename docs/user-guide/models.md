# Model Management

Learn how to work with AI models in the InvokeAI Python Client.

## Overview

Model management is crucial for:
- **Model synchronization**: Matching workflow models to server availability
- **Model selection**: Choosing the right model for your task
- **Model metadata**: Understanding model capabilities and requirements
- **LoRA integration**: Adding style and concept adaptations

## Model Types

### Base Models

InvokeAI supports multiple model architectures:

| Model Type | Description | Use Case |
|------------|-------------|----------|
| **SD 1.5** | Stable Diffusion 1.5 | Legacy, fast, 512x512 optimal |
| **SD 2.x** | Stable Diffusion 2.0/2.1 | Improved, 768x768 optimal |
| **SDXL** | Stable Diffusion XL | High quality, 1024x1024 optimal |
| **SDXL Refiner** | SDXL refinement model | Detail enhancement |
| **FLUX** | Next-gen architecture | State-of-the-art quality |

### Model Components

```python
# Model components in workflows
components = {
    'main_model': 'Primary generation model',
    'vae': 'Variational Autoencoder for latent decoding',
    'clip': 'Text encoder for prompts',
    'unet': 'Denoising U-Net (SD models)',
    'transformer': 'Transformer model (FLUX)',
    'lora': 'Low-Rank Adaptation for style/concept'
}
```

## Model Synchronization

### Basic Sync

The most important model operation is synchronization:

```python
# Sync model fields in workflow
changes = wf.sync_dnn_model(
    by_name=True,  # Match by model name
    by_base=True   # Fallback to base model type
)

# Show what changed
for old_value, new_value in changes:
    print(f"Updated: {old_value} -> {new_value}")
```

### Selective Sync

```python
# Sync specific model fields only
model_field_indices = []

# Find model fields
for inp in wf.list_inputs():
    field = wf.get_input_value(inp.input_index)
    if hasattr(field, 'key') and hasattr(field, 'base'):
        model_field_indices.append(inp.input_index)

# Sync only model fields
changes = wf.sync_dnn_model(
    field_indices=model_field_indices,
    by_name=True,
    by_base=True
)
```

### Sync Strategies

```python
def smart_sync(wf, preferred_models=None):
    """Intelligent model synchronization."""
    preferred_models = preferred_models or {}
    
    # Try exact match first
    changes = wf.sync_dnn_model(by_name=True, by_base=False)
    
    if not changes:
        # Fallback to base model matching
        changes = wf.sync_dnn_model(by_name=False, by_base=True)
    
    # Apply preferences if available
    for inp in wf.list_inputs():
        field = wf.get_input_value(inp.input_index)
        if hasattr(field, 'base') and field.base in preferred_models:
            field.key = preferred_models[field.base]
    
    return changes
```

## Model Discovery

### List Available Models

```python
def list_available_models(client, base_model=None):
    """List models available on server."""
    # This would use the REST API
    params = {}
    if base_model:
        params['base_models'] = base_model
    
    response = client._make_request("GET", "/models/", params=params)
    return response.json()

# Get all SDXL models
sdxl_models = list_available_models(client, base_model="sdxl")
for model in sdxl_models:
    print(f"- {model['model_name']}: {model['description']}")
```

### Get Model Details

```python
def get_model_info(client, model_key):
    """Get detailed model information."""
    response = client._make_request("GET", f"/models/i/{model_key}")
    return response.json()

# Get model details
info = get_model_info(client, "stable-diffusion-xl-base")
print(f"Name: {info['model_name']}")
print(f"Base: {info['base_model']}")
print(f"Type: {info['model_type']}")
print(f"Path: {info['path']}")
```

## Working with Model Fields

### IvkModelIdentifierField

```python
from invokeai_py_client.ivk_fields import IvkModelIdentifierField

# Model identifier field (main model)
model_field = wf.get_input_value(0)
if isinstance(model_field, IvkModelIdentifierField):
    # Set model attributes
    model_field.key = "stable-diffusion-xl-base-1.0"
    model_field.hash = "31e35c80fc"
    model_field.name = "SDXL Base 1.0"
    model_field.base = "sdxl"
    model_field.type = "main"
```

### Model Field Types

```python
# Different model field types
from invokeai_py_client.ivk_fields import (
    IvkModelIdentifierField,  # Main model
    IvkUNetField,             # UNet component
    IvkCLIPField,             # CLIP text encoder
    IvkVAEField,              # VAE component
    IvkTransformerField,      # FLUX transformer
    IvkLoRAField              # LoRA adapter
)

def identify_model_field(field):
    """Identify type of model field."""
    if isinstance(field, IvkModelIdentifierField):
        return "main_model"
    elif isinstance(field, IvkUNetField):
        return "unet"
    elif isinstance(field, IvkCLIPField):
        return "clip"
    elif isinstance(field, IvkTransformerField):
        return "transformer"
    elif isinstance(field, IvkLoRAField):
        return "lora"
    return "unknown"
```

## LoRA Management

### Adding LoRAs

```python
def add_lora_to_workflow(wf, lora_name, weight=1.0):
    """Add LoRA to workflow."""
    # Find LoRA fields
    for inp in wf.list_inputs():
        if inp.field_name == "lora" or "lora" in inp.label.lower():
            field = wf.get_input_value(inp.input_index)
            if hasattr(field, 'key'):
                field.key = lora_name
                field.name = lora_name
                if hasattr(field, 'weight'):
                    field.weight = weight
                return True
    
    print("No LoRA field found in workflow")
    return False

# Add LoRA
add_lora_to_workflow(wf, "my-style-lora", weight=0.8)
```

### Multiple LoRAs

```python
def setup_lora_stack(wf, loras):
    """Set up multiple LoRAs with weights."""
    lora_indices = []
    
    # Find all LoRA fields
    for inp in wf.list_inputs():
        if "lora" in inp.field_name.lower():
            lora_indices.append(inp.input_index)
    
    # Apply LoRAs
    for i, (lora_name, weight) in enumerate(loras):
        if i < len(lora_indices):
            field = wf.get_input_value(lora_indices[i])
            if hasattr(field, 'key'):
                field.key = lora_name
                field.name = lora_name
                if hasattr(field, 'weight'):
                    field.weight = weight
    
    return len(lora_indices)

# Apply multiple LoRAs
loras = [
    ("style-lora", 0.7),
    ("character-lora", 0.5),
    ("detail-lora", 0.3)
]
setup_lora_stack(wf, loras)
```

## Model Selection Strategies

### By Performance

```python
def select_model_by_performance(client, base_model="sdxl"):
    """Select model based on performance criteria."""
    models = list_available_models(client, base_model)
    
    # Prefer certain models
    preferences = {
        'sdxl': ['stable-diffusion-xl-base-1.0', 'sdxl-turbo'],
        'sd-1': ['stable-diffusion-v1-5', 'deliberate-v2'],
        'flux': ['flux-schnell', 'flux-dev']
    }
    
    preferred = preferences.get(base_model, [])
    
    for model in models:
        if model['model_name'] in preferred:
            return model['model_key']
    
    # Return first available if no preference
    return models[0]['model_key'] if models else None
```

### By Use Case

```python
def select_model_for_task(task_type):
    """Select model based on task."""
    task_models = {
        'photorealistic': 'stable-diffusion-xl-base-1.0',
        'artistic': 'sdxl-artistic-model',
        'anime': 'anything-v5',
        'fast_preview': 'sdxl-turbo',
        'high_quality': 'flux-dev',
        'inpainting': 'sdxl-inpainting'
    }
    
    return task_models.get(task_type, 'stable-diffusion-xl-base-1.0')
```

## Model Configuration

### Optimal Settings by Model

```python
def get_optimal_settings(model_base):
    """Get optimal settings for model type."""
    settings = {
        'sd-1': {
            'width': 512,
            'height': 512,
            'steps': 20,
            'cfg_scale': 7.5
        },
        'sd-2': {
            'width': 768,
            'height': 768,
            'steps': 20,
            'cfg_scale': 7.5
        },
        'sdxl': {
            'width': 1024,
            'height': 1024,
            'steps': 30,
            'cfg_scale': 7.0
        },
        'flux': {
            'width': 1024,
            'height': 1024,
            'steps': 4,  # Flux is fast
            'cfg_scale': 3.5
        }
    }
    
    return settings.get(model_base, settings['sdxl'])

# Apply optimal settings
model_field = wf.get_input_value(0)
if hasattr(model_field, 'base'):
    settings = get_optimal_settings(model_field.base)
    
    wf.get_input_value(WIDTH_IDX).value = settings['width']
    wf.get_input_value(HEIGHT_IDX).value = settings['height']
    wf.get_input_value(STEPS_IDX).value = settings['steps']
    wf.get_input_value(CFG_IDX).value = settings['cfg_scale']
```

### Model-Specific Prompting

```python
def adapt_prompt_for_model(prompt, model_base):
    """Adapt prompt style for model."""
    if model_base == 'flux':
        # Flux prefers natural language
        return f"A photograph of {prompt}, high quality, detailed"
    elif model_base == 'sdxl':
        # SDXL works well with tags
        return f"{prompt}, masterpiece, best quality, highly detailed, 8k"
    elif 'anime' in model_base:
        # Anime models need specific tags
        return f"{prompt}, anime style, illustration, detailed"
    else:
        return prompt

# Adapt prompt
original = "a beautiful landscape"
model_field = wf.get_input_value(0)
if hasattr(model_field, 'base'):
    adapted = adapt_prompt_for_model(original, model_field.base)
    wf.get_input_value(PROMPT_IDX).value = adapted
```

## Model Validation

### Check Model Availability

```python
def validate_model(client, model_key):
    """Check if model is available on server."""
    try:
        response = client._make_request("GET", f"/models/i/{model_key}")
        return response.ok
    except:
        return False

# Validate before submission
model_field = wf.get_input_value(0)
if hasattr(model_field, 'key'):
    if not validate_model(client, model_field.key):
        print(f"Model {model_field.key} not available")
        # Try to sync
        wf.sync_dnn_model()
```

### Model Compatibility

```python
def check_model_compatibility(workflow_def):
    """Check if workflow models are compatible."""
    model_types = {}
    
    # Extract model types from nodes
    for node_id, node in workflow_def.nodes.items():
        if 'model' in node.get('type', '').lower():
            model_base = node.get('model', {}).get('base')
            if model_base:
                model_types[node_id] = model_base
    
    # Check compatibility
    bases = set(model_types.values())
    if len(bases) > 1:
        print(f"Warning: Mixed model bases: {bases}")
        return False
    
    return True
```

## Error Handling

### Model Not Found

```python
def handle_model_error(wf, error):
    """Handle model-related errors."""
    if "model not found" in str(error).lower():
        print("Model not found, attempting sync...")
        changes = wf.sync_dnn_model(by_name=True, by_base=True)
        
        if changes:
            print(f"Synced {len(changes)} model fields")
            return True
        else:
            print("No compatible models found")
            # List available models
            models = list_available_models(client)
            print("Available models:")
            for m in models[:5]:
                print(f"  - {m['model_name']}")
    
    return False
```

### Fallback Models

```python
def setup_fallback_models(wf):
    """Configure fallback models."""
    fallbacks = {
        'sdxl': 'stable-diffusion-xl-base-1.0',
        'sd-1': 'stable-diffusion-v1-5',
        'flux': 'flux-schnell'
    }
    
    for inp in wf.list_inputs():
        field = wf.get_input_value(inp.input_index)
        if hasattr(field, 'base') and hasattr(field, 'key'):
            if not field.key and field.base in fallbacks:
                field.key = fallbacks[field.base]
                print(f"Set fallback for {field.base}: {field.key}")
```

## Best Practices

### 1. Always Sync Before Submission

```python
# Standard workflow setup
def setup_workflow(client, workflow_path):
    wf = client.workflow_repo.create_workflow(
        WorkflowDefinition.from_file(workflow_path)
    )
    
    # Always sync models first
    wf.sync_dnn_model(by_name=True, by_base=True)
    
    return wf
```

### 2. Cache Model Information

```python
class ModelCache:
    """Cache model information to reduce API calls."""
    
    def __init__(self, client):
        self.client = client
        self.cache = {}
        self.refresh()
    
    def refresh(self):
        """Refresh model cache."""
        models = list_available_models(self.client)
        self.cache = {m['model_key']: m for m in models}
    
    def get(self, model_key):
        """Get cached model info."""
        return self.cache.get(model_key)
    
    def find_by_base(self, base):
        """Find models by base type."""
        return [m for m in self.cache.values() 
                if m.get('base_model') == base]
```

### 3. Document Model Requirements

```python
"""
Workflow: SDXL Text-to-Image
Required Models:
- Base Model: SDXL (stable-diffusion-xl-base-1.0)
- VAE: sdxl-vae (optional, embedded)
- Refiner: SDXL Refiner (optional)

Optional LoRAs:
- Style LoRAs compatible with SDXL
- Maximum 3 LoRAs recommended
"""
```

## Advanced Model Operations

### Model Switching

```python
def switch_model_variant(wf, variant="turbo"):
    """Switch between model variants."""
    variants = {
        'turbo': 'sdxl-turbo',
        'base': 'stable-diffusion-xl-base-1.0',
        'refiner': 'stable-diffusion-xl-refiner-1.0'
    }
    
    if variant not in variants:
        return False
    
    model_field = wf.get_input_value(0)
    if hasattr(model_field, 'key'):
        model_field.key = variants[variant]
        
        # Adjust settings for variant
        if variant == 'turbo':
            wf.get_input_value(STEPS_IDX).value = 4
            wf.get_input_value(CFG_IDX).value = 1.0
        
        return True
    
    return False
```

### Model Benchmarking

```python
def benchmark_models(client, wf, models, prompt):
    """Benchmark different models."""
    import time
    
    results = {}
    
    for model_key in models:
        # Set model
        model_field = wf.get_input_value(0)
        model_field.key = model_key
        
        # Set prompt
        wf.get_input_value(PROMPT_IDX).value = prompt
        
        # Time execution
        start = time.time()
        submission = wf.submit_sync()
        result = wf.wait_for_completion_sync(submission)
        elapsed = time.time() - start
        
        results[model_key] = {
            'time': elapsed,
            'status': result.get('status')
        }
        
        print(f"{model_key}: {elapsed:.2f}s")
    
    return results
```

## Next Steps

- Master [Execution Modes](execution-modes.md)
- Learn about [Output Mapping](output-mapping.md)
- Explore [Workflow Basics](workflow-basics.md)
- Review [Field Types](field-types.md)