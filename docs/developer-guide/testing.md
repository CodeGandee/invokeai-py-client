# Testing

Testing guidelines and strategies.

## Test Structure

```
tests/
├── test_client.py       # Client tests
├── test_workflow.py     # Workflow tests
├── test_boards.py       # Board tests
├── test_fields.py       # Field tests
├── fixtures/           # Test fixtures
└── mocks/             # Mock objects
```

## Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

def test_workflow_execution():
    """Test workflow execution."""
    # Arrange
    client = Mock()
    workflow = Mock()
    
    # Act
    result = execute_workflow(client, workflow)
    
    # Assert
    assert result is not None
    client.submit.assert_called_once()
```

## Fixtures

```python
@pytest.fixture
def client():
    """Create test client."""
    return InvokeAIClient(base_url="http://test:9090")

@pytest.fixture
def workflow():
    """Create test workflow."""
    return WorkflowDefinition.from_file("test.json")
```

## Mocking

```python
@patch('requests.Session')
def test_api_call(mock_session):
    """Test API call with mock."""
    mock_session.return_value.get.return_value.json.return_value = {
        "status": "success"
    }
    
    client = InvokeAIClient()
    result = client._make_request("GET", "/test")
    assert result.json()["status"] == "success"
```

## Integration Tests

```python
@pytest.mark.integration
def test_full_workflow():
    """Test complete workflow execution."""
    # Requires running InvokeAI server
    client = InvokeAIClient()
    wf = client.workflow_repo.load_workflow("test.json")
    submission = wf.submit_sync()
    result = wf.wait_for_completion_sync(submission)
    assert result["status"] == "COMPLETED"
```

See [Contributing](contributing.md) for development setup.
