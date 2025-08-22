# Boards API

Board and image management APIs.

## BoardRepository

```python
class BoardRepository:
    """Repository for board management."""
    
    def create_board(self, name: str, description: str = "") -> Board:
        """Create new board."""
    
    def get_board_handle(self, board_id: str) -> BoardHandle:
        """Get board handle for operations."""
    
    def list_boards(self) -> List[Board]:
        """List all boards."""
    
    def delete_board(self, board_id: str) -> bool:
        """Delete board."""
```

## BoardHandle

```python
class BoardHandle:
    """Handle for board operations."""
    
    def upload_image_file(self, filepath: str) -> str:
        """Upload image from file."""
    
    def upload_image_data(self, data: bytes, name: str) -> str:
        """Upload image from bytes."""
    
    def download_image(self, image_name: str, full_resolution=True) -> bytes:
        """Download image data."""
    
    def list_images(self) -> List[str]:
        """List board images."""
    
    def star_image(self, image_name: str) -> bool:
        """Star/favorite image."""
```

## Board Model

```python
class Board(BaseModel):
    """Board data model."""
    
    board_id: str
    board_name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    image_count: int
    starred: bool
    
    @classmethod
    def uncategorized(cls) -> 'Board':
        """Get uncategorized board (board_id='none')."""
    
    def is_uncategorized(self) -> bool:
        """Check if this is uncategorized board."""
```

## Usage Examples

```python
# Create board
board = client.board_repo.create_board(
    name="my_outputs",
    description="Generated images"
)

# Get board handle
handle = client.board_repo.get_board_handle("my_outputs")

# Upload image
image_name = handle.upload_image_file("source.png")

# Download image
image_data = handle.download_image(image_name)

# List images
images = handle.list_images()
print(f"Board contains {len(images)} images")
```

See [User Guide](../user-guide/boards.md) for detailed examples.