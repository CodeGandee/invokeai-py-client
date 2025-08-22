# Utilities API

Helper functions and utility classes.

## AssetManager

```python
class AssetManager:
    """Manage image assets."""
    
    def upload_image(self, filepath: str, board_id: str) -> str:
        """Upload image to board."""
    
    def download_image(self, image_name: str, save_path: str):
        """Download image to file."""
    
    def delete_image(self, image_name: str) -> bool:
        """Delete image."""
    
    def move_image(self, image_name: str, to_board: str) -> bool:
        """Move image between boards."""
```

## TypeConverter

```python
class TypeConverter:
    """Convert between field types."""
    
    @staticmethod
    def to_field(value: Any, field_type: str) -> IvkField:
        """Convert value to field."""
    
    @staticmethod
    def from_field(field: IvkField) -> Any:
        """Extract value from field."""
    
    @staticmethod
    def infer_type(value: Any) -> str:
        """Infer field type from value."""
```

## ProgressTracker

```python
class ProgressTracker:
    """Track workflow progress."""
    
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = None
    
    def start(self):
        """Start tracking."""
    
    def update(self, step: int, message: str = ""):
        """Update progress."""
    
    def get_eta(self) -> float:
        """Get estimated time remaining."""
    
    @property
    def progress_percent(self) -> float:
        """Get progress percentage."""
```

## Validators

```python
class WorkflowValidator:
    """Validate workflow definitions."""
    
    @staticmethod
    def validate_structure(definition: Dict) -> List[str]:
        """Validate workflow structure."""
    
    @staticmethod
    def validate_nodes(nodes: Dict) -> List[str]:
        """Validate node definitions."""
    
    @staticmethod
    def validate_edges(edges: List) -> List[str]:
        """Validate edge connections."""

class InputValidator:
    """Validate workflow inputs."""
    
    @staticmethod
    def validate_prompt(prompt: str) -> bool:
        """Validate prompt text."""
    
    @staticmethod
    def validate_dimensions(width: int, height: int) -> bool:
        """Validate image dimensions."""
    
    @staticmethod
    def validate_seed(seed: int) -> bool:
        """Validate seed value."""
```

## File Helpers

```python
def save_workflow(workflow: WorkflowDefinition, filepath: str):
    """Save workflow to JSON file."""

def load_workflow(filepath: str) -> WorkflowDefinition:
    """Load workflow from JSON file."""

def save_image(image_data: bytes, filepath: str):
    """Save image data to file."""

def load_image(filepath: str) -> bytes:
    """Load image as bytes."""

def ensure_directory(path: str):
    """Ensure directory exists."""
```

## Retry Helpers

```python
def retry_on_failure(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Any:
    """Retry function on failure."""

async def async_retry(
    func: Callable,
    max_attempts: int = 3
) -> Any:
    """Async retry wrapper."""
```

## Usage Examples

```python
# Asset management
assets = AssetManager(client)
image_name = assets.upload_image("input.png", "inputs")
assets.download_image(image_name, "output.png")

# Type conversion
converter = TypeConverter()
field = converter.to_field("Hello", "string")
value = converter.from_field(field)

# Progress tracking
tracker = ProgressTracker(total_steps=10)
tracker.start()
for i in range(10):
    tracker.update(i, f"Step {i+1}")
    print(f"Progress: {tracker.progress_percent:.1f}%")

# Validation
errors = WorkflowValidator.validate_structure(workflow_dict)
if errors:
    print(f"Validation errors: {errors}")

# Retry logic
result = retry_on_failure(
    lambda: risky_operation(),
    max_attempts=5,
    delay=2.0
)
```

See [Examples](../examples/index.md) for practical usage.