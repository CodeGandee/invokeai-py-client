# API Client Architecture Patterns for Python

This document outlines best practices for structuring Python API client libraries, particularly regarding the separation of data models from client logic.

## Problem Statement

When building API client libraries, developers often face the question: Should data models (like Pydantic models) contain references to the client to enable method calls directly on the model instances?

**Answer: No.** Data models should remain pure data containers without client references.

## Why Not Mix Client References with Data Models

1. **Separation of Concerns**: Data models should focus solely on data validation and structure
2. **Serialization Issues**: Client references cannot be serialized/deserialized
3. **Circular Dependencies**: Can create problematic import cycles
4. **Testing Difficulties**: Harder to mock and unit test
5. **Memory Management**: Client references can prevent proper garbage collection

## Recommended Patterns

### 1. Repository Pattern (Recommended)

The Repository Pattern provides a collection-like interface for accessing domain objects while keeping data models pure.

**Structure:**
```python
# models.py - Pure data models
from pydantic import BaseModel

class Board(BaseModel):
    board_id: str
    board_name: str
    image_count: int = 0
    # No client reference here!

# repositories/board_repository.py
from typing import List, Optional
from models import Board

class BoardRepository:
    """Repository for board-specific operations."""
    
    def __init__(self, client):
        self._client = client
    
    def get_by_id(self, board_id: str) -> Optional[Board]:
        return self._client.get_board_by_id(board_id)
    
    def list_images(self, board_id: str) -> List[Image]:
        # Board-specific operation
        return self._client.list_board_images(board_id)
    
    def duplicate(self, board_id: str, new_name: str) -> Board:
        # Complex operation using client
        original = self.get_by_id(board_id)
        # ... implementation
```

**Usage:**
```python
client = InvokeAIClient.from_url("http://localhost:9090")
board_repo = BoardRepository(client)

# Clean separation
board = board_repo.get_by_id("abc-123")  # Returns pure Board model
images = board_repo.list_images(board.board_id)
```

**Benefits:**
- Clear separation between data and operations
- Easy to test (mock the repository)
- Can switch implementations without changing models
- Follows Single Responsibility Principle

### 2. Service Layer Pattern

For complex business logic that spans multiple models, use a service layer.

**Structure:**
```python
# services/board_service.py
class BoardService:
    """High-level board operations."""
    
    def __init__(self, client):
        self._client = client
        
    def merge_boards(self, source_ids: List[str], target_name: str) -> Board:
        """Complex operation involving multiple API calls."""
        boards = [self._client.get_board_by_id(id) for id in source_ids]
        new_board = self._client.create_board(target_name)
        
        for board in boards:
            images = self._client.list_board_images(board.board_id)
            for image in images:
                self._client.add_image_to_board(image.name, new_board.board_id)
        
        return new_board
```

**Benefits:**
- Encapsulates complex business logic
- Orchestrates multiple repository/client calls
- Keeps models and repositories simple

### 3. Resource-Based Pattern (Alternative)

Wrap models with behavior without modifying the models themselves.

**Structure:**
```python
# resources/board_resource.py
class BoardResource:
    """Board with operations - wrapper pattern."""
    
    def __init__(self, board: Board, client):
        self._board = board  # Pure data model
        self._client = client
    
    @property
    def data(self) -> Board:
        """Access underlying data model."""
        return self._board
    
    def delete(self) -> None:
        """Delete this board."""
        self._client.delete_board(self._board.board_id)
    
    def list_images(self) -> List[Image]:
        """List images in this board."""
        return self._client.list_board_images(self._board.board_id)
```

**Usage:**
```python
# Client returns resources
board_resource = client.get_board_resource("abc-123")
board_resource.delete()  # Method on resource
board_data = board_resource.data  # Access pure model
```

## Project Structure Recommendation

```
src/invokeai_py_client/
├── models.py              # Pure Pydantic models
├── client.py              # Core client (basic CRUD)
├── repositories/          # Model-specific operations
│   ├── __init__.py
│   ├── board.py          # BoardRepository
│   ├── image.py          # ImageRepository
│   └── workflow.py       # WorkflowRepository
├── services/             # Complex business logic
│   ├── __init__.py
│   └── board_manager.py  # BoardService
└── resources/            # (Optional) Resource wrappers
    ├── __init__.py
    └── board.py
```

## Implementation Example

Here's how to implement the Repository Pattern for the InvokeAI client:

```python
# client.py - Keep it lightweight
class InvokeAIClient:
    """Core API client with basic operations."""
    
    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"
        # Basic setup...
    
    # Low-level API methods only
    def _make_request(self, method: str, endpoint: str, **kwargs):
        # HTTP request logic
        pass

# repositories/board.py
class BoardRepository:
    """All board-related operations."""
    
    def __init__(self, client: InvokeAIClient):
        self._client = client
    
    def list_all(self, include_uncategorized: bool = False) -> List[Board]:
        """List all boards."""
        response = self._client._make_request('GET', '/boards/')
        boards = [Board(**data) for data in response.json()]
        
        if include_uncategorized:
            # Add special handling for uncategorized
            pass
        
        return boards
    
    def create(self, name: str, is_private: bool = False) -> Board:
        """Create a new board."""
        if len(name) > 300:  # API constraint
            raise ValueError(f"Board name too long: {len(name)} characters (max 300)")
        
        response = self._client._make_request(
            'POST', '/boards/',
            params={'board_name': name, 'is_private': is_private}
        )
        return Board(**response.json())

# main.py - Usage
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.repositories import BoardRepository

client = InvokeAIClient.from_url("http://localhost:9090")
boards = BoardRepository(client)

# Clean, intuitive API
my_boards = boards.list_all()
new_board = boards.create("My Artwork")
```

## Anti-Patterns to Avoid

### ❌ Active Record Pattern with Client Reference
```python
# DON'T DO THIS
class Board(BaseModel):
    board_id: str
    board_name: str
    _client: Optional[Any] = None  # Bad: mixing concerns
    
    def delete(self):
        # Bad: model shouldn't know about client
        self._client.delete_board(self.board_id)
```

### ❌ God Client Class
```python
# DON'T DO THIS
class InvokeAIClient:
    # Hundreds of methods for every model type
    def list_boards(self): ...
    def get_board(self): ...
    def delete_board(self): ...
    def list_board_images(self): ...
    def add_image_to_board(self): ...
    def remove_image_from_board(self): ...
    # ... 200 more methods
```

## Best Practices Summary

1. **Keep models pure**: Use Pydantic/dataclasses for data only
2. **Use repositories**: One repository per model type for CRUD operations
3. **Add service layer**: For complex business logic spanning multiple models
4. **Avoid god objects**: Don't put everything in the client class
5. **Think testability**: Separate concerns make testing easier
6. **Follow SOLID principles**: Single responsibility, open/closed, etc.

## References

- [A Design Pattern for Python API Client Libraries](https://bhomnick.net/design-pattern-python-api-client/)
- [The Factory and Repository Pattern with SQLAlchemy and Pydantic](https://medium.com/@lawsontaylor/the-factory-and-repository-pattern-with-sqlalchemy-and-pydantic-33cea9ae14e0)
- [Comprehensive Analysis of Design Patterns for REST API SDKs](https://vineeth.io/posts/sdk-development)
- [Designing Pythonic library APIs](https://benhoyt.com/writings/python-api-design/)
- [FastAPI Best Practices and Design Patterns](https://medium.com/@lautisuarez081/fastapi-best-practices-and-design-patterns-building-quality-python-apis-31774ff3c28a)

## Related Patterns

- **DAO (Data Access Object)**: Similar to Repository but more database-focused
- **Factory Pattern**: For creating model instances with complex initialization
- **Unit of Work**: For managing transactions across multiple repositories
- **Dependency Injection**: For managing repository dependencies