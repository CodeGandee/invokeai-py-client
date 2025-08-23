# How to move an image to a board (InvokeAI Web APIs via Python Client)

Summary
- Goal: Create board "mytest" if needed and move a specific server image (e.g. 311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png) to it.
- Primary transport (matches GUI behavior): board_images router.
- Client APIs to use:
  - [python.InvokeAIClient.from_url()](src/invokeai_py_client/client.py:143)
  - [python.BoardRepository.create_board()](src/invokeai_py_client/board/board_repo.py:176)
  - [python.BoardRepository.get_board_handle_by_name()](src/invokeai_py_client/board/board_repo.py:317)
  - [python.BoardRepository.get_image_by_name()](src/invokeai_py_client/board/board_repo.py:402)
  - [python.BoardRepository.move_image_to_board_by_name()](src/invokeai_py_client/board/board_repo.py:446)
  - [python.BoardHandle.move_image_to()](src/invokeai_py_client/board/board_handle.py:402) (uses board_images; legacy PATCH fallback)
  - [python.BoardHandle.list_images()](src/invokeai_py_client/board/board_handle.py:106) for verification

Backend API mapping (preferred and legacy)
- Create Board: POST /api/v1/boards/ [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md#L118)
- Get Board: GET /api/v1/boards/{board_id} [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md#L121)
- List Board Image Names: GET /api/v1/boards/{board_id}/image_names [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md#L123)
- Add Image To Board (single): POST /api/v1/board_images/ [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md#L126)
- Add Images To Board (batch): POST /api/v1/board_images/batch [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md#L130)
- Remove Images From Board (to uncategorized): POST /api/v1/board_images/batch/delete [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md#L133)
- Legacy fallback only: PATCH /api/v1/images/i/{image_name} with board_id

GUI implementation references (for parity)
- API layer
  - buildBoardImagesUrl helper [TypeScript.buildBoardImagesUrl()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:41)
  - addImageToBoard mutation [TypeScript.addImageToBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:324)
  - removeImageFromBoard mutation [TypeScript.removeImageFromBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:346)
  - addImagesToBoard mutation [TypeScript.addImagesToBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:368)
  - removeImagesFromBoard mutation [TypeScript.removeImagesFromBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:386)
- Drag & Drop wiring
  - dnd target invoking addImagesToBoard [TypeScript.addImagesToBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/dnd/dnd.ts:468)
  - batch drag to board [TypeScript.addImagesToBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/dnd/dnd.ts:474)
- Actions and UI
  - imageActions addImagesToBoard dispatcher [TypeScript.addImagesToBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/imageActions/actions.ts:310)
  - ChangeBoardModal uses add/remove images to board [TypeScript.useAddImagesToBoardMutation()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/changeBoardModal/components/ChangeBoardModal.tsx:61)
  - Boards list drop target [TypeScript.GalleryBoard](context/refcode/InvokeAI/invokeai/frontend/web/src/features/gallery/components/Boards/BoardsList/GalleryBoard.tsx:84)

Prerequisites
- A running InvokeAI instance (default assumed: http://127.0.0.1:9090).
- The target image already exists on the server (name like 311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png, or stem without extension).

Step-by-step
1) Connect to InvokeAI
- Use [python.InvokeAIClient.from_url()](src/invokeai_py_client/client.py:143) to construct the client with the server base URL.

2) Ensure target board exists
- Try [python.BoardRepository.get_board_handle_by_name()](src/invokeai_py_client/board/board_repo.py:317); if None, call [python.BoardRepository.create_board()](src/invokeai_py_client/board/board_repo.py:176).

3) Resolve image metadata by name
- Preferred: [python.BoardRepository.get_image_by_name()](src/invokeai_py_client/board/board_repo.py:402) (GET /images/i/{image_name}).
- Fallback: If you only have a stem or the extension differs, try the stem; else consult uncategorized image names (/boards/none/image_names) and match exact or prefix.

4) Move the image (board_images)
- Easiest: [python.BoardRepository.move_image_to_board_by_name()](src/invokeai_py_client/board/board_repo.py:446), which:
  - Resolves/creates target board handle,
  - Finds the image’s current board (or uncategorized),
  - Calls [python.BoardHandle.move_image_to()](src/invokeai_py_client/board/board_handle.py:402) on the source handle, using board_images endpoints (POST /board_images/ or /board_images/batch; delete batch for uncategorized).
- Direct alternative: If you already know both source handle and target board_id, call [python.BoardHandle.move_image_to()](src/invokeai_py_client/board/board_handle.py:402) yourself.

5) Verify
- Refresh the target board handle and list images via [python.BoardHandle.list_images()](src/invokeai_py_client/board/board_handle.py:106). Confirm the moved image appears.
- Optionally re-fetch image metadata and verify image.board_id equals the target board_id.

Minimal example (concise)
```python
from invokeai_py_client import InvokeAIClient

client = InvokeAIClient.from_url("http://127.0.0.1:9090")

repo = client.board_repo
target_name = "mytest"
image_name = "311a6fb0-c8cc-467d-812c-1d66c1c32c1c.png"

# 1) ensure board
handle = repo.get_board_handle_by_name(target_name) or repo.create_board(target_name)

# 2) resolve image (try exact name first)
img = repo.get_image_by_name(image_name)
if img is None and "." in image_name:
    stem = image_name.rsplit(".", 1)[0]
    img = repo.get_image_by_name(stem)
assert img, f"Image not found on server: {image_name}"
resolved = img.image_name

# 3) move (uses board_images under the hood)
ok = repo.move_image_to_board_by_name(resolved, target_name)
assert ok, f"Failed to move image {resolved} to board {target_name}"

# 4) verify via listing
names = repo.get_board_handle(handle.board_id).list_images()
assert resolved in names, "Move verified by board listing failed"
```

Notes and pitfalls
- Uncategorized sentinel: The server uses a special pseudo-board "none". The client normalizes uncategorized handles to board_id "none". When uploading to uncategorized, board_id should be omitted (see [python.BoardHandle.upload_image()](src/invokeai_py_client/board/board_handle.py:180)).
- Preferred transports: board_images endpoints (single/batch add, batch delete). Legacy PATCH to /images/i/{image_name} is kept as a compatibility fallback in [python.BoardHandle.move_image_to()](src/invokeai_py_client/board/board_handle.py:402).
- Image name resolution: If GUI presents a user-friendly label or if extension was changed (PNG/JPG), try matching the stem, or search uncategorized image names to find the canonical server-side image_name.

Troubleshooting
- 404 on GET /images/i/{image_name}: The name may lack extension or differs on server. Try the stem; optionally query /boards/none/image_names and search for a match.
- Move succeeded but not visible: Board listings may lag briefly. Re-fetch the handle and retry list_images() a few times with small delays.
- Unauthorized: Ensure Authorization header is configured when using API keys (the client will set Bearer based on api_key passed to [python.InvokeAIClient.__init__()](src/invokeai_py_client/client.py:77)).

References
- Client repository API surface: [src/invokeai_py_client/board/board_repo.py](src/invokeai_py_client/board/board_repo.py)
- Board handle ops: [src/invokeai_py_client/board/board_handle.py](src/invokeai_py_client/board/board_handle.py)
- InvokeAI API list (all endpoints): [context/hints/invokeai-kb/invokeai-api-list.md](context/hints/invokeai-kb/invokeai-api-list.md)