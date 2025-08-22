# Examples

Learn by example with these complete, working scripts for common use cases.

## About these examples

- Indices are the stable public API for workflow inputs. Always access and set inputs using their index, not labels or names.
- Only fields placed in the GUI Form are discoverable and settable. Add the parameters you want to control to the Form before exporting the workflow JSON.
- Use InvokeAIClient.from_url("http://host:port") to initialize the client; it parses host/port/base_path for you.
- After changing the Form layout, re-run list_inputs() and update your index usage accordingly.

## Example Categories

<div class="grid cards" markdown>

-   :material-text-box: **[SDXL Text-to-Image](sdxl-text-to-image.md)**
    
    Basic text-to-image generation with SDXL

-   :material-image-edit: **[FLUX Image-to-Image](flux-image-to-image.md)**
    
    Transform existing images with FLUX

-   :material-layers-triple: **[Multi-Stage Refinement](multi-stage-refine.md)**
    
    SDXL to FLUX refinement pipeline

-   :material-code-json: **[Raw API Examples](raw-api.md)**
    
    Direct REST API usage without client abstractions

</div>

## Quick Start Examples

### Minimal Text-to-Image

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# Connect and load
client = InvokeAIClient.from_url("http://localhost:9090")
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflow.json")
)

# Set prompt and generate
wf.get_input_value(0).value = "A beautiful landscape"
wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=180)

# Get images
mappings = wf.map_outputs_to_images(result)
print(f"Generated: {mappings}")
```

### Batch Processing

```python
prompts = ["Sunset", "Mountains", "Ocean"]

for prompt in prompts:
    wf.get_input_value(0).value = prompt
    wf.submit_sync()
    result = wf.wait_for_completion_sync(timeout=180)
    print(f"✓ {prompt}")
```

### Parameter Sweep

```python
for steps in [20, 30, 40]:
    for cfg in [7.0, 8.5, 10.0]:
        wf.get_input_value(4).value = steps
        wf.get_input_value(5).value = cfg
        wf.submit_sync()
        result = wf.wait_for_completion_sync(timeout=180)
        print(f"Steps={steps}, CFG={cfg}: Done")
```

## Running the Examples

### Prerequisites

1. InvokeAI server running at `http://localhost:9090`
2. Required models installed (SDXL, FLUX, etc.)
3. Workflow JSON files from `data/workflows/`

### Setup

```bash
# Clone the repository
git clone https://github.com/CodeGandee/invokeai-py-client
cd invokeai-py-client

# Install dependencies
pixi run dev-setup

# Run an example
pixi run python examples/pipelines/sdxl-text-to-image.py
```

## Example Workflows

### Available Workflow Templates

| Workflow | File | Use Case |
|----------|------|----------|
| SDXL Text-to-Image | `data/workflows/sdxl-text-to-image.json` | Basic generation |
| FLUX Image-to-Image | `data/workflows/flux-image-to-image.json` | Image transformation |
| SDXL→FLUX Refine | `data/workflows/sdxl-flux-refine.json` | Multi-stage pipeline |

### Creating Your Own Workflows

1. Design in InvokeAI GUI
2. Add parameters to Form panel
3. Export as JSON
4. Load with the client

## Common Patterns

### Error Handling

```python
try:
    wf.submit_sync()
    result = wf.wait_for_completion_sync(timeout=180)
    if result.get('status') == 'completed':
        print("Success!")
    else:
        print(f"Failed: {result.get('error_reason')}")
except TimeoutError:
    print("Workflow timed out")
except Exception as e:
    print(f"Error: {e}")
```

### Progress Monitoring

```python
def on_progress(queue_item):
    status = queue_item.get('status')
    prog = queue_item.get('progress', 0.0)  # 0.0..1.0
    print(f"[{prog*100:3.0f}%] {status}")

wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=180, progress_callback=on_progress)
```

### Image Management

```python
# Upload source image
board = client.board_repo.get_board_handle("inputs")  # or get_uncategorized_handle()
img = board.upload_image("source.png")  # returns IvkImage
source_name = img.image_name

# Use in workflow
wf.get_input_value(IMAGE_IDX).value = source_name

# Download results
mappings = wf.map_outputs_to_images(result)
for m in mappings:
    board_id = m.get('board_id', 'none')
    board = client.board_repo.get_board_handle(board_id)
    
    for name in m.get('image_names', []):
        data = board.download_image(name, full_resolution=True)
        with open(f"output_{name}", "wb") as f:
            f.write(data)
```

## Advanced Examples

### Async Parallel Processing

```python
import asyncio

async def process_prompt(client, workflow_def, prompt):
    wf = client.workflow_repo.create_workflow(workflow_def)
    wf.get_input_value(0).value = prompt
    
    submission = await wf.submit()
    result = await wf.wait_for_completion()
    
    return wf.map_outputs_to_images(result)

async def main():
    client = InvokeAIClient.from_url("http://localhost:9090")
    workflow_def = WorkflowDefinition.from_file("workflow.json")
    
    prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
    
    tasks = [
        process_prompt(client, workflow_def, p) 
        for p in prompts
    ]
    
    results = await asyncio.gather(*tasks)
    
    for prompt, result in zip(prompts, results):
        print(f"{prompt}: {result}")

asyncio.run(main())
```

### A/B Testing

```python
def ab_test(wf, prompt, cfg_values):
    results = {}
    
    for cfg in cfg_values:
        wf.get_input_value(0).value = prompt
        wf.get_input_value(5).value = cfg  # CFG index
        
        wf.submit_sync()
        result = wf.wait_for_completion_sync(timeout=180)
        mappings = wf.map_outputs_to_images(result)
        
        results[f"cfg_{cfg}"] = mappings
    
    return results

# Run A/B test
test_results = ab_test(
    wf, 
    "A majestic castle",
    [7.0, 8.5, 10.0, 12.0]
)
```

## Tips and Best Practices

### Performance

- Reuse client instances
- Pre-upload all assets
- Use async for parallel processing
- Cache workflow definitions

### Reliability

- Always check workflow status
- Implement retry logic
- Use appropriate timeouts
- Handle exceptions gracefully

### Organization

- Define index constants
- Group related operations
- Document your workflows
- Version control workflow JSONs

## Troubleshooting Examples

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Now run your workflow
wf.submit_sync()  # Will show detailed logs
```

### Validation

```python
# Validate before submission
try:
    wf.validate_inputs()
    print("✓ All inputs valid")
except ValueError as e:
    print(f"✗ Validation failed: {e}")
```

## Next Steps

- Review individual example guides for detailed walkthroughs
- Check the [API Reference](../api-reference/index.md) for all available methods
- Join the community to share your examples