# How to “Copy Image” and paste to a board’s Assets (GUI flow and API equivalence)

Overview
- GUI capability: Right‑click an image → “Copy Image”, change to a different board, press Ctrl+V to paste the image into that board’s Assets.
- What actually happens in the GUI:
  - Copy Image writes the image into the OS clipboard as an image blob.
  - On paste, the app reads Clipboard files and uploads them to the currently “auto‑add” board’s Assets via the upload endpoint.
  - If the Canvas is focused and a single image is pasted, a modal allows choosing between pasting to Canvas, Bbox, or Assets. Choosing “Assets” uploads to the selected board.

Key GUI references (source)
- Copy → write image to clipboard:
  - Clipboard utilities: [TypeScript.useClipboard()](context/refcode/InvokeAI/invokeai/frontend/web/src/common/hooks/useClipboard.tsx:11) → [TypeScript.writeImage()](context/refcode/InvokeAI/invokeai/frontend/web/src/common/hooks/useClipboard.tsx:67) uses `navigator.clipboard.write(new ClipboardItem({ 'image/png': blob }))`.
  - Copy image hook: [TypeScript.useCopyImageToClipboard()](context/refcode/InvokeAI/invokeai/frontend/web/src/common/hooks/useCopyImageToClipboard.ts:9) converts `image_url` to Blob and calls `writeImage`.
- Paste handler and upload
  - Global paste handler: [FullscreenDropzone.tsx](context/refcode/InvokeAI/invokeai/frontend/web/src/features/dnd/FullscreenDropzone.tsx:122) listens to `window.addEventListener('paste', onPaste)` and extracts `clipboardData.files`.
  - Validation and upload routing: [FullscreenDropzone.tsx](context/refcode/InvokeAI/invokeai/frontend/web/src/features/dnd/FullscreenDropzone.tsx:74) → `validateAndUploadFiles()` prepares [TypeScript.UploadImageArg](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:240) list:
    - `image_category: 'user'` (Assets)
    - `is_intermediate: false`
    - `board_id: selectAutoAddBoardId(...)` (the selected board; `'none'` omitted so it goes uncategorized)
    - Calls [TypeScript.uploadImages()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:561), which dispatches the RTKQ `uploadImage` mutation for each File.
  - Canvas-focused single-image paste: [FullscreenDropzone.tsx](context/refcode/InvokeAI/invokeai/frontend/web/src/features/dnd/FullscreenDropzone.tsx:93) sets [TypeScript.setFileToPaste()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/controlLayers/components/CanvasPasteModal.tsx:26) and opens the paste modal.
- Paste modal (choose Assets/Canvas/Bbox)
  - Paste logic: [TypeScript.CanvasPasteModal](context/refcode/InvokeAI/invokeai/frontend/web/src/features/controlLayers/components/CanvasPasteModal.tsx:29) → [TypeScript.handlePaste()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/controlLayers/components/CanvasPasteModal.tsx:56)
    - For destination `'assets'`: `is_intermediate = false`, `image_category = 'user'`, upload via `useUploadImageMutation` (multipart POST to images/upload with board_id).
    - For Canvas/Bbox: uploads as intermediate, then creates new canvas entities.
  - “Paste to Assets” button: [TypeScript.pasteToAssets()](context/refcode/InvokeAI/invokeai/frontend/web/src/features/controlLayers/components/CanvasPasteModal.tsx:99)

Low-level API endpoints involved
- Upload image: `POST /api/v1/images/upload` (multipart/form-data)
  - Query params:
    - `image_category=user`
    - `is_intermediate=false`
    - `board_id=<target_board_id>` (omit when board is `'none'`)
- Auxiliary for creating a copy from an existing server image in the browser:
  - [TypeScript.copyImage()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:554) downloads the original via `image_url` → Blob → File and re-uploads via `uploadImage`.

Browser-side (GUI-equivalent) flow summary
1) Copy
- Right-click “Copy Image” triggers [TypeScript.useCopyImageToClipboard()](context/refcode/InvokeAI/invokeai/frontend/web/src/common/hooks/useCopyImageToClipboard.ts:9) to:
  - Download `image_url` → Blob
  - [TypeScript.useClipboard.writeImage()](context/refcode/InvokeAI/invokeai/frontend/web/src/common/hooks/useClipboard.tsx:67) writes Blob to OS clipboard

2) Paste
- Paste handler [FullscreenDropzone.tsx](context/refcode/InvokeAI/invokeai/frontend/web/src/features/dnd/FullscreenDropzone.tsx:122) extracts Files from clipboard and:
  - If Canvas-focused and single file, open [TypeScript.CanvasPasteModal](context/refcode/InvokeAI/invokeai/frontend/web/src/features/controlLayers/components/CanvasPasteModal.tsx:29) and on “Paste to Assets” call [TypeScript.handlePaste('assets')](context/refcode/InvokeAI/invokeai/frontend/web/src/features/controlLayers/components/CanvasPasteModal.tsx:56) to upload to the active board’s Assets.
  - Else, directly call [TypeScript.uploadImages()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:561) which dispatches `uploadImage` for each file with `board_id = selectAutoAddBoardId`.

Python client equivalence (copy an existing server image into another board’s Assets)
- If you want to replicate “Copy → Paste to Assets” outside the browser using the Python client:
  - Download the source image bytes from the server.
  - Upload those bytes to the target board with category USER and not intermediate.

Example (Python)
```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.board.board_handle import BoardHandle
from invokeai_py_client.models import ImageCategory

client = InvokeAIClient.from_url("http://127.0.0.1:9090")
repo = client.board_repo

SOURCE_IMAGE_NAME = "abc-123.png"   # existing image to copy
TARGET_BOARD_NAME = "my-destination-board"

# Resolve/create target board
target = repo.get_board_handle_by_name(TARGET_BOARD_NAME) or repo.create_board(TARGET_BOARD_NAME)

# Download the source image bytes (full-res)
# Using low-level request to avoid needing the original board handle:
resp = client._make_request("GET", f"/images/i/{SOURCE_IMAGE_NAME}/full")
image_bytes: bytes = resp.content

# Upload the bytes to the target board's Assets (USER), non-intermediate
uploaded = target.upload_image_data(
    image_data=image_bytes,
    filename=f"copy_of_{SOURCE_IMAGE_NAME}",
    is_intermediate=False,
    image_category=ImageCategory.USER,
)
print("Copied to board:", target.board_name, "as", uploaded.image_name)
```

Alternative (browser plugin or custom JS in GUI context)
- Convert an existing ImageDTO to a File and re-upload with board_id:
  - [TypeScript.imageDTOToFile()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:576)
  - [TypeScript.uploadImage()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:548)
- Or use [TypeScript.copyImage()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:554) which wraps both steps.

Notes and pitfalls
- Board selection for paste target:
  - The GUI uses `selectAutoAddBoardId` as the destination board id for uploads. When automating, ensure you supply the intended `board_id` to land the image in the correct board.
- Uncategorized sentinel:
  - When uploading, omit `board_id` to land in Uncategorized (“none” is a sentinel that the GUI converts to undefined in requests).
- Image category:
  - Use `image_category=user` / [python.ImageCategory.USER](src/invokeai_py_client/board/board_handle.py:182) so images appear in the board’s “Assets” section.
- “Move” vs “Copy”:
  - Copy is implemented as a new upload (re-import) of image bytes. Moving uses the `board_images` endpoints to re-associate the existing image without re-uploading. See:
    - [TypeScript.addImagesToBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:367)
    - [TypeScript.removeImagesFromBoard()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:386)
    - Python equivalent move: [python.BoardHandle.move_image_to()](src/invokeai_py_client/board/board_handle.py:402)

Cross-checks to backend
- Upload endpoint: `POST /api/v1/images/upload` with multipart file and query params `image_category`, `is_intermediate`, `board_id` as used by GUI’s `uploadImage` mutation [TypeScript.uploadImage()](context/refcode/InvokeAI/invokeai/frontend/web/src/services/api/endpoints/images.ts:240).
- For copying-by-reupload: GUI: download via image_url → upload to target board; Python: GET `/images/i/{name}/full` → `BoardHandle.upload_image_data()`.

Related client APIs
- Construct client: [python.InvokeAIClient.from_url()](src/invokeai_py_client/client.py:143)
- Target board handle: [python.BoardRepository.get_board_handle_by_name()](src/invokeai_py_client/board/board_repo.py:317) or [python.BoardRepository.create_board()](src/invokeai_py_client/board/board_repo.py:176)
- Upload bytes to Assets: [python.BoardHandle.upload_image_data()](src/invokeai_py_client/board/board_handle.py:270)

Summary
- Copy in GUI: copies image blob to OS clipboard.
- Paste in GUI: uploads clipboard files to the selected board’s Assets using the images/upload endpoint.
- Equivalent programmatic operation: download the source image bytes and re-upload them to the chosen board with category USER and non‑intermediate.