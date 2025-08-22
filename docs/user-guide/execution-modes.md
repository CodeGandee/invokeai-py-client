# Execution Modes

Learn about different ways to execute workflows: synchronous, asynchronous, and streaming modes.

## Overview

The InvokeAI Python Client supports multiple execution modes:

| Mode | Use Case | Blocking | Events |
|------|----------|----------|--------|
| **Synchronous** | Simple scripts, sequential processing | Yes | No |
| **Asynchronous** | Concurrent operations, web apps | No | Yes |
| **Streaming** | Real-time monitoring, progress UI | No | Yes |
| **Hybrid** | Blocking with progress updates | Yes | Yes |

## Synchronous Execution

### Basic Sync Pattern

The simplest way to execute workflows:

```python
# Submit and wait sequentially
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=120)

if result.get('status') == 'completed':
    print("Success!")
    mappings = wf.map_outputs_to_images(result)
```

### With Progress Callback

```python
def on_progress(queue_item):
    """Called periodically during execution."""
    status = queue_item.get('status')
    progress = queue_item.get('progress_percentage', 0)
    current = queue_item.get('current_step', 0)
    total = queue_item.get('total_steps', 0)
    
    print(f"[{progress:3.0f}%] Status: {status} ({current}/{total})")

# Submit with progress monitoring
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(
    timeout=180,
    poll_interval=2.0,
    progress_callback=on_progress
)
```

### Complete Sync Example

```python
def run_workflow_sync(client, workflow_path, inputs):
    """Complete synchronous workflow execution."""
    # Load workflow
    wf = client.workflow_repo.create_workflow(
        WorkflowDefinition.from_file(workflow_path)
    )
    
    # Sync models
    wf.sync_dnn_model(by_name=True, by_base=True)
    
    # Set inputs
    for index, value in inputs.items():
        field = wf.get_input_value(index)
        if hasattr(field, 'value'):
            field.value = value
    
    # Submit and wait
    print("Submitting workflow...")
    submission = wf.submit_sync()
    
    print("Waiting for completion...")
    result = wf.wait_for_completion_sync(
        timeout=300,
        progress_callback=lambda q: print(f"Progress: {q.get('progress_percentage', 0)}%")
    )
    
    # Check result
    if result.get('status') == 'completed':
        print(" Workflow completed successfully")
        return wf.map_outputs_to_images(result)
    else:
        print(f" Workflow failed: {result.get('status')}")
        return None
```

## Asynchronous Execution

### Basic Async Pattern

For concurrent operations:

```python
import asyncio

async def run_workflow_async(wf):
    """Async workflow execution."""
    # Submit asynchronously
    submission = await wf.submit()
    print(f"Submitted: {submission['batch_id']}")
    
    # Wait for completion
    result = await wf.wait_for_completion(timeout=180)
    
    # Map outputs
    if result.get('status') == 'completed':
        mappings = wf.map_outputs_to_images(result)
        return mappings
    
    return None

# Run async
async def main():
    wf = client.workflow_repo.create_workflow(workflow_def)
    result = await run_workflow_async(wf)
    print(f"Result: {result}")

asyncio.run(main())
```

### Concurrent Workflows

```python
async def process_batch_async(client, workflow_def, prompts):
    """Process multiple prompts concurrently."""
    tasks = []
    
    for prompt in prompts:
        # Create separate workflow instance
        wf = client.workflow_repo.create_workflow(workflow_def)
        wf.get_input_value(0).value = prompt
        
        # Create task
        task = run_workflow_async(wf)
        tasks.append(task)
    
    # Wait for all to complete
    results = await asyncio.gather(*tasks)
    
    return results

# Process batch
async def main():
    prompts = ["Sunset", "Mountains", "Ocean", "Forest"]
    results = await process_batch_async(client, workflow_def, prompts)
    
    for prompt, result in zip(prompts, results):
        print(f"{prompt}: {len(result) if result else 0} images")

asyncio.run(main())
```

### With Event Handling

```python
async def run_with_events(wf):
    """Execute with event subscription."""
    # Submit with event subscription
    submission = await wf.submit(subscribe_events=True)
    
    # Event handler
    async def handle_event(event):
        event_type = event.get('type')
        
        if event_type == 'generator_progress':
            step = event.get('step', 0)
            total = event.get('total_steps', 0)
            print(f"Progress: {step}/{total}")
        
        elif event_type == 'invocation_complete':
            node = event.get('node_id')
            print(f"Node completed: {node}")
        
        elif event_type == 'session_complete':
            print("Session finished!")
    
    # Subscribe to events
    wf.on_event(handle_event)
    
    # Wait for completion
    result = await wf.wait_for_completion()
    return result
```

## Streaming Execution

### Hybrid Streaming

Monitor progress while blocking:

```python
async def submit_sync_monitor_async(wf):
    """Submit synchronously but monitor asynchronously."""
    # Submit
    submission = wf.submit_sync()
    
    # Stream events
    async for event in wf.stream_events(submission['session_id']):
        event_type = event.get('type')
        
        if event_type == 'generator_progress':
            progress = event.get('progress_percentage', 0)
            yield {'type': 'progress', 'value': progress}
        
        elif event_type == 'invocation_complete':
            node = event.get('node', {}).get('type')
            yield {'type': 'node_complete', 'node': node}
        
        elif event_type == 'session_complete':
            yield {'type': 'complete', 'status': event.get('status')}
            break

# Use streaming
async def monitor_workflow():
    async for update in submit_sync_monitor_async(wf):
        if update['type'] == 'progress':
            print(f"Progress: {update['value']}%")
        elif update['type'] == 'complete':
            print(f"Finished: {update['status']}")
```

### WebSocket Streaming

```python
import socketio

class WorkflowMonitor:
    """Real-time workflow monitoring via WebSocket."""
    
    def __init__(self, base_url):
        self.sio = socketio.AsyncClient()
        self.base_url = base_url
        self.events = []
        
        # Register handlers
        self.sio.on('generator_progress', self.on_progress)
        self.sio.on('invocation_complete', self.on_node_complete)
        self.sio.on('session_complete', self.on_complete)
    
    async def connect(self):
        await self.sio.connect(self.base_url)
    
    async def monitor_session(self, session_id):
        """Monitor a specific session."""
        await self.sio.emit('subscribe_session', {'session_id': session_id})
    
    async def on_progress(self, data):
        step = data.get('step', 0)
        total = data.get('total_steps', 0)
        print(f"Progress: {step}/{total}")
        self.events.append(('progress', data))
    
    async def on_node_complete(self, data):
        node_id = data.get('node_id')
        print(f"Node complete: {node_id}")
        self.events.append(('node', data))
    
    async def on_complete(self, data):
        status = data.get('status')
        print(f"Session complete: {status}")
        self.events.append(('complete', data))
        await self.sio.disconnect()

# Use monitor
monitor = WorkflowMonitor("ws://localhost:9090")
await monitor.connect()
await monitor.monitor_session(submission['session_id'])
```

## Execution Control

### Timeouts

```python
# Short timeout for fast models
result = wf.wait_for_completion_sync(timeout=30)

# Long timeout for complex workflows
result = wf.wait_for_completion_sync(timeout=600)

# No timeout (wait indefinitely)
result = wf.wait_for_completion_sync(timeout=None)

# Handle timeout
try:
    result = wf.wait_for_completion_sync(timeout=60)
except TimeoutError:
    print("Workflow timed out after 60 seconds")
    # Optionally cancel
    client.cancel_workflow(submission['item_id'])
```

### Polling Intervals

```python
# Fast polling for real-time feel
result = wf.wait_for_completion_sync(
    timeout=120,
    poll_interval=0.5  # Check every 500ms
)

# Slow polling to reduce load
result = wf.wait_for_completion_sync(
    timeout=300,
    poll_interval=5.0  # Check every 5 seconds
)

# Adaptive polling
def adaptive_poll_interval(attempt):
    """Increase interval over time."""
    if attempt < 10:
        return 1.0  # Fast initially
    elif attempt < 30:
        return 2.0  # Medium
    else:
        return 5.0  # Slow for long runs
```

### Cancellation

```python
def run_with_cancellation(wf, timeout=120):
    """Run workflow with cancellation support."""
    import threading
    
    cancelled = threading.Event()
    
    def check_cancelled():
        """Check if cancelled."""
        if cancelled.is_set():
            raise InterruptedError("Workflow cancelled")
    
    try:
        # Submit
        submission = wf.submit_sync()
        
        # Wait with cancellation check
        result = wf.wait_for_completion_sync(
            timeout=timeout,
            progress_callback=lambda _: check_cancelled()
        )
        
        return result
        
    except InterruptedError:
        # Cancel on server
        client.cancel_workflow(submission['item_id'])
        return None

# Cancel from another thread
def cancel_after(seconds, event):
    import time
    time.sleep(seconds)
    event.set()

cancelled = threading.Event()
threading.Thread(target=cancel_after, args=(30, cancelled)).start()
result = run_with_cancellation(wf)
```

## Queue Management

### Queue Status

```python
def get_queue_status(client, queue_id="default"):
    """Get queue statistics."""
    response = client._make_request("GET", f"/queue/{queue_id}/status")
    status = response.json()
    
    print(f"Queue: {queue_id}")
    print(f"  Pending: {status.get('queue_pending_count', 0)}")
    print(f"  In Progress: {status.get('queue_in_progress_count', 0)}")
    print(f"  Completed: {status.get('queue_completed_count', 0)}")
    print(f"  Failed: {status.get('queue_failed_count', 0)}")
    
    return status
```

### Queue Position

```python
def get_queue_position(client, item_id, queue_id="default"):
    """Get position in queue."""
    response = client._make_request(
        "GET", 
        f"/queue/{queue_id}/i/{item_id}/position"
    )
    position = response.json()
    
    print(f"Position: {position.get('position', 'unknown')}")
    print(f"Ahead: {position.get('ahead_count', 0)}")
    print(f"ETA: {position.get('estimated_time', 'unknown')}")
    
    return position
```

### Priority Submission

```python
def submit_with_priority(wf, priority="normal"):
    """Submit with queue priority."""
    # Priority levels: low, normal, high, urgent
    
    submission_data = wf._build_submission()
    submission_data['priority'] = priority
    
    response = client._make_request(
        "POST",
        "/queue/default/enqueue_batch",
        json=submission_data
    )
    
    return response.json()

# High priority submission
submission = submit_with_priority(wf, priority="high")
```

## Performance Patterns

### Batch Processing

```python
def process_batch(client, workflow_def, items, batch_size=5):
    """Process items in batches."""
    from itertools import islice
    
    def chunks(iterable, size):
        it = iter(iterable)
        while True:
            chunk = list(islice(it, size))
            if not chunk:
                break
            yield chunk
    
    all_results = []
    
    for batch_num, batch in enumerate(chunks(items, batch_size)):
        print(f"Processing batch {batch_num + 1}")
        
        # Process batch concurrently
        batch_results = []
        for item in batch:
            wf = client.workflow_repo.create_workflow(workflow_def)
            # Set inputs from item
            wf.get_input_value(0).value = item['prompt']
            
            # Submit
            submission = wf.submit_sync()
            batch_results.append((wf, submission))
        
        # Wait for batch completion
        for wf, submission in batch_results:
            result = wf.wait_for_completion_sync(timeout=180)
            all_results.append(result)
    
    return all_results
```

### Pipeline Pattern

```python
class WorkflowPipeline:
    """Chain multiple workflows together."""
    
    def __init__(self, client):
        self.client = client
        self.stages = []
    
    def add_stage(self, workflow_def, input_mapper):
        """Add pipeline stage."""
        self.stages.append({
            'workflow': workflow_def,
            'mapper': input_mapper
        })
        return self
    
    def execute(self, initial_input):
        """Execute pipeline."""
        current_output = initial_input
        
        for i, stage in enumerate(self.stages):
            print(f"Stage {i + 1}/{len(self.stages)}")
            
            # Create workflow
            wf = self.client.workflow_repo.create_workflow(
                stage['workflow']
            )
            
            # Map inputs
            stage['mapper'](wf, current_output)
            
            # Execute
            submission = wf.submit_sync()
            result = wf.wait_for_completion_sync()
            
            # Get output for next stage
            current_output = wf.map_outputs_to_images(result)
        
        return current_output

# Use pipeline
pipeline = WorkflowPipeline(client)
pipeline.add_stage(
    workflow1,
    lambda wf, inp: wf.get_input_value(0).value = inp
)
pipeline.add_stage(
    workflow2,
    lambda wf, inp: wf.get_input_value(1).value = inp[0]['image_names'][0]
)
result = pipeline.execute("Initial prompt")
```

## Error Handling

### Retry Logic

```python
def execute_with_retry(wf, max_retries=3, backoff=2.0):
    """Execute with automatic retry."""
    import time
    
    for attempt in range(max_retries):
        try:
            submission = wf.submit_sync()
            result = wf.wait_for_completion_sync(timeout=180)
            
            if result.get('status') == 'completed':
                return result
            elif result.get('status') == 'failed':
                error = result.get('error', 'Unknown error')
                print(f"Attempt {attempt + 1} failed: {error}")
                
                if attempt < max_retries - 1:
                    wait_time = backoff ** attempt
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed after {max_retries} attempts")
                    
        except TimeoutError:
            print(f"Attempt {attempt + 1} timed out")
            if attempt == max_retries - 1:
                raise
    
    return None
```

### Error Recovery

```python
def execute_with_recovery(wf):
    """Execute with error recovery."""
    try:
        submission = wf.submit_sync()
        result = wf.wait_for_completion_sync(timeout=120)
        return result
        
    except TimeoutError:
        print("Timeout - attempting recovery")
        # Try with reduced quality
        wf.get_input_value(STEPS_IDX).value = 10  # Reduce steps
        wf.get_input_value(WIDTH_IDX).value = 512  # Reduce size
        wf.get_input_value(HEIGHT_IDX).value = 512
        
        # Retry with lower settings
        submission = wf.submit_sync()
        return wf.wait_for_completion_sync(timeout=60)
        
    except ConnectionError:
        print("Connection lost - waiting for reconnection")
        time.sleep(10)
        # Recreate client and retry
        client = InvokeAIClient.from_url("http://localhost:9090")
        wf = client.workflow_repo.create_workflow(workflow_def)
        return execute_with_recovery(wf)
```

## Monitoring & Logging

### Execution Logger

```python
import logging
from datetime import datetime

class ExecutionLogger:
    """Log workflow execution details."""
    
    def __init__(self, log_file="workflow.log"):
        self.logger = logging.getLogger("workflow")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_submission(self, submission):
        self.logger.info(f"Submitted: {submission.get('batch_id')}")
    
    def log_progress(self, queue_item):
        progress = queue_item.get('progress_percentage', 0)
        self.logger.info(f"Progress: {progress}%")
    
    def log_completion(self, result):
        status = result.get('status')
        if status == 'completed':
            self.logger.info("Workflow completed successfully")
        else:
            self.logger.error(f"Workflow failed: {status}")

# Use logger
logger = ExecutionLogger()
submission = wf.submit_sync()
logger.log_submission(submission)

result = wf.wait_for_completion_sync(
    progress_callback=logger.log_progress
)
logger.log_completion(result)
```

## Best Practices

### 1. Choose the Right Mode

```python
# Simple, one-off generation
result = wf.wait_for_completion_sync(wf.submit_sync())

# Multiple concurrent generations
results = await asyncio.gather(*[wf.submit() for _ in range(10)])

# Real-time UI updates
async for event in wf.stream_events():
    update_ui(event)
```

### 2. Handle All Status Types

```python
status_handlers = {
    'completed': lambda r: process_results(r),
    'failed': lambda r: log_error(r),
    'canceled': lambda r: cleanup(r),
    'pending': lambda r: wait_more(r)
}

status = result.get('status')
handler = status_handlers.get(status, lambda r: print(f"Unknown: {status}"))
handler(result)
```

### 3. Resource Cleanup

```python
try:
    result = wf.wait_for_completion_sync(submission)
finally:
    # Always cleanup
    if submission:
        # Delete uploaded images
        for img in uploaded_images:
            client.delete_image(img)
```

## Next Steps

- Master [Output Mapping](output-mapping.md)
- Learn about [Image Operations](images.md)
- Explore [Workflow Basics](workflow-basics.md)
- Review [Error Handling](../developer-guide/index.md)