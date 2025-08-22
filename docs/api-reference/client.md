# Client API

Core client class for InvokeAI server interaction.

## InvokeAIClient

### Class Definition

```python
class InvokeAIClient:
    """Main client for InvokeAI API interaction."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:9090",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True
    ):
        """
        Initialize InvokeAI client.
        
        Args:
            base_url: InvokeAI server URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            verify_ssl: Verify SSL certificates
        """
```

### Properties

```python
@property
def board_repo(self) -> BoardRepository:
    """Access board repository for image management."""
    
@property
def workflow_repo(self) -> WorkflowRepository:
    """Access workflow repository for workflow operations."""
    
@property
def is_connected(self) -> bool:
    """Check if client is connected to server."""
    
@property
def server_version(self) -> str:
    """Get InvokeAI server version."""
```

### Connection Methods

```python
def connect(self) -> bool:
    """
    Establish connection to InvokeAI server.
    
    Returns:
        bool: True if connection successful
        
    Raises:
        ConnectionError: If unable to connect
    """

def disconnect(self):
    """Close connection to server."""

def ping(self) -> bool:
    """
    Check server availability.
    
    Returns:
        bool: True if server is responsive
    """

def get_server_info(self) -> Dict[str, Any]:
    """
    Get server information and capabilities.
    
    Returns:
        dict: Server information including version, features
    """
```

### Request Methods

```python
def _make_request(
    self,
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json: Optional[Dict] = None,
    files: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> requests.Response:
    """
    Make HTTP request to API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        params: Query parameters
        json: JSON body data
        files: Files for multipart upload
        headers: Additional headers
        
    Returns:
        Response object
        
    Raises:
        InvokeAIError: On request failure
    """

async def _make_request_async(
    self,
    method: str,
    endpoint: str,
    **kwargs
) -> aiohttp.ClientResponse:
    """Async version of _make_request."""
```

### WebSocket Methods

```python
def connect_websocket(
    self,
    on_message: Callable[[Dict], None],
    on_error: Optional[Callable[[Exception], None]] = None,
    on_close: Optional[Callable[[], None]] = None
) -> WebSocketConnection:
    """
    Connect to server WebSocket for real-time events.
    
    Args:
        on_message: Callback for messages
        on_error: Callback for errors
        on_close: Callback for connection close
        
    Returns:
        WebSocketConnection object
    """

def subscribe_to_queue(
    self,
    queue_id: str = "default",
    callback: Optional[Callable[[Dict], None]] = None
) -> Subscription:
    """
    Subscribe to queue events.
    
    Args:
        queue_id: Queue identifier
        callback: Event callback
        
    Returns:
        Subscription object
    """
```

## Usage Examples

### Basic Connection

```python
from invokeai_py_client import InvokeAIClient

# Simple connection
client = InvokeAIClient()

# Custom configuration
client = InvokeAIClient(
    base_url="http://192.168.1.100:9090",
    timeout=60,
    max_retries=5
)

# With authentication
client = InvokeAIClient(
    base_url="https://invoke.example.com",
    api_key="sk-abc123..."
)
```

### Server Information

```python
# Check connection
if client.ping():
    print("Server is available")

# Get server info
info = client.get_server_info()
print(f"Server version: {info['version']}")
print(f"Available models: {info['models_count']}")
print(f"Features: {info['features']}")
```

### Making Raw Requests

```python
# GET request
response = client._make_request("GET", "/models/")
models = response.json()

# POST request with JSON
data = {"name": "test_board", "description": "Test"}
response = client._make_request("POST", "/boards/", json=data)
board = response.json()

# File upload
with open("image.png", "rb") as f:
    files = {"file": f}
    response = client._make_request(
        "POST",
        "/images/upload",
        files=files
    )
```

### WebSocket Events

```python
def handle_message(msg):
    print(f"Event: {msg.get('event')}")
    if msg.get('event') == 'invocation_complete':
        print(f"Completed: {msg.get('data')}")

# Connect to WebSocket
ws = client.connect_websocket(
    on_message=handle_message,
    on_error=lambda e: print(f"Error: {e}"),
    on_close=lambda: print("Connection closed")
)

# Subscribe to queue
subscription = client.subscribe_to_queue(
    queue_id="default",
    callback=handle_message
)

# Later: unsubscribe
subscription.unsubscribe()
ws.close()
```

### Async Operations

```python
import asyncio

async def async_operations():
    # Async request
    response = await client._make_request_async("GET", "/models/")
    models = await response.json()
    
    # Async workflow execution
    wf = client.workflow_repo.create_workflow(definition)
    submission = await wf.submit_async()
    result = await wf.wait_for_completion_async(submission)
    
    return result

# Run async
result = asyncio.run(async_operations())
```

## Configuration

### Environment Variables

```python
import os

# Set via environment
os.environ['INVOKEAI_URL'] = 'http://localhost:9090'
os.environ['INVOKEAI_API_KEY'] = 'your-key'

# Client will use environment variables
client = InvokeAIClient()  # Uses env vars
```

### Session Configuration

```python
# Configure session
client = InvokeAIClient()

# Set custom headers
client.session.headers.update({
    'X-Custom-Header': 'value'
})

# Configure retries
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry_strategy)
client.session.mount("http://", adapter)
client.session.mount("https://", adapter)
```

## Error Handling

### Exception Types

```python
from invokeai_py_client.exceptions import (
    InvokeAIError,      # Base exception
    ConnectionError,    # Connection failures
    AuthenticationError,  # Auth failures
    TimeoutError,       # Request timeouts
    APIError           # API-specific errors
)
```

### Error Handling Pattern

```python
try:
    client = InvokeAIClient(base_url="http://localhost:9090")
    client.connect()
    
except ConnectionError as e:
    print(f"Failed to connect: {e}")
    # Try fallback server
    client = InvokeAIClient(base_url="http://backup:9090")
    
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Refresh token or re-authenticate
    
except TimeoutError as e:
    print(f"Request timed out: {e}")
    # Retry with longer timeout
    
except InvokeAIError as e:
    print(f"API error: {e}")
    # Handle general errors
```

## Context Manager

```python
# Automatic connection management
with InvokeAIClient() as client:
    # Client is connected
    wf = client.workflow_repo.create_workflow(definition)
    result = wf.submit_sync()
    # Connection closed automatically

# Custom context manager
class ManagedClient:
    def __init__(self, **kwargs):
        self.client = InvokeAIClient(**kwargs)
    
    def __enter__(self):
        self.client.connect()
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.disconnect()
        if exc_type:
            print(f"Error occurred: {exc_val}")
```

## Performance Optimization

### Connection Pooling

```python
# Reuse connections
client = InvokeAIClient()

# Configure pool size
client.session.mount(
    'http://',
    HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20
    )
)
```

### Request Batching

```python
def batch_requests(client, endpoints):
    """Execute multiple requests efficiently."""
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(client._make_request, "GET", ep): ep
            for ep in endpoints
        }
        
        results = {}
        for future in concurrent.futures.as_completed(futures):
            endpoint = futures[future]
            try:
                response = future.result()
                results[endpoint] = response.json()
            except Exception as e:
                results[endpoint] = {"error": str(e)}
        
        return results

# Batch multiple endpoints
endpoints = ["/models/", "/boards/", "/images/"]
results = batch_requests(client, endpoints)
```

## Testing

### Mock Client

```python
from unittest.mock import Mock, patch

def test_workflow():
    # Mock client
    mock_client = Mock(spec=InvokeAIClient)
    mock_client.workflow_repo.create_workflow.return_value = Mock()
    
    # Test workflow creation
    wf = mock_client.workflow_repo.create_workflow("test.json")
    assert wf is not None

# Patch requests
@patch('requests.Session')
def test_connection(mock_session):
    mock_session.return_value.get.return_value.ok = True
    
    client = InvokeAIClient()
    assert client.ping()
```

## Best Practices

1. **Always use context managers** for automatic resource cleanup
2. **Handle exceptions** appropriately for production code
3. **Configure timeouts** based on expected operation duration
4. **Use async methods** for concurrent operations
5. **Cache client instances** to reuse connections
6. **Monitor WebSocket** connections for disconnections
7. **Implement retry logic** for transient failures
8. **Log API interactions** for debugging

## Next Steps

- See [Workflow API](workflow.md) for workflow operations
- Review [Boards API](boards.md) for image management
- Check [Fields API](fields.md) for type system
- Explore [Examples](../examples/index.md) for practical usage