# General Information for All Tasks

- client api source code: `src/invokeai_py_client`
- terminology and concepts: `context/design/terminology.md`
- useful information for testing: `context/tasks/info/info-test-data.md`

if you are not sure about the InvokeAI web APIs:
- Look for the demos first: `<workspace>/examples`
- InvokeAI openapi json: `context\hints\invokeai-kb\invokeai-openapi.json`, use `jq` for faster search
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

## Requirements of the workflow subsystem in `client-api`

### Before you start
in below, we use `data\workflows\flux-image-to-image.json` as an example workflow definition file, denote this as `example-workflow.json`.

we already have partial implementation of the workflow subsystem in `src\invokeai_py_client\workflow.py`, but it is not complete, and the APIs are subject to change.

### Requirements

- The `client-api` should have a `workflow-repo` that manages the workflows, just like the `board-repo` (see `src\invokeai_py_client\repositories\board.py`), it should have methods to list, get, create, delete workflows, and also methods to upload and download workflow definitions.

- our design should work with any workflow definition that is exported from the InvokeAI GUI.

- each workflow has different kinds of nodes, and different numbers of inputs and outputs. Note that, workflows typically write their outputs to a `board`, so in order to find out the outputs of a workflow, we need to look at the nodes in the workflow and see which nodes write to which boards.

- in GUI, user can add some of the fields of the nodes as inputs, by adding them to the `form` section of the workflow definition, these fields are called `workflow-inputs`, they map to some of the fields in the nodes, and they are somewhat like the public interface of the workflow. Our API should capture this concept, and expose these `workflow-inputs` to the user, allowing direct field manipulation through the `get_input` method.

- we know that InvokeAI has a type system, some of them are already defined in our data models, see `src\invokeai_py_client\models.py`, for more info you can see `context\hints\invokeai-kb\about-invokeai-workflow-input-types.md`. We shall define data models for these types (naming them as `Ivk<TypeName>`), and use these data models for the workflow input fields.

- we know that heavy data like images and masks are referred to by their names in the workflow definition, the names are given by the InvokeAI backend when these data are uploaded to the backend, and to get the actual data, we need to download them from the backend given the names. 
  
- when everything is set, we can submit the workflow to the backend, and InvokeAI will execute the workflow, the execution will create a job, and we can track the job status, and get the results back when the job is done. The results will be in the form of `client-types`, which can be used to get the output. `examples/` contains some demos of how to interact with InvokeAI backend about workflows, you can refer to them for more details.

- note that, after everything is done, results are retrieved, those inputs and outputs uploaded to InvokeAI can be discarded, we need to explicitly delete them in the backend, otherwise they will stay in the backend and occupy space.
  
## Workflow subsystem usage pattern

here we describe the use cases of the workflow subsystem in `client-api`, before designing the API, we need to understand how users will use it.

Below we use `data\workflows\sdxl-flux-refine.json` as an example workflow definition file, denote this as `example-workflow.json`, some useful info as to how to find things can be found in `context\tasks\features\task-explore-workflow.md`

### Use case 1: loading `example-workflow.json` and listing inputs

**Scenario**: A developer wants to load a SDXL-FLUX workflow from a JSON file and discover what inputs can be configured before execution.

**Code Example**:
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition, WorkflowHandle, IvkWorkflowInput
from invokeai_py_client.ivk_fields import IvkField
from typing import List, Optional

# Initialize the client
client = InvokeAIClient.from_url("http://localhost:9090")

# Step 1: Load workflow definition from JSON file
workflow_def = WorkflowDefinition.from_file("data/workflows/sdxl-flux-refine.json")

# Alternative: Load from dict
# with open("data/workflows/sdxl-flux-refine.json", "r") as f:
#     workflow_dict = json.load(f)
# workflow_def = WorkflowDefinition.from_dict(workflow_dict)

# Step 2: Create workflow handle using the repository pattern
# The WorkflowRepository creates and manages WorkflowHandle instances
workflow_handle: WorkflowHandle = client.workflow_repo.create_workflow_handle(workflow_def)

# Basic workflow information (from WorkflowDefinition properties)
print(f"Workflow: {workflow_handle.definition.name}")
print(f"Description: {workflow_handle.definition.description}")
print(f"Version: {workflow_handle.definition.version}")
print(f"Author: {workflow_handle.definition.author}")
print()

# List all configurable inputs (returns list ordered by input-index)
inputs: List[IvkWorkflowInput] = workflow_handle.list_inputs()

print(f"Total configurable inputs: {len(inputs)}")
print("=" * 60)

# Inputs are accessed by index (0-based) based on form tree traversal order
for idx, input_info in enumerate(inputs):
    # IvkWorkflowInput has typed properties with IvkField base
    print(f"\n[{idx}] {input_info.label}")
    print(f"  Node: {input_info.node_name} ({input_info.node_id})")
    print(f"  Field: {input_info.field_name}")
    print(f"  Type: {type(input_info.field).__name__}")  # e.g., IvkStringField (subclass of IvkField)
    print(f"  Required: {input_info.required}")
    
    # Show current value if the field has a value property
    # Note: Not all IvkField subclasses have a 'value' property
    # Primitive fields (String, Integer, Float, Boolean) and some others do
    if hasattr(input_info.field, 'value'):
        current_value = input_info.field.value
        if current_value is not None:
            print(f"  Current Value: {current_value}")
    else:
        # For fields without 'value' (e.g., IvkColorField has r,g,b,a)
        print(f"  Current State: {input_info.field.to_json_dict()}")

# Access inputs by index - the primary way to get/set inputs
positive_prompt: IvkWorkflowInput = workflow_handle.get_input(0)  # Index [0] is Positive Prompt
negative_prompt: IvkWorkflowInput = workflow_handle.get_input(1)  # Index [1] is Negative Prompt
width_input: IvkWorkflowInput = workflow_handle.get_input(2)      # Index [2] is Output Width
height_input: IvkWorkflowInput = workflow_handle.get_input(3)     # Index [3] is Output Height

# Example: Print information about a specific input
print(f"\nInput at index 0:")
print(f"  Label: {positive_prompt.label}")  # "Positive Prompt"
print(f"  Node: {positive_prompt.node_name}")  # "Positive" (from node's label field)
print(f"  Field: {positive_prompt.field_name}")  # "value"

# Get all inputs as an indexed list
all_inputs: List[IvkWorkflowInput] = workflow_handle.list_inputs()
# Returns ordered list where index matches input-index:
# [
#     IvkWorkflowInput(...),  # [0] Positive Prompt with IvkField subclass
#     IvkWorkflowInput(...),  # [1] Negative Prompt with IvkField subclass
#     IvkWorkflowInput(...),  # [2] Output Width with IvkField subclass
#     ...                      # up to [23] for this workflow
# ]

# Find input by searching (returns index, or None if not found)
def find_input_index(workflow_handle: WorkflowHandle, node_name: str, field_name: str) -> Optional[int]:
    """Helper to find input index by node/field names if needed."""
    for idx, input_info in enumerate(workflow_handle.list_inputs()):
        if input_info.node_name == node_name and input_info.field_name == field_name:
            return idx
    return None

# Example: Find the FLUX model input
flux_model_idx = find_input_index(workflow_handle, "flux_model_loader", "model")
if flux_model_idx is not None:
    flux_model_input = workflow_handle.get_input(flux_model_idx)
    print(f"\nFound FLUX model input at index {flux_model_idx}")

# Check which required inputs are missing values
missing_inputs = [inp for inp in workflow_handle.list_inputs() 
                   if inp.required and hasattr(inp.field, 'value') and inp.field.value is None]
if missing_inputs:
    print(f"\nRequired inputs still needed:")
    for inp in missing_inputs:
        print(f"  [{inp.input_index}] {inp.label}")

# Alternative: Get another workflow handle for the same definition
# This creates a new instance with independent state
another_workflow = client.workflow_repo.create_workflow_handle(workflow_def)

# Or retrieve an existing workflow handle by ID (if implemented)
# existing_workflow = client.workflow_repo.get_workflow_handle(workflow_id)
```

**Expected Output**:
```
Workflow: SDXL then FLUX
Description: Multi-stage image generation workflow
Version: 3.0.0
Author: InvokeAI

Total configurable inputs: 24
============================================================

[0] Positive Prompt
  Node: Positive (0a167316-ba62-4218-9fcf-b3cff7963df8)
  Field: value
  Type: IvkStringField
  Required: True

[1] Negative Prompt
  Node: Negative (1711c26d-e362-48fa-8f02-3e3e1a6010d4)
  Field: value
  Type: IvkStringField
  Required: True

[2] Output Width
  Node: integer (8e860322-3d35-4013-ab38-29e41af698ed)
  Field: value
  Type: IvkIntegerField
  Required: False
  Current Value: 1024

[3] Output Height
  Node: integer (3e13ab2d-7bd2-4303-b6c5-2c58c51bf2bb)
  Field: value
  Type: IvkIntegerField
  Required: False
  Current Value: 768

[4] SDXL Model
  Node: sdxl_model_loader (fc066a36-5d48-4780-8c2b-d76c70ae0807)
  Field: model
  Type: IvkModelIdentifierField
  Required: True

[5] Output Board
  Node: save_image (4414d4b5-82c3-4513-8c3f-86d88c24aadc)
  Field: board
  Type: IvkBoardField
  Required: False

...

[23] Noise Ratio
  Node: float_math (e6187b94-cd8a-4fa8-b020-c6c858dc43de)
  Field: value
  Type: IvkFloatField
  Required: False
  Current Value: 0.8

Input at index 0:
  Label: Positive Prompt
  Node: Positive            # From node's "label" field in JSON
  Field: value

Input at index 4:
  Label: SDXL Model
  Node: sdxl_model_loader   # Node's "label" was empty, so using "type" (InvokeAI default)
  Field: model

Found FLUX model input at index 11

Required inputs still needed at indices: [0, 1, 4, 11, 12, 13, 14, 19]
  [0] Positive Prompt
  [1] Negative Prompt
  [4] SDXL Model
  [11] Flux Model
  [12] T5 Encoder Model
  [13] CLIP Embed Model
  [14] VAE Model
  [19] Flux Model
```

**Key Design Points**:

1. **Repository Pattern Architecture**: 
   - **WorkflowRepository** - Manages workflow lifecycle, creates and tracks WorkflowHandle instances
   - **WorkflowHandle** - Represents the running state of a workflow, manages inputs and execution
   - **WorkflowDefinition** - Pydantic model for workflow JSON structure (in `workflow_model.py`)
   - Follows same pattern as BoardRepository/BoardHandle for consistency

2. **Data Model Hierarchy**:
   - `IvkWorkflowInput` - Typed data model containing:
     - `label`: User-facing field label (e.g., "Positive Prompt")
     - `node_name`: Node's display name - uses node's "label" field if not empty, otherwise falls back to node's "type" (InvokeAI default)
     - `node_id`: UUID of the workflow node
     - `field_name`: Name of the field in the node (e.g., "value")
     - `field`: IvkField subclass instance (`IvkStringField`, `IvkImageField`, etc.)
     - `required`: Boolean indicating if the input must be provided
   - All field types inherit from `IvkField` base class (renamed from `Field` to avoid conflicts)

3. **Index-Based Access System**:
   - **Input-index**: 0-based index from depth-first form tree traversal
   - Primary access via `workflow_handle.get_input(index)` method
   - Stable ordering guaranteed by form structure
   - Eliminates naming conflicts completely

4. **Type Safety with IvkField**: 
   - All field types are subclasses of `IvkField[T]` generic base
   - `workflow_handle.list_inputs()` returns ordered `List[IvkWorkflowInput]`
   - `workflow_handle.get_input(idx)` returns `IvkWorkflowInput` at that index
   - Field values accessed via direct property access (e.g., `field.value` for primitives)
   - Each field is a typed instance with proper validation

5. **Input Discovery**:
   - Iterate through ordered list to find inputs by properties
   - Helper functions can search by node/field names if needed
   - Missing inputs tracked by indices for clear identification
   - No ambiguity in input references
   - Repository pattern allows creating multiple workflow handles from same definition

### Use case 2: setting inputs of the `example-workflow.json`

**Scenario**: After loading the workflow (from Use Case 1), the developer needs to set values for each input before execution.

**Important Note**: Not all IvkField subclasses have a `value` property:
- **Primitive fields** (IvkStringField, IvkIntegerField, IvkFloatField, IvkBooleanField): Have `value` property
- **Resource fields** (IvkImageField, IvkBoardField, IvkLatentsField, IvkTensorField): Have `value` property
- **Enum fields** (IvkEnumField, IvkSchedulerField): Have `value` property
- **Collection fields** (IvkCollectionField): Have `value` property (a list)
- **Model identifier field** (IvkModelIdentifierField): Uses direct properties (key, hash, name, base, type, submodel_type) - NO `value` property
- **Complex fields** (IvkColorField, IvkBoundingBoxField): Use specific properties instead (e.g., r,g,b,a or x_min,y_min,x_max,y_max)
- **Composite fields** (IvkUNetField, IvkCLIPField, IvkVAEField): Have structured properties, no single `value`

**Code Example**:
```python
# Continuing from Use Case 1, we have:
# - client: InvokeAIClient instance
# - workflow_handle: WorkflowHandle instance with loaded sdxl-flux-refine definition

# Note: All field classes are Pydantic models with validate_assignment=True

# Method 1: Type-aware field access - ALWAYS check field type or hasattr before accessing
# This is the safest approach for production code

# Example: Set text prompts (checking for value property first)
prompt_input = workflow_handle.get_input(0)
if hasattr(prompt_input.field, 'value'):
    prompt_input.field.value = "A serene mountain landscape at sunset, photorealistic, high detail"
else:
    # Handle complex field types
    print(f"Field type {type(prompt_input.field).__name__} doesn't use 'value' property")
    print(f"Available properties: {prompt_input.field.to_json_dict()}")

# Method 1a: Using get_input_value() for cleaner direct field access
# This is preferred when you know the field type
from invokeai_py_client.ivk_fields import IvkStringField, IvkColorField, IvkBoundingBoxField

prompt_field = workflow_handle.get_input_value(0)  # Returns IvkField directly
if isinstance(prompt_field, IvkStringField):
    prompt_field.value = "A serene mountain landscape at sunset, photorealistic, high detail"

negative_field = workflow_handle.get_input_value(1)
if isinstance(negative_field, IvkStringField):
    negative_field.value = "blurry, low quality, distorted"

# Set dimensions (type-safe approach)
width_field = workflow_handle.get_input_value(2)
if hasattr(width_field, 'value'):
    width_field.value = 1024  # Pydantic converts "1024" string automatically

height_field = workflow_handle.get_input_value(3)
if hasattr(height_field, 'value'):
    height_field.value = 768

# Method 2: Handle fields WITHOUT value property using type checking
# Example: If encountering a color field
color_index = 10  # hypothetical index
color_field = workflow_handle.get_input_value(color_index)
if isinstance(color_field, IvkColorField):
    # IvkColorField uses r,g,b,a properties, not value
    color_field.r = 255
    color_field.g = 128
    color_field.b = 0
    color_field.a = 255
    # Or use the helper method
    color_field.set_rgba(255, 128, 0, 255)
    # Or set from hex
    color_field.set_hex("#FF8000")

# Example: If encountering a bounding box field
bbox_index = 11  # hypothetical index
bbox_field = workflow_handle.get_input_value(bbox_index)
if isinstance(bbox_field, IvkBoundingBoxField):
    # IvkBoundingBoxField uses x_min, y_min, x_max, y_max, not value
    bbox_field.x_min = 0
    bbox_field.y_min = 0
    bbox_field.x_max = 512
    bbox_field.y_max = 512
    # Or use the helper method
    bbox_field.set_box(0, 0, 512, 512)


# Method 2: Complete field replacement using set_input_value()
# This method replaces the entire field instance - most general approach
# Useful when you need to create fields with specific configurations

# Example 1: Replace a string field with constraints
original_field = workflow_handle.get_input_value(0)
field_type = type(original_field)

# Create new field of same type with specific configuration
new_prompt_field = field_type(
    value="A majestic dragon soaring through clouds",
    min_length=10,
    max_length=500
)

# Replace the entire field (enforces type consistency)
workflow_handle.set_input_value(0, new_prompt_field)

# Example 2: Replace a model field with all properties
original_model = workflow_handle.get_input_value(4)
if isinstance(original_model, IvkModelIdentifierField):
    # Create new model field with all required properties
    new_model_field = IvkModelIdentifierField(
        key="sdxl-turbo-key-999",
        hash="blake3:turbo999xyz",
        name="SDXL Turbo",
        base="sdxl",
        type="main",
        submodel_type=None
    )
    workflow_handle.set_input_value(4, new_model_field)

# Example 3: Replace a color field
color_index = 10  # hypothetical
original_color = workflow_handle.get_input_value(color_index)
if isinstance(original_color, IvkColorField):
    new_color_field = IvkColorField(r=128, g=64, b=255, a=200)
    workflow_handle.set_input_value(color_index, new_color_field)

# Example of validation error handling
try:
    # This will fail validation - steps must be positive integer
    step_field = workflow_handle.get_input_value(7)
    if isinstance(step_field, IvkIntegerField):
        step_field.value = -5  # Will raise ValueError
except ValueError as e:
    print(f"Field validation error: {e}")
    # Set valid value
    step_field.value = 25

# Validate all inputs
validation_errors = workflow_handle.validate_inputs()
if validation_errors:
    print("Validation errors found:")
    for idx, errors in validation_errors.items():
        input_info = workflow_handle.get_input(idx)
        print(f"  [{idx}] {input_info.label}: {', '.join(errors)}")
else:
    print("All inputs are valid, workflow ready for submission")
```

**Expected Output**:
```
✓ Set [0] Positive Prompt
✓ Set [1] Negative Prompt
✓ Set [2] Output Width
✓ Set [3] Output Height
✓ Set [4] SDXL Model
✓ Set [5] Output Board
✓ Set [6] Scheduler
✓ Set [7] Steps
✓ Set [8] CFG Scale
...
✓ Set [23] Noise Ratio

Field validation error: ensure this value is greater than 0
All inputs are valid
All required inputs are set, workflow ready for submission
```

**Key Design Points**:

1. **Field Property Patterns**:
   - **Fields WITH `.value` property**: 
     - Primitives: IvkStringField, IvkIntegerField, IvkFloatField, IvkBooleanField
     - Resources: IvkImageField, IvkBoardField, IvkLatentsField, IvkTensorField
     - Enums: IvkEnumField, IvkSchedulerField
     - Collections: IvkCollectionField (value is a list)
   - **Fields WITHOUT `.value` property**: 
     - IvkModelIdentifierField (has key, hash, name, base, type, submodel_type properties)
     - IvkColorField (has r,g,b,a properties)
     - IvkBoundingBoxField (has x_min,y_min,x_max,y_max)
     - Composite model fields (IvkUNetField, IvkCLIPField, IvkVAEField)
   - **Type checking**: Always use `hasattr(field, 'value')` or `isinstance(field, FieldType)` before accessing
   - **Direct property access**: Safe pattern is to check first, then access
   - **Helper methods**: Complex fields provide convenience methods like `set_rgba()`, `set_box()`, `set_hex()`

2. **Two Primary Access Methods**:
   - **Method 1 - Direct field access**: `workflow_handle.get_input_value(index)` returns IvkField for direct property manipulation
     - Use `isinstance()` checks to handle different field types safely
     - Best for simple, type-aware field setting
   - **Method 2 - Field replacement**: `workflow_handle.set_input_value(index, new_field)` replaces entire field instance
     - Most general approach - works for any field type
     - Useful for fields with complex initialization or constraints
     - Enforces type consistency (new field must match original type)

3. **Pydantic-Powered Validation**:
   - All `Ivk*Field` classes inherit from `BaseModel` with `validate_assignment=True`
   - Immediate validation on property assignment
   - Automatic type conversion for compatible types (e.g., "1024" → 1024)
   - Custom validators for field-specific constraints
   - Rich error messages with validation context

4. **Type-Safe Field Handling Best Practices**:
   - **Use isinstance() checks**: Always check field type before accessing properties
   - **No assumptions**: Never assume a field has `.value` property
   - **Know your field patterns**: Understand which fields have value vs direct properties
   - **Leverage type hints**: Import specific field types for type checking
   - **Let Pydantic validate**: Fields validate themselves on property assignment

### Use case 3: submitting the workflow and tracking the job status

**Scenario**: After setting all inputs (from Use Case 2), the developer needs to submit the workflow for execution and track its progress through completion. The client library provides three different submission approaches to accommodate different use cases and architectural patterns.

#### 3.1: Simple synchronous submission with polling

**Approach**: Blocking submission with periodic status polling. Best for simple scripts, sequential workflows, and applications where simplicity is preferred over real-time updates.

**Code Example**:
```python
# Continuing from Use Case 2, we have:
# - client: InvokeAIClient instance  
# - workflow_handle: WorkflowHandle instance with all inputs configured

import time
from typing import Optional, Callable, Dict, Any
from invokeai_py_client.models import JobStatus, SessionEvent

def submit_and_track_sync():
    """Simple synchronous workflow submission with status polling."""
    
    # Submit workflow to default queue
    batch_result = workflow_handle.submit_sync(
        queue_id="default",  # Use default queue
        board_id="samples"   # Output images go to "samples" board
    )
    
    print(f"Batch submitted: {batch_result['batch_id']}")
    print(f"Items enqueued: {batch_result['enqueued']}")
    print(f"Item IDs: {batch_result['item_ids']}")
    
    # Get the queue item to track status
    queue_item = workflow_handle.get_queue_item()
    print(f"Session ID: {queue_item['session_id']}")
    print(f"Status: {queue_item['status']}")
    
    # Poll for completion with timeout
    try:
        # Wait for completion (polls every 0.5s, timeout after 60s)
        completed_item = workflow_handle.wait_for_completion_sync(
            poll_interval=0.5,
            timeout=60.0,
            progress_callback=lambda item: print(f"  Status: {item['status']} - Item {item['item_id']}")
        )
        
        print(f"✅ Job completed successfully!")
        if 'completed_at' in completed_item and 'started_at' in completed_item:
            # Calculate execution time if timestamps available
            print(f"  Item ID: {completed_item['item_id']}")
        
        return completed_item
        
    except TimeoutError:
        print("❌ Job timed out")
        workflow_handle.cancel()
        raise
    except Exception as e:
        print(f"❌ Job failed: {e}")
        raise
```

**Expected Output**:
```
Batch submitted: batch_abc123
Items enqueued: 1
Item IDs: [42]
Session ID: session_789xyz
Status: pending
  Status: in_progress - Item 42
  Status: in_progress - Item 42
  Status: in_progress - Item 42
  Status: in_progress - Item 42
  Status: in_progress - Item 42
  Status: completed - Item 42
✅ Job completed successfully!
  Item ID: 42
```

#### 3.2: Asynchronous submission with real-time events

**Approach**: Non-blocking submission with Socket.IO event streaming. Best for interactive applications, dashboards, and scenarios requiring real-time progress updates and concurrent workflow execution.

**Code Example**:

```python
import asyncio

# Option 2: Asynchronous submission with real-time events via Socket.IO
async def submit_and_track_async():
    """Asynchronous workflow submission with real-time event streaming."""
    
    # Define event callbacks for progress tracking
    def on_invocation_started(event: dict[str, Any]):
        """Called when a node starts executing."""
        print(f"  ▶️ Node started: {event['node_id']} ({event['node_type']})")
    
    def on_invocation_progress(event: dict[str, Any]):
        """Called for progress updates during node execution."""
        progress_pct = event.get('progress', 0) * 100
        print(f"  ⏳ Progress: {progress_pct:.1f}% - {event.get('message', '')}")
    
    def on_invocation_complete(event: dict[str, Any]):
        """Called when a node completes successfully."""
        print(f"  ✅ Node completed: {event['node_id']}")
        if 'outputs' in event:
            # Can access intermediate outputs here
            for output_type, output_data in event['outputs'].items():
                print(f"     Output: {output_type}")
    
    def on_invocation_error(event: dict[str, Any]):
        """Called when a node encounters an error."""
        print(f"  ❌ Node error: {event['node_id']} - {event.get('error', 'Unknown error')}")
    
    # Submit with event subscriptions
    batch_result = await workflow_handle.submit(
        queue_id="default",
        board_id="samples",
        priority=5,  # Higher priority
        subscribe_events=True,  # Enable Socket.IO events
        on_invocation_started=on_invocation_started,
        on_invocation_progress=on_invocation_progress,
        on_invocation_complete=on_invocation_complete,
        on_invocation_error=on_invocation_error
    )
    
    print(f"Batch submitted: {batch_result.batch_id}")
    print(f"Session ID: {batch_result.session_id}")
    print(f"Items enqueued: {batch_result.enqueued}")
    
    # Wait for completion with async/await
    try:
        # This awaits completion while receiving real-time events
        job = await workflow_handle.wait_for_completion(timeout=60.0)
        
        print(f"✅ Workflow completed!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status}")
        print(f"  Duration: {job.duration_seconds:.2f}s")
        
        return job
        
    except asyncio.TimeoutError:
        print("❌ Job timed out")
        await workflow_handle.cancel_async()
        raise
    except Exception as e:
        print(f"❌ Job failed: {e}")
        raise
```

**Expected Output**:
```
Batch submitted: batch_def456
Session ID: session_456def
Items enqueued: 1
  ▶️ Node started: node_123 (string)
  ✅ Node completed: node_123
  ▶️ Node started: node_456 (sdxl_model_loader)
  ✅ Node completed: node_456
  ▶️ Node started: node_789 (denoise_latents)
  ⏳ Progress: 25.0% - Denoising step 5/20
  ⏳ Progress: 50.0% - Denoising step 10/20
  ⏳ Progress: 75.0% - Denoising step 15/20
  ⏳ Progress: 100.0% - Denoising step 20/20
  ✅ Node completed: node_789
     Output: latents
  ▶️ Node started: node_abc (l2i)
  ✅ Node completed: node_abc
     Output: image
  ▶️ Node started: node_def (save_image)
  ✅ Node completed: node_def
✅ Workflow completed!
  Job ID: job_xyz789
  Status: completed
  Duration: 18.34s
```

#### 3.3: Hybrid approach - submit synchronously, monitor asynchronously

**Approach**: Simple blocking submission combined with async event monitoring. Best for applications wanting simple submission APIs but rich monitoring capabilities, or transitioning from sync to async patterns.

**Code Example**:
```python
# Option 3: Hybrid approach - submit sync, monitor async
async def submit_sync_monitor_async():
    """Submit synchronously but monitor with async events."""
    
    # Submit synchronously (simpler API)
    batch_result = workflow_handle.submit_sync(
        queue_id="default",
        board_id="samples"
    )
    
    print(f"Submitted batch: {batch_result['batch_id']}")
    
    # Connect to Socket.IO for real-time monitoring
    async with client.connect_socketio() as socket:
        # Subscribe to session events
        await socket.subscribe_session(batch_result['session_id'])
        
        # Monitor events asynchronously
        async for event in socket.listen_events():
            if event.type == SessionEvent.INVOCATION_STARTED:
                print(f"  ▶️ {event.node_type} started")
            elif event.type == SessionEvent.INVOCATION_COMPLETE:
                print(f"  ✅ {event.node_type} completed")
            elif event.type == SessionEvent.INVOCATION_ERROR:
                print(f"  ❌ Error: {event.error}")
                break
            elif event.type == SessionEvent.GRAPH_COMPLETE:
                print(f"✅ Workflow completed!")
                break
    
    # Get final results
    return workflow_handle.get_queue_item()
```

**Expected Output**:
```
Submitted batch: batch_ghi789
  ▶️ string started
  ✅ string completed
  ▶️ sdxl_model_loader started
  ✅ sdxl_model_loader completed
  ▶️ denoise_latents started
  ✅ denoise_latents completed
  ▶️ l2i started
  ✅ l2i completed
  ▶️ save_image started
  ✅ save_image completed
✅ Workflow completed!
```

#### Usage examples and comparison

The three approaches offer different trade-offs for various application architectures:

**Code Example**:
```python
# Usage examples:

# Synchronous (blocking) - simplest approach
print("=== Synchronous Submission ===")
queue_item = submit_and_track_sync()
print(f"Final status: {queue_item['status']}")

# Asynchronous (non-blocking) - for concurrent workflows
print("\n=== Asynchronous Submission ===")
async def main():
    job = await submit_and_track_async()
    print(f"Job completed: {job.id}")
    
    # Can run multiple workflows concurrently
    tasks = [
        submit_and_track_async(),
        submit_and_track_async(),
        submit_and_track_async()
    ]
    results = await asyncio.gather(*tasks)
    print(f"Completed {len(results)} workflows concurrently")

# Run async example
asyncio.run(main())

# Hybrid approach - best of both worlds
print("\n=== Hybrid Submission ===")
asyncio.run(submit_sync_monitor_async())
```

**Key Design Points**:

1. **Dual Submission Modes**:
   - **Synchronous**: `submit_sync()` - Simple blocking call with polling
   - **Asynchronous**: `submit()` - Non-blocking with real-time events
   - Both methods convert workflow to API format and submit to queue
   - Submit endpoint: `/api/v1/queue/{queue_id}/enqueue_batch`

2. **Progress Tracking Options**:
   - **Polling-based** (sync): 
     - `wait_for_completion_sync()` with configurable poll interval
     - Optional progress callback for status updates
     - Poll endpoint: `/api/v1/queue/{queue_id}/i/{item_id}`
   - **Event-driven** (async):
     - Socket.IO connection for real-time events
     - Node-level callbacks: started, progress, complete, error
     - No polling overhead, instant updates

3. **Event Subscription System** (async only):
   - `subscribe_events=True` enables Socket.IO connection
   - Per-node callbacks for granular monitoring:
     - `on_invocation_started`: Node execution begins
     - `on_invocation_progress`: Progress updates (e.g., denoising steps)
     - `on_invocation_complete`: Node finishes with outputs
     - `on_invocation_error`: Node encounters error
   - Session-level events for overall workflow status

4. **Queue Management**:
   - Queue item tracking with session_id, batch_id, item_id
   - Status transitions: pending → in_progress → completed/failed/cancelled
   - Priority queuing support (higher values = higher priority)
   - Board assignment for output organization

5. **Concurrency Support** (async):
   - Run multiple workflows simultaneously with `asyncio.gather()`
   - Each workflow maintains independent state
   - Shared client connection for efficiency
   - Real-time monitoring of all concurrent executions

6. **Error Handling & Cancellation**:
   - Timeout protection in both sync and async modes
   - Cancellation methods: `cancel()` (sync) and `cancel_async()` (async)
   - Cancel endpoint: `/api/v1/queue/{queue_id}/i/{item_id}/cancel`
   - Graceful error propagation with context
   - Automatic cleanup on failure

7. **Hybrid Approach**:
   - Submit synchronously for simplicity
   - Monitor asynchronously for real-time updates
   - Best for applications needing simple submission but rich monitoring
   - Combines ease of sync API with power of async events

### Use case 4: retrieving outputs and cleaning up

**Scenario**: After workflow execution completes (from Use Case 3), the developer needs to retrieve generated outputs and clean up resources. Note: Advanced output retrieval methods are planned but not yet implemented.

**Code Example**:
```python
# Continuing from Use Case 3, we have:
# - client: InvokeAIClient instance
# - workflow_handle: WorkflowHandle with completed execution
# - Queue item has status='completed'

from pathlib import Path
from typing import List, Dict, Any, Optional
from invokeai_py_client.models import IvkImage
from invokeai_py_client.board import BoardHandle

# Step 1: Verify workflow completion via queue item
queue_item = workflow_handle.get_queue_item()
if queue_item and queue_item['status'] == 'completed':
    print(f"✅ Workflow completed successfully!")
    print(f"   Session ID: {queue_item.get('session_id', 'N/A')}")
    print(f"   Item ID: {queue_item.get('item_id', 'N/A')}")
    
    # Queue item contains session outputs
    session_data = queue_item.get('session', {})
    if session_data:
        # Session may have status and results
        print(f"   Session status: {session_data.get('status', 'unknown')}")

# Step 2: Retrieve outputs using BoardHandle (current approach)
# Since workflow.get_outputs() is not yet implemented, use board API directly

# Get board handle for the output board we specified during submission
board_id = "samples"  # The board we used in submit_sync(board_id="samples")
board_handle: BoardHandle = client.board_repo.get_board_handle(board_id)

# List images that were generated (newest first)
image_names = board_handle.list_images(limit=10, order_by="created_at")
print(f"\n📸 Found {len(image_names)} images in '{board_id}' board")

# Download the generated images
output_dir = Path("./outputs") / workflow_handle.batch_id
output_dir.mkdir(parents=True, exist_ok=True)

for idx, image_name in enumerate(image_names):
    # Download image bytes directly from board
    image_bytes = board_handle.download_image(image_name)
    
    # Save to disk
    output_path = output_dir / f"output_{idx}_{image_name}"
    output_path.write_bytes(image_bytes)
    print(f"   Downloaded: {output_path.name} ({len(image_bytes)} bytes)")

# Step 3: Alternative - Process images directly with PIL
from PIL import Image
import io

# If you need to process images, download and decode them
if image_names:
    first_image_bytes = board_handle.download_image(image_names[0])
    pil_image = Image.open(io.BytesIO(first_image_bytes))
    print(f"\n🖼️ Loaded image: {pil_image.size} {pil_image.mode}")
    
    # Process as needed
    # pil_image.thumbnail((256, 256))  # Create thumbnail
    # pil_image.save("thumbnail.jpg")

# Step 4: Track uploaded input assets (cleanup not yet implemented)
uploaded_assets = workflow_handle.get_uploaded_assets()
if uploaded_assets:
    print(f"\n📎 Uploaded assets tracked: {len(uploaded_assets)}")
    for asset in uploaded_assets:
        print(f"   - {asset}")
    # Note: workflow_handle.cleanup_inputs() not yet implemented
    # Must manually delete using image API if needed

# Step 5: Manual cleanup of generated outputs (if needed)
print("\n🧹 Cleaning up outputs...")

# Delete images from board using BoardHandle
for image_name in image_names[:3]:  # Example: delete first 3
    success = board_handle.delete_image(image_name)
    if success:
        print(f"   ✅ Deleted: {image_name}")
    else:
        print(f"   ❌ Failed to delete: {image_name}")

# Alternative: Move images to another board instead of deleting
# board_handle.move_image_to(image_name, "archive_board_id")

# Step 6: Cleanup limitations and future improvements
# Note: The following methods are planned but not yet implemented:
# - workflow_handle.get_outputs() - Will return structured WorkflowOutput
# - workflow_handle.cleanup_inputs() - Will delete uploaded input assets
# - workflow_handle.cleanup_outputs() - Will delete generated outputs
# - workflow_handle.cleanup_queue_items() - Will prune queue items

# Current workaround: Track resources manually and use board/image APIs directly
print("\n📝 Resource tracking summary:")
print(f"   Batch ID: {workflow_handle.batch_id}")
print(f"   Session ID: {workflow_handle.session_id}")
print(f"   Uploaded assets: {len(uploaded_assets)}")
print(f"   Generated images: {len(image_names)}")
```

**Expected Output**:
```
✅ Workflow completed successfully!
   Session ID: session_456def
   Item ID: 42

📸 Found 3 images in 'samples' board

   Downloaded: output_0_img_001.png (2457600 bytes)
   Downloaded: output_1_img_002.png (2654208 bytes)
   Downloaded: output_2_img_003.png (2789376 bytes)

🖼️ Loaded image: (1024, 768) RGB

📎 Uploaded assets tracked: 2
   - uploaded_image_123.png
   - uploaded_mask_456.png

🧹 Cleaning up outputs...
   ✅ Deleted: img_001.png
   ✅ Deleted: img_002.png
   ✅ Deleted: img_003.png

📝 Resource tracking summary:
   Batch ID: batch_def456
   Session ID: session_456def
   Uploaded assets: 2
   Generated images: 3
```