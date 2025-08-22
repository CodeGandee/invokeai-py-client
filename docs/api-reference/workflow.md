# Workflow API

Workflow management and execution APIs.

## WorkflowDefinition

```python
class WorkflowDefinition(BaseModel):
    """Workflow definition model."""
    
    id: str
    name: Optional[str]
    nodes: Dict[str, Dict[str, Any]]
    edges: List[Dict[str, Any]]
    exposedFields: List[Dict[str, Any]]
    
    @classmethod
    def from_file(cls, filepath: str) -> 'WorkflowDefinition':
        """Load workflow from JSON file."""
    
    def validate_structure(self) -> bool:
        """Validate workflow structure."""
```

## WorkflowHandle

```python
class WorkflowHandle:
    """Handle for workflow execution."""
    
    def list_inputs(self) -> List[IvkWorkflowInput]:
        """List all workflow inputs."""
    
    def get_input_value(self, index: int) -> IvkField:
        """Get input field by index."""
    
    def set_input_value(self, index: int, value: Any):
        """Set input value by index."""
    
    def sync_dnn_model(self, by_name=True, by_base=True) -> List:
        """Synchronize model fields with server."""
    
    def submit_sync(self) -> Dict[str, Any]:
        """Submit workflow synchronously."""
    
    def wait_for_completion_sync(self, submission, timeout=300) -> Dict:
        """Wait for workflow completion."""
    
    def map_outputs_to_images(self, result) -> List[str]:
        """Extract image names from result."""
```

## WorkflowRepository

```python
class WorkflowRepository:
    """Repository for workflow management."""
    
    def create_workflow(self, definition, board_id=None) -> WorkflowHandle:
        """Create workflow handle."""
    
    def load_workflow(self, filepath, board_id=None) -> WorkflowHandle:
        """Load workflow from file."""
```

## Usage Examples

```python
# Load and execute workflow
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("workflow.json")
)

# Sync models
wf.sync_dnn_model(by_name=True, by_base=True)

# Set inputs
wf.get_input_value(0).value = "A beautiful landscape"
wf.get_input_value(1).value = 42  # seed

# Execute
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(submission)
images = wf.map_outputs_to_images(result)
```

See [User Guide](../user-guide/workflow-basics.md) for detailed examples.
