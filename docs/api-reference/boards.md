# Boards API

Focus
- Accurate, to-the-point reference for managing boards and images with the current client code.
- Matches the implemented signatures and behaviors.

Source locations
- Board repository: [`BoardRepository`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_repo.py#L21){:target="_blank"}
- Board handle: [`BoardHandle`](https://github.com/CodeGandee/invokeai-py-client/blob/main/src/invokeai_py_client/board/board_handle.py#L23){:target="_blank"}

## BoardRepository

Create, list, update, and resolve boards. Returns BoardHandle for per-board operations.

```python
class BoardRepository:
    def list_boards(self, all: bool = True, include_uncategorized: bool = False) -> list[Board]: ...
    def get_board_by_id(self, board_id: str) -> Board | None: ...
    def get_boards_by_name(self, name: str) -> list[Board]: ...
    def create_board(self, name: str, is_private: bool = False) -> BoardHandle: ...
    def delete_board(self, board_id: str, delete_images: bool = False) -> bool: ...
    def get_board_handle(self, board_id: str | None) -> BoardHandle: ...
    def get_board_handle_by_name(self, name: str) -> BoardHandle | None: ...
    def get_uncategorized_board(self) -> Board: ...
    def get_uncategorized_handle(self) -> BoardHandle: ...
    def update_board(self, board_id: str, name: str | None = None, is_private: bool | None = None) -> Board | None: ...
```

Notes
- include_uncategorized=False by default. Use get_uncategorized_board()/get_uncategorized_handle() for the sentinel uncategorized board (board_id="none").
- create_board returns a BoardHandle for the created board. The underlying API expects query params board_name and is_private.
- delete_board(board_id, delete_images=False): If delete_images=False, images are moved to uncategorized; True deletes images. You cannot delete the uncategorized board.

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
- list_images() supports ordering, pagination, and search. The uncategorized variant uses the images endpoint instead of boards/.../image_names.
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