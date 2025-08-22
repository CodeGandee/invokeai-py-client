# Extensions

Creating extensions and plugins for the client.

## Custom Field Types

```python
from invokeai_py_client.ivk_fields import IvkField

class CustomField(IvkField):
    """Custom field implementation."""
    
    def validate_field(self) -> bool:
        # Custom validation
        return True
    
    def to_api_format(self) -> Dict:
        # Convert to API format
        return {"value": self.value}
    
    @classmethod
    def from_api_format(cls, data: Dict):
        # Create from API data
        return cls(value=data["value"])
```

## Custom Repositories

```python
class CustomRepository:
    """Custom repository for specialized operations."""
    
    def __init__(self, client):
        self.client = client
    
    def custom_operation(self):
        # Implement custom logic
        pass
```

## Workflow Processors

```python
class WorkflowProcessor:
    """Process workflows with custom logic."""
    
    def preprocess(self, workflow):
        # Modify before submission
        pass
    
    def postprocess(self, result):
        # Process results
        pass
```

## Event Handlers

```python
class CustomEventHandler:
    """Handle workflow events."""
    
    def on_start(self, event):
        print(f"Started: {event}")
    
    def on_progress(self, event):
        print(f"Progress: {event}")
    
    def on_complete(self, event):
        print(f"Complete: {event}")
```

See [Architecture](architecture.md) for design patterns.
