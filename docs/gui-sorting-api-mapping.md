# InvokeAI GUI Sorting Options → API Parameters

This document shows how the InvokeAI web GUI sorting controls map to REST API parameters.

## GUI Controls

The InvokeAI web interface provides these sorting options for board images:

1. **Dropdown Menu**: "Newest First" / "Oldest First"
2. **Checkbox**: "Show starred images first"

## API Parameter Mapping

### Endpoint
```
GET /api/v1/images/names
```

### Parameters

| GUI Control | API Parameter | Values | Description |
|-------------|---------------|---------|-------------|
| "Newest First" | `order_dir` | `"DESC"` | Sort by creation date descending (most recent first) |
| "Oldest First" | `order_dir` | `"ASC"` | Sort by creation date ascending (oldest first) |
| "Show starred images first" ✓ | `starred_first` | `true` | Starred images appear first, then by date order |
| "Show starred images first" ✗ | `starred_first` | `false` | All images sorted purely by date (no starred priority) |

### Response Format
```json
{
  "image_names": ["image1.png", "image2.png", ...],
  "starred_count": 2,
  "total_count": 51
}
```

## Examples

### Default GUI Behavior (Newest First + Starred Priority)
```bash
curl "http://localhost:9090/api/v1/images/names?board_id=probe&order_dir=DESC&starred_first=true"
```

### Oldest First with Starred Priority
```bash
curl "http://localhost:9090/api/v1/images/names?board_id=probe&order_dir=ASC&starred_first=true"
```

### Pure Chronological (Newest First, No Starred Priority)
```bash
curl "http://localhost:9090/api/v1/images/names?board_id=probe&order_dir=DESC&starred_first=false"
```

### Pure Chronological (Oldest First, No Starred Priority)
```bash
curl "http://localhost:9090/api/v1/images/names?board_id=probe&order_dir=ASC&starred_first=false"
```

## Python Implementation

```python
import requests

def get_board_images_sorted(board_id, newest_first=True, starred_first=True):
    """
    Get board images with GUI-equivalent sorting.
    
    Args:
        board_id: Board ID (or "none" for uncategorized)
        newest_first: True for "Newest First", False for "Oldest First"
        starred_first: True to show starred images first
    """
    url = "http://localhost:9090/api/v1/images/names"
    params = {
        "board_id": board_id,
        "order_dir": "DESC" if newest_first else "ASC",
        "starred_first": starred_first
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Example: Replicate default GUI behavior
result = get_board_images_sorted("probe", newest_first=True, starred_first=True)
print(f"Found {len(result['image_names'])} images")
print(f"Starred images: {result['starred_count']}")
```

## Observed Behavior

Testing on the "probe" board shows that the sorting parameters work as expected:

- **With `starred_first=true`**: Starred images (`ad7ae269-...`) appear first regardless of date
- **With `starred_first=false`**: Pure chronological order (`d5ecea7e-...` is actually the newest)
- **With `order_dir=ASC/DESC`**: Reverses the chronological order appropriately

## Additional Parameters

The `/api/v1/images/names` endpoint also supports:
- `limit`: Maximum number of images to return
- `offset`: Skip first N images (for pagination)
- `categories`: Filter by image categories
- `is_intermediate`: Include/exclude intermediate images

These provide additional filtering beyond the basic GUI sorting options.
