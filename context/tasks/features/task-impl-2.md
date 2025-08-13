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

- in GUI, user can add some of the fields of the nodes as inputs, by adding them to the `form` section of the workflow definition, these fields are called `workflow-inputs`, they map to some of the fields in the nodes, and they are somewhat like the public interface of the workflow. Our API should capture this concept, and expose these `workflow-inputs` to the user, via some generic methods like `set_input`, `get_input`, etc.

- we know that InvokeAI has a type system, some of them are already defined in our data models, see `src\invokeai_py_client\models.py`, for more info you can see `context\hints\invokeai-kb\about-invokeai-workflow-input-types.md`. We shall define data models for these types (naming them as `Ink<TypeName>`), and use these data models in the `set_input` and `get_input` methods.

- we know that heavy data like images and masks are referred to by their names in the workflow definition, the names are given by the InvokeAI backend when these data are uploaded to the backend, and to get the actual data, we need to download them from the backend given the names. 
  
- when everything is set, we can submit the workflow to the backend, and InvokeAI will execute the workflow, the execution will create a job, and we can track the job status, and get the results back when the job is done. The results will be in the form of `client-types`, which can be used to get the output. `examples/` contains some demos of how to interact with InvokeAI backend about workflows, you can refer to them for more details.

- note that, after everything is done, results are retrieved, those inputs and outputs uploaded to InvokeAI can be discarded, we need to explicitly delete them in the backend, otherwise they will stay in the backend and occupy space.
  
## Workflow subsystem usage pattern

here we describe the use cases of the workflow subsystem in `client-api`, before designing the API, we need to understand how users will use it.

### Use case 1: loading `example-workflow.json` and listing inputs

**Scenario**: A developer wants to load a FLUX image-to-image workflow from a JSON file and discover what inputs can be configured before execution.

**Code Example**:
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.models import WorkflowDefinition, InkWorkflowInput
from typing import List, Dict
import json

# Initialize the client
client = InvokeAIClient.from_url("http://localhost:9090")

# Step 1: Read workflow JSON and create WorkflowDefinition data model
with open("data/workflows/flux-image-to-image.json", "r") as f:
    workflow_dict = json.load(f)

workflow_def = WorkflowDefinition.from_dict(workflow_dict)

# Step 2: Create workflow instance from the definition
workflow = client.create_workflow(workflow_def)

# Basic workflow information (from WorkflowDefinition properties)
print(f"Workflow: {workflow.definition.name}")
print(f"Description: {workflow.definition.description}")
print(f"Version: {workflow.definition.version}")
print(f"Author: {workflow.definition.author}")
print()

# List all configurable inputs (returns list of InkWorkflowInput data models)
inputs: List[InkWorkflowInput] = workflow.list_inputs()

print(f"Total configurable inputs: {len(inputs)}")
print("=" * 60)

for input_info in inputs:
    # InkWorkflowInput has typed properties
    print(f"\nInput: {input_info.user_name}")
    print(f"  System Name: {input_info.system_name}")  # e.g., "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.model"
    print(f"  Type: {type(input_info.field).__name__}")  # e.g., InkModelIdentifierField
    print(f"  Required: {input_info.required}")
    
    # Show current value if set
    if input_info.field.value is not None:
        print(f"  Current Value: {input_info.field.value}")

# Get inputs by system-defined names (always unique, guaranteed to work)
inputs_by_system: Dict[str, InkWorkflowInput] = workflow.get_inputs_by_system_name()
# Returns dict keyed by system name:
# {
#     'f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.model': InkWorkflowInput(...),
#     '01f674f8-b3d1-4df1-acac-6cb8e0bfb63c.prompt': InkWorkflowInput(...),
#     '2981a67c-480f-4237-9384-26b68dbf912b.image': InkWorkflowInput(...),
#     ...
# }

# Get inputs by user-defined names (only works if names are unique)
try:
    inputs_by_user: Dict[str, InkWorkflowInput] = workflow.get_inputs_by_user_name()
    # Returns dict keyed by user name:
    # {
    #     'model': InkWorkflowInput(...),
    #     'prompt': InkWorkflowInput(...), 
    #     'image': InkWorkflowInput(...),
    #     ...
    # }
    print("\nUser-defined names are unique, can use either naming scheme")
except ValueError as e:
    print(f"\nWarning: {e}")
    print("Must use system-defined names for this workflow")

# Check which inputs are missing required values
missing = workflow.get_missing_required_inputs()
if missing:
    print(f"\nRequired inputs still needed: {', '.join(missing)}")
```

**Expected Output**:
```
Workflow: flux-image-to-image
Description: A simple image-to-image workflow using a FLUX dev model.
Version: 1.1.0
Author: InvokeAI

Total configurable inputs: 8
============================================================

Input: model
  System Name: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.model
  Type: InkModelIdentifierField
  Required: True
  Current Value: FLUX Dev (Quantized)

Input: t5_encoder_model
  System Name: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.t5_encoder_model
  Type: InkT5EncoderField
  Required: True

Input: clip_embed_model
  System Name: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.clip_embed_model
  Type: InkCLIPEmbedField
  Required: True

Input: vae_model
  System Name: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.vae_model
  Type: InkVAEModelField
  Required: True

Input: prompt
  System Name: 01f674f8-b3d1-4df1-acac-6cb8e0bfb63c.prompt
  Type: InkStringField
  Required: True

Input: image
  System Name: 2981a67c-480f-4237-9384-26b68dbf912b.image
  Type: InkImageField
  Required: True

Input: num_steps
  System Name: 9c773392-5647-4f2b-958e-9da1707b6e6a.num_steps
  Type: InkIntegerField
  Required: False
  Current Value: 20

Input: denoising_start
  System Name: 9c773392-5647-4f2b-958e-9da1707b6e6a.denoising_start
  Type: InkFloatField
  Required: False
  Current Value: 0.7

Warning: Multiple 'prompt' fields found in workflow (nodes: 01f674f8-b3d1-4df1-acac-6cb8e0bfb63c, e87ba3b6-c98f-4644-903a-e13c421f2add)
Must use system-defined names for this workflow

Required inputs still needed: f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.t5_encoder_model, f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.clip_embed_model, f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.vae_model, 01f674f8-b3d1-4df1-acac-6cb8e0bfb63c.prompt, 2981a67c-480f-4237-9384-26b68dbf912b.image
```

**Key Design Points**:

1. **Data Model Architecture**: 
   - `WorkflowDefinition` - Pydantic model for workflow JSON structure
   - `InkWorkflowInput` - Typed data model containing:
     - `user_name`: Simple field name (e.g., "prompt")
     - `system_name`: Unique identifier (e.g., "nodeId.fieldName")
     - `field`: The actual typed field instance (`InkStringField`, `InkImageField`, etc.)
     - `required`: Boolean indicating if the input must be provided

2. **Dual Naming System**:
   - **System-defined names**: `{node_id}.{field_name}` - Always unique, guaranteed to work
   - **User-defined names**: Simple field names - May collide across nodes
   - Two separate accessor methods with clear behavior

3. **Type Safety**: 
   - All methods return proper data models, not raw dicts
   - `workflow.list_inputs()` returns `List[InkWorkflowInput]`
   - `get_inputs_by_*` methods return `Dict[str, InkWorkflowInput]`
   - Each field is a typed instance (`InkStringField`, `InkImageField`, etc.)

4. **Conflict Resolution**: 
   - `get_inputs_by_user_name()` raises `ValueError` when names collide
   - Clear error messages indicate which nodes have conflicts
   - System names always work as fallback

### Use case 2: setting inputs of the `example-workflow.json`

**Scenario**: After loading the workflow (from Use Case 1), the developer needs to set values for each input before execution.

**Code Example**:
```python
# Continuing from Use Case 1, we have:
# - client: InvokeAIClient instance
# - workflow: Workflow instance with loaded flux-image-to-image definition

# Note: All field classes (InkModelIdentifierField, InkStringField, etc.) are Pydantic models
# with validate_assignment=True, providing automatic validation and type conversion

# Get inputs by system-defined names (always works)
inputs_by_system = workflow.get_inputs_by_system_name()

# Set model fields - can pass dict, Pydantic validates and converts to InkModelIdentifierField
inputs_by_system['f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.model'].field.value = {
    "key": "fe04e4c3-2287-4ba5-8c34-107d3da215ae",
    "name": "FLUX Dev (Quantized)",
    "base": "flux",
    "type": "main"
}

inputs_by_system['f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.t5_encoder_model'].field.value = {
    "key": "t5-encoder-key-123",
    "name": "T5 Encoder FLUX",
    "base": "flux",
    "type": "t5_encoder"
}

inputs_by_system['f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.clip_embed_model'].field.value = {
    "key": "clip-embed-key-456",
    "name": "CLIP-L Encoder",
    "base": "flux",
    "type": "clip_embed"
}

inputs_by_system['f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90.vae_model'].field.value = {
    "key": "vae-model-key-789",
    "name": "FLUX VAE",
    "base": "flux",
    "type": "vae"
}

# Set prompt - InkStringField accepts string directly
inputs_by_system['01f674f8-b3d1-4df1-acac-6cb8e0bfb63c.prompt'].field.value = (
    "A serene mountain landscape at sunset, photorealistic, high detail"
)

# Upload and set image input
uploaded_image = client.board_repo.upload_image_by_file(
    "input_images/mountain.jpg",
    board_id=None  # Upload to uncategorized
)
# InkImageField can accept dict or just the image_name string - Pydantic handles conversion
inputs_by_system['2981a67c-480f-4237-9384-26b68dbf912b.image'].field.value = uploaded_image.image_name

# Set optional parameters - automatic type conversion
inputs_by_system['9c773392-5647-4f2b-958e-9da1707b6e6a.num_steps'].field.value = "30"  # String converted to int
inputs_by_system['9c773392-5647-4f2b-958e-9da1707b6e6a.denoising_start'].field.value = 0.65  # Float stays float

# Example of per-field validation error handling
try:
    # This will fail validation - num_steps must be positive integer
    inputs_by_system['9c773392-5647-4f2b-958e-9da1707b6e6a.num_steps'].field.value = -5
except ValueError as e:
    print(f"Field validation error: {e}")
    # Set valid value
    inputs_by_system['9c773392-5647-4f2b-958e-9da1707b6e6a.num_steps'].field.value = 30

# Validate all inputs together
validation_errors = workflow.validate_inputs()
if validation_errors:
    print("Validation errors found:")
    for field_name, errors in validation_errors.items():
        print(f"  {field_name}: {', '.join(errors)}")
else:
    print("All inputs are valid")

# Check if all required inputs are set
missing = workflow.get_missing_required_inputs()
if missing:
    print(f"Still missing required inputs: {', '.join(missing)}")
else:
    print("All required inputs are set, workflow ready for submission")
```

**Expected Output**:
```
Field validation error: ensure this value is greater than 0
All inputs are valid
All required inputs are set, workflow ready for submission
```

**Key Design Points**:

1. **Pydantic-Powered Field Models**:
   - All `Ink*Field` classes are Pydantic models with `validate_assignment=True`
   - Immediate validation when setting `.value` property
   - Type conversion handles common cases (string "30" → int 30)
   - Per-field validation errors provide immediate feedback

2. **Flexible Input Formats**:
   - **Model fields**: Accept dict or `InkModelIdentifierField` instance
   - **Image fields**: Accept string (image_name) or dict with image_name
   - **Primitive fields**: Automatic type coercion (strings to numbers when appropriate)

3. **Two-Level Validation**:
   - **Per-field validation**: Immediate feedback via Pydantic when setting values
   - **Workflow-level validation**: `validate_inputs()` checks all inputs for inter-field dependencies
   - Separation of concerns between field-level and workflow-level validation

4. **Image Upload Integration**:
   - Upload via `BoardRepository` returns `IvkImage` 
   - Use `image_name` property for workflow reference
   - Pydantic handles string-to-InkImageField conversion

5. **Pre-submission Checks**:
   - `validate_inputs()` returns dict of errors for comprehensive validation
   - `get_missing_required_inputs()` ensures all required fields are set
   - Clear workflow readiness status before submission

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

5. **Performance Considerations**:
   - API polling: ~50ms per status check (synchronous mode)
   - Socket.IO events: <5ms latency (real-time async mode)
   - Choose async with events for responsive UIs
   - Use sync polling for simple scripts and batch operations

6. **Queue Management**:
   - Support for multiple queues (default, priority, batch)
   - Queue position tracking for job scheduling
   - Batch ID for grouping related workflows

### Use case 4: retrieving outputs and cleaning up