# About InvokeAI Output Nodes

InvokeAI output nodes are workflow nodes that can save their results to boards. These nodes inherit from the `WithBoard` mixin, which provides a `board` field allowing users to specify where output images should be saved.

## What are Output Nodes?

Output nodes are distinguished from regular processing nodes by their ability to persist results to InvokeAI's board system. They inherit from `WithBoard` mixin:

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

## Categories of Output Nodes

### 1. VAE & Latent Operations
Convert between latent space and image space, fundamental for AI image generation:

- **`l2i`** - Latents to Image (SD1.5, SDXL)
- **`flux_vae_decode`** - FLUX VAE Decode
- **`sd3_l2i`** - SD3 Latents to Image
- **`cogview4_l2i`** - CogView4 Latents to Image
- **`cogview4_i2l`** - CogView4 Image to Latents
- **`sd3_i2l`** - SD3 Image to Latents

### 2. Core Image Processing
Basic image manipulation and enhancement operations:

- **`save_image`** - Save Image (primary output node)
- **`img_crop`** - Image Crop
- **`img_resize`** - Image Resize  
- **`img_scale`** - Image Scale
- **`img_blur`** - Image Blur
- **`unsharp_mask`** - Unsharp Mask
- **`img_conv`** - Image Convert
- **`img_chan`** - Image Channel
- **`img_mul`** - Image Multiply
- **`img_lerp`** - Image Lerp
- **`img_ilerp`** - Image Inverse Lerp
- **`img_paste`** - Image Paste
- **`img_watermark`** - Image Watermark
- **`img_nsfw`** - Image NSFW Blur

### 3. Edge Detection & Feature Extraction
Preprocessors for ControlNet and feature detection:

- **`canny_edge_detection`** - Canny Edge Detection
- **`hed_edge_detection`** - HED Edge Detection  
- **`lineart_edge_detection`** - Lineart Edge Detection
- **`lineart_anime_edge_detection`** - Lineart Anime Edge Detection
- **`pidi_edge_detection`** - PiDiNet Edge Detection
- **`mlsd_detection`** - MLSD Detection
- **`normal_map`** - Normal Map Generation
- **`depth_anything_depth_estimation`** - Depth Anything Depth Estimation
- **`dw_openpose_detection`** - DWPose Detection
- **`mediapipe_face_detection`** - MediaPipe Face Detection

### 4. AI Model Operations
Advanced AI-powered image processing:

- **`denoise`** - Denoising operations
- **`sd3_denoise`** - SD3 Denoise
- **`cogview4_denoise`** - CogView4 Denoise
- **`esrgan`** - ESRGAN Upscaling
- **`spandrel_image_to_image`** - Spandrel Image-to-Image
- **`face_identifier`** - Face Identification

### 5. Mask Operations
Mask creation, manipulation, and application:

- **`mask_from_alpha`** - Mask from Alpha Channel
- **`mask_edge`** - Mask Edge Processing
- **`mask_combine`** - Mask Combine
- **`mask_from_id`** - Mask from ID
- **`canvas_v2_mask_and_crop`** - Canvas V2 Mask and Crop
- **`expand_mask_with_fade`** - Expand Mask with Fade
- **`apply_mask_to_image`** - Apply Mask to Image
- **`mask_tensor_to_image`** - Mask Tensor to Image
- **`apply_mask_tensor_to_image`** - Apply Mask Tensor to Image

### 6. Composition & Enhancement
Image composition, blending, and enhancement:

- **`color_correct`** - Color Correction
- **`img_hue_adjust`** - Image Hue Adjustment
- **`img_channel_offset`** - Image Channel Offset
- **`img_channel_multiply`** - Image Channel Multiply
- **`color_map`** - Color Map
- **`content_shuffle`** - Content Shuffle
- **`cv_inpaint`** - OpenCV Inpaint
- **`infill_image_processor`** - Infill Image Processor
- **`blank_image`** - Blank Image Creation
- **`img_noise`** - Image Noise
- **`merge_tiles_to_image`** - Merge Tiles to Image

### 7. Specialized Operations
Application-specific and advanced operations:

- **`invoke_adjust_image_hue_plus`** - Advanced Hue Adjustment
- **`invoke_image_enhance`** - Image Enhancement
- **`invoke_equivalent_achromatic_lightness`** - Achromatic Lightness
- **`invoke_image_blend`** - Image Blending
- **`invoke_image_compositor`** - Image Compositor
- **`invoke_image_value_thresholds`** - Value Thresholds
- **`canvas_paste_back`** - Canvas Paste Back
- **`crop_image_to_bounding_box`** - Crop to Bounding Box
- **`paste_image_into_bounding_box`** - Paste into Bounding Box
- **`flux_kontext_concatenate_images`** - FLUX Kontext Image Concatenation

## Usage in Workflows

Output nodes are typically placed at the end of processing chains to save results:

```json
{
  "id": "save_image_node",
  "type": "save_image", 
  "inputs": {
    "image": {
      "node_id": "processing_node",
      "field": "image"
    },
    "board": {
      "board_id": "my_board_id"
    }
  }
}
```

## Key Characteristics

1. **Board Integration**: All output nodes can specify a target board for saving results
2. **Metadata Support**: Most inherit from `WithMetadata` for preserving image metadata
3. **Return ImageOutput**: Output nodes typically return `ImageOutput` objects containing image references
4. **Workflow Endpoints**: Often serve as terminal nodes in processing workflows

## Board Specification

The `board` field accepts:
- `null` - Save to default/uncategorized board  
- `{board_id: "board_uuid"}` - Save to specific board
- Can be connected from upstream board selection nodes

## Common Patterns

### Basic Save
```python
# Simple image save
save_node = SaveImageInvocation(
    image=processed_image,
    board=None  # Save to uncategorized
)
```

### Preprocessor Chain
```python
# Edge detection for ControlNet
canny_node = CannyEdgeDetectionInvocation(
    image=source_image,
    low_threshold=100,
    high_threshold=200,
    board={"board_id": "preprocessor_board"}
)
```

### VAE Decode
```python
# Convert latents to final image
l2i_node = LatentsToImageInvocation(
    latents=generated_latents,
    vae=vae_field,
    board={"board_id": "output_board"}
)
```

## JSON Serialization 

InvokeAI uses Pydantic's built-in JSON serialization to convert `Invocation` classes to workflow JSON format. The process involves several key components:

### @invocation Decorator

The `@invocation` decorator transforms Python classes into workflow-compatible JSON structures:

```python
@invocation(
    "save_image",
    title="Save Image", 
    tags=["image", "save"],
    category="image",
    version="1.2.2"
)
class SaveImageInvocation(BaseInvocation, WithMetadata, WithBoard):
    # Field definitions...
```

The decorator:
1. **Validates invocation type** - Must be unique, non-whitespace string
2. **Creates UIConfig** - Stores metadata (title, tags, category, version, node_pack)
3. **Processes fields** - Handles InputField/OutputField transformations
4. **Adds type field** - Literal field with invocation type as default
5. **Registers invocation** - Adds to InvocationRegistry for schema generation

### JSON Schema Generation

BaseInvocation provides automatic JSON schema generation through Pydantic:

```python
class BaseInvocation(ABC, BaseModel):
    @staticmethod
    def json_schema_extra(schema: dict[str, Any], model_class: Type[BaseInvocation]) -> None:
        """Adds various UI-facing attributes to the invocation's OpenAPI schema."""
        if title := model_class.UIConfig.title:
            schema["title"] = title
        if tags := model_class.UIConfig.tags:
            schema["tags"] = tags
        # ... adds category, node_pack, classification, version
        schema["class"] = "invocation"
        schema["required"].extend(["type", "id"])
```

### Workflow JSON Structure

InvokeAI workflows serialize invocations with this structure:

```json
{
  "id": "node-uuid",
  "type": "invocation", 
  "data": {
    "id": "node-uuid",
    "type": "save_image",
    "version": "1.2.2", 
    "label": "",
    "notes": "",
    "isOpen": true,
    "isIntermediate": false,
    "useCache": true,
    "nodePack": "invokeai",
    "inputs": {
      "board": {
        "name": "board",
        "label": "Output Board",
        "description": "",
        "value": {
          "board_id": "board-uuid"
        }
      },
      "image": {
        "name": "image", 
        "label": "",
        "description": ""
      }
    }
  },
  "position": {
    "x": 100,
    "y": 200
  }
}
```

### Field Serialization

**Input Fields** are serialized based on their `Input` type:
- **Input.Direct**: Value stored in `inputs.field_name.value`
- **Input.Connection**: No value, expects connection from another node
- **Input.Any**: May have value OR connection

**Board Fields** (WithBoard mixin):
```json
"board": {
  "name": "board",
  "label": "Output Board", 
  "description": "",
  "value": {
    "board_id": "a17c2b12-d25a-4e41-9217-d94a543b9e73"
  }
}
```

**Connection Fields** (no direct value):
```json
"image": {
  "name": "image",
  "label": "", 
  "description": ""
  // No "value" - expects connection
}
```

### Pydantic model_dump()

For API communication, InvokeAI uses Pydantic's `model_dump()` method:

```python
# From sockets.py - event serialization
data=event[1].model_dump(mode="json")

# Standard serialization excludes None values
super().model_dump(*args, exclude_none=True, **kwargs)
```

### TypeAdapter for Dynamic Loading

InvokeAI uses Pydantic TypeAdapter for parsing JSON back to invocation instances:

```python
class InvocationRegistry:
    @classmethod
    def get_invocation_typeadapter(cls) -> TypeAdapter[Any]:
        """Gets a pydantic TypeAdapter for the union of all invocation types."""
        return TypeAdapter(Annotated[Union[tuple(cls.get_invocation_classes())], Field(discriminator="type")])
```

This enables:
- **Workflow loading** - Parse JSON back to Python objects
- **Type validation** - Ensure valid invocation types and field values  
- **Dynamic dispatch** - Route to correct invocation class based on "type" field

### Key JSON Characteristics

1. **Type-driven**: The "type" field determines which invocation class to instantiate
2. **Metadata-rich**: Includes UI information (title, category, version, etc.)
3. **Field validation**: Pydantic validates all field types and constraints
4. **Connection-aware**: Distinguishes between direct values and node connections
5. **Board integration**: Special handling for board field serialization
6. **Cache control**: useCache field controls invocation caching behavior

## References

- [InvokeAI Fields Documentation](https://github.com/invoke-ai/InvokeAI/blob/main/invokeai/app/invocations/fields.py)
- [InvokeAI Invocations Directory](https://github.com/invoke-ai/InvokeAI/tree/main/invokeai/app/invocations)
- [BaseInvocation Source](https://github.com/invoke-ai/InvokeAI/blob/main/invokeai/app/invocations/baseinvocation.py)
- [Pydantic TypeAdapter Documentation](https://docs.pydantic.dev/latest/concepts/type_adapter/)
- [Workflow Schema Documentation](https://invoke-ai.github.io/InvokeAI/workflows/)