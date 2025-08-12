# InvokeAI Concepts Documentation

This document explains the domain-specific concepts and enumerations used in the InvokeAI Python client library.

## Table of Contents
- [Image Categories](#image-categories)
- [Job Status](#job-status)
- [Base Model Architectures](#base-model-architectures)
- [Boards](#boards)
- [Workflows](#workflows)

---

## Image Categories

`ImageCategory` defines the purpose and processing role of images in InvokeAI. Each category affects how the image is handled in the generation pipeline.

### USER
**Purpose**: User-uploaded content  
**Use Cases**:
- Personal photos for img2img transformation
- Reference images for style transfer
- Source images for editing
- Initial images for variation generation

```python
# Upload a personal photo as reference
board_repo.upload_image_by_file(
    "my_photo.jpg",
    image_category=ImageCategory.USER
)
```

### GENERAL
**Purpose**: AI-generated images and general outputs  
**Use Cases**:
- Results from txt2img generation
- Outputs from img2img transformation
- Final rendered images
- General purpose generated content

```python
# Category automatically set for generated images
# When retrieving:
if image.image_category == ImageCategory.GENERAL:
    print("This is a generated image")
```

**Note**: The API uses "general" not "generated" for historical reasons.

### CONTROL
**Purpose**: ControlNet conditioning images  
**Use Cases**:
- Canny edge detection maps
- OpenPose skeleton detection
- Depth maps (MiDaS, ZoeDepth)
- Normal maps
- Segmentation maps
- Line art extraction

```python
# Upload a depth map for ControlNet
board_repo.upload_image_by_data(
    depth_map_bytes,
    ".png",
    image_category=ImageCategory.CONTROL
)
```

These images guide the AI generation process by providing structural information without dictating style or content.

### MASK
**Purpose**: Inpainting and outpainting masks  
**Use Cases**:
- Inpainting masks (white = regenerate, black = keep)
- Outpainting expansion areas
- Selective editing regions
- Layer masks for compositing

```python
# Upload an inpainting mask
board_repo.upload_image_by_data(
    mask_bytes,
    ".png",
    image_category=ImageCategory.MASK
)
```

Masks are typically binary (black/white) or grayscale images defining areas for regeneration.

### OTHER
**Purpose**: Special purpose images  
**Use Cases**:
- Intermediate processing steps
- Custom workflow artifacts
- Debugging outputs
- Experimental features

---

## Job Status

`JobStatus` represents the lifecycle of a workflow execution in InvokeAI's queue system.

### State Transitions

```
PENDING → RUNNING → COMPLETED
           ↓         ↓
         FAILED   CANCELLED
```

### PENDING
- Job is queued and waiting for available resources
- May be waiting for other jobs to complete
- Can transition to: RUNNING, CANCELLED

### RUNNING
- Job is actively being processed
- GPU/CPU resources are allocated
- Progress updates are available
- Can transition to: COMPLETED, FAILED, CANCELLED

### COMPLETED
- Job finished successfully
- Results are available
- Resources have been released
- Terminal state (no further transitions)

### FAILED
- Job encountered an error during execution
- Error details available in job.error
- Resources have been released
- Terminal state (no further transitions)

### CANCELLED
- Job was cancelled by user request or system
- Partial results may be available
- Resources have been released
- Terminal state (no further transitions)

```python
# Monitor job status
job = workflow.submit_sync()
while not job.is_complete():
    if job.status == JobStatus.RUNNING:
        print(f"Progress: {job.progress * 100:.1f}%")
    elif job.status == JobStatus.FAILED:
        print(f"Error: {job.error}")
        break
    time.sleep(1)
```

---

## Base Model Architectures

`BaseModelEnum` identifies the underlying AI model architecture, which determines capabilities and requirements.

### SD1 (Stable Diffusion 1.x)
**Characteristics**:
- Resolution: 512×512 native
- VRAM: 4-6 GB
- Speed: Fastest
- Ecosystem: Largest (most LoRAs, embeddings, checkpoints)

**Best For**:
- Quick iterations
- Limited VRAM systems
- Artistic styles (huge variety of fine-tunes)

### SD2 (Stable Diffusion 2.x)
**Characteristics**:
- Resolution: 512×512 or 768×768
- VRAM: 6-8 GB
- Speed: Moderate
- Ecosystem: Limited

**Best For**:
- Better coherence than SD1
- Less NSFW content (different training data)
- Specific SD2-trained styles

### SDXL (Stable Diffusion XL)
**Characteristics**:
- Resolution: 1024×1024 native
- VRAM: 10-12 GB
- Speed: Slower than SD1/2
- Ecosystem: Growing rapidly

**Best For**:
- High-quality, detailed images
- Professional work
- Modern photorealistic styles
- Text rendering in images

### SDXL_REFINER
**Characteristics**:
- Resolution: Same as SDXL
- VRAM: Additional 6-8 GB
- Speed: Adds 20-30% to generation time
- Purpose: Detail enhancement

**Best For**:
- Final polish on SDXL outputs
- Enhancing faces and fine details
- Typically used for last 20% of denoising steps

### FLUX
**Characteristics**:
- Resolution: Variable, up to 2048×2048
- VRAM: 24+ GB
- Speed: Slow but high quality
- Architecture: Transformer-based (different from SD)

**Best For**:
- State-of-the-art quality
- Complex prompts
- Professional production
- When quality matters more than speed

### FLUX_SCHNELL
**Characteristics**:
- Resolution: Same as FLUX
- VRAM: 16-20 GB
- Speed: 4-8 steps (much faster than FLUX)
- Quality: Good but not as refined as full FLUX

**Best For**:
- Rapid prototyping with FLUX
- Real-time applications
- When speed matters more than ultimate quality

```python
# Check model compatibility
def get_recommended_model(vram_gb: int) -> BaseModelEnum:
    if vram_gb < 6:
        return BaseModelEnum.SD1
    elif vram_gb < 12:
        return BaseModelEnum.SD2
    elif vram_gb < 24:
        return BaseModelEnum.SDXL
    else:
        return BaseModelEnum.FLUX
```

---

## Boards

Boards are InvokeAI's organizational system for managing images.

### Concepts

**Board**: A container for related images (like a folder or album)
- Has unique ID and name
- Tracks image count
- Can be archived or deleted
- Supports batch operations

**Uncategorized Board**: Special system board
- Always exists (cannot be deleted)
- ID is "none" in API calls
- Default location for images without board assignment
- Accessed via `board_id=None` in most operations

### Common Operations

```python
# Create a project board
board = client.create_board("Project XYZ")

# Upload to specific board
image = board_repo.upload_image_by_file(
    "concept.jpg",
    board_id=board.board_id
)

# Move image between boards
board_repo.move_image_to_board(
    image.image_name,
    target_board.board_id
)

# Get uncategorized images
uncategorized = board_repo.list_images("none")
```

---

## Workflows

Workflows are node-based processing pipelines that define complex generation tasks.

### Components

**Nodes**: Individual operations (prompts, models, samplers, etc.)
**Edges**: Connections between nodes defining data flow
**Form**: Public parameters exposed for user input

### Workflow Structure

```python
workflow = WorkflowDefinition(
    nodes=[
        {
            "id": "prompt_node",
            "type": "prompt",
            "data": {"text": "A beautiful landscape"}
        },
        {
            "id": "model_node", 
            "type": "main_model",
            "data": {"model": "sdxl-base"}
        },
        {
            "id": "sampler_node",
            "type": "denoise_latents",
            "data": {"steps": 30, "cfg_scale": 7.5}
        }
    ],
    edges=[
        {"source": "prompt_node", "target": "sampler_node"},
        {"source": "model_node", "target": "sampler_node"}
    ]
)
```

### Workflow Lifecycle

1. **Definition**: Create or load workflow structure
2. **Configuration**: Set input parameters
3. **Submission**: Send to queue as job
4. **Execution**: Process nodes in dependency order
5. **Completion**: Retrieve results

```python
# Load and execute workflow
workflow = client.create_workflow("my_workflow.json")
workflow.set_input("prompt", "cyberpunk city")
workflow.set_input("seed", 42)

job = workflow.submit_sync()
results = workflow.wait_for_completion_sync()
output_image = results["output_image"]
```

---

## Best Practices

### Type Safety
Always use enums instead of strings when possible:
```python
# Good - Type safe, IDE support
image_category=ImageCategory.CONTROL

# Avoid - Error prone
image_category="control"
```

### Category Selection
Choose the most specific category for your use case:
- Don't use USER for generated images
- Don't use GENERAL for control images
- Use MASK only for actual masks

### Model Selection
Consider your hardware and requirements:
- Development/Testing: SD1 for speed
- Production: SDXL or FLUX for quality
- Limited VRAM: SD1 or SD2
- Best quality: FLUX (if hardware allows)

### Board Organization
Create logical groupings:
- By project: "Website Redesign", "Product Shots"
- By style: "Photorealistic", "Anime", "Abstract"
- By status: "Draft", "Review", "Final"
- By date: "2024-01-Weekly", "2024-02-Weekly"

### Job Monitoring
Always handle all job states:
```python
if job.status == JobStatus.COMPLETED:
    process_results(job.outputs)
elif job.status == JobStatus.FAILED:
    log_error(job.error)
    retry_or_notify()
elif job.status == JobStatus.CANCELLED:
    cleanup_partial_results()
```

---

## Summary

These InvokeAI concepts form the foundation of the system:

- **ImageCategory**: Defines image purpose and processing role
- **JobStatus**: Tracks workflow execution lifecycle
- **BaseModelEnum**: Identifies AI model architecture and capabilities
- **Boards**: Organize and manage generated images
- **Workflows**: Define complex generation pipelines

Understanding these concepts is essential for effectively using the InvokeAI Python client and building applications on top of InvokeAI.