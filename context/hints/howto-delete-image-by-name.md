# How To Delete an Image By Name via InvokeAI Web API

This guide explains how to add two deletion capabilities to the python client:

1. Repository-level delete: delete an image by name regardless of which board it belongs to.
2. Board-specific delete: delete an image only if it belongs to a given board; otherwise raise an error.

## Relevant Existing Code & APIs

Existing components:
- `BoardRepository` (`src/invokeai_py_client/board/board_repo.py`)
- `BoardHandle` (`src/invokeai_py_client/board/board_handle.py`)
- Current `BoardHandle.delete_image()` already calls: `DELETE /api/v1/images/i/{image_name}` but does NOT verify board membership (returns bool)

API endpoints (from InvokeAI OpenAPI):
- Delete image: `DELETE /api/v1/images/i/{image_name}`
- Get image metadata: `GET /api/v1/images/i/{image_name}/metadata`
- List image names in a board: `GET /api/v1/boards/{board_id}/image_names`
- List uncategorized images (indirect): `GET /api/v1/images/` with params including `categories` and `is_board_id=none`

## Design Summary

| Function | Location | Purpose | Return / Error Semantics |
|----------|----------|---------|--------------------------|
| `delete_image_by_name(image_name: str) -> bool` | `BoardRepository` | Global delete (any board) | `True` if deleted; `False` if 404 (not found) |
| `delete_image(image_name: str) -> bool` (updated) OR new `delete_image_strict(...)` | `BoardHandle` | Board-scoped delete with membership enforcement | Raise `ValueError` if image not on this board; return `True` on success; `False` if race causes 404 at delete time |

You may either (A) change existing `BoardHandle.delete_image` behavior (breaking change—update tests) or (B) introduce a new method (preferred if preserving backward compatibility). If you change semantics, deprecate old behavior with a clear docstring note.

## Membership Verification Strategy

Avoid paginating through all board images (could be large). Instead:
1. Call `GET /api/v1/images/i/{image_name}/metadata`.
2. Inspect returned JSON for the image's `board_id` (or absence meaning uncategorized).
3. Normalize uncategorized: server uses `null` for no board; client sentinel is `"none"`.
4. Compare with `self.board_id`:
   - If mismatch: raise `ValueError(f"Image {image_name} not found on board {self.board_name} ({self.board_id})")`.
   - If match (or both uncategorized): proceed to delete.
5. If metadata endpoint returns 404: if implementing board method, also raise `ValueError` (image does not exist or never belonged here); repository method should just return `False`.

Rationale: metadata fetch is O(1) versus potentially O(N) enumeration. Minimal overhead before destructive operation.

## Edge Cases & Error Handling

- Race: Image removed between metadata fetch and delete -> DELETE returns 404; treat as `False` (repository) or raise only if mismatch at membership stage; simplest: return `False` and optionally log.
- Concurrent count accuracy: Decrement `image_count` defensively with `max(0, count-1)` after successful delete. Do NOT decrement if delete failed.
- Uncategorized images: metadata will show no `board_id`; treat as belonging only to a handle whose `board_id` is `"none"`.
- Network / non-404 HTTP errors: re-raise to caller (consistent with existing patterns).

## Proposed Method Signatures

```python
class BoardRepository:
    def delete_image_by_name(self, image_name: str) -> bool:
        """Delete an image by name from any board (global scope).
        Returns True if deleted, False if not found."""
        ...

class BoardHandle:
    def delete_image_strict(self, image_name: str) -> bool:
        """Delete image only if it belongs to this board.
        Raises ValueError if image not on this board.
        Returns True if deletion succeeded, False if race lost."""
        ...
```

(If replacing existing `delete_image`, rename old implementation to `_delete_image_unchecked` during transition or just modify in place and update tests.)

## Implementation Steps (Repository Method)

1. Build endpoint path: `f"/images/i/{image_name}"`.
2. `try` `_client._make_request("DELETE", path)`.
3. On success: return `True`.
4. On `requests.HTTPError` check `status_code == 404`: return `False`; else re-raise.

Minimal code snippet:
```python
try:
    self._client._make_request("DELETE", f"/images/i/{image_name}")
    return True
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 404:
        return False
    raise
```

## Implementation Steps (Board Handle Strict Method)

1. Fetch metadata:
```python
try:
    resp = self.client._make_request("GET", f"/images/i/{image_name}/metadata")
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 404:
        raise ValueError(f"Image {image_name} not found on board {self.board_name}") from e
    raise
meta = resp.json()
```
2. Extract board id (structure may vary; inspect actual response). Common patterns:
   - `meta.get("board_id")`
   - or nested: `meta.get("image", {}).get("board_id")`
3. Normalize both sides:
```python
img_board_id = extracted or "none"
if img_board_id != self.board_id:
    raise ValueError(
        f"Image {image_name} not found on board {self.board_name} ({self.board_id}); belongs to {img_board_id}"
    )
```
4. Perform DELETE (reuse repository logic or direct):
```python
try:
    self.client._make_request("DELETE", f"/images/i/{image_name}")
    self.board.image_count = max(0, self.board.image_count - 1)
    return True
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 404:
        # Race: treat as False (already deleted elsewhere)
        return False
    raise
```

## Test Plan

Add / adjust tests under `tests/`:

1. `test_delete_image_any_board()`
   - Upload an image to some board.
   - Call `client.board_repo.delete_image_by_name(name)` => True.
   - Call again => False.

2. `test_delete_image_strict_wrong_board()`
   - Upload image to Board A.
   - Attempt `Board B` handle strict delete => expect `ValueError`.

3. Update existing `test_delete_image_by_name.py` if semantics of `BoardHandle.delete_image` change.

4. Race simulation (optional): delete image externally, then call strict delete -> metadata 404 -> ValueError.

## Backward Compatibility Strategy

If changing existing `BoardHandle.delete_image` to strict version:
- Update docstring to state new behavior (raises when not on board).
- Note change in `CHANGELOG`.
- Provide a transitional alias if needed: `delete_image_unchecked()` that retains old bool-only behavior (optional).

If adding new method (`delete_image_strict`):
- Mark old method as deprecated in docstring: "Will be removed in a future version; use delete_image_strict for board membership enforcement.".

## Logging (Optional)

Consider adding debug logs around mismatch cases to aid users.

## Potential Pitfalls

- Assuming metadata JSON shape: verify once (print or inspect) before finalizing extraction.
- Large boards: avoid full enumeration for membership checking.
- Uncached `image_count`: refreshing board after delete is optional; simple decrement is sufficient.
- Image names are globally unique in InvokeAI (UUID-based); safe to call global delete without board context.

## Future Extensions

- Batch deletion by names list at repository level (POST to `/api/v1/images/delete` if supported) for efficiency.
- Soft delete / trash concept (not currently in API list) if backend adds it.

## Source References

- InvokeAI image delete endpoint: `DELETE /api/v1/images/i/{image_name}` (API list)
- Image metadata endpoint for board membership: `GET /api/v1/images/i/{image_name}/metadata`
- Existing code pattern for deletion return semantics: `BoardHandle.delete_image` in `board_handle.py`.

---
**Implementers:** Follow the steps above, then update / add tests and changelog. Do not forget to run the test suite after modifications.
