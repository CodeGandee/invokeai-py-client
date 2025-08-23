# Quick Client

High-level convenience wrapper around the low-level repositories and workflow APIs. Use QuickClient to perform common tasks in a few lines, while the library handles workflow loading, input discovery, model selection, synchronous submission and output mapping.

## Import

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.quick import QuickClient
```

## Initialize

```python
client = InvokeAIClient.from_url("http://127.0.0.1:9090")
qc = QuickClient(client)
```

## Methods

### copy_image_to_board(image_name: str, target_board_id: str) -> IvkImage | None

Duplicate an existing image to another board using a tiny server-side workflow (no client download/re-upload). A new image is created on the target board even if the source image already belongs to it.

Parameters:
- image_name: Name of the existing image stored on the server (e.g., "abc123.png")
- target_board_id: Destination board id (use `client.board_repo.get_board_handle_by_name(...).board_id` or "none" for Uncategorized)

Returns:
- IvkImage (metadata for the newly created image) or None if the workflow completed but produced no image

Raises ValueError if:
- Target board does not exist
- Source image does not exist
- API/workflow errors occur (connectivity, validation, etc.)

Example:
```python
repo = client.board_repo
dest = repo.get_board_handle_by_name("quickcopy-assets") or repo.create_board("quickcopy-assets")
copied = qc.copy_image_to_board("some_image.png", dest.board_id)
print(copied.image_name if copied else "No image produced")
```

Implementation notes:
- Loads prebuilt workflow json: src/invokeai_py_client/quick/prebuilt-workflows/copy-image.json
- Submits synchronously and waits for completion
- Maps outputs to returned image name and resolves IvkImage by name

### generate_image_sdxl_t2i(
  positive_prompt: str,
  negative_prompt: str,
  width: int,
  height: int,
  steps: int | None = None,
  model_name: str | None = None,
  scheduler: str | None = None,
  board_id: str | None = None
) -> IvkImage | None

Create an SDXL text-to-image generation using a prebuilt workflow and return the generated image metadata.

Behavior:
- Rounds width/height to nearest multiples of 8
- If model_name is provided, selects the first SDXL main model whose name contains the substring (case-insensitive); otherwise picks the first available SDXL main model
- If scheduler is provided, normalizes common aliases then sets the field if present
- If steps is provided, overrides default steps
- If board_id is None, uses "none" (Uncategorized). If non-None, validates the board exists.

Returns:
- IvkImage (the first generated image’s metadata), or None if canceled or no output images were produced

Raises ValueError on API/workflow errors (cancellation returns None).

Example:
```python
img = qc.generate_image_sdxl_t2i(
    positive_prompt="A futuristic city skyline with flying cars, cyberpunk neon, detailed architecture",
    negative_prompt="blurry, low quality, distorted, ugly",
    width=1024,
    height=1024,
    steps=30,                   # or None to use workflow default
    model_name="juggernaut",    # substring match (optional)
    scheduler="dpmpp_3m_k",     # optional
    board_id="none",            # or a real board_id
)
if img:
    print("Generated:", img.image_name, "on board:", img.board_id)
```

Implementation notes:
- Loads prebuilt workflow json: src/invokeai_py_client/quick/prebuilt-workflows/sdxl-text-to-image.json
- Synchronizes embedded model identifier with server inventory
- Submits synchronously, waits for completion, maps outputs to image names, and returns resolved IvkImage

## Reference

- Class: QuickClient — see source [src/invokeai_py_client/quick/quick_client.py](../../src/invokeai_py_client/quick/quick_client.py)
- Prebuilt Workflows:
  - copy-image.json — server-side image duplication
  - sdxl-text-to-image.json — SDXL text-to-image generation
- Related:
  - Workflow basics — docs/api-reference/workflow.md
  - Boards — docs/api-reference/boards.md
  - Field types — docs/api-reference/fields.md

## Troubleshooting

- Target board not found:
  - Ensure you pass a valid board_id. Create a board with `client.board_repo.create_board(name)` and use the returned `.board_id`.
- No output images:
  - Check workflow parameters; ensure width/height are reasonable, steps > 0, and the selected model exists on the server.
- Model selection:
  - If `model_name` is provided but no models match, QuickClient falls back to the first SDXL main model if available; otherwise raises ValueError.