# Quick Start

Run your first InvokeAI workflow in Python in just 5 minutes!

## Prerequisites

Before starting, ensure you have:

1. ✅ InvokeAI Python Client [installed](installation.md)
2. ✅ InvokeAI server running at `http://localhost:9090`
3. ✅ A workflow JSON file exported from the InvokeAI GUI

## Step 1: Export a Workflow

First, create and export a workflow from the InvokeAI GUI:

1. Open InvokeAI in your browser
2. Create or load a workflow in the Workflow Editor
3. **Important**: Add the fields you want to control to the **Form** panel
4. Click **Export** and save the JSON file

!!! tip "Form Fields = Programmable Inputs"
    Only fields added to the Form panel will be accessible from Python. Drag the parameters you want to control into the Form before exporting.

## Step 2: Basic Script

Create a Python script to load and run your workflow:

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# 1. Connect to InvokeAI
client = InvokeAIClient.from_url("http://localhost:9090")

# 2. Load your exported workflow
workflow_def = WorkflowDefinition.from_file("my-workflow.json")
wf = client.workflow_repo.create_workflow(workflow_def)

# 3. List available inputs
print("Available inputs:")
for inp in wf.list_inputs():
    print(f"  [{inp.input_index:2d}] {inp.label or inp.field_name}")

# 4. Set input values by index
# Example: Set positive prompt (usually index 0 or 1)
prompt_field = wf.get_input_value(0)
if hasattr(prompt_field, 'value'):
    prompt_field.value = "A majestic mountain landscape at sunset"

# 5. Submit and wait for completion
print("Submitting workflow...")
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=120)

# 6. Check results
if result.get('status') == 'completed':
    print("✅ Workflow completed successfully!")
    
    # Map outputs to images
    mappings = wf.map_outputs_to_images(result)
    for m in mappings:
        images = m.get('image_names', [])
        if images:
            print(f"Generated {len(images)} images: {images}")
else:
    print(f"❌ Workflow failed: {result.get('status')}")
```

## Step 3: Run the Script

Execute your script:

```bash
python my_workflow.py
```

Expected output:
```
Available inputs:
  [ 0] Positive Prompt
  [ 1] Negative Prompt
  [ 2] Width
  [ 3] Height
  [ 4] Steps
Submitting workflow...
✅ Workflow completed successfully!
Generated 1 images: ['image_abc123.png']
```

## Step 4: Download Generated Images

Add image download to your script:

```python
# After workflow completion...
mappings = wf.map_outputs_to_images(result)

for mapping in mappings:
    board_id = mapping.get('board_id', 'none')
    image_names = mapping.get('image_names', [])
    
    if image_names:
        # Get board handle
        board = client.board_repo.get_board_handle(board_id)
        
        # Download first image
        first_image = image_names[0]
        image_data = board.download_image(first_image, full_resolution=True)
        
        # Save to disk
        with open(f"output_{first_image}", "wb") as f:
            f.write(image_data)
        print(f"Saved: output_{first_image}")
```

## Complete Example: Text-to-Image

Here's a complete, working example for SDXL text-to-image:

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

def main():
    # Connect to InvokeAI
    client = InvokeAIClient.from_url("http://localhost:9090")
    
    # Load workflow
    wf = client.workflow_repo.create_workflow(
        WorkflowDefinition.from_file("sdxl-text-to-image.json")
    )
    
    # Define input indices (discover these via wf.list_inputs())
    IDX_POSITIVE = 0
    IDX_NEGATIVE = 1
    IDX_WIDTH = 2
    IDX_HEIGHT = 3
    IDX_STEPS = 4
    
    # Set parameters
    wf.get_input_value(IDX_POSITIVE).value = "A futuristic city at night"
    wf.get_input_value(IDX_NEGATIVE).value = "blurry, low quality"
    wf.get_input_value(IDX_WIDTH).value = 1024
    wf.get_input_value(IDX_HEIGHT).value = 1024
    wf.get_input_value(IDX_STEPS).value = 30
    
    # Submit and wait
    print("Generating image...")
    submission = wf.submit_sync()
    result = wf.wait_for_completion_sync(
        timeout=180,
        progress_callback=lambda r: print(f"Status: {r.get('status')}")
    )
    
    # Handle results
    if result.get('status') == 'completed':
        mappings = wf.map_outputs_to_images(result)
        for m in mappings:
            for image_name in m.get('image_names', []):
                # Download image
                board_id = m.get('board_id', 'none')
                board = client.board_repo.get_board_handle(board_id)
                data = board.download_image(image_name, full_resolution=True)
                
                # Save locally
                filename = f"generated_{image_name}"
                with open(filename, "wb") as f:
                    f.write(data)
                print(f"✅ Saved: {filename}")
    else:
        print(f"❌ Generation failed: {result}")

if __name__ == "__main__":
    main()
```

## Understanding Indices

The client uses **indices** to access workflow inputs. These indices are determined by the order of fields in your Form panel:

```python
# List all inputs with their indices
for inp in wf.list_inputs():
    print(f"[{inp.input_index}] {inp.label} ({inp.field_name})")

# Output example:
# [0] Positive Prompt (prompt)
# [1] Negative Prompt (negative_prompt)
# [2] Width (width)
# [3] Height (height)
```

!!! important "Index Stability"
    Indices remain stable as long as you don't reorder fields in the Form. If you modify the Form structure, re-run `list_inputs()` to get the new indices.

## Common Patterns

### Batch Processing

Run multiple generations with different prompts:

```python
prompts = [
    "A serene lake at sunrise",
    "A bustling cyberpunk street",
    "An ancient temple in the jungle"
]

for prompt_text in prompts:
    # Set prompt
    wf.get_input_value(0).value = prompt_text
    
    # Submit and wait
    submission = wf.submit_sync()
    result = wf.wait_for_completion_sync(timeout=120)
    
    print(f"Generated: {prompt_text}")
```

### Parameter Sweeps

Test different settings:

```python
for steps in [20, 30, 40]:
    for cfg in [7.0, 8.5, 10.0]:
        wf.get_input_value(4).value = steps  # Steps index
        wf.get_input_value(5).value = cfg    # CFG index
        
        submission = wf.submit_sync()
        result = wf.wait_for_completion_sync()
        
        print(f"Steps={steps}, CFG={cfg}: Done")
```

## Troubleshooting

### No Inputs Found

If `list_inputs()` returns empty:
- Check that you added fields to the Form panel in the GUI
- Re-export the workflow after adding fields

### Connection Refused

If you can't connect to InvokeAI:
- Verify the server is running: `curl http://localhost:9090/api/v1/app/version`
- Check the URL and port match your server configuration

### Workflow Fails

If the workflow fails to complete:
- Check server logs for errors
- Verify all required fields have values
- Ensure models referenced in the workflow are installed

## Next Steps

Now that you've run your first workflow:

- Learn about [Core Concepts](concepts.md) to understand how the client works
- Explore [Field Types](../user-guide/field-types.md) for working with different inputs
- See [Examples](../examples/index.md) for more complex use cases
- Read the [User Guide](../user-guide/index.md) for advanced features