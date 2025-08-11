# How to Implement InvokeAI Workflow Fields in Python Clients

Practical examples and patterns for implementing InvokeAI workflow field types in Python client libraries.

## Client Field Implementation Patterns

### Pydantic Model Approach

Create client-side models that mirror InvokeAI's field structure:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Union
from enum import Enum

class ImageField(BaseModel):
    image_name: str = Field(description="The name of the image")

class ColorField(BaseModel):
    r: int = Field(ge=0, le=255, description="Red component")
    g: int = Field(ge=0, le=255, description="Green component") 
    b: int = Field(ge=0, le=255, description="Blue component")
    a: int = Field(ge=0, le=255, description="Alpha component")
    
    def tuple(self) -> tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

class ModelIdentifierField(BaseModel):
    key: str = Field(description="The model's unique key")
    hash: str = Field(description="The model's BLAKE3 hash")
    name: str = Field(description="The model's name")
    base: str = Field(description="The model's base type")
    type: str = Field(description="The model's type")
    submodel_type: Optional[str] = None
```

### Node Input Builders

Create builder classes for complex node inputs:

```python
class FluxDenoiseInputBuilder:
    def __init__(self):
        self.data = {
            "id": str(uuid.uuid4()),
            "type": "flux_denoise", 
            "denoising_start": 0.0,
            "denoising_end": 1.0,
            "add_noise": True,
            "guidance": 3.5,
            "num_steps": 50,
            "width": 1024,
            "height": 1024,
        }
    
    def with_transformer(self, transformer_field: dict) -> 'FluxDenoiseInputBuilder':
        self.data["transformer"] = transformer_field
        return self
    
    def with_conditioning(self, positive: dict, negative: Optional[dict] = None) -> 'FluxDenoiseInputBuilder':
        self.data["positive_text_conditioning"] = positive
        if negative:
            self.data["negative_text_conditioning"] = negative
        return self
    
    def with_latents(self, latents: dict) -> 'FluxDenoiseInputBuilder':
        self.data["latents"] = latents
        return self
    
    def with_size(self, width: int, height: int) -> 'FluxDenoiseInputBuilder':
        self.data["width"] = width
        self.data["height"] = height
        return self
    
    def build(self) -> dict:
        return self.data

# Usage
flux_denoise = (FluxDenoiseInputBuilder()
    .with_transformer({"transformer": model_ref, "loras": []})
    .with_conditioning({"conditioning_name": "pos_cond_uuid"})
    .with_size(1024, 1024)
    .build())
```

### Type-Safe Field Validators

Implement validation for complex field types:

```python
class FieldValidator:
    @staticmethod
    def validate_color_field(color: dict) -> bool:
        required_keys = {"r", "g", "b", "a"}
        if not all(key in color for key in required_keys):
            return False
        return all(0 <= color[key] <= 255 for key in required_keys)
    
    @staticmethod
    def validate_image_field(image: dict) -> bool:
        return "image_name" in image and isinstance(image["image_name"], str)
    
    @staticmethod
    def validate_model_identifier(model: dict) -> bool:
        required_keys = {"key", "hash", "name", "base", "type"}
        return all(key in model and isinstance(model[key], str) for key in required_keys)
    
    @staticmethod
    def validate_bounding_box(bbox: dict) -> bool:
        required_keys = {"x_min", "x_max", "y_min", "y_max"}
        if not all(key in bbox for key in required_keys):
            return False
        
        # Validate coordinate relationships
        if bbox["x_min"] >= bbox["x_max"] or bbox["y_min"] >= bbox["y_max"]:
            return False
            
        return True
```

## Workflow Construction Examples

### Basic Text-to-Image Workflow

```python
def create_txt2img_workflow(
    prompt: str,
    model_key: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 50
) -> dict:
    """Create a basic FLUX text-to-image workflow."""
    
    # Generate UUIDs for node connections
    model_loader_id = str(uuid.uuid4())
    text_encoder_id = str(uuid.uuid4())
    denoise_id = str(uuid.uuid4())
    vae_decode_id = str(uuid.uuid4())
    
    workflow = {
        "name": "FLUX Text-to-Image",
        "meta": {"version": "3.0.0", "category": "user"},
        "nodes": [
            # FLUX Model Loader
            {
                "id": model_loader_id,
                "type": "invocation",
                "data": {
                    "id": model_loader_id,
                    "type": "flux_model_loader",
                    "model": {
                        "key": model_key,
                        "hash": "model_hash_here",
                        "name": "FLUX.1-dev",
                        "base": "flux",
                        "type": "main"
                    }
                }
            },
            # FLUX Text Encoder
            {
                "id": text_encoder_id,
                "type": "invocation",
                "data": {
                    "id": text_encoder_id,
                    "type": "flux_text_encoder",
                    "prompt": prompt,
                    "clip_l": None,  # Will be connected
                    "t5_encoder": None  # Will be connected
                }
            },
            # FLUX Denoise
            {
                "id": denoise_id,
                "type": "invocation",
                "data": {
                    "id": denoise_id,
                    "type": "flux_denoise",
                    "width": width,
                    "height": height,
                    "num_steps": steps,
                    "guidance": 3.5,
                    "denoising_start": 0.0,
                    "denoising_end": 1.0,
                    "transformer": None,  # Will be connected
                    "positive_text_conditioning": None  # Will be connected
                }
            },
            # FLUX VAE Decode
            {
                "id": vae_decode_id,
                "type": "invocation",
                "data": {
                    "id": vae_decode_id,
                    "type": "flux_vae_decode",
                    "latents": None,  # Will be connected
                    "vae": None  # Will be connected
                }
            }
        ],
        "edges": [
            # Model loader to text encoder
            {
                "id": f"{model_loader_id}-clip_l-{text_encoder_id}",
                "source": model_loader_id,
                "target": text_encoder_id,
                "sourceHandle": "clip_l",
                "targetHandle": "clip_l"
            },
            {
                "id": f"{model_loader_id}-t5_encoder-{text_encoder_id}",
                "source": model_loader_id,
                "target": text_encoder_id,
                "sourceHandle": "t5_encoder", 
                "targetHandle": "t5_encoder"
            },
            # Model loader to denoise
            {
                "id": f"{model_loader_id}-transformer-{denoise_id}",
                "source": model_loader_id,
                "target": denoise_id,
                "sourceHandle": "transformer",
                "targetHandle": "transformer"
            },
            # Text encoder to denoise
            {
                "id": f"{text_encoder_id}-conditioning-{denoise_id}",
                "source": text_encoder_id,
                "target": denoise_id,
                "sourceHandle": "conditioning",
                "targetHandle": "positive_text_conditioning"
            },
            # Denoise to VAE decode
            {
                "id": f"{denoise_id}-latents-{vae_decode_id}",
                "source": denoise_id,
                "target": vae_decode_id,
                "sourceHandle": "latents",
                "targetHandle": "latents"
            },
            # Model loader VAE to decode
            {
                "id": f"{model_loader_id}-vae-{vae_decode_id}",
                "source": model_loader_id,
                "target": vae_decode_id,
                "sourceHandle": "vae",
                "targetHandle": "vae"
            }
        ]
    }
    
    return workflow
```

### Image-to-Image with ControlNet

```python
def create_img2img_controlnet_workflow(
    input_image: ImageField,
    control_image: ImageField,
    prompt: str,
    controlnet_model_key: str,
    strength: float = 0.8
) -> dict:
    """Create FLUX img2img workflow with ControlNet."""
    
    # Node IDs
    vae_encode_id = str(uuid.uuid4())
    controlnet_id = str(uuid.uuid4())
    denoise_id = str(uuid.uuid4())
    
    workflow = {
        "nodes": [
            # VAE Encode input image
            {
                "id": vae_encode_id,
                "type": "invocation",
                "data": {
                    "id": vae_encode_id,
                    "type": "flux_vae_encode",
                    "image": input_image.model_dump(),
                    "vae": None  # Connected from model loader
                }
            },
            # FLUX ControlNet
            {
                "id": controlnet_id,
                "type": "invocation", 
                "data": {
                    "id": controlnet_id,
                    "type": "flux_controlnet",
                    "image": control_image.model_dump(),
                    "controlnet_model": {
                        "key": controlnet_model_key,
                        "hash": "controlnet_hash",
                        "name": "ControlNet Model",
                        "base": "flux",
                        "type": "controlnet"
                    },
                    "conditioning_scale": 1.0,
                    "begin_step_percent": 0.0,
                    "end_step_percent": 1.0
                }
            },
            # FLUX Denoise with img2img + ControlNet
            {
                "id": denoise_id,
                "type": "invocation",
                "data": {
                    "id": denoise_id,
                    "type": "flux_denoise",
                    "latents": None,  # Connected from VAE encode
                    "control": None,  # Connected from ControlNet
                    "denoising_start": 1.0 - strength,
                    "denoising_end": 1.0,
                    # ... other fields
                }
            }
        ],
        "edges": [
            # VAE encode to denoise
            {
                "source": vae_encode_id,
                "target": denoise_id,
                "sourceHandle": "latents",
                "targetHandle": "latents"
            },
            # ControlNet to denoise
            {
                "source": controlnet_id,
                "target": denoise_id,
                "sourceHandle": "control",
                "targetHandle": "control"
            }
        ]
    }
    
    return workflow
```

## Field Type Conversion Utilities

### JSON Schema to Python Types

```python
def convert_openapi_field_to_python_type(field_schema: dict) -> type:
    """Convert OpenAPI field schema to Python type annotation."""
    
    field_type = field_schema.get("type", "any")
    field_ref = field_schema.get("$ref", "")
    
    # Handle references to complex types
    if field_ref:
        if "ImageField" in field_ref:
            return ImageField
        elif "ColorField" in field_ref:
            return ColorField
        elif "ModelIdentifierField" in field_ref:
            return ModelIdentifierField
        # Add other complex types...
    
    # Handle primitive types
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict
    }
    
    python_type = type_mapping.get(field_type, str)
    
    # Handle arrays
    if field_type == "array" and "items" in field_schema:
        item_type = convert_openapi_field_to_python_type(field_schema["items"])
        return List[item_type]
    
    return python_type
```

### Dynamic Node Input Validation

```python
class NodeInputValidator:
    def __init__(self, openapi_schema: dict):
        self.schema = openapi_schema
        self.components = openapi_schema.get("components", {}).get("schemas", {})
    
    def validate_node_inputs(self, node_type: str, inputs: dict) -> tuple[bool, list[str]]:
        """Validate node inputs against OpenAPI schema."""
        errors = []
        
        # Find node schema
        node_schema = None
        for schema_name, schema_def in self.components.items():
            if (schema_name.endswith("Invocation") and 
                schema_def.get("properties", {}).get("type", {}).get("default") == node_type):
                node_schema = schema_def
                break
        
        if not node_schema:
            return False, [f"Unknown node type: {node_type}"]
        
        properties = node_schema.get("properties", {})
        
        # Validate each input field
        for field_name, field_value in inputs.items():
            if field_name not in properties:
                errors.append(f"Unknown field: {field_name}")
                continue
            
            field_def = properties[field_name]
            
            # Check if field is input field
            if field_def.get("field_kind") != "input":
                continue
                
            # Validate field value
            if not self._validate_field_value(field_def, field_value):
                errors.append(f"Invalid value for field {field_name}: {field_value}")
        
        # Check required fields
        for field_name, field_def in properties.items():
            if (field_def.get("field_kind") == "input" and 
                field_def.get("orig_required", False) and
                field_name not in inputs):
                errors.append(f"Missing required field: {field_name}")
        
        return len(errors) == 0, errors
    
    def _validate_field_value(self, field_def: dict, value: any) -> bool:
        """Validate individual field value."""
        field_type = field_def.get("type", "")
        
        # Basic type checking
        if field_type == "integer" and not isinstance(value, int):
            return False
        elif field_type == "number" and not isinstance(value, (int, float)):
            return False
        elif field_type == "boolean" and not isinstance(value, bool):
            return False
        elif field_type == "string" and not isinstance(value, str):
            return False
        
        # Numeric constraints
        if isinstance(value, (int, float)):
            if "minimum" in field_def and value < field_def["minimum"]:
                return False
            if "maximum" in field_def and value > field_def["maximum"]:
                return False
            if "exclusiveMinimum" in field_def and value <= field_def["exclusiveMinimum"]:
                return False
            if "exclusiveMaximum" in field_def and value >= field_def["exclusiveMaximum"]:
                return False
        
        # String constraints
        if isinstance(value, str):
            if "minLength" in field_def and len(value) < field_def["minLength"]:
                return False
            if "maxLength" in field_def and len(value) > field_def["maxLength"]:
                return False
            if "pattern" in field_def:
                import re
                if not re.match(field_def["pattern"], value):
                    return False
        
        return True
```

## Connection Graph Utilities

### Dependency Resolution

```python
class WorkflowGraphBuilder:
    def __init__(self):
        self.nodes = {}
        self.edges = []
    
    def add_node(self, node_id: str, node_type: str, inputs: dict) -> 'WorkflowGraphBuilder':
        self.nodes[node_id] = {
            "id": node_id,
            "type": "invocation",
            "data": {
                "id": node_id,
                "type": node_type,
                **inputs
            }
        }
        return self
    
    def connect(self, source_id: str, target_id: str, 
                source_field: str, target_field: str) -> 'WorkflowGraphBuilder':
        edge_id = f"{source_id}-{source_field}-{target_id}-{target_field}"
        self.edges.append({
            "id": edge_id,
            "source": source_id,
            "target": target_id,
            "sourceHandle": source_field,
            "targetHandle": target_field
        })
        
        # Update target node input to None (will be connected)
        if target_id in self.nodes:
            self.nodes[target_id]["data"][target_field] = None
        
        return self
    
    def build(self) -> dict:
        return {
            "name": "Generated Workflow",
            "meta": {"version": "3.0.0", "category": "user"},
            "nodes": list(self.nodes.values()),
            "edges": self.edges
        }

# Usage
workflow = (WorkflowGraphBuilder()
    .add_node("model", "flux_model_loader", {"model": model_ref})
    .add_node("encode", "flux_text_encoder", {"prompt": "beautiful landscape"})
    .add_node("denoise", "flux_denoise", {"width": 1024, "height": 1024})
    .connect("model", "encode", "clip_l", "clip_l")
    .connect("model", "denoise", "transformer", "transformer")
    .connect("encode", "denoise", "conditioning", "positive_text_conditioning")
    .build())
```

## Error Handling Patterns

```python
class WorkflowValidationError(Exception):
    def __init__(self, message: str, field_name: str = None, node_id: str = None):
        super().__init__(message)
        self.field_name = field_name
        self.node_id = node_id

def safe_create_node_input(node_type: str, **kwargs) -> dict:
    """Create node input with validation and error handling."""
    try:
        # Basic input structure
        node_input = {
            "id": str(uuid.uuid4()),
            "type": node_type
        }
        
        # Validate each input field
        for field_name, field_value in kwargs.items():
            # Perform field-specific validation
            if field_name == "width" and not (64 <= field_value <= 4096):
                raise WorkflowValidationError(
                    f"Width must be between 64 and 4096, got {field_value}",
                    field_name="width"
                )
            
            node_input[field_name] = field_value
        
        return node_input
        
    except Exception as e:
        raise WorkflowValidationError(
            f"Failed to create {node_type} node: {str(e)}",
            node_id=node_input.get("id")
        )
```

## Testing Field Types

```python
import pytest
from typing import Any

class TestFieldTypes:
    def test_color_field_validation(self):
        # Valid color
        color = ColorField(r=255, g=128, b=0, a=255)
        assert color.tuple() == (255, 128, 0, 255)
        
        # Invalid color (out of range)
        with pytest.raises(ValueError):
            ColorField(r=256, g=0, b=0, a=255)
    
    def test_image_field_serialization(self):
        image = ImageField(image_name="test.png")
        serialized = image.model_dump()
        assert serialized == {"image_name": "test.png"}
    
    def test_workflow_node_creation(self):
        builder = FluxDenoiseInputBuilder()
        node = builder.with_size(512, 512).build()
        
        assert node["width"] == 512
        assert node["height"] == 512
        assert node["type"] == "flux_denoise"
    
    def test_node_input_validation(self):
        validator = NodeInputValidator(openapi_schema)
        
        # Valid inputs
        valid_inputs = {
            "width": 1024,
            "height": 1024,
            "num_steps": 50
        }
        is_valid, errors = validator.validate_node_inputs("flux_denoise", valid_inputs)
        assert is_valid
        
        # Invalid inputs
        invalid_inputs = {
            "width": -100,  # Invalid range
            "unknown_field": "test"  # Unknown field
        }
        is_valid, errors = validator.validate_node_inputs("flux_denoise", invalid_inputs)
        assert not is_valid
        assert len(errors) > 0
```

These implementation patterns provide a solid foundation for building robust Python clients that can properly handle InvokeAI's complex field type system while maintaining type safety and validation.