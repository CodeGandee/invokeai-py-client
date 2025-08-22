# Frequently Asked Questions

## General Questions

### What is InvokeAI Python Client?

The InvokeAI Python Client is a library that allows you to programmatically execute workflows created in the InvokeAI GUI. It provides type-safe access to workflow parameters and handles batch processing, output mapping, and asset management.

### How is this different from using the InvokeAI API directly?

The client provides several advantages over raw API calls:
- **Type Safety**: Strongly-typed field classes with validation
- **Workflow Preservation**: Your GUI-designed workflows work exactly as intended
- **Index-Based Access**: Stable parameter access that survives workflow updates
- **Automatic Mapping**: Built-in output-to-image mapping
- **Simplified Interface**: High-level methods for common operations

### Do I need to know Python to use this?

Basic Python knowledge is helpful but not required for simple use cases. The documentation includes complete examples you can adapt to your needs.

## Installation & Setup

### What Python version do I need?

Python 3.9 or higher is required. You can check your version with:
```bash
python --version
```

### How do I install the client?

The recommended method is using pixi:
```bash
pixi add invokeai-py-client
```

Or using pip:
```bash
pip install invokeai-py-client
```

### Do I need InvokeAI installed?

You need an InvokeAI server running (default: http://localhost:9090), but you don't need the full InvokeAI installation in your Python environment. The client communicates with the server via REST API.

## Workflow Questions

### Why can't I see all my workflow parameters?

Only fields added to the **Form** panel in the InvokeAI GUI are accessible from Python. To make a parameter programmable:
1. Open your workflow in the GUI
2. Drag the desired fields into the Form panel
3. Re-export the workflow JSON

### What are indices and why use them?

Indices are the position numbers of fields in your Form (0, 1, 2, ...). They provide a stable way to access inputs because:
- Field names might not be unique
- Labels can change
- Indices only change if you restructure the Form

### How do I find the index for a specific field?

List all inputs with their indices:
```python
for inp in wf.list_inputs():
    print(f"[{inp.input_index}] {inp.label or inp.field_name}")
```

### Can I modify the workflow structure from Python?

No, and this is by design. The client treats your workflow JSON as immutable - it only substitutes values, never modifies the graph structure. This ensures your carefully designed workflows work exactly as intended.

## Execution Questions

### How long do workflows take to execute?

Execution time depends on:
- Workflow complexity
- Model size (SDXL, Flux, etc.)
- Image dimensions
- Number of steps
- Server hardware

Typical ranges:
- Simple SDXL: 10-30 seconds
- Complex Flux: 60-180 seconds

### Can I run multiple workflows in parallel?

Yes! Use async execution:
```python
async def run_parallel():
    tasks = []
    for prompt in prompts:
        wf.get_input_value(0).value = prompt
        tasks.append(wf.submit())
    
    results = await asyncio.gather(*tasks)
```

### What happens if a workflow fails?

The client returns a queue item with status information. Check for errors:
```python
result = wf.wait_for_completion_sync(submission)
if result.get('status') == 'failed':
    error = result.get('error_reason')
    print(f"Workflow failed: {error}")
```

## Board & Image Questions

### What is the "none" board?

The "none" board (with string ID `"none"`) is the uncategorized board in InvokeAI. Images not assigned to a specific board go here by default.

### How do I download generated images?

After workflow completion:
```python
mappings = wf.map_outputs_to_images(result)
for m in mappings:
    board_id = m.get('board_id', 'none')
    board = client.board_repo.get_board_handle(board_id)
    
    for image_name in m.get('image_names', []):
        data = board.download_image(image_name, full_resolution=True)
        with open(f"output_{image_name}", "wb") as f:
            f.write(data)
```

### Can I upload images for image-to-image workflows?

Yes, upload to a board first:
```python
board = client.board_repo.get_board_handle("my_board")
image_name = board.upload_image_file("source.png")

# Then use as input
wf.get_input_value(IMAGE_IDX).value = image_name
```

## Model Questions

### What does sync_dnn_model do?

Model synchronization matches model references in your workflow to models available on the server. This is useful when:
- Model names differ between export and server
- You're sharing workflows between installations
- Models have been updated

### Why does my workflow fail with "model not found"?

The model referenced in your workflow doesn't match server records. Fix with:
```python
wf.sync_dnn_model(by_name=True, by_base=True)
```

## Performance Questions

### How can I speed up batch processing?

1. **Use async execution** for parallel processing
2. **Reuse client instances** to avoid connection overhead
3. **Batch similar operations** together
4. **Pre-upload all assets** before starting
5. **Use appropriate timeouts** to fail fast

### Is there a rate limit?

The client doesn't impose rate limits, but your InvokeAI server might. Check server configuration for queue limits and concurrent execution settings.

## Troubleshooting

### Connection refused error

1. Check if InvokeAI is running:
   ```bash
   curl http://localhost:9090/api/v1/app/version
   ```
2. Verify the URL matches your server
3. Check firewall/security settings

### No inputs found

- Ensure fields are in the Form panel
- Re-export the workflow after changes
- Check that the workflow file loaded correctly

### Index out of range

- The Form structure changed
- Re-run `list_inputs()` to see current indices
- Update your index constants

### Images not mapping to outputs

- Ensure output nodes have board fields exposed in Form
- Check that the workflow completed successfully
- Verify board permissions

## Advanced Topics

### Can I extend the client with custom field types?

Yes! See the [Developer Guide](developer-guide/extensions.md) for instructions on adding new field types.

### How do I contribute to the project?

We welcome contributions! See our [Contributing Guide](developer-guide/contributing.md) for details.

### Where can I get help?

- **GitHub Issues**: [Report bugs](https://github.com/CodeGandee/invokeai-py-client/issues)
- **Discussions**: [Ask questions](https://github.com/CodeGandee/invokeai-py-client/discussions)
- **Discord**: Join the InvokeAI community

## Migration & Compatibility

### Is this compatible with all InvokeAI versions?

The client targets InvokeAI 4.0+. Check compatibility:
```python
# In your InvokeAI server
http://localhost:9090/api/v1/app/version
```

### Can I use old workflow JSON files?

Yes, as long as they were exported from a compatible InvokeAI version and include the Form structure.