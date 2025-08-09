# InvokeAI Workflow Basics

This guide covers the fundamentals of creating and using InvokeAI workflows through the Python API.

## Overview

InvokeAI uses a node-based workflow system where:
- **Nodes** represent individual operations (like text prompts, model loading, image generation)
- **Edges** connect nodes together via their inputs and outputs
- **Workflows** are JSON representations of these node graphs plus metadata
- **Invocations** are the backend execution units that process the workflow

## Workflow Structure

### Basic Workflow Components

A workflow JSON contains:
- `nodes`: Array of node objects with inputs/outputs
- `edges`: Array of connections between nodes
- `meta`: Metadata (name, description, version, etc.)

### Essential Nodes for Text-to-Image

```json
{
  "meta": {
    "version": "3.0.0",
    "name": "Basic Text to Image",
    "description": "Simple text-to-image workflow"
  },
  "nodes": [
    {
      "id": "load_checkpoint",
      "type": "load_checkpoint",
      "data": {
        "model": "stable-diffusion-v1-5"
      }
    },
    {
      "id": "positive_prompt",
      "type": "clip_text_encode",
      "data": {
        "text": "a beautiful landscape"
      }
    },
    {
      "id": "negative_prompt", 
      "type": "clip_text_encode",
      "data": {
        "text": "blurry, low quality"
      }
    },
    {
      "id": "noise",
      "type": "noise",
      "data": {
        "width": 512,
        "height": 512,
        "seed": 42
      }
    },
    {
      "id": "denoise",
      "type": "denoise_latents",
      "data": {
        "steps": 20,
        "cfg": 7.5,
        "scheduler": "euler",
        "denoising_start": 0.0,
        "denoising_end": 1.0
      }
    },
    {
      "id": "decode",
      "type": "l2i",
      "data": {}
    },
    {
      "id": "save",
      "type": "save_image",
      "data": {
        "board": {
          "board_id": "default"
        }
      }
    }
  ],
  "edges": [
    {
      "source": {
        "node_id": "load_checkpoint",
        "field": "unet"
      },
      "destination": {
        "node_id": "denoise",
        "field": "unet"
      }
    },
    {
      "source": {
        "node_id": "load_checkpoint", 
        "field": "clip"
      },
      "destination": {
        "node_id": "positive_prompt",
        "field": "clip"
      }
    },
    {
      "source": {
        "node_id": "positive_prompt",
        "field": "conditioning"
      },
      "destination": {
        "node_id": "denoise",
        "field": "positive_conditioning"
      }
    }
  ]
}
```

## Python API Usage

### Basic Setup

```python
import json
import requests
import time
from pathlib import Path

class InvokeAIClient:
    def __init__(self, base_url="http://localhost:9090"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def execute_workflow(self, workflow_data):
        """Execute a workflow and return the session ID"""
        url = f"{self.base_url}/api/v1/sessions/"
        
        # Create session
        response = self.session.post(url, json={
            "graph": workflow_data
        })
        response.raise_for_status()
        
        session_data = response.json()
        session_id = session_data["id"]
        
        # Invoke the session
        invoke_url = f"{self.base_url}/api/v1/sessions/{session_id}/invoke"
        response = self.session.put(invoke_url)
        response.raise_for_status()
        
        return session_id
    
    def wait_for_completion(self, session_id, timeout=300):
        """Wait for workflow execution to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_url = f"{self.base_url}/api/v1/sessions/{session_id}"
            response = self.session.get(status_url)
            response.raise_for_status()
            
            session_data = response.json()
            
            if session_data["is_complete"]:
                return session_data
            
            time.sleep(1)
        
        raise TimeoutError(f"Workflow did not complete within {timeout} seconds")
    
    def get_session_images(self, session_id):
        """Get generated images from completed session"""
        url = f"{self.base_url}/api/v1/sessions/{session_id}/images"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def download_image(self, image_name, save_path):
        """Download image by name"""
        url = f"{self.base_url}/api/v1/images/i/{image_name}/full"
        response = self.session.get(url)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
```

### Example Usage

```python
# Initialize client
client = InvokeAIClient()

# Load workflow from file
with open('text_to_image_workflow.json', 'r') as f:
    workflow = json.load(f)

# Customize workflow parameters
workflow["nodes"][1]["data"]["text"] = "a majestic dragon in a fantasy landscape"
workflow["nodes"][4]["data"]["seed"] = 123456
workflow["nodes"][4]["data"]["steps"] = 30

# Execute workflow
try:
    session_id = client.execute_workflow(workflow)
    print(f"Started workflow execution: {session_id}")
    
    # Wait for completion
    result = client.wait_for_completion(session_id)
    print("Workflow completed successfully!")
    
    # Get generated images
    images = client.get_session_images(session_id)
    
    # Download images
    for image in images:
        image_name = image["image_name"]
        save_path = f"output_{image_name}"
        client.download_image(image_name, save_path)
        print(f"Downloaded: {save_path}")
        
except Exception as e:
    print(f"Error: {e}")
```

## Image-to-Image Operations

Image-to-image (img2img) workflows transform existing images while preserving desired characteristics. The key parameter is `denoising_strength` which controls the balance between original content preservation and AI transformation.

### Understanding Denoising Strength

```python
# Denoising strength values and their effects:
DENOISE_STRENGTH_GUIDE = {
    0.0: "No change - returns original image",
    0.1: "Minimal enhancement - subtle color/lighting adjustments", 
    0.3: "Light modifications - style tweaks, minor corrections",
    0.5: "Moderate changes - style transfer, significant adjustments",
    0.7: "Heavy transformation - major style/content changes",
    0.9: "Near complete regeneration - uses original as loose reference",
    1.0: "Complete regeneration - original used only for composition"
}
```

### Complete Image-to-Image Workflow JSON

```json
{
  "meta": {
    "version": "3.0.0", 
    "name": "Image-to-Image Transformation",
    "description": "Transform existing images with controllable modification strength"
  },
  "nodes": [
    {
      "id": "input_image",
      "type": "load_image",
      "data": {
        "image": "input.jpg"
      }
    },
    {
      "id": "model_loader",
      "type": "checkpoint_loader_simple",
      "data": {
        "ckpt_name": "sd_xl_base_1.0.safetensors"
      }
    },
    {
      "id": "vae_loader",
      "type": "vae_loader",
      "data": {
        "vae_name": "sdxl_vae.safetensors"
      }
    },
    {
      "id": "positive_prompt",
      "type": "clip_text_encode",
      "data": {
        "text": "professional photography, enhanced lighting, detailed textures"
      }
    },
    {
      "id": "negative_prompt",
      "type": "clip_text_encode", 
      "data": {
        "text": "blurry, low quality, distorted, oversaturated"
      }
    },
    {
      "id": "vae_encode",
      "type": "vae_encode",
      "data": {}
    },
    {
      "id": "ksampler",
      "type": "ksampler",
      "data": {
        "seed": 42,
        "steps": 20,
        "cfg": 7.5,
        "sampler_name": "dpmpp_2m",
        "scheduler": "karras",
        "denoise": 0.6
      }
    },
    {
      "id": "vae_decode",
      "type": "vae_decode", 
      "data": {}
    },
    {
      "id": "save_image",
      "type": "save_image",
      "data": {
        "filename_prefix": "img2img_result_"
      }
    }
  ],
  "edges": [
    {"source": {"node_id": "model_loader", "field": "model"}, "destination": {"node_id": "ksampler", "field": "model"}},
    {"source": {"node_id": "model_loader", "field": "clip"}, "destination": {"node_id": "positive_prompt", "field": "clip"}},
    {"source": {"node_id": "model_loader", "field": "clip"}, "destination": {"node_id": "negative_prompt", "field": "clip"}},
    {"source": {"node_id": "input_image", "field": "image"}, "destination": {"node_id": "vae_encode", "field": "pixels"}},
    {"source": {"node_id": "vae_loader", "field": "vae"}, "destination": {"node_id": "vae_encode", "field": "vae"}},
    {"source": {"node_id": "vae_encode", "field": "latent"}, "destination": {"node_id": "ksampler", "field": "latent_image"}},
    {"source": {"node_id": "positive_prompt", "field": "conditioning"}, "destination": {"node_id": "ksampler", "field": "positive"}},
    {"source": {"node_id": "negative_prompt", "field": "conditioning"}, "destination": {"node_id": "ksampler", "field": "negative"}},
    {"source": {"node_id": "ksampler", "field": "latent"}, "destination": {"node_id": "vae_decode", "field": "samples"}},
    {"source": {"node_id": "vae_loader", "field": "vae"}, "destination": {"node_id": "vae_decode", "field": "vae"}},
    {"source": {"node_id": "vae_decode", "field": "image"}, "destination": {"node_id": "save_image", "field": "images"}}
  ]
}
```

### Python Image-to-Image Implementation

```python
from typing import Optional, Dict, Any, List, Callable
import random

class ImageToImageWorkflow:
    """Comprehensive Image-to-Image workflow management"""
    
    def __init__(self, client):
        self.client = client
    
    def create_img2img_workflow(
        self,
        input_image_path: str,
        positive_prompt: str,
        negative_prompt: str = "blurry, low quality, distorted",
        denoise_strength: float = 0.6,
        cfg_scale: float = 7.5,
        steps: int = 20,
        seed: Optional[int] = None,
        model_name: str = "sd_xl_base_1.0.safetensors",
        sampler: str = "dpmpp_2m",
        scheduler: str = "karras"
    ) -> Dict[str, Any]:
        """Create image-to-image workflow with specified parameters"""
        
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
            
        # Validate denoise strength
        if not 0.0 <= denoise_strength <= 1.0:
            raise ValueError("denoise_strength must be between 0.0 and 1.0")
            
        workflow = {
            "meta": {
                "version": "3.0.0",
                "name": "Image-to-Image Workflow",
                "description": f"Transform {input_image_path} with {denoise_strength} strength"
            },
            "nodes": [
                {
                    "id": "load_input",
                    "type": "load_image",
                    "data": {"image": input_image_path}
                },
                {
                    "id": "checkpoint",
                    "type": "checkpoint_loader_simple",
                    "data": {"ckpt_name": model_name}
                },
                {
                    "id": "vae_loader",
                    "type": "vae_loader", 
                    "data": {"vae_name": "sdxl_vae.safetensors"}
                },
                {
                    "id": "encode_positive",
                    "type": "clip_text_encode",
                    "data": {"text": positive_prompt}
                },
                {
                    "id": "encode_negative",
                    "type": "clip_text_encode",
                    "data": {"text": negative_prompt}
                },
                {
                    "id": "encode_image",
                    "type": "vae_encode",
                    "data": {}
                },
                {
                    "id": "sample",
                    "type": "ksampler",
                    "data": {
                        "seed": seed,
                        "steps": steps,
                        "cfg": cfg_scale,
                        "sampler_name": sampler,
                        "scheduler": scheduler,
                        "denoise": denoise_strength
                    }
                },
                {
                    "id": "decode_result",
                    "type": "vae_decode",
                    "data": {}
                },
                {
                    "id": "save_result",
                    "type": "save_image",
                    "data": {"filename_prefix": f"img2img_{denoise_strength}_"}
                }
            ],
            "edges": [
                {"source": {"node_id": "checkpoint", "field": "model"}, "destination": {"node_id": "sample", "field": "model"}},
                {"source": {"node_id": "checkpoint", "field": "clip"}, "destination": {"node_id": "encode_positive", "field": "clip"}},
                {"source": {"node_id": "checkpoint", "field": "clip"}, "destination": {"node_id": "encode_negative", "field": "clip"}},
                {"source": {"node_id": "load_input", "field": "image"}, "destination": {"node_id": "encode_image", "field": "pixels"}},
                {"source": {"node_id": "vae_loader", "field": "vae"}, "destination": {"node_id": "encode_image", "field": "vae"}},
                {"source": {"node_id": "encode_image", "field": "latent"}, "destination": {"node_id": "sample", "field": "latent_image"}},
                {"source": {"node_id": "encode_positive", "field": "conditioning"}, "destination": {"node_id": "sample", "field": "positive"}},
                {"source": {"node_id": "encode_negative", "field": "conditioning"}, "destination": {"node_id": "sample", "field": "negative"}},
                {"source": {"node_id": "sample", "field": "latent"}, "destination": {"node_id": "decode_result", "field": "samples"}},
                {"source": {"node_id": "vae_loader", "field": "vae"}, "destination": {"node_id": "decode_result", "field": "vae"}},
                {"source": {"node_id": "decode_result", "field": "image"}, "destination": {"node_id": "save_result", "field": "images"}}
            ]
        }
        
        return workflow
    
    def batch_img2img_variations(
        self,
        input_image_path: str,
        base_prompt: str,
        denoise_values: List[float] = [0.3, 0.5, 0.7],
        variations: List[str] = None
    ) -> List[str]:
        """Generate multiple img2img variations with different parameters"""
        
        if variations is None:
            variations = [
                "enhanced colors and lighting",
                "artistic style, painterly effect", 
                "dramatic lighting, cinematic mood",
                "vintage film aesthetic",
                "modern digital art style"
            ]
        
        session_ids = []
        
        for i, denoise in enumerate(denoise_values):
            for j, variation in enumerate(variations):
                prompt = f"{base_prompt}, {variation}"
                
                workflow = self.create_img2img_workflow(
                    input_image_path=input_image_path,
                    positive_prompt=prompt,
                    denoise_strength=denoise,
                    seed=random.randint(0, 2**32 - 1)
                )
                
                try:
                    session_id = self.client.execute_workflow(workflow)
                    session_ids.append(session_id)
                    print(f"Started variation {i+1}-{j+1}: denoise={denoise}, prompt='{variation}'")
                    
                except Exception as e:
                    print(f"Failed to start variation {i+1}-{j+1}: {e}")
        
        return session_ids

# Usage examples
img2img_client = ImageToImageWorkflow(client)

# Basic image enhancement
enhancement_workflow = img2img_client.create_img2img_workflow(
    input_image_path="portrait.jpg",
    positive_prompt="professional portrait photography, enhanced lighting, detailed skin texture",
    denoise_strength=0.35,
    steps=25
)

# Style transfer
style_workflow = img2img_client.create_img2img_workflow(
    input_image_path="landscape.jpg", 
    positive_prompt="oil painting, impressionist style, vibrant colors, artistic brushstrokes",
    denoise_strength=0.7,
    steps=30
)

# Batch variations for client review
variations = img2img_client.batch_img2img_variations(
    input_image_path="product.jpg",
    base_prompt="professional product photography",
    denoise_values=[0.2, 0.4, 0.6],
    variations=[
        "studio lighting, white background",
        "dramatic shadows, artistic lighting", 
        "lifestyle setting, natural lighting",
        "macro detail view, enhanced textures"
    ]
)
```

## Common Workflow Templates

### Basic Text-to-Image
- Load checkpoint → Text encode (positive/negative) → Noise → Denoise → Decode → Save

### Image-to-Image  
- Load checkpoint → Load image → Text encode → Noise → Denoise (partial) → Decode → Save

### ControlNet Pipeline
- Load checkpoint → Load control image → ControlNet processor → Text encode → ControlNet → Denoise → Decode → Save

### LoRA Enhanced
- Load checkpoint → Load LoRA → Text encode → Noise → Denoise → Decode → Save

## Performance Tips

1. **Batch Processing**: Create multiple sessions for parallel processing
2. **Model Caching**: Reuse loaded models across sessions when possible  
3. **Parameter Optimization**: Tune steps, CFG, and resolution for speed vs quality
4. **Error Recovery**: Implement proper session cleanup and retry logic
5. **Resource Management**: Monitor VRAM usage and queue management
