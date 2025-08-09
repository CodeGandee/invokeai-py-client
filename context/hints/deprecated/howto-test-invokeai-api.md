# How to Test InvokeAI API

This guide demonstrates how to test InvokeAI API operations including image upload, text-to-image generation, image-to-image transformation, and downloading results.

## Prerequisites

- InvokeAI server running at `http://127.0.0.1:9090`
- Python with required packages:
  ```bash
  pixi add --pypi requests opencv-python pillow
  ```

## Key Learnings and Important Notes

### 1. Model Loader Types
- **CRITICAL**: Use `sdxl_model_loader` for SDXL models, NOT `main_model_loader`
- SDXL models have both `clip` and `clip2` outputs
- SD1.5/SD2 models use `main_model_loader` with only `clip` output

### 2. Graph Structure
InvokeAI uses a node-based graph system:
- **Nodes**: Operations (model loading, prompting, denoising, etc.)
- **Edges**: Connections between node outputs and inputs
- Each edge must connect valid output fields to input fields

### 3. API Endpoints

#### Check API Status
```python
GET /api/v1/app/version
```

#### Upload Image
```python
POST /api/v1/images/upload
Content-Type: multipart/form-data
Parameters:
  - file: image file
  - image_category: "general"
  - is_intermediate: false
```

#### Get Models
```python
GET /api/v2/models/
```

#### Enqueue Workflow
```python
POST /api/v1/queue/{queue_id}/enqueue_batch
Content-Type: application/json
Body: { "batch": { "batch_id": "...", "graph": {...}, "runs": 1 } }
```

#### Check Queue Status
```python
GET /api/v1/queue/{queue_id}/status
```

#### Download Image
```python
GET /api/v1/images/i/{image_name}/full
```

## Complete Working Example

```python
import requests
import json
import cv2
import numpy as np
import time
from pathlib import Path

def test_invokeai_api():
    base_url = "http://127.0.0.1:9090"
    session = requests.Session()
    
    # 1. Generate test image with OpenCV
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    for i in range(512):
        img[i, :] = [i//2, 100 + i//4, 255 - i//2]
    cv2.circle(img, (256, 256), 80, (255, 200, 0), -1)
    cv2.imwrite("./tmp/test.png", img)
    
    # 2. Upload image
    with open("./tmp/test.png", 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        params = {'image_category': 'general', 'is_intermediate': False}
        response = session.post(f"{base_url}/api/v1/images/upload", 
                               files=files, params=params)
    uploaded_name = response.json()['image_name']
    
    # 3. Get SDXL model
    models = session.get(f"{base_url}/api/v2/models/").json()
    sdxl_model = next(m for m in models['models'] 
                     if m['type'] == 'main' and m['base'] == 'sdxl')
    
    # 4. Create text-to-image graph (SDXL)
    txt2img_graph = {
        "id": "txt2img",
        "nodes": {
            "model": {
                "id": "model",
                "type": "sdxl_model_loader",  # CRITICAL: Use sdxl_model_loader!
                "inputs": {"model": {"key": sdxl_model['key']}}
            },
            "pos_prompt": {
                "id": "pos_prompt",
                "type": "sdxl_compel_prompt",
                "inputs": {
                    "prompt": "beautiful landscape",
                    "style": "photographic"
                }
            },
            "neg_prompt": {
                "id": "neg_prompt",
                "type": "sdxl_compel_prompt",
                "inputs": {"prompt": "ugly, blurry", "style": ""}
            },
            "noise": {
                "id": "noise",
                "type": "noise",
                "inputs": {"width": 1024, "height": 1024, "seed": 42}
            },
            "denoise": {
                "id": "denoise",
                "type": "denoise_latents",
                "inputs": {
                    "steps": 15,
                    "cfg_scale": 7.0,
                    "scheduler": "euler",
                    "denoising_start": 0,
                    "denoising_end": 1
                }
            },
            "l2i": {
                "id": "l2i",
                "type": "l2i",
                "inputs": {"fp32": False}
            }
        },
        "edges": [
            # Connect CLIP and CLIP2 for SDXL
            {"source": {"node_id": "model", "field": "clip"},
             "destination": {"node_id": "pos_prompt", "field": "clip"}},
            {"source": {"node_id": "model", "field": "clip2"},
             "destination": {"node_id": "pos_prompt", "field": "clip2"}},
            {"source": {"node_id": "model", "field": "clip"},
             "destination": {"node_id": "neg_prompt", "field": "clip"}},
            {"source": {"node_id": "model", "field": "clip2"},
             "destination": {"node_id": "neg_prompt", "field": "clip2"}},
            # Other connections
            {"source": {"node_id": "model", "field": "unet"},
             "destination": {"node_id": "denoise", "field": "unet"}},
            {"source": {"node_id": "model", "field": "vae"},
             "destination": {"node_id": "l2i", "field": "vae"}},
            {"source": {"node_id": "pos_prompt", "field": "conditioning"},
             "destination": {"node_id": "denoise", "field": "positive_conditioning"}},
            {"source": {"node_id": "neg_prompt", "field": "conditioning"},
             "destination": {"node_id": "denoise", "field": "negative_conditioning"}},
            {"source": {"node_id": "noise", "field": "noise"},
             "destination": {"node_id": "denoise", "field": "noise"}},
            {"source": {"node_id": "denoise", "field": "latents"},
             "destination": {"node_id": "l2i", "field": "latents"}}
        ]
    }
    
    # 5. Enqueue batch
    batch = {
        "batch": {
            "batch_id": f"batch_{int(time.time())}",
            "graph": txt2img_graph,
            "runs": 1
        }
    }
    response = session.post(f"{base_url}/api/v1/queue/default/enqueue_batch", 
                           json=batch)
    
    # 6. Wait for completion
    time.sleep(30)  # Or poll queue status
    
    # 7. Download results
    images = session.get(f"{base_url}/api/v1/images/?limit=1").json()
    image_name = images['items'][0]['image_name']
    img_data = session.get(f"{base_url}/api/v1/images/i/{image_name}/full").content
    with open(f"./tmp/result_{image_name}", 'wb') as f:
        f.write(img_data)
```

## Image-to-Image Workflow

For image-to-image, add these nodes and adjust the graph:

```python
# Additional nodes for img2img
"input_img": {
    "id": "input_img",
    "type": "image",
    "inputs": {"image": {"image_name": uploaded_name}}
},
"i2l": {
    "id": "i2l",
    "type": "i2l",
    "inputs": {"fp32": False}
}

# Additional edges
{"source": {"node_id": "input_img", "field": "image"},
 "destination": {"node_id": "i2l", "field": "image"}},
{"source": {"node_id": "model", "field": "vae"},
 "destination": {"node_id": "i2l", "field": "vae"}},
{"source": {"node_id": "i2l", "field": "latents"},
 "destination": {"node_id": "denoise", "field": "latents"}}

# Adjust denoising_start for strength (0.3 = keep 70% of original)
"denoising_start": 0.3
```

## Common Issues and Solutions

### Issue: Black images (16KB) when using board assignment
**Problem**: Images generated with board assignment in the l2i node come out as black 16KB files.
**Solution**: Generate images WITHOUT board assignment, then assign to boards afterward:
```python
# DON'T DO THIS - causes black images:
"l2i": {
    "id": "l2i",
    "type": "l2i",
    "board": {"board_id": board_id}  # This causes issues
}

# DO THIS INSTEAD - generate first:
"l2i": {
    "id": "l2i",
    "type": "l2i",
    "fp32": False
    # No board field
}

# Then assign to board after generation:
response = session.post(
    f"{base_url}/api/v1/board_images/",
    json={"board_id": board_id, "image_name": image_name}
)
```

### Issue: "Edge source field clip2 does not exist"
**Solution**: You're using `main_model_loader` with an SDXL model. Use `sdxl_model_loader` instead.

### Issue: Workflow fails validation
**Solution**: Check that all edge connections are valid. Use the OpenAPI schema to verify field names.

### Issue: Generation takes too long
**Solution**: 
- Reduce steps (10-15 is often sufficient for testing)
- Use simpler schedulers like "euler"
- Reduce image dimensions

### Issue: Windows console Unicode errors
**Solution**: Avoid Unicode characters in console output. Use ASCII alternatives like `[OK]` instead of `✓`.

## Testing Checklist

1. ✅ API is accessible at `http://127.0.0.1:9090`
2. ✅ Can upload images via multipart/form-data
3. ✅ Can list available models
4. ✅ Can create and enqueue text-to-image workflow
5. ✅ Can create and enqueue image-to-image workflow
6. ✅ Can check queue status
7. ✅ Can download generated images

## Files Created During Testing

```
./tmp/
├── opencv_test_image.png    # Generated with OpenCV
├── test_input.png           # Another test image
├── result_1_*.png           # Text-to-image results
├── result_2_*.png           # More results
└── result_3_*.png           # Image-to-image results
```

## Full Demo Scripts

- `invokeai_api_demo.py` - Simple, robust demonstration of all operations
- `test_invokeai_api.py` - More comprehensive test with error handling

## API Documentation

- Swagger UI: http://127.0.0.1:9090/docs
- OpenAPI Schema: http://127.0.0.1:9090/openapi.json

## Important Tips

1. **Always use the correct model loader type** - This is the most common error
2. **SDXL requires both clip and clip2 connections**
3. **Use lower step counts for testing** (10-20 steps)
4. **Check queue status instead of blocking indefinitely**
5. **Handle API errors gracefully**
6. **Create tmp directory before saving files**
7. **Use session objects for connection pooling**

## Next Steps

- Implement proper error handling and retries
- Add progress monitoring via WebSocket
- Create reusable workflow templates
- Implement batch processing for multiple images
- Add support for ControlNet and other advanced features