# Client API

Complete reference for the main InvokeAI client interface, covering connection management, repository access, HTTP operations, and Socket.IO event handling. Key source locations include the main [`InvokeAIClient`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L33){:target="_blank"} class, [`from_url()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L142){:target="_blank"} constructor, [`_make_request()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L525){:target="_blank"} HTTP helper, [`health_check()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L412){:target="_blank"} connectivity testing, and Socket.IO methods [`connect_socketio()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L428){:target="_blank"}/[`socketio_session()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L470){:target="_blank"}.

## InvokeAIClient

Main client class for interacting with an InvokeAI server instance. This class represents a connection to an InvokeAI server and provides high-level operations for workflow execution, asset management, and job tracking.

### Constructor

```python
def __init__(
    self,
    host: str = "localhost",
    port: int = 9090,
    api_key: str | None = None,
    timeout: float = 30.0,
    base_path: str = "/api/v1",
    use_https: bool = False,
    verify_ssl: bool = True,
    max_retries: int = 3,
    **kwargs: Any,
) -> None:
```

Initialize the InvokeAI client with connection parameters.

**Parameters:**
- `host` (str): The hostname or IP address of the InvokeAI server
- `port` (int): The port number of the InvokeAI server  
- `api_key` (str, optional): API key for authentication, if required
- `timeout` (float): Request timeout in seconds
- `base_path` (str): Base path for API endpoints
- `use_https` (bool): Whether to use HTTPS for connections
- `verify_ssl` (bool): Whether to verify SSL certificates
- `max_retries` (int): Maximum number of retry attempts for failed requests

**Example:**
```python
# Direct initialization
client = InvokeAIClient(
    host="192.168.1.100",
    port=9090,
    timeout=60.0,
    use_https=True
)
```

### `from_url()` - URL Helper Constructor

```python
@classmethod
def from_url(cls, url: str, **kwargs: Any) -> InvokeAIClient:
```

Create an InvokeAI client from a URL. Parses the URL into host/port/base_path automatically.

**Parameters:**
- `url` (str): The URL of the InvokeAI instance (e.g., "http://localhost:9090")
- `**kwargs`: Additional keyword arguments passed to the constructor

**Returns:**
- `InvokeAIClient`: A configured client instance

**Examples:**
```python
# Recommended approach - automatic URL parsing
client = InvokeAIClient.from_url("http://localhost:9090")

# With custom base path
client = InvokeAIClient.from_url("https://my-invoke.ai:8080/api/v1")

# With additional parameters
client = InvokeAIClient.from_url(
    "http://localhost:9090", 
    timeout=120.0,
    api_key="my-key"
)
```

**Source:** [`InvokeAIClient.from_url()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L142){:target="_blank"}

### Repository Properties

The client provides repository instances for different operations, lazily constructed and cached on first access.

#### `board_repo` Property

```python
@property
def board_repo(self) -> BoardRepository:
```

Get the board repository instance for board-related operations.

**Returns:**
- `BoardRepository`: Repository for managing boards and images

**Example:**
```python
# Access board operations
boards = client.board_repo.list_boards()
handle = client.board_repo.get_board_handle("my-board-id")
```

**Source:** [`InvokeAIClient.board_repo`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L215){:target="_blank"}

#### `workflow_repo` Property

```python
@property
def workflow_repo(self) -> WorkflowRepository:
```

Get the workflow repository instance for workflow-related operations.

**Returns:**
- `WorkflowRepository`: Repository for creating and managing workflows

**Example:**
```python
# Create workflow from definition
definition = WorkflowDefinition.from_file("workflow.json")
workflow = client.workflow_repo.create_workflow(definition)
```

**Source:** [`InvokeAIClient.workflow_repo`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L251){:target="_blank"}

#### `dnn_model_repo` Property  

```python
@property
def dnn_model_repo(self) -> DnnModelRepository:
```

Get the DNN model repository instance for model discovery and management.

**Returns:**
- `DnnModelRepository`: Repository for listing and accessing models

**Example:**
```python
# Discovery: list/get
models = client.dnn_model_repo.list_models()
sdxl_models = [m for m in models if str(getattr(m, "base", "")).lower() == "sdxl"]
```

Model management (v2 model_manager):
- Install from local path/URL/HF; idempotent (409 already-installed returns a synthetic COMPLETED handle)
- Monitor install jobs with `ModelInstJobHandle.wait_until()`
- Convert/delete models; `delete_all_models()` convenience
- Scan folders for models; empty cache; get cache stats
- HF login/logout/status

```python
from invokeai_py_client.dnn_model import ModelInstallJobFailed

h = client.dnn_model_repo.install_model("/mnt/extra/sdxl/main/my_model.safetensors", inplace=True)
try:
    info = h.wait_until(timeout=None)
    print("installed", getattr(info, "model_key", None))
except ModelInstallJobFailed as e:
    print("failed", getattr(e.info, "error", None))
```

### Core Methods

#### `_make_request()` - HTTP Request Helper

```python
def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
```

Make an HTTP request to the API. This is the core method used by all repositories and handles for HTTP communication.

**Parameters:**
- `method` (str): HTTP method ("GET", "POST", "PUT", "DELETE", etc.)
- `endpoint` (str): API endpoint path (will be appended to base_url)
- `**kwargs`: Additional arguments passed to requests (json, data, params, etc.)

**Returns:**
- `requests.Response`: HTTP response object

**Behavior:**
- Adds timeout if not provided in kwargs
- Raises `requests.HTTPError` for HTTP error status codes  
- Full URL constructed as: `base_url + endpoint`
- Includes authentication headers if API key is configured

**Source:** [`InvokeAIClient._make_request()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L525){:target="_blank"}

#### `health_check()` - Connection Verification

```python
def health_check(self) -> bool:
```

Check if the InvokeAI instance is healthy and reachable.

**Returns:**
- `bool`: True if server responds successfully, False otherwise

**Behavior:**
- Sends GET request to `{base_url}/health`
- Returns True on successful response, False on any error
- Does not raise exceptions - safe for connectivity testing

**Example:**
```python
client = InvokeAIClient.from_url("http://localhost:9090")
if client.health_check():
    print("InvokeAI server is reachable")
else:
    print("Cannot connect to InvokeAI server")
```

**Source:** [`InvokeAIClient.health_check()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L412){:target="_blank"}

### Socket.IO Operations (Async)

The client provides async Socket.IO functionality for real-time event monitoring during workflow execution.

#### `connect_socketio()` - Establish Socket.IO Connection

```python
async def connect_socketio(self) -> socketio.AsyncClient:
```

Connect to the InvokeAI Socket.IO server for real-time events.

**Returns:**
- `socketio.AsyncClient`: Connected Socket.IO client instance

**Connection Details:**
- Connects to `ws(s)://{host}:{port}` with path `/ws/socket.io`
- Uses same host/port as HTTP client
- Enables real-time workflow progress and status updates

**Source:** [`InvokeAIClient.connect_socketio()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L428){:target="_blank"}

#### `disconnect_socketio()` - Close Socket.IO Connection

```python
async def disconnect_socketio(self) -> None:
```

Disconnect from the Socket.IO server and clean up the connection.

#### `socketio_session()` - Managed Socket.IO Context

```python
@asynccontextmanager
async def socketio_session(self) -> AsyncGenerator[socketio.AsyncClient, None]:
```

Context manager for Socket.IO connections. Automatically connects and disconnects.

**Yields:**
- `socketio.AsyncClient`: Connected Socket.IO client for event handling

**Example:**
```python
async def monitor_workflow():
    client = InvokeAIClient.from_url("http://localhost:9090")
    
    async with client.socketio_session() as sio:
        # Subscribe to queue events
        await sio.emit("subscribe_queue", {"queue_id": "default"})
        
        @sio.on("queue_item_status_changed")
        async def on_status_change(data):
            print(f"Status: {data.get('status')}")
        
        # Your async workflow operations...
        await asyncio.sleep(10)
        
        # Unsubscribe before context exits
        await sio.emit("unsubscribe_queue", {"queue_id": "default"})
```

### Context Management

#### `close()` - Resource Cleanup

```python
def close(self) -> None:
```

Close the client connection and clean up all resources.

**Behavior:**
- Closes HTTP session and connection pools
- Attempts to disconnect Socket.IO if connected
- Should be called when done with the client

#### Context Manager Support

```python
def __enter__(self) -> InvokeAIClient:
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
```

Enables usage as a context manager for automatic resource cleanup.

**Example:**
```python
with InvokeAIClient.from_url("http://localhost:9090") as client:
    boards = client.board_repo.list_boards()
    # client.close() called automatically on exit
```

**Source:** [`InvokeAIClient.close()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L493){:target="_blank"}

Note on non-existent methods
- Older docs mentioned connect(), disconnect(), ping(), get_server_info(), connect_websocket(), subscribe_to_queue(). These are not present. Use:
  - health_check() for a quick probe
  - _make_request("GET", "/app/version") if you need version info
  - connect_socketio()/socketio_session() for WebSocket(SIO) usage

## Usage Examples

Basic connection and quick probe
```python
from invokeai_py_client import InvokeAIClient

# 1) Using URL helper (recommended)
client = InvokeAIClient.from_url("http://localhost:9090")

# 2) Or explicit host/port (base_path defaults to /api/v1)
client = InvokeAIClient(host="localhost", port=9090)

# Quick probe
if client.health_check():
    print("InvokeAI reachable")

# Read version (raw request)
resp = client._make_request("GET", "/app/version")
print(resp.json())
```

Create a workflow and run (blocking)
```python
from invokeai_py_client.workflow import WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/sdxl-text-to-image.json")
)

# Discover inputs and set values (indices are the stable handle)
for inp in wf.list_inputs():
    print(f"[{inp.input_index:02d}] {inp.label or inp.field_name}")

field = wf.get_input_value(0)
if hasattr(field, "value"):
    field.value = "A cinematic sunset over snowy mountains"

submission = wf.submit_sync()
queue_item = wf.wait_for_completion_sync(timeout=180)
for m in wf.map_outputs_to_images(queue_item):
    print(m["node_id"], m.get("image_names"))
```
- Mirrors the example: [`sdxl-text-to-image.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/sdxl-text-to-image.py){:target="_blank"}

Boards and images
```python
# List boards
boards = client.board_repo.list_boards(include_uncategorized=True)
for b in boards:
    print(getattr(b, "board_id", "?"), getattr(b, "board_name", ""))

# Get a handle and download an image (by name)
bh = client.board_repo.get_board_handle("none")  # uncategorized
names = bh.list_images(limit=10)
if names:
    data = bh.download_image(names[0], full_resolution=True)
    with open(names[0], "wb") as f:
        f.write(data)
```
- See handle methods: [`BoardHandle`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L23){:target="_blank"} class

Socket.IO events (async)
```python
import asyncio

async def main():
    client = InvokeAIClient.from_url("http://localhost:9090")
    async with client.socketio_session() as sio:
        await sio.emit("subscribe_queue", {"queue_id": "default"})
        
        @sio.on("queue_item_status_changed")
        async def on_status(evt):
            print("Status:", evt.get("status"))

        # Submit a workflow (sync submit), then wait using your own logic
        # The server will emit events while processing

        await asyncio.sleep(5)
        await sio.emit("unsubscribe_queue", {"queue_id": "default"})

asyncio.run(main())
```

DNN models (read-only repo)
```python
# List models (fresh API call)
models = client.dnn_model_repo.list_models()
print(f"Total models: {len(models)}")

# Use sync_dnn_model during workflow prep to normalize identifiers
wf.sync_dnn_model(by_name=True, by_base=True)
```

## Best practices
- Use from_url() to avoid manual host/port parsing.
- Treat indices as the public, stable input API.
- Keep Socket.IO connections long-lived if you need frequent events; reuse via socketio_session().
- For uploads, prefer BoardHandle.upload_image or upload_image_data; omit board_id for uncategorized (“none” is a sentinel for read ops).
- Handle HTTP errors raised by _make_request() and use repository methods wherever available.

Cross-references
- Workflows: [docs/api-reference/workflow.md](workflow.md)
- Boards: [docs/api-reference/boards.md](boards.md)
- Fields: [docs/api-reference/fields.md](fields.md)
- Examples: [docs/examples/index.md](../examples/index.md)
