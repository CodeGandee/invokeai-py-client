# Raw API Examples

Direct REST API usage examples for advanced use cases.

## Overview

While the InvokeAI Python Client provides convenient abstractions, there are cases where direct API access is useful:

- Custom endpoints not yet wrapped by the client
- Fine-grained control over request/response payloads
- Low-level debugging and troubleshooting
- Integration with external systems or pipelines

What you'll learn

- How to make authenticated HTTP requests to the InvokeAI REST API
- How to create sessions and enqueue workflow batches
- How to upload/download images with multipart/form-data
- How to manage the queue (list, cancel, prune)
- How to monitor real-time events using Socket.IO

Prerequisites

- An InvokeAI server available (e.g., http://localhost:9090)
- Familiarity with Python requests and basic HTTP
- An exported workflow graph when enqueuing batches

## Basic API Request

### Using the Client's Request Helper

```python
from invokeai_py_client import InvokeAIClient

# Initialize client (URL helper parses host/port/base_path)
client = InvokeAIClient.from_url("http://localhost:9090")

# Make raw API request
response = client._make_request("GET", "/models/")
response.raise_for_status()
models = response.json()

for model in models.get("models", []):
    print(f"{model['model_name']}: {model['base_model']}")
```

### Direct requests Library

```python
import requests

base_url = "http://localhost:9090/api/v1"
headers = {"Content-Type": "application/json"}

# Get server version
response = requests.get(f"{base_url}/app/version", headers=headers)
version_info = response.json()
print(f"Server version: {version_info['version']}")

# List boards
response = requests.get(f"{base_url}/boards/", headers=headers)
boards = response.json()
for board in boards['items']:
    print(f"Board: {board['board_name']} (ID: {board['board_id']})")
```

## Session Management

### Create and Monitor Session

```python
import json
import requests
from typing import Dict, Any

class RawAPISession:
    """Direct API session management."""
    
    def __init__(self, base_url: str):
        self.base_url = f"{base_url}/api/v1"
        self.headers = {"Content-Type": "application/json"}
        self.session_id = None
    
    def create_session(self) -> str:
        """Create new session."""
        response = requests.post(
            f"{self.base_url}/sessions/",
            headers=self.headers
        )
        response.raise_for_status()
        session_data = response.json()
        self.session_id = session_data['id']
        return self.session_id
    
    def enqueue_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enqueue batch job."""
        response = requests.post(
            f"{self.base_url}/queue/default/enqueue_batch",
            headers=self.headers,
            json=batch_data
        )
        response.raise_for_status()
        return response.json()
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get session status."""
        response = requests.get(
            f"{self.base_url}/queue/default/session/{self.session_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_results(self) -> Dict[str, Any]:
        """Get session results."""
        response = requests.get(
            f"{self.base_url}/sessions/{self.session_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Use raw session
session = RawAPISession("http://localhost:9090")
session_id = session.create_session()
print(f"Created session: {session_id}")

# Prepare workflow batch
batch_data = {
    "prepend": False,
    "batch": {
        "graph": workflow_graph,  # Your workflow graph here
        "runs": 1
    }
}

# Submit batch
batch_result = session.enqueue_batch(batch_data)
print(f"Batch ID: {batch_result['batch']['batch_id']}")

# Monitor status
import time
while True:
    status = session.get_session_status()
    if status['status'] in ['COMPLETED', 'FAILED', 'CANCELED']:
        break
    print(f"Status: {status['status']}")
    time.sleep(1)

# Get results
results = session.get_results()
```

## Image Operations

### Upload Image via API

```python
def upload_image_raw(base_url: str, board_id: str, image_path: str) -> str:
    """Upload image using raw API."""
    url = f"{base_url}/api/v1/images/upload"
    
    # Prepare multipart form data
    with open(image_path, 'rb') as f:
        files = {
            'file': (os.path.basename(image_path), f, 'image/png')
        }
        data = {
            'board_id': board_id,
            'image_category': 'general',
            'is_intermediate': 'false'
        }
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        
    result = response.json()
    return result['image_name']

# Upload image
image_name = upload_image_raw(
    "http://localhost:9090",
    "my_board_id",
    "source.png"
)
print(f"Uploaded: {image_name}")
```

### Download Image via API

```python
def download_image_raw(base_url: str, image_name: str, save_path: str):
    """Download image using raw API."""
    # Get image URL
    url = f"{base_url}/api/v1/images/i/{image_name}/full"
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Save to file
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded to: {save_path}")

# Download image
download_image_raw(
    "http://localhost:9090",
    "output_abc123.png",
    "downloaded.png"
)
```

## Model Management

### List and Load Models

```python
def manage_models_raw(base_url: str):
    """Model management via raw API."""
    api_url = f"{base_url}/api/v1"
    headers = {"Content-Type": "application/json"}
    
    # List all models
    response = requests.get(f"{api_url}/models/", headers=headers)
    models = response.json()
    
    print("Available models:")
    for model in models['models']:
        print(f"  - {model['model_name']} ({model['base_model']})")
    
    # Get specific model info
    model_key = "stable-diffusion-xl-base-1.0"
    response = requests.get(
        f"{api_url}/models/i/{model_key}",
        headers=headers
    )
    
    if response.ok:
        model_info = response.json()
        print(f"\nModel details for {model_key}:")
        print(f"  Path: {model_info['path']}")
        print(f"  Type: {model_info['model_type']}")
        print(f"  Format: {model_info['model_format']}")
    
    # Load model (if needed)
    load_request = {
        "model_key": model_key,
        "submodel_type": "unet"
    }
    response = requests.post(
        f"{api_url}/models/load",
        headers=headers,
        json=load_request
    )
    
    if response.ok:
        print(f"Model loaded successfully")

# Execute model management
manage_models_raw("http://localhost:9090")
```

## Queue Management

### Advanced Queue Control

```python
class QueueManager:
    """Direct queue management via API."""
    
    def __init__(self, base_url: str):
        self.api_url = f"{base_url}/api/v1"
        self.headers = {"Content-Type": "application/json"}
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        response = requests.get(
            f"{self.api_url}/queue/default/status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def list_queue_items(self, limit: int = 10) -> list:
        """List items in queue."""
        params = {"limit": limit}
        response = requests.get(
            f"{self.api_url}/queue/default/list",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()['items']
    
    def cancel_item(self, item_id: str) -> bool:
        """Cancel queue item."""
        response = requests.delete(
            f"{self.api_url}/queue/default/cancel/{item_id}",
            headers=self.headers
        )
        return response.ok
    
    def clear_queue(self) -> Dict[str, Any]:
        """Clear entire queue."""
        response = requests.delete(
            f"{self.api_url}/queue/default/clear",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def prune_queue(self) -> Dict[str, Any]:
        """Prune completed items."""
        response = requests.delete(
            f"{self.api_url}/queue/default/prune",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Use queue manager
queue = QueueManager("http://localhost:9090")

# Check status
status = queue.get_queue_status()
print(f"Queue: {status['queue_size']} pending, {status['in_progress']} running")

# List items
items = queue.list_queue_items()
for item in items:
    print(f"Item {item['item_id']}: {item['status']}")

# Cancel specific item
if items:
    cancelled = queue.cancel_item(items[0]['item_id'])
    print(f"Cancelled: {cancelled}")
```

## WebSocket Events

Real-time events are delivered via Socket.IO on the InvokeAI server. When working at the raw API level, prefer a Socket.IO client instead of a plain WebSocket library.

Notes

- The Socket.IO endpoint uses the same host/port as HTTP with path /ws/socket.io.
- The high-level client provides an async context manager: InvokeAIClient.socketio_session(), which you can use directly.
- If you need raw access, use python-socketio (AsyncClient).

### Real-time Event Monitoring (Socket.IO)

```python
import asyncio
import socketio

async def monitor_events(url: str = "http://localhost:9090"):
    """Monitor real-time queue events via Socket.IO."""
    # Create Async Socket.IO client
    sio = socketio.AsyncClient()

    @sio.event
    async def connect():
        print("Connected to Socket.IO")

    @sio.event
    async def disconnect():
        print("Disconnected")

    @sio.on("queue_item_status_changed")
    async def on_status(evt):
        print("Status:", evt.get("status"), "item:", evt.get("item_id"))

    @sio.on("invocation_progress")
    async def on_progress(evt):
        # evt may include 'progress' as 0.0..1.0
        print(f"Progress: {evt.get('progress', 0.0)*100:.0f}%",
              "session:", evt.get("session_id"))

    # Connect to host (Socket.IO server uses /ws/socket.io)
    await sio.connect(
        url.replace("http", "ws"),
        transports=["websocket"],
        socketio_path="/ws/socket.io"
    )

    # Subscribe (example channel)
    await sio.emit("subscribe_queue", {"queue_id": "default"})

    try:
        # Keep listening for a while; in real apps, do useful work here
        await asyncio.sleep(10)
    finally:
        await sio.emit("unsubscribe_queue", {"queue_id": "default"})
        await sio.disconnect()

asyncio.run(monitor_events())
```

Alternatively, using the high-level client:

```python
import asyncio
from invokeai_py_client import InvokeAIClient

async def with_client_session():
    client = InvokeAIClient.from_url("http://localhost:9090")
    async with client.socketio_session() as sio:
        @sio.on("queue_item_status_changed")
        async def on_status(evt):
            print("Status:", evt.get("status"))

        await sio.emit("subscribe_queue", {"queue_id": "default"})
        await asyncio.sleep(10)
        await sio.emit("unsubscribe_queue", {"queue_id": "default"})

asyncio.run(with_client_session())
```

## Board Operations

### Advanced Board Management

```python
def manage_boards_raw(base_url: str):
    """Board management via raw API."""
    api_url = f"{base_url}/api/v1"
    headers = {"Content-Type": "application/json"}
    
    # Create board
    board_data = {
        "board_name": "API Test Board",
        "description": "Created via raw API"
    }
    response = requests.post(
        f"{api_url}/boards/",
        headers=headers,
        json=board_data
    )
    board = response.json()
    board_id = board['board_id']
    print(f"Created board: {board_id}")
    
    # Update board
    update_data = {
        "board_name": "Updated Board Name",
        "description": "Updated description",
        "starred": True
    }
    response = requests.patch(
        f"{api_url}/boards/{board_id}",
        headers=headers,
        json=update_data
    )
    print("Board updated")
    
    # List board images
    response = requests.get(
        f"{api_url}/boards/{board_id}/image_names",
        headers=headers
    )
    images = response.json()
    print(f"Board has {len(images)} images")
    
    # Move images to board
    if images:
        move_data = {
            "board_id": board_id,
            "image_names": images[:5]  # Move first 5
        }
        response = requests.post(
            f"{api_url}/images/move",
            headers=headers,
            json=move_data
        )
        print(f"Moved {len(move_data['image_names'])} images")
    
    # Delete board
    response = requests.delete(
        f"{api_url}/boards/{board_id}",
        headers=headers
    )
    print("Board deleted")

# Execute board management
manage_boards_raw("http://localhost:9090")
```

## Workflow Graph Construction

### Build Graph Programmatically

```python
def build_workflow_graph(prompt: str, model_key: str) -> Dict[str, Any]:
    """Build workflow graph structure."""
    graph = {
        "id": "text_to_image_workflow",
        "nodes": {
            "model_loader": {
                "id": "model_loader",
                "type": "main_model_loader",
                "inputs": {
                    "model": {
                        "key": model_key,
                        "base": "sdxl",
                        "type": "main"
                    }
                }
            },
            "positive_prompt": {
                "id": "positive_prompt",
                "type": "compel",
                "inputs": {
                    "prompt": prompt,
                    "style": "none"
                }
            },
            "negative_prompt": {
                "id": "negative_prompt",
                "type": "compel",
                "inputs": {
                    "prompt": "blurry, low quality",
                    "style": "none"
                }
            },
            "noise": {
                "id": "noise",
                "type": "noise",
                "inputs": {
                    "seed": 12345,
                    "width": 1024,
                    "height": 1024
                }
            },
            "denoise": {
                "id": "denoise",
                "type": "denoise_latents",
                "inputs": {
                    "steps": 30,
                    "cfg_scale": 7.5,
                    "scheduler": "euler",
                    "denoise_start": 0.0,
                    "denoise_end": 1.0
                }
            },
            "latents_to_image": {
                "id": "latents_to_image",
                "type": "l2i",
                "inputs": {}
            }
        },
        "edges": [
            {
                "source": {"node_id": "model_loader", "field": "clip"},
                "destination": {"node_id": "positive_prompt", "field": "clip"}
            },
            {
                "source": {"node_id": "model_loader", "field": "clip"},
                "destination": {"node_id": "negative_prompt", "field": "clip"}
            },
            {
                "source": {"node_id": "model_loader", "field": "unet"},
                "destination": {"node_id": "denoise", "field": "unet"}
            },
            {
                "source": {"node_id": "positive_prompt", "field": "conditioning"},
                "destination": {"node_id": "denoise", "field": "positive_conditioning"}
            },
            {
                "source": {"node_id": "negative_prompt", "field": "conditioning"},
                "destination": {"node_id": "denoise", "field": "negative_conditioning"}
            },
            {
                "source": {"node_id": "noise", "field": "noise"},
                "destination": {"node_id": "denoise", "field": "noise"}
            },
            {
                "source": {"node_id": "denoise", "field": "latents"},
                "destination": {"node_id": "latents_to_image", "field": "latents"}
            },
            {
                "source": {"node_id": "model_loader", "field": "vae"},
                "destination": {"node_id": "latents_to_image", "field": "vae"}
            }
        ]
    }
    
    return graph

# Build and submit graph
graph = build_workflow_graph(
    "A majestic mountain landscape",
    "stable-diffusion-xl-base-1.0"
)

# Submit via API
batch_data = {
    "prepend": False,
    "batch": {
        "graph": graph,
        "runs": 1
    }
}

response = requests.post(
    "http://localhost:9090/api/v1/queue/default/enqueue_batch",
    json=batch_data
)
print(f"Submitted: {response.json()}")
```

## Error Handling

### Comprehensive Error Management

```python
from typing import Optional, Callable
import time

class APIErrorHandler:
    """Handle API errors with retry logic."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """Execute function with retry on failure."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            
            except requests.HTTPError as e:
                last_error = e
                
                # Check if retryable
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    wait_time = self.backoff_factor ** attempt
                    print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Non-retryable error
                    print(f"Non-retryable error: {e.response.status_code}")
                    raise
            
            except requests.ConnectionError as e:
                last_error = e
                wait_time = self.backoff_factor ** attempt
                print(f"Connection error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise
        
        # All retries exhausted
        print(f"All {self.max_retries} attempts failed")
        raise last_error

# Use error handler
handler = APIErrorHandler(max_retries=3)

def risky_api_call():
    response = requests.get("http://localhost:9090/api/v1/models/")
    response.raise_for_status()
    return response.json()

try:
    result = handler.execute_with_retry(risky_api_call)
    print(f"Success: {len(result['models'])} models")
except Exception as e:
    print(f"Failed after retries: {e}")
```

## Performance Optimization

### Connection Pooling

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_optimized_session() -> requests.Session:
    """Create session with connection pooling and retry."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
    )
    
    # Configure adapter with connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )
    
    # Mount adapter
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    
    return session

# Use optimized session
session = create_optimized_session()

# All requests use connection pooling
response = session.get("http://localhost:9090/api/v1/models/")
models = response.json()

# Reuses connection
response = session.get("http://localhost:9090/api/v1/boards/")
boards = response.json()
```

## Authentication

### API Key Authentication

```python
def setup_authenticated_client(base_url: str, api_key: str):
    """Setup client with API key authentication."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test authentication
    response = requests.get(
        f"{base_url}/api/v1/app/version",
        headers=headers
    )
    
    if response.ok:
        print("Authentication successful")
        return headers
    else:
        raise ValueError(f"Authentication failed: {response.status_code}")

# Use authenticated requests
api_key = "your-api-key-here"
headers = setup_authenticated_client("http://localhost:9090", api_key)

# All subsequent requests use auth headers
response = requests.get(
    "http://localhost:9090/api/v1/models/",
    headers=headers
)
```

## Next Steps

- Review [SDXL Text-to-Image](sdxl-text-to-image.md) for workflow examples
- Explore [FLUX Image-to-Image](flux-image-to-image.md) for advanced techniques
- See [Multi-Stage Refine](multi-stage-refine.md) for complex pipelines
- Check the [API Reference](../api-reference/index.md) for detailed specifications