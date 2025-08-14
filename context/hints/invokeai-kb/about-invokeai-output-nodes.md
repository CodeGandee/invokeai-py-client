# InvokeAI Output Nodes - Understanding Board Assignment and Gallery Saving

This guide explains how InvokeAI output nodes work, particularly focusing on nodes that generate images and can save them to boards/galleries.

## What Makes a Node an "Output Node"?

Output nodes in InvokeAI are nodes that produce final assets (typically images) that can be saved to the InvokeAI gallery and organized into boards. These nodes have specific characteristics that distinguish them from intermediate processing nodes.

### Key Characteristics of Output Nodes

1. **Inheritance Pattern**: Output nodes inherit from `WithBoard` mixin
2. **Return Type**: They return `ImageOutput` or similar output types
3. **Image Saving**: They use `context.images.save()` to persist images
4. **Board Support**: They can assign outputs to specific boards

## Anatomy of an Output Node

Here's the pattern used by output nodes like `FluxVaeDecodeInvocation`:

```python
from invokeai.app.invocations.baseinvocation import BaseInvocation, invocation
from invokeai.app.invocations.fields import WithBoard, WithMetadata
from invokeai.app.invocations.primitives import ImageOutput

@invocation(
    "flux_vae_decode",
    title="Latents to Image - FLUX",
    tags=["latents", "image", "vae", "l2i", "flux"],
    category="latents",
    version="1.0.2",
)
class FluxVaeDecodeInvocation(BaseInvocation, WithMetadata, WithBoard):
    """Generates an image from latents."""
    
    # Input fields...
    
    def invoke(self, context: InvocationContext) -> ImageOutput:
        # Process the image...
        image = self._vae_decode(vae_info=vae_info, latents=latents)
        
        # Save the image - this respects the board assignment
        image_dto = context.images.save(image=image)
        
        # Return ImageOutput with the saved image info
        return ImageOutput.build(image_dto)
```

## The WithBoard Mixin

The `WithBoard` mixin (defined in `invokeai/app/invocations/fields.py`) adds a board field to any node:

```python
class WithBoard(BaseModel):
    """
    Inherit from this class if your node needs a board input field.
    """
    
    board: Optional[BoardField] = Field(
        default=None,
        description=FieldDescriptions.board,
        json_schema_extra=InputFieldJSONSchemaExtra(
            field_kind=FieldKind.Internal,
            input=Input.Direct,
            orig_required=False,
        ).model_dump(exclude_none=True),
    )
```

### How Board Assignment Works

1. **GUI Integration**: When a node has `WithBoard`, the GUI automatically shows:
   - A board selection dropdown
   - A "Save to Gallery" checkbox
   
2. **Behind the Scenes**: 
   - If a board is selected, the `board` field contains the board ID
   - The `context.images.save()` method uses this board ID when saving
   - If no board is selected, images go to the "uncategorized" board

3. **The Save Process**:
   ```python
   # The context.images.save() method internally handles board assignment
   image_dto = context.images.save(
       image=image,  # The PIL image to save
       # The board ID is automatically taken from self.board if WithBoard is used
   )
   ```

## Common Output Node Types

### Image Generation Nodes
These nodes produce final images from various sources:

```python
# Latents to Image nodes
class LatentsToImageInvocation(BaseInvocation, WithMetadata, WithBoard):
    """SD1.5, SDXL latents decoder"""
    
class FluxVaeDecodeInvocation(BaseInvocation, WithMetadata, WithBoard):
    """FLUX-specific VAE decoder"""
    
class SD3LatentsToImageInvocation(BaseInvocation, WithMetadata, WithBoard):
    """SD3-specific latents decoder"""
```

### Image Processing Nodes
These nodes process existing images and output new ones:

```python
class CannyEdgeDetectionInvocation(BaseInvocation, WithMetadata, WithBoard):
    """Canny edge detection processor"""
    
class ImageCropInvocation(BaseInvocation, WithMetadata, WithBoard):
    """Crop images"""
    
class ImageBlurInvocation(BaseInvocation, WithMetadata, WithBoard):
    """Blur images"""
```

## Finding Output Destinations in Workflows

To identify where a node outputs its results in a workflow:

### 1. Check Node Inheritance
Look for nodes that inherit from `WithBoard`:
```bash
# Find all output nodes
grep -r "class.*Invocation.*WithBoard" invokeai/app/invocations/
```

### 2. Check Return Types
Look for nodes returning `ImageOutput`:
```bash
# Find nodes that return images
grep -r "return ImageOutput" invokeai/app/invocations/
```

### 3. In Workflow JSON
In workflow definitions, output nodes can be identified by:
```json
{
  "nodes": [
    {
      "id": "output_node_id",
      "data": {
        "type": "flux_vae_decode",
        "inputs": {
          // Other inputs...
          "board": {
            "board_id": "target_board_id"  // Board assignment
          }
        },
        "use_cache": false,  // Output nodes often have caching disabled
        "is_intermediate": false  // Output nodes are NOT intermediate
      }
    }
  ]
}
```

### 4. Check is_intermediate Flag
- **Output nodes**: `is_intermediate: false` - Images are saved to gallery
- **Processing nodes**: `is_intermediate: true` - Temporary images, not saved

## ImageOutput Structure

The `ImageOutput` class (from `invokeai/app/invocations/primitives.py`):

```python
@invocation_output("image_output")
class ImageOutput(BaseInvocationOutput):
    """Base class for nodes that output a single image"""
    
    image: ImageField = OutputField(description="The output image")
    width: int = OutputField(description="The width of the image in pixels")
    height: int = OutputField(description="The height of the image in pixels")
    
    @classmethod
    def build(cls, image_dto: ImageDTO) -> "ImageOutput":
        return cls(
            image=ImageField(image_name=image_dto.image_name),
            width=image_dto.width,
            height=image_dto.height,
        )
```

## Creating Custom Output Nodes

To create a custom node that outputs to boards:

```python
@invocation(
    "my_custom_output",
    title="My Custom Output",
    tags=["custom", "output"],
    category="custom",
    version="1.0.0",
)
class MyCustomOutputInvocation(BaseInvocation, WithMetadata, WithBoard):
    """Custom node that outputs images to boards."""
    
    # Input fields
    input_image: ImageField = InputField(description="Input image")
    
    def invoke(self, context: InvocationContext) -> ImageOutput:
        # Get input image
        image = context.images.get_pil(self.input_image.image_name)
        
        # Process the image (your custom logic here)
        processed_image = self.process_image(image)
        
        # Save to board (board assignment handled automatically)
        image_dto = context.images.save(image=processed_image)
        
        # Return the output
        return ImageOutput.build(image_dto)
    
    def process_image(self, image):
        # Your custom processing logic
        return image
```

## Key Points to Remember

1. **WithBoard Mixin**: Essential for board assignment capability
2. **context.images.save()**: Handles the actual saving and board assignment
3. **ImageOutput.build()**: Standard way to construct image outputs
4. **is_intermediate Flag**: Controls whether images appear in gallery
5. **Board Field**: Optional - if not set, images go to "uncategorized"

## Related Files

- `invokeai/app/invocations/fields.py` - WithBoard mixin definition
- `invokeai/app/invocations/primitives.py` - ImageOutput class
- `invokeai/app/invocations/flux_vae_decode.py` - FLUX VAE decoder example
- `invokeai/app/invocations/latents_to_image.py` - Standard latents decoder
- `invokeai/app/invocations/baseinvocation.py` - Base invocation classes

## References

- [InvokeAI Invocation API](https://github.com/invoke-ai/InvokeAI/blob/main/docs/contributing/INVOCATIONS.md)
- [Workflow Documentation](https://github.com/invoke-ai/InvokeAI/blob/main/docs/contributing/frontend/workflows.md)