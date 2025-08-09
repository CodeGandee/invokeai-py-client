# How to Use InvokeAI API

This guide explains how to use the InvokeAI REST API to submit images, perform text-to-image generation, and image-to-image transformations.

## Prerequisites

- InvokeAI server running (typically at `http://localhost:9090`)
- Access to the API documentation at `/api/docs` when the server is running
- API authentication if configured (token/key)

## Core Concepts

InvokeAI uses a **graph-based workflow system** where:
- **Nodes** represent operations (loading models, generating images, etc.)
- **Edges** connect node outputs to inputs
- **Workflows** are executed by enqueueing them to a processing queue

## Key API Endpoints

### 1. Image Upload
```
POST /api/v1/images/upload
```
Upload images to the system using multipart/form-data.

**Parameters:**
- `image_category` (required): Category of the image
- `is_intermediate` (required): Whether this is an intermediate image (boolean)
- `board_id` (optional): Board to add the image to
- `session_id` (optional): Session ID for the upload

**Example:**
```python
import requests

files = {'file': open('input.jpg', 'rb')}
params = {
    'image_category': 'general',
    'is_intermediate': False
}
response = requests.post(
    'http://localhost:9090/api/v1/images/upload',
    files=files,
    params=params
)
image_data = response.json()
image_name = image_data['image_name']
```

### 2. Enqueue Workflow for Processing
```
POST /api/v1/queue/{queue_id}/enqueue_batch
```
Submit a workflow graph for execution.

**Request Body:**
```json
{
  "batch": {
    "batch_id": "unique-batch-id",
    "graph": {
      "id": "workflow-graph-id",
      "nodes": {
        "node_id": {
          "type": "invocation_type",
          "inputs": {}
        }
      },
      "edges": [
        {
          "source": {
            "node_id": "source_node",
            "field": "output_field"
          },
          "destination": {
            "node_id": "target_node",
            "field": "input_field"
          }
        }
      ]
    },
    "runs": 1
  }
}
```

## Text-to-Image Workflow

A basic text-to-image workflow requires these node types:

1. **main_model_loader** - Loads the SD model
2. **compel** (x2) - Processes positive and negative prompts
3. **noise** - Generates initial noise
4. **denoise_latents** - Performs the denoising process
5. **l2i** (latents to image) - Converts latents to final image

### Minimal Text-to-Image Graph Structure
```json
{
  "nodes": {
    "model_loader": {
      "type": "main_model_loader",
      "inputs": {
        "model": {
          "key": "stable-diffusion-v1-5",
          "base": "sd-1"
        }
      }
    },
    "positive_prompt": {
      "type": "compel",
      "inputs": {
        "prompt": "a beautiful landscape"
      }
    },
    "negative_prompt": {
      "type": "compel",
      "inputs": {
        "prompt": "ugly, blurry"
      }
    },
    "noise": {
      "type": "noise",
      "inputs": {
        "width": 512,
        "height": 512,
        "seed": 42
      }
    },
    "denoise": {
      "type": "denoise_latents",
      "inputs": {
        "steps": 30,
        "cfg_scale": 7.5,
        "scheduler": "dpmpp_sde_k",
        "denoising_start": 0,
        "denoising_end": 1
      }
    },
    "latents_to_image": {
      "type": "l2i",
      "inputs": {
        "fp32": true
      }
    }
  },
  "edges": [
    {
      "source": {"node_id": "model_loader", "field": "clip"},
      "destination": {"node_id": "positive_prompt", "field": "clip"}
    },
    {
      "source": {"node_id": "model_loader", "field": "clip"},
      "destination": {"node_id": "negative_prompt", "field": "clip"}
    },
    {
      "source": {"node_id": "model_loader", "field": "unet"},
      "destination": {"node_id": "denoise", "field": "unet"}
    },
    {
      "source": {"node_id": "model_loader", "field": "vae"},
      "destination": {"node_id": "latents_to_image", "field": "vae"}
    },
    {
      "source": {"node_id": "positive_prompt", "field": "conditioning"},
      "destination": {"node_id": "denoise", "field": "positive_conditioning"}
    },
    {
      "source": {"node_id": "negative_prompt", "field": "conditioning"},
      "destination": {"node_id": "denoise", "field": "negative_conditioning"}
    },
    {
      "source": {"node_id": "noise", "field": "noise"},
      "destination": {"node_id": "denoise", "field": "noise"}
    },
    {
      "source": {"node_id": "denoise", "field": "latents"},
      "destination": {"node_id": "latents_to_image", "field": "latents"}
    }
  ]
}
```

## Image-to-Image Workflow

Image-to-image workflows are similar but include additional nodes:

1. **image** - Input image node
2. **i2l** (image to latents) - Converts input image to latents
3. Modified **denoise_latents** with `denoising_start` > 0

### Key Differences from Text-to-Image
```json
{
  "nodes": {
    "input_image": {
      "type": "image",
      "inputs": {
        "image": {
          "image_name": "uploaded_image_name.png"
        }
      }
    },
    "image_to_latents": {
      "type": "i2l",
      "inputs": {}
    },
    "denoise": {
      "type": "denoise_latents",
      "inputs": {
        "denoising_start": 0.3,  // Start from 30% (preserves more original)
        "denoising_end": 1.0
      }
    }
  }
}
```

## Complete Python Example

```python
import requests
import json

class InvokeAIClient:
    def __init__(self, base_url="http://localhost:9090"):
        self.base_url = base_url
        
    def text_to_image(self, prompt, negative_prompt="", steps=30):
        # Build the workflow graph
        workflow = self._build_text_to_image_graph(
            prompt, negative_prompt, steps
        )
        
        # Submit to queue
        response = requests.post(
            f"{self.base_url}/api/v1/queue/default/enqueue_batch",
            json={"batch": workflow}
        )
        return response.json()
    
    def _build_text_to_image_graph(self, prompt, negative_prompt, steps):
        # Graph structure simplified for clarity
        return {
            "batch_id": "txt2img_batch",
            "graph": {
                "id": "txt2img_workflow",
                "nodes": {...},  # As shown above
                "edges": [...]   # As shown above
            },
            "runs": 1
        }
```

## Common Node Types

### Model Management
- `main_model_loader`: Load SD/SDXL models
- `vae_loader`: Load VAE models
- `lora_loader`: Load LoRA models

### Text Processing
- `compel`: Process prompts with CLIP
- `sdxl_compel_prompt`: SDXL-specific prompt processing
- `flux_text_encoder`: FLUX model text encoding

### Image Operations
- `image`: Load image by name
- `i2l`: Image to latents
- `l2i`: Latents to image
- `canvas_paste_back`: Composite operations
- `image_resize`: Resize images

### Generation
- `noise`: Generate noise tensor
- `denoise_latents`: SD1.5/SD2 denoising
- `flux_denoise`: FLUX model denoising

### Control
- `controlnet`: ControlNet processing
- `ip_adapter`: IP-Adapter for style transfer
- `t2i_adapter`: T2I-Adapter support

## API Response Monitoring

After enqueueing, monitor the queue status:
```
GET /api/v1/queue/{queue_id}/status
```

Get specific batch results:
```
GET /api/v1/queue/{queue_id}/batch/{batch_id}
```

## Error Handling

Common error responses:
- `415`: Unsupported media type (wrong image format)
- `422`: Validation error (missing/invalid parameters)
- `500`: Server error (check logs)

## Resources

- [InvokeAI Documentation](https://invoke-ai.github.io/InvokeAI/)
- [Workflow Editor Basics](https://invoke-ai.github.io/InvokeAI/nodes/NODES/)
- [Community Workflows](https://github.com/invoke-ai/invoke-workflows)
- OpenAPI Schema: Available at `/api/openapi.json` when server is running

## Notes

- The exact node types and parameters depend on the InvokeAI version
- FLUX models use different node types (e.g., `flux_denoise` instead of `denoise_latents`)
- For production use, implement proper error handling and retry logic
- Consider using the WebSocket API for real-time progress updates