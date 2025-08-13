# How to Use InvokeAI Real-time Streaming

## Overview

InvokeAI provides real-time event streaming through Socket.IO, **not through the REST API**. This allows clients to receive live updates about workflow execution, model loading, and download progress.

## Architecture

### No REST API Streaming
The InvokeAI REST API (`/api/v1/*`) does **NOT** support streaming responses. All endpoints return standard JSON responses and require polling for updates.

### Socket.IO Event System
Real-time updates are provided via Socket.IO at the `/ws/socket.io` endpoint.

**Source**: [`invokeai/app/api/sockets.py`](../../refcode/InvokeAI/invokeai/app/api/sockets.py)

## Socket.IO Configuration

### Server Setup
```python
# From invokeai/app/api/sockets.py, lines 92-95
self._sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
self._app = ASGIApp(socketio_server=self._sio, socketio_path="/ws/socket.io")
app.mount("/ws", self._app)
```

### Available Events

#### Queue Events (lines 56-64)
```python
QUEUE_EVENTS = {
    InvocationStartedEvent,      # Node execution started
    InvocationProgressEvent,      # Progress updates during execution
    InvocationCompleteEvent,      # Node completed successfully
    InvocationErrorEvent,         # Node failed with error
    QueueItemStatusChangedEvent,  # Queue item status changed
    BatchEnqueuedEvent,          # Batch added to queue
    QueueClearedEvent,           # Queue was cleared
}
```

#### Model Events (lines 66-80)
```python
MODEL_EVENTS = {
    DownloadStartedEvent,
    DownloadProgressEvent,
    DownloadCompleteEvent,
    DownloadErrorEvent,
    ModelLoadStartedEvent,
    ModelLoadCompleteEvent,
    ModelInstallStartedEvent,
    # ... more model events
}
```

## Client Implementation

### Python Socket.IO Client

#### Installation
```bash
pip install python-socketio[asyncio_client]
```

#### Basic Connection
```python
import socketio
import asyncio

# Create async client
sio = socketio.AsyncClient()

# Connect to InvokeAI
await sio.connect(
    'http://localhost:9090',
    socketio_path='/ws/socket.io'
)
```

### Subscribing to Queue Events

To receive events for a specific queue, emit the `subscribe_queue` event:

```python
# Subscribe to queue events (from sockets.py, lines 106-107)
await sio.emit('subscribe_queue', {
    'queue_id': 'default'  # or your specific queue_id
})
```

### Event Handlers

```python
@sio.on('invocation_started')
async def on_invocation_started(data):
    """Handler for InvocationStartedEvent"""
    print(f"Node started: {data['node_id']}")
    print(f"Type: {data['invocation_type']}")
    print(f"Session: {data['session_id']}")

@sio.on('invocation_progress') 
async def on_invocation_progress(data):
    """Handler for InvocationProgressEvent"""
    # Progress data structure varies by node type
    print(f"Progress for {data['node_id']}: {data.get('progress_message')}")
    
@sio.on('invocation_complete')
async def on_invocation_complete(data):
    """Handler for InvocationCompleteEvent"""
    print(f"Node complete: {data['node_id']}")
    # Result structure depends on node output type
    result = data.get('result', {})
    
@sio.on('invocation_error')
async def on_invocation_error(data):
    """Handler for InvocationErrorEvent"""
    print(f"Node failed: {data['node_id']}")
    print(f"Error: {data.get('error_type')}: {data.get('error_message')}")
```

### Complete Example: Workflow Execution with Streaming

```python
import socketio
import asyncio
import requests
import json

async def execute_workflow_with_streaming():
    # 1. Submit workflow via REST API
    workflow_data = {
        "prepend": False,
        "batch": {
            "graph": {...},  # Your workflow graph
            "runs": 1
        }
    }
    
    response = requests.post(
        "http://localhost:9090/api/v1/queue/default/enqueue_batch",
        json=workflow_data
    )
    result = response.json()
    batch_id = result['batch']['batch_id']
    session_id = result['item_ids'][0]  # Get first item
    
    # 2. Set up Socket.IO for streaming
    sio = socketio.AsyncClient()
    
    # Track completion
    completed = asyncio.Event()
    
    @sio.on('invocation_started')
    async def on_start(data):
        if data['session_id'] == session_id:
            print(f"🔵 {data['node_id']} started")
    
    @sio.on('invocation_progress')
    async def on_progress(data):
        if data['session_id'] == session_id:
            print(f"⏳ {data.get('progress_message', 'Processing...')}")
    
    @sio.on('invocation_complete')
    async def on_complete(data):
        if data['session_id'] == session_id:
            print(f"✅ {data['node_id']} complete")
    
    @sio.on('queue_item_status_changed')
    async def on_status_changed(data):
        if data['item_id'] == session_id:
            if data['status'] in ['completed', 'failed', 'canceled']:
                completed.set()
    
    # 3. Connect and subscribe
    await sio.connect('http://localhost:9090', socketio_path='/ws/socket.io')
    await sio.emit('subscribe_queue', {'queue_id': 'default'})
    
    # 4. Wait for completion
    await completed.wait()
    
    # 5. Cleanup
    await sio.emit('unsubscribe_queue', {'queue_id': 'default'})
    await sio.disconnect()

# Run the example
asyncio.run(execute_workflow_with_streaming())
```

## Event Data Structures

### InvocationStartedEvent
**Source**: [`invokeai/app/services/events/events_common.py`](../../refcode/InvokeAI/invokeai/app/services/events/events_common.py), line 108
```python
{
    "queue_id": "default",
    "item_id": 123,
    "batch_id": "batch_abc123",
    "session_id": "session_xyz",
    "invocation_id": "node_abc",
    "invocation_type": "flux_model_loader",
    "invocation_source_id": "f8d9d7c8-9ed7-4bd7-9e42-ab0e89bfac90"
}
```

### InvocationProgressEvent
**Source**: [`events_common.py`](../../refcode/InvokeAI/invokeai/app/services/events/events_common.py), line 134
```python
{
    "queue_id": "default",
    "item_id": 123,
    "batch_id": "batch_abc123",
    "session_id": "session_xyz",
    "invocation_id": "node_abc",
    "invocation_type": "denoise_latents",
    "progress_message": "Step 10/20",
    "percentage": 50,
    "image": {...}  # Optional progress image
}
```

## JavaScript/TypeScript Client

For web clients, the frontend uses Socket.IO in TypeScript:

**Source**: [`invokeai/frontend/web/src/services/events/useSocketIO.ts`](../../refcode/InvokeAI/invokeai/frontend/web/src/services/events/useSocketIO.ts)

```typescript
import { io } from 'socket.io-client';

const socket = io('http://localhost:9090', {
    path: '/ws/socket.io'
});

// Subscribe to queue
socket.emit('subscribe_queue', { queue_id: 'default' });

// Listen for events
socket.on('invocation_started', (data) => {
    console.log('Node started:', data);
});
```

## Important Notes

1. **No REST API Streaming**: The REST API does not support streaming. Use polling or Socket.IO.

2. **Queue Subscription Required**: You must subscribe to a queue to receive its events (line 107 in `sockets.py`).

3. **Event Filtering**: Events are room-based. Only subscribers to a specific queue_id receive that queue's events.

4. **Connection Management**: Always unsubscribe and disconnect properly to avoid memory leaks.

5. **Error Handling**: Socket.IO connections can drop. Implement reconnection logic for production use.

## Alternative: Polling-based Approach

If Socket.IO is not suitable, use REST API polling:

```python
import time
import requests

def poll_job_status(item_id: int, queue_id: str = "default"):
    """Poll job status via REST API"""
    url = f"http://localhost:9090/api/v1/queue/{queue_id}/i/{item_id}"
    
    while True:
        response = requests.get(url)
        item = response.json()
        
        print(f"Status: {item['status']}")
        
        if item['status'] in ['completed', 'failed', 'canceled']:
            return item
            
        time.sleep(0.5)  # Poll every 500ms
```

## References

- **Socket.IO Implementation**: [`invokeai/app/api/sockets.py`](../../refcode/InvokeAI/invokeai/app/api/sockets.py)
- **Event Definitions**: [`invokeai/app/services/events/events_common.py`](../../refcode/InvokeAI/invokeai/app/services/events/events_common.py)
- **Frontend Socket.IO**: [`invokeai/frontend/web/src/services/events/`](../../refcode/InvokeAI/invokeai/frontend/web/src/services/events/)
- **Queue Router API**: [`invokeai/app/api/routers/session_queue.py`](../../refcode/InvokeAI/invokeai/app/api/routers/session_queue.py)