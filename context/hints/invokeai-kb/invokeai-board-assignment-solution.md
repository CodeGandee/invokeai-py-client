# InvokeAI Board Assignment Solution

## Problem
When assigning images to boards during generation in InvokeAI v6.3.0, the images come out as black 16KB files.

## Root Cause
The board assignment in the l2i node during generation causes the image generation to fail silently, producing black placeholder images.

## Solution
Generate images WITHOUT board assignment first, then assign them to boards using the board API afterward.

## Working Approach

```python
# 1. Generate image without board
graph = {
    "nodes": {
        "l2i": {
            "id": "l2i",
            "type": "l2i",
            "fp32": False
            # NO board field here
        }
    }
}

# 2. After generation, assign to board
response = session.post(
    f"{base_url}/api/v1/board_images/",
    json={
        "board_id": board_id,
        "image_name": image_name
    }
)
```

## Important Notes
1. The `/api/v1/images/` endpoint returns images sorted by creation date, which may include old images
2. To get newly generated images, track the batch/session results or compare image lists before/after generation
3. Different SDXL models all work fine without board assignment (tested: cyberrealisticXL, xxmix9realistic, NightVision XL)
4. The issue appears to be specific to the board assignment during the generation process

## API Endpoints for Board Management
- Create board: `POST /api/v1/boards/`
- List boards: `GET /api/v1/boards/`
- Get board images: `GET /api/v1/boards/{board_id}/image_names`
- Assign image to board: `POST /api/v1/board_images/`
- Remove from board: `DELETE /api/v1/board_images/`

## Verified Working Models
All SDXL models work correctly when board assignment is done post-generation:
- cyberrealisticXL_v5
- xxmix9realisticsdxl_v10
- NightVision XL
- JuggernautXL_version5 (and others)