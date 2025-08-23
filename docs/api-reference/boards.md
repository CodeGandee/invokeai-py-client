# Boards API

Complete reference for board and image management using the Repository pattern, covering board lifecycle operations, image upload/download, and organizational features. Key implementations include [`BoardRepository`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L21){:target="_blank"} for board management and [`BoardHandle`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L23){:target="_blank"} for per-board operations.

## BoardRepository

Repository for managing boards and their lifecycle. Implements the Repository pattern to separate board operations from the main client interface.

### Core Board Management Methods

#### `list_boards()` - Retrieve All Boards

```python
def list_boards(self, all: bool = True, include_uncategorized: bool = False) -> list[Board]:
```

List all available boards with optional filtering.

**Parameters:**
- `all` (bool): Include all boards regardless of visibility (default: True)
- `include_uncategorized` (bool): Whether to include the special uncategorized board (default: False)

**Returns:**
- `list[Board]`: List of Board objects with metadata and image counts

**Example:**
```python
# Get all boards excluding uncategorized
boards = client.board_repo.list_boards()

# Include uncategorized board
all_boards = client.board_repo.list_boards(include_uncategorized=True)

# Find boards with images
active_boards = [b for b in boards if b.image_count > 0]
```

#### `create_board()` - Create New Board

```python  
def create_board(self, name: str, is_private: bool = False) -> BoardHandle:
```

Create a new board and return its handle for immediate operations.

**Parameters:**
- `name` (str): Display name for the board
- `is_private` (bool): Whether the board should be private (default: False)

**Returns:**
- `BoardHandle`: Handle for performing operations on the created board

**Example:**
```python
# Create public board
renders_board = client.board_repo.create_board("Project Renders")
print(f"Created board: {renders_board.board_name}")

# Create private board
private_board = client.board_repo.create_board("Personal", is_private=True)

# Immediately upload to new board
image = private_board.upload_image("secret.png")
```

#### `delete_board()` - Remove Board

```python
def delete_board(self, board_id: str, delete_images: bool = False) -> bool:
```

Delete a board with optional image handling.

**Parameters:**
- `board_id` (str): ID of the board to delete
- `delete_images` (bool): If False, moves images to uncategorized; if True, deletes images (default: False)

**Returns:**
- `bool`: True if deletion succeeded, False otherwise

**Important Notes:**
- Cannot delete the uncategorized board (board_id="none")
- By default, images are preserved by moving to uncategorized
- Use `delete_images=True` to permanently remove images

**Example:**
```python
# Safe delete - preserve images
success = client.board_repo.delete_board("old-project")

# Delete board and all its images (permanent)
client.board_repo.delete_board("temp-board", delete_images=True)
```

### Board Lookup and Resolution Methods

#### `get_board_by_id()` - Direct ID Lookup

```python
def get_board_by_id(self, board_id: str) -> Board | None:
```

Retrieve a specific board by its ID.

**Parameters:**
- `board_id` (str): Unique board identifier

**Returns:**
- `Board | None`: Board object if found, None if not found

#### `get_boards_by_name()` - Name-Based Search

```python
def get_boards_by_name(self, name: str) -> list[Board]:
```

Find boards matching a specific name (may return multiple results).

**Parameters:**
- `name` (str): Board name to search for

**Returns:**
- `list[Board]`: List of matching boards (can be empty)

### Handle Creation Methods

#### `get_board_handle()` - Primary Handle Factory

```python
def get_board_handle(self, board_id: str | None) -> BoardHandle:
```

Create a handle for performing operations on a specific board.

**Parameters:**
- `board_id` (str | None): Board ID, use "none" or None for uncategorized

**Returns:**
- `BoardHandle`: Handle for board operations

**Example:**
```python
# Get handle for specific board
handle = client.board_repo.get_board_handle("my-board-123")

# Get uncategorized handle
uncategorized = client.board_repo.get_board_handle(None)
# or
uncategorized = client.board_repo.get_board_handle("none")
```

#### `get_board_handle_by_name()` - Name-Based Handle

```python  
def get_board_handle_by_name(self, name: str) -> BoardHandle | None:
```

Get handle for first board matching the given name.

**Parameters:**
- `name` (str): Board name to search for

**Returns:**
- `BoardHandle | None`: Handle if board found, None otherwise

### Uncategorized Board Helpers

#### `get_uncategorized_board()` & `get_uncategorized_handle()`

```python
def get_uncategorized_board(self) -> Board:
def get_uncategorized_handle(self) -> BoardHandle:
```

Convenience methods for accessing the special uncategorized board.

**Example:**
```python
# Direct uncategorized access
uncat_board = client.board_repo.get_uncategorized_board()
uncat_handle = client.board_repo.get_uncategorized_handle()

# Upload to Assets tab (uncategorized)
image = uncat_handle.upload_image("reference.jpg")
```

#### `update_board()` - Modify Board Properties

```python
def update_board(
    self, 
    board_id: str, 
    name: str | None = None, 
    is_private: bool | None = None
) -> Board | None:
```

Update board name and/or privacy settings.

**Parameters:**
- `board_id` (str): ID of board to update  
- `name` (str | None): New name for the board (optional)
- `is_private` (bool | None): New privacy setting (optional)

**Returns:**
- `Board | None`: Updated board object if successful, None otherwise

Implementation details
- `list_boards`: [`BoardRepository.list_boards()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L59){:target="_blank"}
- `create_board`: [`BoardRepository.create_board()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L175){:target="_blank"}
- `delete_board`: [`BoardRepository.delete_board()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L219){:target="_blank"}
- `get_board_handle`: [`BoardRepository.get_board_handle()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L267){:target="_blank"}
- `update_board`: [`BoardRepository.update_board()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L401){:target="_blank"}

Usage
```python
# List boards (optionally include uncategorized)
boards = client.board_repo.list_boards(include_uncategorized=True)
for b in boards:
    print(b.board_id, b.board_name, b.image_count)

# Create a board and get its handle
handle = client.board_repo.create_board("my_outputs")
print("Board:", handle.board_id, handle.board_name)

# Look up by name → first match, then get handle
h = client.board_repo.get_board_handle_by_name("my_outputs")
if h:
    print("Found board", h.board_name)
```

## BoardHandle

Perform image operations in the context of one board (including uncategorized).

```python
class BoardHandle:
    @property
    def board_id(self) -> str: ...  # "none" for uncategorized
    @property
    def board_name(self) -> str: ...
    @property
    def is_uncategorized(self) -> bool: ...
    def refresh(self) -> None: ...

    def list_images(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_dir: str = "DESC",
        starred_first: bool = False,
        search_term: str | None = None,
    ) -> list[str]: ...

    def upload_image(
        self,
        file_path: str | Path,
        is_intermediate: bool = False,
        image_category: ImageCategory = ImageCategory.USER,
        session_id: str | None = None,
    ) -> IvkImage: ...

    def upload_image_data(
        self,
        image_data: bytes,
        filename: str | None = None,
        is_intermediate: bool = False,
        image_category: ImageCategory = ImageCategory.USER,
        session_id: str | None = None,
    ) -> IvkImage: ...

    def download_image(self, image_name: str, full_resolution: bool = True) -> bytes: ...
    def move_image_to(self, image_name: str, target_board_id: str) -> bool: ...
    def remove_image(self, image_name: str) -> bool: ...
    def delete_image(self, image_name: str) -> bool: ...
    def star_image(self, image_name: str) -> bool: ...
    def unstar_image(self, image_name: str) -> bool: ...
    def get_image_count(self) -> int: ...
```

Important behaviors
- Uncategorized uploads: When uploading to uncategorized, the handle omits board_id so images land under the GUI’s Uncategorized. Passing "none" as board_id is intentionally avoided for uploads.
- list_images() supports ordering, pagination, and search. For uncategorized, the handle now uses the fast name list endpoint: `/api/v1/boards/none/image_names`.
- download_image() checks membership first via list_images(); it raises if the image is not in this board.
- star_image() / unstar_image() toggle the starred flag.
- remove_image() moves an image off the current board to uncategorized. move_image_to() allows moving across boards.
- Returns: upload_image(_data) returns IvkImage; download_image returns bytes.

Implementation details
- `upload_image`: [`BoardHandle.upload_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L182){:target="_blank"}
- `upload_image_data`: [`BoardHandle.upload_image_data()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L272){:target="_blank"}
- `list_images`: [`BoardHandle.list_images()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L106){:target="_blank"}
- `download_image`: [`BoardHandle.download_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L357){:target="_blank"}
- Image operations: [`BoardHandle.move_image_to()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L404){:target="_blank"}, [`BoardHandle.remove_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L436){:target="_blank"}, [`BoardHandle.delete_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L460){:target="_blank"}, [`BoardHandle.star_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L490){:target="_blank"}, [`BoardHandle.unstar_image()`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L510){:target="_blank"}

Examples
```python
# Upload from file (to a named board)
handle = client.board_repo.create_board("assets")
img = handle.upload_image("data/images/sample.png")
print("Uploaded:", img.image_name)

# Upload from bytes to uncategorized (Assets tab)
uncat = client.board_repo.get_uncategorized_handle()
with open("data/images/sample.png", "rb") as f:
    img2 = uncat.upload_image_data(f.read(), "sample.png")
print("Uploaded to Uncategorized:", img2.image_name)

# List, star, and download
names = handle.list_images(limit=20, starred_first=True)
if names:
    handle.star_image(names[0])
    data = handle.download_image(names[0], full_resolution=True)
    with open(names[0], "wb") as out:
        out.write(data)
```

### Image Deletion

Single-image delete (via BoardHandle)
```python
# Preconditions:
# - image_name is the server-side token (exact value returned by listings/DTO)
# - For uncategorized images, you can list names via: GET /api/v1/boards/none/image_names

uncat = client.board_repo.get_uncategorized_handle()
image_name = "0712249f-1047-4314-a338-d6807920f245.png"  # example

# Delete and confirm via server contract
deleted = uncat.delete_image(image_name)  # returns True only if server reports deletion
print("Deleted?", deleted)
```
- Implementation: [`BoardHandle.delete_image()`](src/invokeai_py_client/board/board_handle.py:460)
- Behavior: issues `DELETE /api/v1/images/i/{image_name}` and parses the response JSON (`deleted_images` list). Returns `True` only if the specified `image_name` appears in `deleted_images`; otherwise `False`. A 404 results in `False`.

Resolving exact image_name
```python
# If unsure about exact token (with/without extension), resolve robustly:
def resolve_exact_image_name(client, rough):
    # Try DTO as-is
    try:
        if client._make_request("GET", f"/images/i/{rough}").status_code == 200:
            return rough
    except Exception:
        pass
    # Try stem
    stem = rough.rsplit(".", 1)[0] if "." in rough else rough
    try:
        if client._make_request("GET", f"/images/i/{stem}").status_code == 200:
            return stem
    except Exception:
        pass
    # Fallback to uncategorized list (board_id="none")
    try:
        names = client._make_request("GET", "/boards/none/image_names").json()
        if isinstance(names, list):
            if rough in names: return rough
            if stem in names: return stem
            for n in names:
                if n.startswith(stem):  # prefix fallback
                    return n
    except Exception:
        pass
    return None
```

Bulk deletion (raw API)
```python
# Delete all uncategorized images:
resp = client._make_request("DELETE", "/images/uncategorized")
print(resp.json())  # -> {'deleted_images': [...], 'affected_boards': [...]}

# Delete a list of images:
payload = {"image_names": ["a.png", "b.png", "c.png"]}
resp = client._make_request("POST", "/images/delete", json=payload)
print(resp.json())  # -> {'deleted_images': [...], 'affected_boards': [...]}
```
Upstream endpoints (reference):
- Single delete: `DELETE /api/v1/images/i/{image_name}` (see [images router delete_image](context/refcode/InvokeAI/invokeai/app/api/routers/images.py:163))
- Bulk delete list: `POST /api/v1/images/delete` (see [delete_images_from_list](context/refcode/InvokeAI/invokeai/app/api/routers/images.py:398))
- Delete all uncategorized: `DELETE /api/v1/images/uncategorized` (see [delete_uncategorized_images](context/refcode/InvokeAI/invokeai/app/api/routers/images.py:422))

Error-handling pattern (optional)
```python
# Raise on not found; raise on unknown failure; True on success; False otherwise.
def delete_image_strict(client, image_name: str) -> bool:
    # Confirm existence
    try:
        exists = client._make_request("GET", f"/images/i/{image_name}").status_code == 200
    except Exception as e:
        raise RuntimeError(f"connection error verifying existence: {e}")
    if not exists:
        raise FileNotFoundError(f"image does not exist: {image_name}")

    # Attempt deletion
    try:
        deleted = client.board_repo.get_uncategorized_handle().delete_image(image_name)
    except Exception as e:
        raise RuntimeError(f"delete failed: {e}")

    if deleted:
        return True

    # Unknown failure if server didn’t report deletion and image still exists
    try:
        still_exists = client._make_request("GET", f"/images/i/{image_name}").status_code == 200
    except Exception as e:
        raise RuntimeError(f"connection error verifying deletion: {e}")

    if still_exists:
        raise RuntimeError("unknown error")

    return False
```

Model
```python
class Board(BaseModel):
    board_id: str | None
    board_name: str
    description: str | None
    created_at: datetime | None
    updated_at: datetime | None
    image_count: int
    starred: bool | None

    @classmethod
    def uncategorized(cls, image_count: int = 0) -> "Board": ...
    def is_uncategorized(self) -> bool: ...
```

Cross-references
- User guide: [docs/user-guide/boards.md](../user-guide/boards.md)
- Examples: [`flux-image-to-image.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/pipelines/flux-image-to-image.py){:target="_blank"}
- Raw API demos: [`api-demo-boards.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/raw-apis/api-demo-boards.py){:target="_blank"}, [`api-demo-upload-image.py`](https://github.com/CodeGandee/invokeai-py-client/blob/main/examples/raw-apis/api-demo-upload-image.py){:target="_blank"}