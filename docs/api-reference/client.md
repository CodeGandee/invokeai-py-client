# Client API

Focus
- Accurate, to-the-point reference for connecting to InvokeAI, accessing repositories, making requests, and using Socket.IO events.
- Matches the current code in this repo.

Source locations
- Client class: [`InvokeAIClient`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L33){:target="_blank"}
- from_url constructor: [`InvokeAIClient.from_url()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L142){:target="_blank"}
- HTTP request helper: [`InvokeAIClient._make_request()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L525){:target="_blank"}
- Health check: [`InvokeAIClient.health_check()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L412){:target="_blank"}
- Socket.IO connect/session: [`InvokeAIClient.connect_socketio()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L428){:target="_blank"}, [`InvokeAIClient.socketio_session()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L470){:target="_blank"}

## InvokeAIClient

Constructor and URL helper
```python
class InvokeAIClient:
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
    ) -> None: ...
    
    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> "InvokeAIClient": ...
```

- Use from_url() for convenience:
  - Source: [`InvokeAIClient.from_url()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L142){:target="_blank"}
- Base URL formed as: http(s)://{host}:{port}{base_path}
- API key (if any) is sent as Bearer Authorization header

Repositories (properties)
```python
@property
def board_repo(self) -> BoardRepository: ...
@property
def workflow_repo(self) -> WorkflowRepository: ...
@property
def dnn_model_repo(self) -> DnnModelRepository: ...
```
- Lazily constructed and cached on first access:
  - [`InvokeAIClient.board_repo`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L215){:target="_blank"}
  - [`InvokeAIClient.workflow_repo`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L251){:target="_blank"}
  - [`InvokeAIClient.dnn_model_repo`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L281){:target="_blank"}

HTTP requests
```python
def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response: ...
```
- Helper used across repositories/handles:
  - Adds timeout if not provided
  - Raises for HTTP errors
  - Full URL = base_url + endpoint
  - Source: [`InvokeAIClient._make_request()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L525){:target="_blank"}

Health check
```python
def health_check(self) -> bool: ...
```
- Tries GET {base_url}/health
- Returns True/False
- Source: [`InvokeAIClient.health_check()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L412){:target="_blank"}

Socket.IO (async)
```python
async def connect_socketio(self) -> socketio.AsyncClient: ...
async def disconnect_socketio(self) -> None: ...
@asynccontextmanager
async def socketio_session(self) -> AsyncGenerator[socketio.AsyncClient, None]: ...
```
- Connects to ws(s)://{host}:{port} with path /ws/socket.io
- Use to subscribe to queue rooms and receive live events
- Source: [`InvokeAIClient.connect_socketio()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L428){:target="_blank"}

Context management
```python
def close(self) -> None: ...
def __enter__(self) -> "InvokeAIClient": ...
def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
```
- Ensures HTTP session closed
- Attempts to disconnect Socket.IO if connected
- Source: [`InvokeAIClient.close()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L493){:target="_blank"}

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