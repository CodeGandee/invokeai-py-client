# Models and Enums

Focus
- Accurate, to-the-point reference for models and enums used by the client.
- Matches the current code in this repo.

Source locations
- Job status and image category enums: [`JobStatus`, `ImageCategory`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L17){:target="_blank"}
- Image DTO: [`IvkImage`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L117){:target="_blank"}
- Job DTO: [`IvkJob`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L196){:target="_blank"}
- DNN model metadata: [`IvkDnnModel`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L283){:target="_blank"}

## Enums

JobStatus (queue/lifecycle states)
```python
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```
- Note the string values are lowercase and include "running" and "cancelled"
  - Source: [`JobStatus`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L17){:target="_blank"} enum

ImageCategory (image purpose)
```python
class ImageCategory(str, Enum):
    USER = "user"        # user uploads (Assets)
    GENERAL = "general"  # model outputs
    CONTROL = "control"  # conditioning images (e.g., depth/edges/pose)
    MASK = "mask"        # inpainting masks
    OTHER = "other"      # misc/intermediate
```
- Source: [`ImageCategory`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L32){:target="_blank"} enum

BaseModelEnum (architectures)
```python
class BaseModelEnum(str, Enum):
    SD1 = "sd-1"
    SD2 = "sd-2"
    SDXL = "sdxl"
    SDXL_REFINER = "sdxl-refiner"
    FLUX = "flux"
    FLUX_SCHNELL = "flux-schnell"
```
- Includes FLUX_SCHNELL for fast FLUX variants
- Source: [`BaseModelEnum`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L77){:target="_blank"} enum

## IvkImage (Image DTO)

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

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "IvkImage": ...
    def to_dict(self) -> dict[str, Any]: ...
```
- Convenience:
  - from_api_response() coerces image_category string → ImageCategory
  - to_dict() emits a clean dict
- Used by [`BoardHandle.upload_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L182){:target="_blank"} and [`BoardHandle.upload_image_data()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L272){:target="_blank"}
- Source: [`IvkImage`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L117){:target="_blank"} class

Quick usage
```python
img = IvkImage.from_api_response({"image_name": "abc.png", "image_category": "general"})
print(img.image_name, img.image_category.value)
```

## IvkJob (Queue item/job DTO)

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
    def from_api_response(cls, data: dict[str, Any]) -> "IvkJob": ...
    def is_complete(self) -> bool: ...
    def is_successful(self) -> bool: ...
    def to_dict(self) -> dict[str, Any]: ...
```
- Helpers:
  - is_complete() checks for COMPLETED/FAILED/CANCELLED
  - is_successful() checks for COMPLETED
- Source: [`IvkJob`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/models.py#L196){:target="_blank"} class

Note
- The client’s workflow execution methods return raw queue item dicts from the server; use IvkJob if you need a typed wrapper in your own code.

## IvkDnnModel (Model metadata)

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