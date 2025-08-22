# User Guide

This comprehensive guide covers all features of the InvokeAI Python Client.

## Guide Overview

The User Guide is organized by feature area to help you find what you need quickly.

## Topics

<div class="grid cards" markdown>

-   :material-workflow: **[Workflow Basics](workflow-basics.md)**
    
    Loading, managing, and executing workflows

-   :material-form-textbox: **[Working with Inputs](inputs.md)**
    
    Discovering, accessing, and setting input values

-   :material-format-list-bulleted-type: **[Field Types](field-types.md)**
    
    Complete reference for all field types

-   :material-folder-multiple-image: **[Board Management](boards.md)**
    
    Creating boards and organizing images

-   :material-image: **[Image Operations](images.md)**
    
    Uploading, downloading, and managing images

-   :material-database: **[Model Management](models.md)**
    
    Working with AI models and synchronization

-   :material-play-circle: **[Execution Modes](execution-modes.md)**
    
    Sync, async, and streaming execution options

-   :material-map-marker: **[Output Mapping](output-mapping.md)**
    
    Mapping workflow outputs to generated images

</div>

## Quick Feature Reference

### Essential Operations

| Task | Method | Guide |
|------|--------|-------|
| Load workflow | `WorkflowDefinition.from_file()` | [Workflow Basics](workflow-basics.md) |
| List inputs | `wf.list_inputs()` | [Working with Inputs](inputs.md) |
| Set value | `wf.get_input_value(idx).value = ...` | [Field Types](field-types.md) |
| Submit | `wf.submit_sync()` | [Execution Modes](execution-modes.md) |
| Map outputs | `wf.map_outputs_to_images()` | [Output Mapping](output-mapping.md) |

### Board & Image Operations

| Task | Method | Guide |
|------|--------|-------|
| List boards | `client.board_repo.list_boards()` | [Board Management](boards.md) |
| Upload image | `board.upload_image_file()` | [Image Operations](images.md) |
| Download image | `board.download_image()` | [Image Operations](images.md) |

### Advanced Features

| Task | Method | Guide |
|------|--------|-------|
| Sync models | `wf.sync_dnn_model()` | [Model Management](models.md) |
| Async execution | `await wf.submit()` | [Execution Modes](execution-modes.md) |
| Progress tracking | `progress_callback=...` | [Execution Modes](execution-modes.md) |

## Common Workflows

### Basic Text-to-Image

```python
# 1. Load workflow
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflow.json")
)

# 2. Set inputs
wf.get_input_value(0).value = "A beautiful landscape"

# 3. Execute
result = wf.wait_for_completion_sync(
    wf.submit_sync()
)

# 4. Get images
mappings = wf.map_outputs_to_images(result)
```

### Batch Processing

```python
for prompt in prompts:
    wf.get_input_value(0).value = prompt
    result = wf.wait_for_completion_sync(wf.submit_sync())
    # Process result...
```

### Image-to-Image

```python
# Upload source image
board = client.board_repo.get_board_handle("my_board")
image_name = board.upload_image_file("source.png")

# Set as input
wf.get_input_value(IMAGE_IDX).value = image_name

# Execute workflow
result = wf.wait_for_completion_sync(wf.submit_sync())
```

## Best Practices

### 1. Index Management

Always discover and document your indices:

```python
# Run once to discover
for inp in wf.list_inputs():
    print(f"[{inp.input_index}] {inp.label}")

# Then define constants
IDX_PROMPT = 0
IDX_WIDTH = 2
IDX_HEIGHT = 3
```

### 2. Error Handling

Wrap operations in appropriate error handling:

```python
try:
    result = wf.wait_for_completion_sync(
        wf.submit_sync(), 
        timeout=180
    )
except TimeoutError:
    print("Workflow timed out")
except Exception as e:
    print(f"Workflow failed: {e}")
```

### 3. Resource Management

Clean up resources when done:

```python
# Delete uploaded images after use
for image_name in uploaded_images:
    client.delete_image(image_name)
```

## Troubleshooting

### Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| No inputs found | Add fields to Form in GUI | [Working with Inputs](inputs.md) |
| Index out of range | Re-export workflow, update indices | [Working with Inputs](inputs.md) |
| Model not found | Use `sync_dnn_model()` | [Model Management](models.md) |
| Timeout errors | Increase timeout, check server | [Execution Modes](execution-modes.md) |

## Next Steps

- Start with [Workflow Basics](workflow-basics.md) to understand workflow management
- Learn about [Field Types](field-types.md) for handling different inputs
- Explore [Examples](../examples/index.md) for complete working code
- Check the [API Reference](../api-reference/index.md) for detailed documentation