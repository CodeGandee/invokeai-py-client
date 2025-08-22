# Models API

Data models and enumerations.

## Core Models

```python
class IvkImage(BaseModel):
    """Image data model."""
    image_name: str
    image_url: str
    thumbnail_url: str
    board_id: Optional[str]
    width: int
    height: int
    created_at: datetime
    starred: bool

class IvkJob(BaseModel):
    """Job/session data model."""
    session_id: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]

class IvkDnnModel(BaseModel):
    """DNN model data."""
    model_key: str
    model_name: str
    base_model: BaseModelEnum
    model_type: str
    model_format: str
    path: str
```

## Enumerations

```python
class JobStatus(str, Enum):
    """Job status values."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"

class ImageCategory(str, Enum):
    """Image categories."""
    GENERAL = "general"
    CONTROL = "control"
    MASK = "mask"
    OTHER = "other"

class BaseModelEnum(str, Enum):
    """Base model types."""
    SD_1 = "sd-1"
    SD_2 = "sd-2"
    SDXL = "sdxl"
    SDXL_REFINER = "sdxl-refiner"
    FLUX = "flux"

class SchedulerName(str, Enum):
    """Scheduler types."""
    DDIM = "ddim"
    DDPM = "ddpm"
    DEIS = "deis"
    DPM_2 = "dpm_2"
    DPM_2_A = "dpm_2_a"
    EULER = "euler"
    EULER_A = "euler_a"
    HEUN = "heun"
    KDPM_2 = "kdpm_2"
    KDPM_2_A = "kdpm_2_a"
    LMS = "lms"
    PNDM = "pndm"
    UNIPC = "unipc"
```

## Session Events

```python
class SessionEvent(BaseModel):
    """WebSocket session event."""
    event: str
    session_id: str
    timestamp: datetime
    data: Dict[str, Any]

class InvocationEvent(BaseModel):
    """Node invocation event."""
    invocation_id: str
    invocation_type: str
    status: str
    outputs: Optional[Dict[str, Any]]
    error: Optional[str]
```

## Usage Examples

```python
# Create image model
image = IvkImage(
    image_name="output_123.png",
    image_url="/api/v1/images/i/output_123.png",
    thumbnail_url="/api/v1/images/t/output_123.png",
    board_id="results",
    width=1024,
    height=1024,
    created_at=datetime.now(),
    starred=False
)

# Job tracking
job = IvkJob(
    session_id="abc-123",
    status=JobStatus.IN_PROGRESS,
    created_at=datetime.now()
)

# Update status
job.status = JobStatus.COMPLETED
job.completed_at = datetime.now()

# Model info
model = IvkDnnModel(
    model_key="sdxl-base",
    model_name="SDXL Base 1.0",
    base_model=BaseModelEnum.SDXL,
    model_type="main",
    model_format="diffusers",
    path="models/sdxl/base"
)
```

See [User Guide](../user-guide/index.md) for detailed usage.