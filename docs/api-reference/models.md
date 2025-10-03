# Models and Enums

Comprehensive reference for Pydantic data models and enumerations used throughout the client for type-safe API integration, including workflow execution states, image categorization, and model architectures. Key implementations include [`JobStatus`/`ImageCategory`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L17){:target="_blank"} enums, [`IvkImage`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L117){:target="_blank"} metadata model, [`IvkJob`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L196){:target="_blank"} queue tracking, and [`IvkDnnModel`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L283){:target="_blank"} model metadata.

## Enumerations

Core enumerations used throughout the client for type safety and API compatibility.

### `JobStatus` - Workflow Execution States

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"  
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

Represents the lifecycle states of workflow execution jobs in InvokeAI's queue system.

**State Transitions:**
```
PENDING → RUNNING → COMPLETED
        ↘       ↘ FAILED
        ↘ CANCELLED
```

**State Descriptions:**
- `PENDING`: Job queued, waiting for execution resources
- `RUNNING`: Job actively being processed by InvokeAI
- `COMPLETED`: Job finished successfully with results available
- `FAILED`: Job encountered an error during execution
- `CANCELLED`: Job was cancelled by user or system

**Usage in Job Monitoring:**
```python
# Check job completion
if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
    print("Job finished")

# Wait for specific status
while job.status == JobStatus.PENDING:
    time.sleep(1)
    job = client.get_job(job.id)
```

See: `src/invokeai_py_client/models.py` (JobStatus)

### `ImageCategory` - Image Classification System

```python
class ImageCategory(str, Enum):
    USER = "user"        # User uploads (Assets tab)
    GENERAL = "general"  # Generated model outputs  
    CONTROL = "control"  # ControlNet conditioning images
    MASK = "mask"        # Inpainting and outpainting masks
    OTHER = "other"      # Miscellaneous/intermediate results
```

Defines the purpose and processing pipeline for images in InvokeAI workflows.

**Category Purposes:**
- **USER**: User-uploaded reference images, init images, assets
- **GENERAL**: Final generated outputs from diffusion models
- **CONTROL**: Conditioning images for ControlNet (depth, edges, pose, etc.)
- **MASK**: Binary masks defining regions for inpainting/outpainting
- **OTHER**: Temporary, intermediate, or utility images

**Workflow Integration:**
```python
# Upload reference image
ref_img = board_handle.upload_image(
    "reference.jpg", 
    image_category=ImageCategory.USER
)

# Upload ControlNet depth map
depth_img = board_handle.upload_image(
    "depth_map.png",
    image_category=ImageCategory.CONTROL
)
```

See: `src/invokeai_py_client/models.py` (ImageCategory)

### BaseDnnModelType & DnnModelType — DNN Model Taxonomy

```python
from invokeai_py_client.dnn_model import BaseDnnModelType, DnnModelType
```

Use BaseDnnModelType (e.g., StableDiffusionXL, Flux) with DnnModelType (e.g., Main, VAE, ControlNet).

**Model Selection Example:**
```python
models = client.dnn_model_repo.list_models()
sdxl_models = [m for m in models if m.base == BaseDnnModelType.StableDiffusionXL]
```

**Source:** [`BaseModelEnum`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L77){:target="_blank"}

## Pydantic Data Models

Type-safe data models using Pydantic for validation and serialization.

### `IvkImage` - Image Metadata Model

```python
class IvkImage(BaseModel):
    image_name: str
    board_id: str | None = None
    image_category: ImageCategory = ImageCategory.GENERAL
    width: int | None = None
    height: int | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    starred: bool = False
    metadata: dict[str, Any] | None = None
    thumbnail_url: str | None = None
    image_url: str | None = None
    is_intermediate: bool = False
    workflow_id: str | None = None
    node_id: str | None = None
    session_id: str | None = None
```

Represents image metadata with InvokeAI-specific attributes and relationships.

**Core Attributes:**
- `image_name` (str): Unique image identifier/filename on server
- `board_id` (str | None): Board containing this image ("none" for uncategorized)
- `image_category` (ImageCategory): Purpose classification (USER, GENERAL, CONTROL, etc.)
- `width/height` (int | None): Image dimensions in pixels
- `starred` (bool): User favorite status

**Workflow Tracking:**
- `workflow_id` (str | None): ID of workflow that generated this image
- `node_id` (str | None): Specific node within workflow that produced image
- `session_id` (str | None): Execution session identifier
- `is_intermediate` (bool): Whether image is temporary/intermediate result

**Metadata & URLs:**
- `metadata` (dict | None): Custom metadata and generation parameters
- `thumbnail_url/image_url` (str | None): Access URLs for image data
- `created_at/updated_at` (datetime | str | None): Timestamp information

#### Convenience Methods

**`from_api_response()` - API Deserialization**

```python
@classmethod
def from_api_response(cls, data: dict[str, Any]) -> IvkImage:
```

Create IvkImage instance from InvokeAI API response data.

**Features:**
- Automatic type coercion (string → ImageCategory enum)
- Handles missing optional fields gracefully
- Validates data structure and types

**`to_dict()` - Clean Serialization**

```python
def to_dict(self) -> dict[str, Any]:
```

Convert to clean dictionary for JSON serialization or API submission.

**Usage Examples:**
```python
# From API response
api_data = {"image_name": "abc123.png", "image_category": "general"}
img = IvkImage.from_api_response(api_data)
print(f"Image: {img.image_name}, Category: {img.image_category.value}")

# Create programmatically
img = IvkImage(
    image_name="my_image.png",
    image_category=ImageCategory.USER,
    starred=True,
    metadata={"prompt": "A beautiful landscape"}
)

# Export for API
data = img.to_dict()
```

**Integration with BoardHandle:**
- Returned by [`BoardHandle.upload_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L182){:target="_blank"}
- Returned by [`BoardHandle.upload_image_data()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L272){:target="_blank"}

**Source:** [`IvkImage`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L117){:target="_blank"}

### `IvkJob` - Queue Item Model

```python
class IvkJob(BaseModel):
    id: str
    workflow_id: str | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0.0..1.0
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    outputs: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> IvkJob: ...
    def is_complete(self) -> bool: ...
    def is_successful(self) -> bool: ...
    def to_dict(self) -> dict[str, Any]: ...
```
Helpers:
  - is_complete() checks for COMPLETED/FAILED/CANCELLED
  - is_successful() checks for COMPLETED
- Source: [`IvkJob`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L196){:target="_blank"} class

Note
- The client’s workflow execution methods return raw queue item dicts from the server; use IvkJob if you need a typed wrapper in your own code.

### `IvkDnnModel` - Model Metadata

```python
class IvkDnnModel(BaseModel):
    key: str
    name: str
    base: BaseModelEnum
    type: str                 # "main", "vae", "lora", ...
    hash: str | None = None
    path: str | None = None
    description: str | None = None
    format: str | None = None # "diffusers", "checkpoint", ...
    variant: str | None = None
    metadata: dict[str, Any] = {}

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "IvkDnnModel": ...
    def to_dict(self) -> dict[str, Any]: ...
```
- Used by the DNN model repository (read-only) and by workflow model sync:
  - [`InvokeAIClient.dnn_model_repo`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/client.py#L281){:target="_blank"}
  - [`WorkflowHandle.sync_dnn_model()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/workflow/workflow_handle.py#L1649){:target="_blank"}
- Source: [`IvkDnnModel`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L283){:target="_blank"} class

## Cross-references

- Client: [docs/api-reference/client.md](client.md)
- Workflows: [docs/api-reference/workflow.md](workflow.md)
- Fields and enums for inputs: [docs/api-reference/fields.md](fields.md)
- Boards and images: [docs/api-reference/boards.md](boards.md)
### DnnModel — DNN Model Metadata

```python
from invokeai_py_client.dnn_model import DnnModel

class DnnModel(BaseModel):
    key: str
    name: str
    type: DnnModelType
    base: BaseDnnModelType
    hash: str
    description: str = ""
    format: DnnModelFormat
    path: str
    source: str = ""
    file_size: int | None = None
    variant: str | None = None
    prediction_type: str | None = None
```

Use `client.dnn_model_repo.list_models()` to fetch DnnModel instances and
`get_model_by_key()` to retrieve a specific model.
