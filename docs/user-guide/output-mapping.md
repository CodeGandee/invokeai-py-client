# Output Mapping

Learn how to extract and map workflow outputs to meaningful results.

## Overview

Output mapping is essential for:
- **Result extraction**: Getting generated images from workflow outputs
- **Multi-output handling**: Managing workflows with multiple outputs
- **Metadata preservation**: Maintaining generation parameters
- **Batch result processing**: Handling results from batch operations

## Understanding Workflow Outputs

### Output Structure

```python
# Workflow output structure
result = {
    'status': 'COMPLETED',
    'session_id': 'abc123',
    'invocation_outputs': [
        {
            'invocation_id': 'node_123',
            'invocation_type': 'l2i',  # Latents to image
            'outputs': {
                'image': {
                    'image_name': 'output_xyz.png',
                    'width': 1024,
                    'height': 1024,
                    'board_id': 'results_board'
                }
            }
        },
        # More invocation outputs...
    ]
}
```

### Output Types

```python
# Common output types
output_types = {
    'l2i': 'Latents to Image - final image output',
    'nsfw_checker': 'NSFW detection results',
    'metadata': 'Generation metadata',
    'img_resize': 'Resized image output',
    'img_watermark': 'Watermarked image',
    'canvas_paste': 'Canvas composite output'
}
```

## Basic Output Mapping

### Map to Images

```python
def map_outputs_to_images(result):
    """Extract all images from workflow result."""
    images = []
    
    if result.get('status') != 'COMPLETED':
        return images
    
    for output in result.get('invocation_outputs', []):
        outputs = output.get('outputs', {})
        
        # Check for image output
        if 'image' in outputs:
            image_info = outputs['image']
            images.append({
                'name': image_info['image_name'],
                'width': image_info.get('width'),
                'height': image_info.get('height'),
                'board_id': image_info.get('board_id'),
                'node_id': output['invocation_id'],
                'type': output['invocation_type']
            })
    
    return images

# Use the mapping
result = wf.wait_for_completion_sync(submission)
images = map_outputs_to_images(result)

for img in images:
    print(f"Generated: {img['name']} ({img['width']}x{img['height']})")
```

### WorkflowHandle Helper

```python
# Built-in output mapping
images = wf.map_outputs_to_images(result)

for image_name in images:
    print(f"Image: {image_name}")
    
    # Download the image
    board = client.board_repo.get_board_handle("results")
    image_data = board.download_image(image_name)
```

## Advanced Output Mapping

### Filter by Node Type

```python
def get_outputs_by_type(result, node_type):
    """Get outputs from specific node types."""
    outputs = []
    
    for output in result.get('invocation_outputs', []):
        if output['invocation_type'] == node_type:
            outputs.append(output['outputs'])
    
    return outputs

# Get only final images (l2i nodes)
final_images = get_outputs_by_type(result, 'l2i')

# Get metadata outputs
metadata = get_outputs_by_type(result, 'metadata')
```

### Map by Node ID

```python
def get_output_by_node_id(result, node_id):
    """Get output from specific node."""
    for output in result.get('invocation_outputs', []):
        if output['invocation_id'] == node_id:
            return output['outputs']
    return None

# Get output from specific node
node_output = get_output_by_node_id(result, 'main_output_node')
if node_output and 'image' in node_output:
    image_name = node_output['image']['image_name']
```

## Multi-Output Workflows

### Handle Multiple Outputs

```python
def map_multi_output_workflow(result):
    """Map outputs from workflow with multiple output nodes."""
    outputs = {
        'main_image': None,
        'refined_image': None,
        'thumbnail': None,
        'metadata': {}
    }
    
    for output in result.get('invocation_outputs', []):
        node_id = output['invocation_id']
        node_outputs = output['outputs']
        
        # Map based on node ID or type
        if 'main_l2i' in node_id:
            outputs['main_image'] = node_outputs.get('image')
        elif 'refiner_l2i' in node_id:
            outputs['refined_image'] = node_outputs.get('image')
        elif 'thumbnail' in node_id:
            outputs['thumbnail'] = node_outputs.get('image')
        elif output['invocation_type'] == 'metadata':
            outputs['metadata'].update(node_outputs)
    
    return outputs

# Process multi-output result
mapped = map_multi_output_workflow(result)

if mapped['main_image']:
    print(f"Main: {mapped['main_image']['image_name']}")
if mapped['refined_image']:
    print(f"Refined: {mapped['refined_image']['image_name']}")
```

### Output Collections

```python
def map_collection_outputs(result):
    """Map outputs that produce collections."""
    collections = {}
    
    for output in result.get('invocation_outputs', []):
        outputs = output['outputs']
        
        # Check for collection outputs
        if 'collection' in outputs:
            collection_name = output['invocation_id']
            collections[collection_name] = outputs['collection']
        
        # Check for image collection
        if 'images' in outputs:
            collections[f"{output['invocation_id']}_images"] = outputs['images']
    
    return collections
```

## Metadata Extraction

### Extract Generation Parameters

```python
def extract_generation_metadata(result):
    """Extract generation parameters from result."""
    metadata = {
        'prompt': None,
        'negative_prompt': None,
        'seed': None,
        'steps': None,
        'cfg_scale': None,
        'model': None,
        'dimensions': None
    }
    
    for output in result.get('invocation_outputs', []):
        node_type = output['invocation_type']
        outputs = output['outputs']
        
        # Extract from different node types
        if node_type == 'compel' and 'prompt' in outputs:
            if 'positive' in output['invocation_id']:
                metadata['prompt'] = outputs['prompt']
            else:
                metadata['negative_prompt'] = outputs['prompt']
        
        elif node_type == 'noise' and 'seed' in outputs:
            metadata['seed'] = outputs['seed']
        
        elif node_type == 'denoise' and 'steps' in outputs:
            metadata['steps'] = outputs['steps']
            metadata['cfg_scale'] = outputs.get('cfg_scale')
        
        elif node_type == 'l2i' and 'image' in outputs:
            img = outputs['image']
            metadata['dimensions'] = f"{img['width']}x{img['height']}"
    
    return metadata

# Extract and display metadata
meta = extract_generation_metadata(result)
print(f"Generated with: {meta['prompt'][:50]}...")
print(f"Seed: {meta['seed']}, Steps: {meta['steps']}")
```

### Preserve Workflow Context

```python
def create_result_package(wf, submission, result):
    """Create comprehensive result package."""
    images = wf.map_outputs_to_images(result)
    
    package = {
        'session_id': submission['session_id'],
        'workflow_name': wf.definition.meta.get('name', 'unnamed'),
        'timestamp': datetime.now().isoformat(),
        'status': result['status'],
        'images': images,
        'metadata': extract_generation_metadata(result),
        'input_values': {}
    }
    
    # Include input values
    for inp in wf.list_inputs():
        field = wf.get_input_value(inp.input_index)
        if hasattr(field, 'value'):
            package['input_values'][inp.label] = field.value
    
    return package

# Create full result package
package = create_result_package(wf, submission, result)
save_json(package, f"results/{package['session_id']}.json")
```

## Batch Processing Results

### Map Batch Results

```python
def process_batch_results(results):
    """Process results from batch execution."""
    batch_output = {
        'successful': [],
        'failed': [],
        'statistics': {
            'total': len(results),
            'completed': 0,
            'failed': 0,
            'images_generated': 0
        }
    }
    
    for i, result in enumerate(results):
        if result['status'] == 'COMPLETED':
            images = map_outputs_to_images(result)
            batch_output['successful'].append({
                'index': i,
                'images': images,
                'count': len(images)
            })
            batch_output['statistics']['completed'] += 1
            batch_output['statistics']['images_generated'] += len(images)
        else:
            batch_output['failed'].append({
                'index': i,
                'status': result['status'],
                'error': result.get('error')
            })
            batch_output['statistics']['failed'] += 1
    
    return batch_output

# Process batch
batch_results = []
for params in batch_params:
    wf.apply_params(params)
    submission = wf.submit_sync()
    result = wf.wait_for_completion_sync(submission)
    batch_results.append(result)

batch_output = process_batch_results(batch_results)
print(f"Batch complete: {batch_output['statistics']}")
```

### Aggregate Outputs

```python
def aggregate_batch_outputs(results, output_board):
    """Aggregate all outputs to single board."""
    all_images = []
    
    for result in results:
        if result['status'] == 'COMPLETED':
            images = map_outputs_to_images(result)
            all_images.extend(images)
    
    # Move all to output board
    board = client.board_repo.get_board_handle(output_board)
    for img_info in all_images:
        if img_info['board_id'] != output_board:
            # Move image to aggregate board
            move_image(client, img_info['name'], 
                      img_info['board_id'], output_board)
    
    return len(all_images)
```

## Error Handling

### Safe Output Mapping

```python
def safe_map_outputs(result):
    """Safely map outputs with error handling."""
    try:
        if not result:
            return {'error': 'No result provided', 'images': []}
        
        if result.get('status') != 'COMPLETED':
            return {
                'error': f"Workflow {result.get('status', 'UNKNOWN')}",
                'images': []
            }
        
        images = map_outputs_to_images(result)
        
        if not images:
            return {'warning': 'No images generated', 'images': []}
        
        return {'success': True, 'images': images}
        
    except Exception as e:
        return {'error': str(e), 'images': []}

# Use safe mapping
mapped = safe_map_outputs(result)
if mapped.get('success'):
    for img in mapped['images']:
        print(f"Success: {img['name']}")
else:
    print(f"Issue: {mapped.get('error') or mapped.get('warning')}")
```

### Partial Results

```python
def handle_partial_results(result):
    """Handle workflows that partially complete."""
    all_outputs = []
    errors = []
    
    for output in result.get('invocation_outputs', []):
        if 'error' in output:
            errors.append({
                'node': output['invocation_id'],
                'error': output['error']
            })
        elif 'outputs' in output:
            all_outputs.append(output)
    
    # Extract what we can
    images = []
    for output in all_outputs:
        if 'image' in output.get('outputs', {}):
            images.append(output['outputs']['image']['image_name'])
    
    return {
        'partial': True,
        'images': images,
        'errors': errors,
        'completion_rate': len(all_outputs) / 
                          (len(all_outputs) + len(errors))
    }
```

## Output Formats

### JSON Export

```python
def export_results_json(result, filepath):
    """Export results to JSON format."""
    export_data = {
        'session_id': result.get('session_id'),
        'status': result.get('status'),
        'images': map_outputs_to_images(result),
        'metadata': extract_generation_metadata(result),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    return filepath
```

### CSV Export

```python
import csv

def export_results_csv(results, filepath):
    """Export batch results to CSV."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['session_id', 'image_name', 'width', 
                        'height', 'prompt', 'seed', 'status'])
        
        for result in results:
            meta = extract_generation_metadata(result)
            images = map_outputs_to_images(result)
            
            for img in images:
                writer.writerow([
                    result.get('session_id'),
                    img['name'],
                    img.get('width'),
                    img.get('height'),
                    meta.get('prompt', '')[:100],
                    meta.get('seed'),
                    result.get('status')
                ])
    
    return filepath
```

## Performance Optimization

### Lazy Output Loading

```python
class LazyOutputMapper:
    """Lazy load outputs only when accessed."""
    
    def __init__(self, result):
        self.result = result
        self._images = None
        self._metadata = None
    
    @property
    def images(self):
        if self._images is None:
            self._images = map_outputs_to_images(self.result)
        return self._images
    
    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = extract_generation_metadata(self.result)
        return self._metadata
    
    def get_image(self, index=0):
        """Get specific image by index."""
        if index < len(self.images):
            return self.images[index]
        return None

# Use lazy mapper
mapper = LazyOutputMapper(result)
# Images only extracted when accessed
if mapper.images:
    print(f"Generated {len(mapper.images)} images")
```

### Selective Mapping

```python
def map_selected_outputs(result, output_filter):
    """Map only selected outputs."""
    selected = []
    
    for output in result.get('invocation_outputs', []):
        if output_filter(output):
            selected.append(output['outputs'])
    
    return selected

# Map only l2i outputs
l2i_only = map_selected_outputs(
    result,
    lambda o: o['invocation_type'] == 'l2i'
)

# Map outputs from specific nodes
specific_nodes = map_selected_outputs(
    result,
    lambda o: o['invocation_id'] in ['node1', 'node2']
)
```

## Best Practices

### 1. Always Check Status

```python
# Always verify completion before mapping
if result.get('status') == 'COMPLETED':
    images = wf.map_outputs_to_images(result)
else:
    print(f"Workflow failed: {result.get('status')}")
    images = []
```

### 2. Handle Missing Outputs

```python
# Defensive output access
for output in result.get('invocation_outputs', []):
    outputs = output.get('outputs', {})
    if image := outputs.get('image'):
        # Process image
        pass
```

### 3. Document Expected Outputs

```python
"""
Workflow: SDXL Text-to-Image
Expected Outputs:
- l2i node: Final generated image
- nsfw_checker: Safety check results
- metadata node: Generation parameters
"""
```

## Next Steps

- Learn about [Boards](boards.md) for organizing outputs
- Explore [Image Operations](images.md) for handling results
- Master [Execution Modes](execution-modes.md) for different patterns
- Review [Workflow Basics](workflow-basics.md) for complete examples