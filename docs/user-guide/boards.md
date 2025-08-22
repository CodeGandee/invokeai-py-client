# Board Management

Learn how to create, manage, and organize images using InvokeAI boards.

## What are Boards?

Boards are containers for organizing images in InvokeAI. Think of them as folders or albums that group related images together.

## Board Basics

### List All Boards

```python
# Get all boards including uncategorized
boards = client.board_repo.list_boards(include_uncategorized=True)

for board in boards:
    print(f"Board: {board.board_name}")
    print(f"  ID: {board.board_id}")
    print(f"  Images: {board.image_count}")
    print(f"  Created: {board.created_at}")
```

### The Uncategorized Board

The special "none" board (ID = `"none"`) holds uncategorized images:

```python
# Access uncategorized board
uncategorized = client.board_repo.get_board_handle("none")
images = uncategorized.list_images()
print(f"Uncategorized images: {len(images)}")
```

!!! important "String 'none' vs Python None"
    The uncategorized board uses the string `"none"` as its ID, not Python's `None` object.

## Creating Boards

### Create a New Board

```python
# Create board
new_board = client.board_repo.create_board(
    name="My Project",
    description="Images for my project"
)

print(f"Created board: {new_board.board_id}")
```

### Board Naming

```python
# Board names should be descriptive
good_names = [
    "SDXL_Landscapes_2024",
    "Character_Concepts_v2",
    "Test_Outputs_Batch_5"
]

# Avoid generic names
bad_names = [
    "Board1",
    "Test",
    "Images"
]
```

## Board Handles

### Get Board Handle

```python
# Get handle for board operations
board = client.board_repo.get_board_handle("board_id_here")

# Board handle provides methods for:
# - Uploading images
# - Downloading images
# - Listing images
# - Managing metadata
```

### Board Handle Cache

Handles are cached for efficiency:

```python
# First call creates handle
board1 = client.board_repo.get_board_handle("my_board")

# Second call returns cached handle
board2 = client.board_repo.get_board_handle("my_board")

assert board1 is board2  # Same object
```

## Board Operations

### List Images in Board

```python
board = client.board_repo.get_board_handle("my_board")

# Get all image names
image_names = board.list_images()
print(f"Board contains {len(image_names)} images")

for name in image_names[:10]:  # First 10
    print(f"  - {name}")
```

### Get Board Details

```python
# Get board metadata
board_info = client.board_repo.get_board("board_id")

print(f"Name: {board_info.board_name}")
print(f"Description: {board_info.description}")
print(f"Image count: {board_info.image_count}")
print(f"Cover image: {board_info.cover_image_name}")
```

### Update Board

```python
# Update board properties
client.board_repo.update_board(
    board_id="my_board",
    name="Updated Name",
    description="New description"
)
```

### Delete Board

```python
# Delete board (images move to uncategorized)
client.board_repo.delete_board("board_id")

# Or delete with images
client.board_repo.delete_board(
    board_id="board_id",
    delete_images=True  # Also delete contained images
)
```

## Board Selection in Workflows

### Setting Output Board

```python
# Find board field in workflow
for inp in wf.list_inputs():
    if inp.field_name == "board":
        board_field = wf.get_input_value(inp.input_index)
        
        # Set to specific board
        board_field.value = "my_output_board"
        
        # Or use uncategorized
        board_field.value = "none"
```

### Dynamic Board Selection

```python
def select_board_by_name(client, name):
    """Find board ID by name."""
    boards = client.board_repo.list_boards()
    
    for board in boards:
        if board.board_name == name:
            return board.board_id
    
    # Not found, create it
    new_board = client.board_repo.create_board(name=name)
    return new_board.board_id

# Use in workflow
board_id = select_board_by_name(client, "Daily Outputs")
wf.get_input_value(BOARD_IDX).value = board_id
```

## Board Organization Strategies

### By Project

```python
# Organize by project
projects = [
    "Project_Alpha_Characters",
    "Project_Alpha_Environments",
    "Project_Beta_Concepts"
]

for project in projects:
    client.board_repo.create_board(name=project)
```

### By Date

```python
from datetime import datetime

# Daily boards
today = datetime.now().strftime("%Y-%m-%d")
board_name = f"Outputs_{today}"

board = client.board_repo.create_board(name=board_name)
```

### By Workflow Type

```python
# Boards for different workflows
workflow_boards = {
    "txt2img": "Text_to_Image_Results",
    "img2img": "Image_to_Image_Results",
    "inpaint": "Inpainting_Results",
    "upscale": "Upscaled_Images"
}

for workflow_type, board_name in workflow_boards.items():
    client.board_repo.create_board(name=board_name)
```

## Board Management Patterns

### Board Manager Class

```python
class BoardManager:
    """Helper for board management."""
    
    def __init__(self, client):
        self.client = client
        self.board_repo = client.board_repo
    
    def ensure_board_exists(self, name, description=""):
        """Create board if it doesn't exist."""
        boards = self.board_repo.list_boards()
        
        for board in boards:
            if board.board_name == name:
                return board.board_id
        
        # Create new
        new_board = self.board_repo.create_board(
            name=name,
            description=description
        )
        return new_board.board_id
    
    def clean_empty_boards(self):
        """Delete boards with no images."""
        boards = self.board_repo.list_boards()
        
        for board in boards:
            if board.image_count == 0:
                print(f"Deleting empty board: {board.board_name}")
                self.board_repo.delete_board(board.board_id)
    
    def archive_board(self, board_id, archive_name=None):
        """Rename board to archive it."""
        if not archive_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"Archive_{timestamp}"
        
        self.board_repo.update_board(
            board_id=board_id,
            name=archive_name
        )

# Use it
manager = BoardManager(client)
board_id = manager.ensure_board_exists("My Workflow Outputs")
```

### Batch Board Operations

```python
def move_images_between_boards(client, from_board_id, to_board_id):
    """Move all images from one board to another."""
    from_board = client.board_repo.get_board_handle(from_board_id)
    images = from_board.list_images()
    
    for image_name in images:
        # Move image (requires API call)
        client.move_image_to_board(image_name, to_board_id)
    
    print(f"Moved {len(images)} images")
```

## Board Statistics

```python
def get_board_statistics(client):
    """Get statistics about all boards."""
    boards = client.board_repo.list_boards(include_uncategorized=True)
    
    total_boards = len(boards)
    total_images = sum(b.image_count for b in boards)
    
    # Find largest board
    largest = max(boards, key=lambda b: b.image_count)
    
    # Find oldest board
    oldest = min(boards, key=lambda b: b.created_at)
    
    print(f"Total boards: {total_boards}")
    print(f"Total images: {total_images}")
    print(f"Largest board: {largest.board_name} ({largest.image_count} images)")
    print(f"Oldest board: {oldest.board_name}")
    
    return {
        'total_boards': total_boards,
        'total_images': total_images,
        'largest_board': largest,
        'oldest_board': oldest
    }
```

## Error Handling

### Board Not Found

```python
try:
    board = client.board_repo.get_board_handle("invalid_id")
except Exception as e:
    print(f"Board not found: {e}")
    # Create it or use uncategorized
    board = client.board_repo.get_board_handle("none")
```

### Name Conflicts

```python
def create_unique_board(client, base_name):
    """Create board with unique name."""
    boards = client.board_repo.list_boards()
    existing_names = {b.board_name for b in boards}
    
    # Find unique name
    name = base_name
    counter = 1
    while name in existing_names:
        name = f"{base_name}_{counter}"
        counter += 1
    
    return client.board_repo.create_board(name=name)
```

## Best Practices

### 1. Use Descriptive Names

```python
# Good: Descriptive and organized
board_name = f"{workflow_type}_{date}_{project}"

# Bad: Generic
board_name = "board1"
```

### 2. Regular Cleanup

```python
# Periodically clean up old boards
def cleanup_old_boards(client, days_old=30):
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(days=days_old)
    boards = client.board_repo.list_boards()
    
    for board in boards:
        if board.created_at < cutoff and board.image_count == 0:
            client.board_repo.delete_board(board.board_id)
```

### 3. Board Templates

```python
# Create standard board structure
def setup_project_boards(client, project_name):
    templates = [
        f"{project_name}_Inputs",
        f"{project_name}_Outputs",
        f"{project_name}_Finals",
        f"{project_name}_Archive"
    ]
    
    board_ids = {}
    for template in templates:
        board = client.board_repo.create_board(name=template)
        board_ids[template] = board.board_id
    
    return board_ids
```

## Next Steps

- Learn about [Image Operations](images.md) for upload/download
- Understand [Output Mapping](output-mapping.md) for result organization
- Explore [Execution Modes](execution-modes.md) for workflow running
- Master [Model Management](models.md) for AI model handling