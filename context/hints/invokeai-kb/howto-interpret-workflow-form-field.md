# How to Interpret the `form` Field in InvokeAI Workflows

## Overview

The `form` field in InvokeAI workflow definitions creates a hierarchical GUI structure for user inputs. It maps UI elements to actual workflow node fields, organizing them into a user-friendly interface.

## Form Structure

### Element Types

1. **container** - Groups elements with layout (row/column)
2. **node-field** - References an actual workflow node field
3. **divider** - Visual separator
4. **text** - Static text element

### Hierarchy Organization

The form uses a tree structure with parent-child relationships:
- Root container holds top-level elements
- Containers can nest other containers
- Elements reference parents via `parentId`
- Children are ordered lists maintaining UI sequence

## JSONPath Queries for Form Analysis

### Finding All Form Elements
```jsonpath
$.form.elements.*
```

### Getting Root Container and Its Children
```jsonpath
# Root container
$.form.elements.root

# Root's direct children IDs
$.form.elements.root.data.children[*]
```

### Finding All Node-Field Elements
```jsonpath
$.form.elements[?(@.type == "node-field")]
```

### Extracting Field References
```jsonpath
# Get all field identifiers
$.form.elements[?(@.type == "node-field")].data.fieldIdentifier

# Specific field's node ID and field name
$.form.elements["node-field-I7XLCaNo7D"].data.fieldIdentifier.nodeId
$.form.elements["node-field-I7XLCaNo7D"].data.fieldIdentifier.fieldName
```

### Finding Container Layouts
```jsonpath
# All containers with their layouts
$.form.elements[?(@.type == "container")].data.layout
```

## Mapping Form Fields to Workflow Nodes

### Step 1: Identify the Form Field
```json
{
  "id": "node-field-I7XLCaNo7D",
  "type": "node-field",
  "data": {
    "fieldIdentifier": {
      "nodeId": "0a167316-ba62-4218-9fcf-b3cff7963df8",
      "fieldName": "value"
    }
  }
}
```

### Step 2: Find the Referenced Node
```jsonpath
$.nodes[?(@.id == "0a167316-ba62-4218-9fcf-b3cff7963df8")]
```

### Step 3: Get Field Label from Node
```jsonpath
# Node's label (used when field has no specific label)
$.nodes[?(@.id == "0a167316-ba62-4218-9fcf-b3cff7963df8")].data.label

# Field's specific label
$.nodes[?(@.id == "0a167316-ba62-4218-9fcf-b3cff7963df8")].data.inputs.value.label
```

## Python Example: Extracting Form Hierarchy

```python
import json

def analyze_workflow_form(workflow_json):
    """Extract and map form field hierarchy"""
    
    # Load workflow
    data = json.loads(workflow_json) if isinstance(workflow_json, str) else workflow_json
    
    # Get nodes for reference
    nodes = {n['id']: n for n in data['nodes']}
    
    # Get form elements
    form_elements = data.get('form', {}).get('elements', {})
    
    # Build hierarchy
    def process_element(elem_id, indent=0):
        elem = form_elements.get(elem_id)
        if not elem:
            return
        
        elem_type = elem.get('type')
        
        if elem_type == 'container':
            layout = elem['data'].get('layout', '')
            print(f"{'  ' * indent}container: {elem_id} [{layout}]")
            
            # Process children in order
            for child_id in elem['data'].get('children', []):
                process_element(child_id, indent + 1)
                
        elif elem_type == 'node-field':
            field_id = elem['data']['fieldIdentifier']
            node_id = field_id['nodeId']
            field_name = field_id['fieldName']
            
            # Get labels from node
            node = nodes.get(node_id, {})
            node_label = node.get('data', {}).get('label', '')
            field_label = node.get('data', {}).get('inputs', {}).get(field_name, {}).get('label', field_name)
            
            display = node_label or node['data'].get('type', 'unknown')
            print(f"{'  ' * indent}{display}: {field_label}")
    
    # Start from root
    process_element('root')
```

## Input-Index: Unique Field Identification

The `input-index` is a **critical** concept for workflow field management. Each `node-field` element gets a unique 0-based index based on depth-first tree traversal order.

### Python Example: Extracting Input Indices

```python
def extract_input_indices(workflow_json):
    """Extract input fields with their unique indices"""
    
    data = json.loads(workflow_json) if isinstance(workflow_json, str) else workflow_json
    form_elements = data.get('form', {}).get('elements', {})
    
    input_fields = []  # Will store (index, elem_id, nodeId, fieldName)
    
    def traverse_form(elem_id):
        """Traverse form tree and collect node-fields in order"""
        elem = form_elements.get(elem_id)
        if not elem:
            return
        
        elem_type = elem.get('type')
        
        if elem_type == 'container':
            # Process children in order
            for child_id in elem['data'].get('children', []):
                traverse_form(child_id)
        
        elif elem_type == 'node-field':
            field_id = elem['data']['fieldIdentifier']
            input_fields.append({
                'input_index': len(input_fields),  # 0-based index
                'element_id': elem_id,
                'node_id': field_id['nodeId'],
                'field_name': field_id['fieldName']
            })
    
    # Start traversal from root
    traverse_form('root')
    
    return input_fields

# Example usage
input_fields = extract_input_indices(workflow_data)
for field in input_fields[:5]:
    print(f"[{field['input_index']:2d}] {field['node_id']}.{field['field_name']}")
```

### Input-Index in SDXL-FLUX Workflow

The tree traversal produces this ordered list of input fields:

```
[ 0] Positive: Positive Prompt
[ 1] Negative: Negative Prompt  
[ 2] integer: Output Width
[ 3] integer: Output Height
[ 4] sdxl_model_loader: SDXL Model
[ 5] save_image: Output Board
[ 6] SDXL Generation: scheduler
[ 7] SDXL Generation: steps
[ 8] SDXL Generation: cfg_scale
...
[21] Flux Refinement: num_steps
[22] flux_controlnet: Control
[23] float_math: Noise Ratio
```

Total: 24 input fields (indices 0-23)

### Why Input-Index Matters

The `input-index` is **essential** for:

1. **API Calls**: When submitting workflow jobs, inputs may be provided as an ordered array where position matters
2. **Field Identification**: Provides a stable, unique identifier independent of internal IDs
3. **User Interface**: Determines the display order of fields in generated forms
4. **Validation**: Ensures all required fields are present and in correct positions
5. **Client Libraries**: Simplifies field access through array indexing rather than complex ID lookups

Example API usage:
```python
# Input values can be provided by index
workflow_inputs = [None] * 24  # Initialize array with 24 slots
workflow_inputs[0] = "beautiful landscape"  # Positive prompt at index 0
workflow_inputs[1] = "ugly, blurry"         # Negative prompt at index 1
workflow_inputs[2] = 1024                   # Width at index 2
workflow_inputs[3] = 768                    # Height at index 3
```

## Real Example: SDXL-FLUX Workflow

### Finding Positive Prompt Field

1. **Form element**: `node-field-I7XLCaNo7D`
2. **References**: Node `0a167316-ba62-4218-9fcf-b3cff7963df8`, field `value`
3. **Node type**: `string`
4. **Node label**: "Positive"
5. **Field label**: "Positive Prompt"
6. **Display in UI**: "Positive: Positive Prompt"

### JSONPath to get this information:
```bash
# Get form element
jq '.form.elements["node-field-I7XLCaNo7D"]' workflow.json

# Get referenced node
jq '.nodes[] | select(.id == "0a167316-ba62-4218-9fcf-b3cff7963df8")' workflow.json

# Get field label
jq '.nodes[] | select(.id == "0a167316-ba62-4218-9fcf-b3cff7963df8") | .data.inputs.value.label' workflow.json
```

## Form Hierarchy Visualization

The form creates this GUI structure with input-indices for node-fields:

[View as interactive graph (DOT source)](../../tasks/features/task-explore-workflow-1.1.dot)
```
root [column]
├── container-7c03yu1NtQ [column]
│   ├── [ 0] Positive Prompt (string node)
│   └── [ 1] Negative Prompt (string node)
├── container-NUthxkxiim [row]
│   ├── [ 2] Output Width (integer node)
│   └── [ 3] Output Height (integer node)
├── [divider]
├── [text]
├── container-jDD5sGca9b [row]
│   ├── [ 4] SDXL Model (sdxl_model_loader node)
│   └── [ 5] Output Board (save_image node)
├── container-RE4CvGerzK [row]
│   ├── [ 6] Scheduler (SDXL Generation node)
│   ├── [ 7] Steps (SDXL Generation node)
│   └── [ 8] CFG Scale (SDXL Generation node)
├── [divider]
├── [text]
├── container-AfasC3AOQk [row]
│   ├── [ 9] Positive Append (string_join_three node)
│   └── [10] Negative Append (string_join_three node)
├── container-cMoTmqMMjI [column]
│   ├── [11] Flux Model (flux_model_loader node)
│   ├── [12] T5 Encoder Model (flux_model_loader node)
│   ├── [13] CLIP Embed Model (flux_model_loader node)
│   └── [14] VAE Model (flux_model_loader node)
├── [15] Output Board (save_image node)
├── container-QHHlyRlvkH [row]
│   ├── [16] Noise Ratio (float_math node)
│   ├── [17] Num Steps (Flux Domain Transfer node)
│   └── [18] Control Weight (flux_controlnet node)
├── [divider]
├── [text]
├── [19] Flux Model (flux_model_loader node)
├── [20] Output Board (save_image node)
└── container-wV9vXi46A8 [row]
    ├── [21] Num Steps (Flux Refinement node)
    ├── [22] Control (flux_controlnet node)
    └── [23] Noise Ratio (float_math node)
```

Total: 39 elements (24 input fields with indices 0-23)

## Key Insights

1. **Form != Workflow Structure**: The form is purely for UI organization, not workflow execution order
2. **Label Hierarchy**: Field labels come from `node.data.inputs[field].label`, fallback to `node.data.label`, then `node.data.type`
3. **Exposed Fields**: Only fields in `exposedFields` array are meant to be user-configurable
   - These should match the node-field elements in the form
   - Not all form fields may be in exposedFields (UI-only elements)
4. **Container Layouts**: 
   - `row`: Horizontal arrangement
   - `column`: Vertical arrangement
5. **Field References**: Always use `nodeId` + `fieldName` to uniquely identify a workflow field
6. **Input-Index (CRITICAL)**: All `node-field` elements have a total ordering from tree traversal
   - Each input field gets a unique 0-based index called `input-index`
   - This index is determined by depth-first traversal of the form tree
   - The `input-index` uniquely identifies each input field in the workflow
   - Essential for mapping user inputs to workflow fields in API calls

## Relationship: exposedFields vs form.elements

The `exposedFields` array lists which node fields are exposed for user input:
```json
"exposedFields": [
  {"nodeId": "0a167316-...", "fieldName": "value"},  // Positive prompt
  {"nodeId": "1711c26d-...", "fieldName": "value"}   // Negative prompt
]
```

These correspond to `node-field` elements in the form:
```jsonpath
# Find form elements for exposed fields
$.form.elements[?(@.type == "node-field" && 
                  @.data.fieldIdentifier.nodeId == "0a167316-..." && 
                  @.data.fieldIdentifier.fieldName == "value")]
```

## Common Patterns

### Model Selection Fields
```jsonpath
# Find all model loader fields
$.form.elements[?(@.data.fieldIdentifier.fieldName == "model")]
```

### Output Board Fields
```jsonpath
# Find save_image board selections
$.nodes[?(@.data.type == "save_image")].id
$.form.elements[?(@.data.fieldIdentifier.fieldName == "board")]
```

### Prompt Fields
```jsonpath
# Find text input fields
$.nodes[?(@.data.type == "string")].id
$.form.elements[?(@.data.fieldIdentifier.fieldName == "value" || @.data.fieldIdentifier.fieldName == "prompt")]
```

## References

- InvokeAI Workflow Schema v3.0.0
- Example workflow: `data/workflows/sdxl-flux-refine.json`
- Related: `howto-find-invokeai-workflow-schema.md`