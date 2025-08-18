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

**Scenario**: After setting all inputs (from Use Case 2), the developer needs to submit the workflow for execution and track its progress through completion.

**Code Example**:
```python
# Continuing from Use Case 2, we have:
# - client: InvokeAIClient instance  
# - workflow: Workflow instance with all inputs configured

import asyncio
from typing import Optional, Callable
from invokeai_py_client.models import SessionQueueItem, EnqueueBatchResult, JobStatus, SessionEvent

# Option 1: Synchronous submission with polling
def submit_and_track_sync():
    """Simple synchronous workflow submission with status polling."""
    
    # Submit workflow to default queue
    result = workflow.submit_sync(
        queue_id="default",  # Use default queue
        board_id="samples"   # Output images go to "samples" board
    )
    
    print(f"Batch submitted: {result.batch_id}")
    print(f"Items enqueued: {result.enqueued}/{result.requested}")
    print(f"Item IDs: {result.item_ids}")
    
    # Get the queue item to track status
    job = workflow.get_queue_item()
    print(f"Session ID: {job.session_id}")
    print(f"Status: {job.status}")
    
    # Poll for completion with timeout
    try:
        # Wait for completion (polls every 0.5s, timeout after 60s)
        job = workflow.wait_for_completion_sync(
            poll_interval=0.5,
            timeout=60.0,
            progress_callback=lambda j: print(f"  Status: {j.status} - Item {j.item_id}")
        )
        
        print(f"✅ Job completed successfully!")
        print(f"  Execution time: {(job.completed_at - job.started_at).total_seconds()}s")
        
        return job
        
    except TimeoutError:
        print("❌ Job timed out")
        workflow.cancel()
        raise
    except Exception as e:
        print(f"❌ Job failed: {e}")
        raise


# Option 2: Asynchronous submission with real-time events
async def submit_and_track_async():
    """Advanced async workflow submission with Socket.IO event streaming."""
    
    # Define event handlers for real-time progress
    def on_invocation_started(event: dict):
        print(f"🔵 Node started: {event.get('node_id')} ({event.get('invocation_type')})")
    
    def on_invocation_progress(event: dict):
        progress = event.get('progress')
        if progress:
            percentage = progress.get('percentage', 0)
            message = progress.get('message', '')
            print(f"⏳ Progress: {percentage}% - {message}")
    
    def on_invocation_complete(event: dict):
        print(f"✅ Node complete: {event.get('node_id')}")
        result = event.get('result')
        if result and result.get('type') == 'image_output':
            image = result.get('image', {})
            print(f"   Generated image: {image.get('image_name')}")
    
    def on_invocation_error(event: dict):
        print(f"❌ Node error: {event.get('node_id')} - {event.get('error', 'Unknown error')}")
    
    # Submit with event subscription
    result = await workflow.submit(
        queue_id="default",
        board_id="samples",
        # Subscribe to real-time events via Socket.IO
        subscribe_events=True,
        on_invocation_started=on_invocation_started,
        on_invocation_progress=on_invocation_progress,
        on_invocation_complete=on_invocation_complete,
        on_invocation_error=on_invocation_error
    )
    
    print(f"Batch submitted: {result.batch_id}")
    print(f"Items enqueued: {result.enqueued}")
    
    # Get queue item for tracking
    job = await workflow.get_queue_item()
    print(f"Session ID: {job.session_id}")
    print(f"Subscribed to queue events for session")
    
    # Wait for completion with live updates
    try:
        job = await workflow.wait_for_completion(timeout=60.0)
        print(f"✅ Workflow completed successfully!")
        return job
    except asyncio.TimeoutError:
        print("❌ Job timed out, cancelling...")
        await workflow.cancel()
        raise
    except Exception as e:
        print(f"❌ Job failed: {e}")
        raise


# Usage examples showing different approaches:

# 1. Simple synchronous for basic needs
print("=== Synchronous Submission ===")
job = submit_and_track_sync()

# 2. Async with real-time events for rich feedback
print("\n=== Async with Events ===")
job = asyncio.run(submit_and_track_async())

# Both methods return the same SessionQueueItem object with results
print(f"\nFinal status: {job.status}")
print(f"Session ID: {job.session_id}")
print(f"Batch ID: {job.batch_id}")
if job.completed_at and job.started_at:
    elapsed = (job.completed_at - job.started_at).total_seconds()
    print(f"Total execution time: {elapsed}s")
```

**Expected Output**:
```
=== Synchronous Submission ===
Batch submitted: batch_abc123
Items enqueued: 1/1
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
  Execution time: 18.234s

=== Async with Events ===  
Batch submitted: batch_def456
Items enqueued: 1
Session ID: session_456def
Subscribed to queue events for session
🔵 Node started: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90 (flux_model_loader)
✅ Node complete: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90
🔵 Node started: 01f674f8-b3d1-4df1-acac-6cb8e0bfb63c (flux_text_encoder)
⏳ Progress: 50% - Encoding tokens
✅ Node complete: 01f674f8-b3d1-4df1-acac-6cb8e0bfb63c
🔵 Node started: 9c773392-5647-4f2b-958e-9da1707b6e6a (denoise_latents)
⏳ Progress: 10% - Step 2/20
⏳ Progress: 50% - Step 10/20
⏳ Progress: 100% - Step 20/20
✅ Node complete: 9c773392-5647-4f2b-958e-9da1707b6e6a
🔵 Node started: vae_decode (l2i)
✅ Node complete: vae_decode
🔵 Node started: save_image (image)
✅ Node complete: save_image
   Generated image: abc123_mountain_landscape.png
✅ Workflow completed successfully!

Final status: completed
Session ID: session_456def
Batch ID: batch_def456
Total execution time: 18.234s
```

**Key Design Points**:

1. **Two Submission Patterns**:
   - **Synchronous**: `submit_sync()` returns EnqueueBatchResult, then poll via API
   - **Asynchronous**: `await submit()` with Socket.IO event streaming for real-time updates

2. **Real-time Event System**:
   - Socket.IO at `/ws/socket.io` endpoint for live updates
   - Event types: InvocationStartedEvent, InvocationProgressEvent, InvocationCompleteEvent, InvocationErrorEvent
   - Queue subscription via `subscribe_queue` event with queue_id
   - Per-node granular updates with node_id and invocation_type

3. **Job Tracking Information**:
   - **SessionQueueItem** model contains execution metadata
   - **EnqueueBatchResult** provides batch_id, item_ids, enqueued count
   - Item status: pending, in_progress, completed, failed, canceled
   - Timestamps: created_at, started_at, completed_at for timing

4. **Error Handling & Cancellation**:
   - Timeout protection with automatic cancellation
   - Graceful error propagation with detailed messages
   - `workflow.cancel()` for user-initiated cancellation
   - Cleanup of partial results on failure

### Use case 4: retrieving outputs and cleaning up

**Scenario**: After workflow execution completes (from Use Case 3), the developer needs to retrieve generated outputs from output-nodes (those with board field exposed in form), optionally access debug-nodes outputs, and clean up temporary resources.

**Code Example**:
```python
# Continuing from Use Case 3, we have:
# - client: InvokeAIClient instance
# - workflow: Workflow instance with completed job
# - job: SessionQueueItem with status='completed'

from pathlib import Path
from typing import List, Dict, Any, Optional
from invokeai_py_client.models import (
    WorkflowOutput, InkImageOutput, InkLatentsOutput, 
    InkConditioningOutput, IvkImage, OutputNode, DebugNode
)

# Step 1: Get workflow outputs (distinguishes output-nodes vs debug-nodes)
outputs: WorkflowOutput = workflow.get_outputs()

print(f"✅ Workflow completed successfully!")
print(f"   Session ID: {outputs.session_id}")
print(f"   Batch ID: {outputs.batch_id}")
print(f"   Execution time: {outputs.execution_time:.2f}s")

# Step 2: Access outputs from TRUE OUTPUT-NODES (user-configurable boards)
# Based on Task 1.3: Only nodes with board field exposed in form are output-nodes
# For SDXL-FLUX workflow: indices [5], [15], [20]
user_outputs: List[InkImageOutput] = outputs.get_user_outputs()

print(f"\n🎯 User-Facing Outputs (from output-nodes):")
print(f"   Total stages: {len(user_outputs)}")

for idx, output in enumerate(user_outputs):
    # Each output corresponds to an output-node with board field at specific index
    print(f"\n   Stage {idx + 1}: {output.stage_name}")
    print(f"   - Image: {output.image_name} ({output.width}x{output.height})")
    print(f"   - Board: {output.board_id} (configured at input index [{output.input_index}])")
    print(f"   - Node Type: {output.node_type}")  # e.g., save_image
    print(f"   - Node ID: {output.node_id}")

# Step 3: Optionally access DEBUG-NODES outputs (not user-configurable)
# Based on Task 1.3: Nodes with board capability but NOT exposed in form
# For SDXL-FLUX: l2i and save_image nodes for internal processing
debug_outputs: List[InkImageOutput] = outputs.get_debug_outputs()

if debug_outputs:
    print(f"\n🔧 Debug/Internal Outputs (from debug-nodes):")
    for debug in debug_outputs:
        print(f"   - {debug.image_name} from {debug.node_type}({debug.node_id})")
        print(f"     Fixed board: {debug.board_id}")

# Step 4: Retrieve outputs - Three different approaches

# Approach 1: Load directly to memory as PIL Image (for immediate processing)
from PIL import Image
import io

print("\n🖼️ Loading images to memory for processing:")
for idx, output in enumerate(user_outputs):
    # Get as PIL Image object - decoded and ready for processing
    pil_image: Image.Image = workflow.get_image_as_pil(output)
    print(f"   Stage {idx + 1}: {output.stage_name}")
    print(f"   - Size: {pil_image.size}")
    print(f"   - Mode: {pil_image.mode}")
    print(f"   - Format: {pil_image.format}")
    
    # Now you can process the image in memory
    # pil_image.thumbnail((256, 256))  # Create thumbnail
    # pil_image.filter(ImageFilter.BLUR)  # Apply filter
    # analysis = analyze_image(pil_image)  # Custom analysis
    
    # Optional: Save processed image
    # pil_image.save(f"processed_{output.image_name}")

# Approach 2: Direct download to disk WITHOUT decoding (most efficient for storage)
download_dir = Path("./outputs") / outputs.batch_id

print("\n💾 Direct download to disk (no decoding):")
for idx, output in enumerate(user_outputs):
    # Download raw bytes directly to file - no decode/re-encode overhead
    stage_dir = download_dir / f"stage_{idx + 1}_{output.stage_name}"
    local_path = workflow.download_image_raw(
        image_output=output,
        output_dir=stage_dir,
        preserve_format=True  # Keep original format from server
    )
    print(f"   Stage {idx + 1} saved to: {local_path}")
    # This is fastest for batch downloads - no CPU overhead

# Approach 3: Get raw bytes for flexible handling
print("\n📦 Getting raw bytes for custom handling:")
for idx, output in enumerate(user_outputs):
    # Get raw image bytes - you decide what to do with them
    image_bytes: bytes = workflow.get_image_bytes(output)
    print(f"   Stage {idx + 1}: {len(image_bytes)} bytes")
    
    # Examples of what you can do with raw bytes:
    # - Upload to S3/cloud storage without temp files
    # - Stream to another service
    # - Store in database BLOB
    # - Custom image processing with other libraries
    
    # Example: Load to PIL if needed
    # pil_image = Image.open(io.BytesIO(image_bytes))
    
    # Example: Direct save without processing
    # with open(f"raw_{output.image_name}", "wb") as f:
    #     f.write(image_bytes)

# Optional: Also handle debug outputs if needed
if workflow.has_debug_outputs():
    debug_outputs = outputs.get_debug_outputs()
    for debug in debug_outputs:
        # Debug outputs can also be retrieved as PIL or bytes
        debug_pil = workflow.get_image_as_pil(debug)
        # Or download raw
        debug_path = workflow.download_image_raw(
            debug, 
            output_dir=download_dir / "debug",
            preserve_format=True
        )

# Comparison of retrieval methods:
# 
# | Method               | Use Case                        | Performance | Memory Usage |
# |---------------------|----------------------------------|-------------|--------------|
# | get_image_as_pil()  | Image processing, analysis      | Slower      | High         |
# | download_image_raw()| Archive, storage                | Fastest     | Low          |
# | get_image_bytes()   | Cloud upload, streaming         | Fast        | Medium       |
#
# For real-time processing, use get_image_as_pil()
# For archival/storage, use download_image_raw() 
# For cloud storage, use get_image_bytes() to avoid temp files

# Example: User-implemented batch download with progress
def download_all_outputs(workflow, output_dir: Path):
    """Example of user-implemented batch download."""
    outputs = workflow.get_outputs()
    user_outputs = outputs.get_user_outputs()
    
    for i, output in enumerate(user_outputs, 1):
        print(f"Downloading {i}/{len(user_outputs)}: {output.image_name}")
        path = workflow.download_image_raw(output, output_dir, preserve_format=True)
        print(f"  → {path}")
    
    return len(user_outputs)

# Step 5: Access other output types (latents, conditioning, etc.)
# These may come from both output-nodes and debug-nodes
latents_outputs: List[InkLatentsOutput] = outputs.latents
conditioning_outputs: List[InkConditioningOutput] = outputs.conditioning

if latents_outputs:
    print(f"\n📦 Found {len(latents_outputs)} latent outputs:")
    for latent in latents_outputs:
        print(f"   - {latent.latents_name}")
        print(f"     Shape: {latent.shape}")
        print(f"     Node: {latent.node_id}")

if conditioning_outputs:
    print(f"\n🎨 Found {len(conditioning_outputs)} conditioning outputs:")
    for cond in conditioning_outputs:
        print(f"   - {cond.conditioning_name}")
        print(f"     Node: {cond.node_id}")

# Step 6: Clean up uploaded input assets
print("\n🧹 Cleaning up temporary resources...")

# Get list of assets that were uploaded for this workflow
uploaded_assets = workflow.get_uploaded_assets()
print(f"   Found {len(uploaded_assets)} uploaded assets to clean")

# Clean up all uploaded inputs in one call
cleanup_result = workflow.cleanup_inputs()
print(f"   ✅ Deleted {cleanup_result.deleted_count} input assets")
if cleanup_result.failed_deletions:
    print(f"   ⚠️ Failed to delete {len(cleanup_result.failed_deletions)} assets:")
    for asset_name, error in cleanup_result.failed_deletions.items():
        print(f"      - {asset_name}: {error}")

# Step 7: Optional - Clean up outputs after download
if workflow.auto_cleanup_outputs:
    # This is configured when creating the workflow
    output_cleanup = workflow.cleanup_outputs(
        delete_from_board=True,  # Remove from board
        delete_images=True        # Actually delete image files
    )
    print(f"   ✅ Cleaned {output_cleanup.deleted_count} output images")

# Step 8: Clean up completed queue items
queue_cleanup = workflow.cleanup_queue_items()
print(f"   ✅ Pruned {queue_cleanup.pruned_count} completed queue items")

# Usage example with error handling
try:
    # Get outputs - raises if workflow not completed
    outputs = workflow.get_outputs()
    
    # Choose retrieval method based on needs
    for output in outputs.get_user_outputs():
        try:
            # For processing: Get as PIL
            pil_img = workflow.get_image_as_pil(output)
            # process_image(pil_img)
        except ImageDecodeError as e:
            print(f"Failed to decode image: {e}")
            # Fall back to raw bytes
            raw_bytes = workflow.get_image_bytes(output)
    
    # For storage: Iterate and download without decoding
    for output in outputs.get_user_outputs():
        path = workflow.download_image_raw(
            output,
            output_dir=Path("./outputs"),
            preserve_format=True
        )
        print(f"Saved: {path}")
    
    # Cleanup with confirmation
    if workflow.has_uploaded_assets():
        cleanup = workflow.cleanup_inputs()
        print(f"Cleaned up {cleanup.deleted_count} temporary assets")
        
except WorkflowNotCompletedError:
    print("❌ Workflow not yet completed, cannot retrieve outputs")
except DownloadError as e:
    print(f"❌ Failed to download outputs: {e}")
    # Outputs remain on server, can retry later
except CleanupError as e:
    print(f"⚠️ Cleanup partially failed: {e}")
    # Some resources may remain, check error details
```

**Expected Output**:
```
✅ Workflow completed successfully!
   Session ID: session_456def
   Batch ID: batch_def456
   Execution time: 18.23s

🎯 User-Facing Outputs (from output-nodes):
   Total stages: 3

   Stage 1: SDXL Generation
   - Image: sdxl_output_001.png (1024x768)
   - Board: samples (configured at input index [5])
   - Node Type: save_image
   - Node ID: 4414d4b5-82c3-4513-8c3f-86d88c24aadc

   Stage 2: Flux Domain Transfer
   - Image: flux_transfer_002.png (1024x768)
   - Board: flux_outputs (configured at input index [15])
   - Node Type: save_image
   - Node ID: 67e997b2-2d56-43f4-8d2e-886c04e18d9f

   Stage 3: Flux Refinement
   - Image: flux_refined_003.png (1024x768)
   - Board: final_outputs (configured at input index [20])
   - Node Type: save_image
   - Node ID: abc466fe-12eb-48a5-87d8-488c8bda180f

🔧 Debug/Internal Outputs (from debug-nodes):
   - latents_intermediate.png from l2i(cf3922d2-e1bc-40cd-8fcd-2a93708d52c2)
     Fixed board: __internal__
   - hed_edges.png from save_image(bb95a42f-3f83-4a6f-8111-745fc1c653fa)
     Fixed board: __debug__

🖼️ Loading images to memory for processing:
   Stage 1: SDXL Generation
   - Size: (1024, 768)
   - Mode: RGB
   - Format: PNG
   Stage 2: Flux Domain Transfer
   - Size: (1024, 768)
   - Mode: RGB
   - Format: PNG
   Stage 3: Flux Refinement
   - Size: (1024, 768)
   - Mode: RGB
   - Format: PNG

💾 Direct download to disk (no decoding):
   Stage 1 saved to: outputs/batch_def456/stage_1_SDXL Generation/sdxl_output_001.png
   Stage 2 saved to: outputs/batch_def456/stage_2_Flux Domain Transfer/flux_transfer_002.png
   Stage 3 saved to: outputs/batch_def456/stage_3_Flux Refinement/flux_refined_003.png

📦 Getting raw bytes for custom handling:
   Stage 1: 2457600 bytes
   Stage 2: 2654208 bytes
   Stage 3: 2789376 bytes

📦 Found 2 latent outputs:
   - latents_sdxl_stage
     Shape: [1, 4, 128, 96]
     Node: denoise_latents_sdxl
   - latents_flux_stage
     Shape: [1, 16, 128, 128]
     Node: flux_denoise_latents

🧹 Cleaning up temporary resources...
   Found 2 uploaded assets to clean
   ✅ Deleted 2 input assets
   ✅ Pruned 1 completed queue items
```

**Key Design Points**:

1. **Output-Nodes vs Debug-Nodes Distinction** (from Task 1.3):
   - **Output-nodes**: Nodes with WithBoard mixin AND board field exposed in form
   - **Debug-nodes**: Nodes with WithBoard mixin but NOT exposed in form
   - `outputs.get_user_outputs()` - Returns only user-configurable outputs (from output-nodes)
   - `outputs.get_debug_outputs()` - Returns internal/debug outputs (from debug-nodes)
   - Each output knows its input-index for board configuration (e.g., [5], [15], [20])

2. **Multi-Stage Output Management**:
   - Workflow outputs organized by stages (SDXL, Flux Domain Transfer, Flux Refinement)
   - Each stage corresponds to an output-node with configurable board
   - Stage outputs can be downloaded individually or as a batch
   - Debug outputs kept separate from user-facing outputs

3. **Pythonic Output Access**:
   - `workflow.get_outputs()` returns `WorkflowOutput` data model
   - Separates user outputs from debug outputs automatically
   - All outputs wrapped in Pydantic models (`InkImageOutput`, `InkLatentsOutput`, etc.)
   - Output metadata includes node type, stage name, and input-index

4. **Three Image Retrieval Approaches**:
   - **PIL Image to Memory**: `workflow.get_image_as_pil()` - Returns PIL Image object for immediate processing
   - **Direct Download (No Decoding)**: `workflow.download_image_raw()` - Streams raw bytes to disk, most efficient for storage
   - **Raw Bytes**: `workflow.get_image_bytes()` - Returns bytes for flexible handling (cloud upload, streaming, etc.)
   - Choice depends on use case: processing vs storage vs streaming
   - Users implement their own batch logic using these primitives

5. **Managed Cleanup**:
   - `workflow.cleanup_inputs()` - Delete uploaded assets
   - `workflow.cleanup_outputs()` - Delete generated outputs (both user and debug)
   - `workflow.cleanup_queue_items()` - Prune completed queue items
   - Returns structured `CleanupResult` with success/failure details

6. **Type Safety**:
   - All outputs are typed Pydantic models
   - `InkImageOutput` includes `input_index`, `stage_name`, `node_type` properties
   - `WorkflowOutput` container with typed accessors for user vs debug outputs
   - `OutputNode` and `DebugNode` models for clear distinction

7. **Node Type Awareness**:
   - `workflow.has_debug_outputs()` - Check if debug outputs exist
   - Support for any node type with WithBoard mixin (save_image, l2i, etc.)
   - Board configuration tracking via input indices
   - Clear distinction between user-facing and internal outputs