# How to Use InvokeAI Workflow API - Complete Guide

This comprehensive guide covers how to use InvokeAI's workflow system for advanced image generation via Python API, including SDXL+ControlNet+IP-Adapter workflows, Flux1+ControlNet integration, image-to-image operations, and complete workflow JSON structures.

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

## Advanced Workflow Features

### SDXL + ControlNet + IP-Adapter Workflow

SDXL combined with ControlNet and IP-Adapter provides exceptional control over image generation, allowing you to maintain structure while applying artistic styles and precise conditioning.

#### Essential Components

1. **SDXL Base Model**: Provides high-quality 1024x1024+ generation
2. **ControlNet**: Maintains structural guidance (pose, edges, depth)
3. **IP-Adapter**: Applies style and visual characteristics from reference images
4. **VAE**: Handles encoding/decoding between pixel and latent space

#### Complete SDXL+ControlNet+IP-Adapter Workflow JSON

```json
{
  "meta": {
    "version": "3.0.0",
    "name": "SDXL ControlNet IP-Adapter Workflow",
    "description": "Advanced workflow combining SDXL, ControlNet, and IP-Adapter"
  },
  "nodes": [
    {
      "id": "sdxl_model_loader",
      "type": "sdxl_model_loader",
      "data": {
        "model": "stabilityai/stable-diffusion-xl-base-1.0"
      }
    },
    {
      "id": "sdxl_refiner_loader", 
      "type": "sdxl_model_loader",
      "data": {
        "model": "stabilityai/stable-diffusion-xl-refiner-1.0"
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
      "id": "controlnet_loader",
      "type": "controlnet_loader",
      "data": {
        "control_net_name": "diffusers_xl_canny_mid.safetensors"
      }
    },
    {
      "id": "ip_adapter_loader",
      "type": "ip_adapter_loader", 
      "data": {
        "ip_adapter_name": "ip-adapter-plus_sdxl_vit-h.safetensors"
      }
    },
    {
      "id": "clip_vision_loader",
      "type": "clip_vision_loader",
      "data": {
        "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
      }
    },
    {
      "id": "positive_prompt",
      "type": "sdxl_prompt_styler",
      "data": {
        "text_positive": "masterpiece, best quality, highly detailed, photorealistic portrait",
        "text_negative": "",
        "style": "photographic",
        "log_prompt": false
      }
    },
    {
      "id": "negative_prompt",
      "type": "sdxl_prompt_styler", 
      "data": {
        "text_positive": "",
        "text_negative": "blurry, low quality, distorted, deformed, watermark",
        "style": "photographic",
        "log_prompt": false
      }
    },
    {
      "id": "controlnet_input_image",
      "type": "load_image",
      "data": {
        "image": "control_image.png"
      }
    },
    {
      "id": "ip_adapter_image", 
      "type": "load_image",
      "data": {
        "image": "style_reference.png"
      }
    },
    {
      "id": "canny_preprocessor",
      "type": "canny_edge_preprocessor",
      "data": {
        "low_threshold": 100,
        "high_threshold": 200,
        "resolution": 1024
      }
    },
    {
      "id": "controlnet_apply",
      "type": "apply_controlnet",
      "data": {
        "strength": 0.8,
        "start_percent": 0.0,
        "end_percent": 1.0
      }
    },
    {
      "id": "ip_adapter_apply",
      "type": "ip_adapter",
      "data": {
        "weight": 0.7,
        "noise": 0.0,
        "weight_type": "original",
        "start_at": 0.0,
        "end_at": 1.0
      }
    },
    {
      "id": "noise_seed",
      "type": "noise",
      "data": {
        "width": 1024,
        "height": 1024, 
        "seed": 42
      }
    },
    {
      "id": "base_sampler",
      "type": "ksampler",
      "data": {
        "seed": 42,
        "steps": 25,
        "cfg": 8.0,
        "sampler_name": "dpmpp_2m",
        "scheduler": "karras",
        "denoise": 1.0
      }
    },
    {
      "id": "refiner_sampler",
      "type": "ksampler", 
      "data": {
        "seed": 42,
        "steps": 20,
        "cfg": 8.0,
        "sampler_name": "dpmpp_2m",
        "scheduler": "karras", 
        "denoise": 0.3
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
        "filename_prefix": "sdxl_controlnet_ipadapter_"
      }
    }
  ],
  "edges": [
    {
      "source": {"node_id": "sdxl_model_loader", "field": "unet"},
      "destination": {"node_id": "base_sampler", "field": "model"}
    },
    {
      "source": {"node_id": "sdxl_model_loader", "field": "clip"},
      "destination": {"node_id": "positive_prompt", "field": "clip"}
    },
    {
      "source": {"node_id": "sdxl_model_loader", "field": "clip"}, 
      "destination": {"node_id": "negative_prompt", "field": "clip"}
    },
    {
      "source": {"node_id": "controlnet_input_image", "field": "image"},
      "destination": {"node_id": "canny_preprocessor", "field": "image"}
    },
    {
      "source": {"node_id": "canny_preprocessor", "field": "image"},
      "destination": {"node_id": "controlnet_apply", "field": "image"}
    },
    {
      "source": {"node_id": "controlnet_loader", "field": "control_net"},
      "destination": {"node_id": "controlnet_apply", "field": "control_net"}
    },
    {
      "source": {"node_id": "ip_adapter_image", "field": "image"},
      "destination": {"node_id": "ip_adapter_apply", "field": "image"}
    },
    {
      "source": {"node_id": "ip_adapter_loader", "field": "ip_adapter"},
      "destination": {"node_id": "ip_adapter_apply", "field": "ipadapter"}
    },
    {
      "source": {"node_id": "clip_vision_loader", "field": "clip_vision"},
      "destination": {"node_id": "ip_adapter_apply", "field": "clip_vision"}
    },
    {
      "source": {"node_id": "positive_prompt", "field": "conditioning"},
      "destination": {"node_id": "base_sampler", "field": "positive"}
    },
    {
      "source": {"node_id": "negative_prompt", "field": "conditioning"},
      "destination": {"node_id": "base_sampler", "field": "negative"}
    },
    {
      "source": {"node_id": "noise_seed", "field": "noise"},
      "destination": {"node_id": "base_sampler", "field": "latent_image"}
    },
    {
      "source": {"node_id": "controlnet_apply", "field": "conditioning"},
      "destination": {"node_id": "base_sampler", "field": "positive"}
    },
    {
      "source": {"node_id": "ip_adapter_apply", "field": "model"},
      "destination": {"node_id": "base_sampler", "field": "model"}
    },
    {
      "source": {"node_id": "base_sampler", "field": "latent"},
      "destination": {"node_id": "refiner_sampler", "field": "latent_image"}
    },
    {
      "source": {"node_id": "refiner_sampler", "field": "latent"},
      "destination": {"node_id": "vae_decode", "field": "samples"}
    },
    {
      "source": {"node_id": "vae_loader", "field": "vae"},
      "destination": {"node_id": "vae_decode", "field": "vae"}
    },
    {
      "source": {"node_id": "vae_decode", "field": "image"},
      "destination": {"node_id": "save_image", "field": "images"}
    }
  ]
}
```

#### Python Implementation for SDXL+ControlNet+IP-Adapter

```python
def create_advanced_sdxl_workflow(
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality, distorted",
    control_image_path: str = None,
    style_image_path: str = None,
    controlnet_strength: float = 0.8,
    ip_adapter_weight: float = 0.7,
    width: int = 1024,
    height: int = 1024,
    seed: int = None
):
    """Create an advanced SDXL workflow with ControlNet and IP-Adapter"""
    
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    
    workflow = {
        "meta": {
            "version": "3.0.0",
            "name": "Advanced SDXL Workflow",
            "description": f"SDXL with ControlNet and IP-Adapter - {positive_prompt[:50]}"
        },
        "nodes": [
            # Base SDXL model
            {
                "id": "sdxl_base",
                "type": "sdxl_model_loader",
                "data": {"model": "stabilityai/stable-diffusion-xl-base-1.0"}
            },
            # VAE for high quality encoding/decoding
            {
                "id": "vae", 
                "type": "vae_loader",
                "data": {"vae_name": "sdxl_vae.safetensors"}
            },
            # Text encoding
            {
                "id": "positive_text",
                "type": "clip_text_encode",
                "data": {"text": positive_prompt}
            },
            {
                "id": "negative_text",
                "type": "clip_text_encode", 
                "data": {"text": negative_prompt}
            },
            # Noise generation
            {
                "id": "noise",
                "type": "random_noise",
                "data": {"width": width, "height": height, "seed": seed}
            },
            # Main sampling
            {
                "id": "sampler",
                "type": "ksampler_advanced",
                "data": {
                    "add_noise": True,
                    "noise_seed": seed,
                    "steps": 25,
                    "cfg": 8.0,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "start_at_step": 0,
                    "end_at_step": 20,
                    "return_with_leftover_noise": True
                }
            },
            # VAE decode
            {
                "id": "decode",
                "type": "vae_decode",
                "data": {}
            },
            # Save result
            {
                "id": "save",
                "type": "save_image",
                "data": {"filename_prefix": "sdxl_advanced_"}
            }
        ],
        "edges": []
    }
    
    # Add ControlNet if control image provided
    if control_image_path:
        workflow["nodes"].extend([
            {
                "id": "control_image",
                "type": "load_image",
                "data": {"image": control_image_path}
            },
            {
                "id": "controlnet_model",
                "type": "controlnet_loader", 
                "data": {"control_net_name": "diffusers_xl_canny_mid.safetensors"}
            },
            {
                "id": "canny_processor",
                "type": "canny_edge_preprocessor",
                "data": {"low_threshold": 100, "high_threshold": 200}
            },
            {
                "id": "apply_controlnet",
                "type": "apply_controlnet",
                "data": {
                    "strength": controlnet_strength,
                    "start_percent": 0.0,
                    "end_percent": 1.0
                }
            }
        ])
    
    # Add IP-Adapter if style image provided
    if style_image_path:
        workflow["nodes"].extend([
            {
                "id": "style_image",
                "type": "load_image", 
                "data": {"image": style_image_path}
            },
            {
                "id": "ip_adapter_model",
                "type": "ip_adapter_loader",
                "data": {"ip_adapter_name": "ip-adapter-plus_sdxl_vit-h.safetensors"}
            },
            {
                "id": "clip_vision",
                "type": "clip_vision_loader",
                "data": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
            },
            {
                "id": "apply_ip_adapter",
                "type": "ip_adapter",
                "data": {
                    "weight": ip_adapter_weight,
                    "weight_type": "original",
                    "start_at": 0.0,
                    "end_at": 1.0
                }
            }
        ])
    
    # Build edges dynamically based on enabled features
    workflow["edges"] = build_workflow_edges(workflow["nodes"], control_image_path, style_image_path)
    
    return workflow

def build_workflow_edges(nodes, has_controlnet, has_ip_adapter):
    """Build the connection edges for the workflow"""
    edges = [
        # Basic connections
        {"source": {"node_id": "sdxl_base", "field": "unet"}, "destination": {"node_id": "sampler", "field": "model"}},
        {"source": {"node_id": "sdxl_base", "field": "clip"}, "destination": {"node_id": "positive_text", "field": "clip"}},
        {"source": {"node_id": "sdxl_base", "field": "clip"}, "destination": {"node_id": "negative_text", "field": "clip"}},
        {"source": {"node_id": "positive_text", "field": "conditioning"}, "destination": {"node_id": "sampler", "field": "positive"}},
        {"source": {"node_id": "negative_text", "field": "conditioning"}, "destination": {"node_id": "sampler", "field": "negative"}},
        {"source": {"node_id": "noise", "field": "noise"}, "destination": {"node_id": "sampler", "field": "latent_image"}},
        {"source": {"node_id": "sampler", "field": "latent"}, "destination": {"node_id": "decode", "field": "samples"}},
        {"source": {"node_id": "vae", "field": "vae"}, "destination": {"node_id": "decode", "field": "vae"}},
        {"source": {"node_id": "decode", "field": "image"}, "destination": {"node_id": "save", "field": "images"}}
    ]
    
    # Add ControlNet edges if enabled
    if has_controlnet:
        edges.extend([
            {"source": {"node_id": "control_image", "field": "image"}, "destination": {"node_id": "canny_processor", "field": "image"}},
            {"source": {"node_id": "canny_processor", "field": "image"}, "destination": {"node_id": "apply_controlnet", "field": "image"}},
            {"source": {"node_id": "controlnet_model", "field": "control_net"}, "destination": {"node_id": "apply_controlnet", "field": "control_net"}},
            {"source": {"node_id": "apply_controlnet", "field": "conditioning"}, "destination": {"node_id": "sampler", "field": "positive"}}
        ])
    
    # Add IP-Adapter edges if enabled
    if has_ip_adapter:
        edges.extend([
            {"source": {"node_id": "style_image", "field": "image"}, "destination": {"node_id": "apply_ip_adapter", "field": "image"}},
            {"source": {"node_id": "ip_adapter_model", "field": "ip_adapter"}, "destination": {"node_id": "apply_ip_adapter", "field": "ipadapter"}},
            {"source": {"node_id": "clip_vision", "field": "clip_vision"}, "destination": {"node_id": "apply_ip_adapter", "field": "clip_vision"}},
            {"source": {"node_id": "apply_ip_adapter", "field": "model"}, "destination": {"node_id": "sampler", "field": "model"}}
        ])
    
    return edges

# Usage example
workflow = create_advanced_sdxl_workflow(
    positive_prompt="a beautiful portrait of a woman, elegant lighting, professional photography",
    control_image_path="pose_reference.jpg", 
    style_image_path="art_style_reference.jpg",
    controlnet_strength=0.8,
    ip_adapter_weight=0.6
)
```

### Flux1 + ControlNet Integration 

Flux1 represents the next generation of diffusion models with superior text understanding and image quality. InvokeAI v6.3.0+ includes native FLUX Kontext support for multiple reference images.

#### FLUX ControlNet Models and Setup

```python
# FLUX ControlNet models available
FLUX_CONTROLNET_MODELS = {
    "canny": "XLabs-AI/flux-controlnet-canny",
    "depth": "XLabs-AI/flux-controlnet-depth", 
    "hed": "XLabs-AI/flux-controlnet-hed",
    "pose": "XLabs-AI/flux-controlnet-pose"
}

# Model placement: /models/xlabs/controlnets/
# Memory requirements:
# - FP8 quantized: 8GB+ VRAM
# - GGUF quantized: 6GB+ VRAM  
# - NF4 quantized: 6GB+ VRAM
# - Original: 16GB+ VRAM
```

#### Complete FLUX + ControlNet Workflow

```json
{
  "meta": {
    "version": "3.0.0",
    "name": "FLUX ControlNet Workflow",
    "description": "FLUX.1 with ControlNet for precise structural control"
  },
  "nodes": [
    {
      "id": "flux_model_loader",
      "type": "flux_model_loader",
      "data": {
        "model": "black-forest-labs/FLUX.1-dev",
        "precision": "fp8_e4m3fn"
      }
    },
    {
      "id": "flux_vae",
      "type": "vae_loader",
      "data": {
        "vae_name": "FLUX1/ae.safetensors"
      }
    },
    {
      "id": "flux_clip",
      "type": "clip_loader", 
      "data": {
        "clip_name": "FLUX1/clip_l.safetensors",
        "type": "flux"
      }
    },
    {
      "id": "controlnet_loader",
      "type": "flux_controlnet_loader",
      "data": {
        "control_net_name": "flux-controlnet-canny.safetensors"
      }
    },
    {
      "id": "positive_prompt",
      "type": "flux_text_encode",
      "data": {
        "text": "a photorealistic portrait of a person, detailed facial features, soft lighting",
        "guidance": 3.5
      }
    },
    {
      "id": "control_image_input",
      "type": "load_image",
      "data": {
        "image": "control_reference.png"
      }
    },
    {
      "id": "canny_preprocessor",
      "type": "canny_edge_preprocessor",
      "data": {
        "low_threshold": 100,
        "high_threshold": 200,
        "resolution": 1024
      }
    },
    {
      "id": "flux_controlnet_apply",
      "type": "flux_controlnet",
      "data": {
        "strength": 0.8,
        "control_guidance_start": 0.0,
        "control_guidance_end": 1.0
      }
    },
    {
      "id": "flux_noise",
      "type": "flux_empty_latent",
      "data": {
        "width": 1024,
        "height": 1024,
        "batch_size": 1
      }
    },
    {
      "id": "flux_sampler",
      "type": "flux_sampler",
      "data": {
        "seed": 42,
        "steps": 20,
        "max_shift": 1.15,
        "base_shift": 0.5,
        "sampler_name": "euler",
        "scheduler": "simple",
        "guidance": 3.5,
        "denoise": 1.0
      }
    },
    {
      "id": "flux_decode",
      "type": "vae_decode",
      "data": {}
    },
    {
      "id": "save_flux_result",
      "type": "save_image", 
      "data": {
        "filename_prefix": "flux_controlnet_"
      }
    }
  ],
  "edges": [
    {"source": {"node_id": "flux_model_loader", "field": "model"}, "destination": {"node_id": "flux_sampler", "field": "model"}},
    {"source": {"node_id": "flux_clip", "field": "clip"}, "destination": {"node_id": "positive_prompt", "field": "clip"}},
    {"source": {"node_id": "control_image_input", "field": "image"}, "destination": {"node_id": "canny_preprocessor", "field": "image"}},
    {"source": {"node_id": "canny_preprocessor", "field": "image"}, "destination": {"node_id": "flux_controlnet_apply", "field": "image"}},
    {"source": {"node_id": "controlnet_loader", "field": "control_net"}, "destination": {"node_id": "flux_controlnet_apply", "field": "control_net"}},
    {"source": {"node_id": "positive_prompt", "field": "conditioning"}, "destination": {"node_id": "flux_sampler", "field": "conditioning"}},
    {"source": {"node_id": "flux_controlnet_apply", "field": "conditioning"}, "destination": {"node_id": "flux_sampler", "field": "conditioning"}},
    {"source": {"node_id": "flux_noise", "field": "latent"}, "destination": {"node_id": "flux_sampler", "field": "latent_image"}},
    {"source": {"node_id": "flux_sampler", "field": "latent"}, "destination": {"node_id": "flux_decode", "field": "samples"}},
    {"source": {"node_id": "flux_vae", "field": "vae"}, "destination": {"node_id": "flux_decode", "field": "vae"}},
    {"source": {"node_id": "flux_decode", "field": "image"}, "destination": {"node_id": "save_flux_result", "field": "images"}}
  ]
}
```

#### Python FLUX ControlNet Implementation

```python
import json
import random
from typing import Optional, Dict, Any

class FluxControlNetWorkflow:
    """Create and manage FLUX ControlNet workflows"""
    
    def __init__(self, client):
        self.client = client
        
    def create_flux_controlnet_workflow(
        self,
        prompt: str,
        control_image_path: str,
        controlnet_type: str = "canny",
        strength: float = 0.8,
        guidance: float = 3.5,
        steps: int = 20,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create FLUX ControlNet workflow"""
        
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
            
        # Map ControlNet types to model files
        controlnet_models = {
            "canny": "flux-controlnet-canny.safetensors",
            "depth": "flux-controlnet-depth.safetensors", 
            "hed": "flux-controlnet-hed.safetensors",
            "pose": "flux-controlnet-pose.safetensors"
        }
        
        # Map ControlNet types to preprocessors
        preprocessors = {
            "canny": {"type": "canny_edge_preprocessor", "params": {"low_threshold": 100, "high_threshold": 200}},
            "depth": {"type": "midas_depth_processor", "params": {"a": 6.28, "bg_threshold": 0.1}},
            "hed": {"type": "hed_preprocessor", "params": {"safe": True}},
            "pose": {"type": "openpose_preprocessor", "params": {"detect_hand": True, "detect_body": True}}
        }
        
        if controlnet_type not in controlnet_models:
            raise ValueError(f"Unsupported ControlNet type: {controlnet_type}")
            
        preprocessor_config = preprocessors[controlnet_type]
        
        workflow = {
            "meta": {
                "version": "3.0.0",
                "name": f"FLUX {controlnet_type.upper()} ControlNet",
                "description": f"FLUX.1 with {controlnet_type} ControlNet"
            },
            "nodes": [
                # FLUX model components
                {
                    "id": "flux_model",
                    "type": "flux_model_loader",
                    "data": {
                        "model": "black-forest-labs/FLUX.1-dev",
                        "precision": "fp8_e4m3fn"  # Memory optimized
                    }
                },
                {
                    "id": "flux_vae",
                    "type": "vae_loader", 
                    "data": {"vae_name": "FLUX1/ae.safetensors"}
                },
                {
                    "id": "flux_clip",
                    "type": "clip_loader",
                    "data": {
                        "clip_name": "FLUX1/clip_l.safetensors",
                        "type": "flux"
                    }
                },
                # ControlNet components
                {
                    "id": "controlnet",
                    "type": "flux_controlnet_loader",
                    "data": {"control_net_name": controlnet_models[controlnet_type]}
                },
                {
                    "id": "control_image",
                    "type": "load_image",
                    "data": {"image": control_image_path}
                },
                {
                    "id": "preprocessor", 
                    "type": preprocessor_config["type"],
                    "data": {
                        "resolution": max(width, height),
                        **preprocessor_config["params"]
                    }
                },
                # Text encoding
                {
                    "id": "text_encode",
                    "type": "flux_text_encode",
                    "data": {
                        "text": prompt,
                        "guidance": guidance
                    }
                },
                # Generation setup
                {
                    "id": "empty_latent",
                    "type": "flux_empty_latent",
                    "data": {
                        "width": width,
                        "height": height,
                        "batch_size": 1
                    }
                },
                # ControlNet application
                {
                    "id": "apply_controlnet",
                    "type": "flux_controlnet",
                    "data": {
                        "strength": strength,
                        "control_guidance_start": 0.0,
                        "control_guidance_end": 1.0
                    }
                },
                # Sampling
                {
                    "id": "sampler",
                    "type": "flux_sampler",
                    "data": {
                        "seed": seed,
                        "steps": steps,
                        "max_shift": 1.15,
                        "base_shift": 0.5,
                        "sampler_name": "euler",
                        "scheduler": "simple",
                        "guidance": guidance,
                        "denoise": 1.0
                    }
                },
                # Output
                {
                    "id": "decode",
                    "type": "vae_decode",
                    "data": {}
                },
                {
                    "id": "save",
                    "type": "save_image",
                    "data": {"filename_prefix": f"flux_{controlnet_type}_"}
                }
            ],
            "edges": [
                # Model connections
                {"source": {"node_id": "flux_model", "field": "model"}, "destination": {"node_id": "sampler", "field": "model"}},
                {"source": {"node_id": "flux_clip", "field": "clip"}, "destination": {"node_id": "text_encode", "field": "clip"}},
                
                # ControlNet processing
                {"source": {"node_id": "control_image", "field": "image"}, "destination": {"node_id": "preprocessor", "field": "image"}},
                {"source": {"node_id": "preprocessor", "field": "image"}, "destination": {"node_id": "apply_controlnet", "field": "image"}},
                {"source": {"node_id": "controlnet", "field": "control_net"}, "destination": {"node_id": "apply_controlnet", "field": "control_net"}},
                
                # Conditioning
                {"source": {"node_id": "text_encode", "field": "conditioning"}, "destination": {"node_id": "apply_controlnet", "field": "conditioning"}},
                {"source": {"node_id": "apply_controlnet", "field": "conditioning"}, "destination": {"node_id": "sampler", "field": "conditioning"}},
                
                # Generation pipeline
                {"source": {"node_id": "empty_latent", "field": "latent"}, "destination": {"node_id": "sampler", "field": "latent_image"}},
                {"source": {"node_id": "sampler", "field": "latent"}, "destination": {"node_id": "decode", "field": "samples"}},
                {"source": {"node_id": "flux_vae", "field": "vae"}, "destination": {"node_id": "decode", "field": "vae"}},
                {"source": {"node_id": "decode", "field": "image"}, "destination": {"node_id": "save", "field": "images"}}
            ]
        }
        
        return workflow
    
    def execute_flux_workflow(self, workflow: Dict[str, Any]) -> str:
        """Execute FLUX workflow and return session ID"""
        try:
            session_id = self.client.execute_workflow(workflow)
            print(f"FLUX workflow started: {session_id}")
            
            result = self.client.wait_for_completion(session_id, timeout=600)
            print("FLUX generation completed!")
            
            return session_id
            
        except Exception as e:
            print(f"FLUX workflow error: {e}")
            raise

# Usage example
flux_client = FluxControlNetWorkflow(client)

# Create pose-controlled portrait
pose_workflow = flux_client.create_flux_controlnet_workflow(
    prompt="a professional headshot of a business executive, confident expression, modern office background",
    control_image_path="pose_reference.jpg",
    controlnet_type="pose",
    strength=0.9,
    guidance=4.0,
    steps=25
)

# Execute workflow
session_id = flux_client.execute_flux_workflow(pose_workflow)
```

### Image-to-Image Operations

Image-to-image (img2img) workflows transform existing images while preserving desired characteristics. The key parameter is `denoising_strength` which controls the balance between original content preservation and AI transformation.

#### Understanding Denoising Strength

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

#### Complete Image-to-Image Workflow JSON

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

#### Python Image-to-Image Implementation

```python
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
    
    def img2img_with_masking(
        self,
        input_image_path: str,
        mask_image_path: str,
        positive_prompt: str,
        denoise_strength: float = 0.8,
        mask_blur: int = 4
    ) -> Dict[str, Any]:
        """Create masked img2img workflow for inpainting/regional editing"""
        
        workflow = self.create_img2img_workflow(
            input_image_path=input_image_path,
            positive_prompt=positive_prompt,
            denoise_strength=denoise_strength
        )
        
        # Add masking nodes
        mask_nodes = [
            {
                "id": "load_mask",
                "type": "load_image_mask",
                "data": {"image": mask_image_path}
            },
            {
                "id": "set_mask",
                "type": "set_latent_noise_mask",
                "data": {}
            },
            {
                "id": "mask_blur",
                "type": "blur_mask",
                "data": {"blur_radius": mask_blur}
            }
        ]
        
        workflow["nodes"].extend(mask_nodes)
        
        # Add mask edges
        mask_edges = [
            {"source": {"node_id": "load_mask", "field": "mask"}, "destination": {"node_id": "mask_blur", "field": "mask"}},
            {"source": {"node_id": "mask_blur", "field": "mask"}, "destination": {"node_id": "set_mask", "field": "mask"}},
            {"source": {"node_id": "encode_image", "field": "latent"}, "destination": {"node_id": "set_mask", "field": "samples"}},
            {"source": {"node_id": "set_mask", "field": "samples"}, "destination": {"node_id": "sample", "field": "latent_image"}}
        ]
        
        workflow["edges"].extend(mask_edges)
        
        return workflow

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

# Masked editing for specific regions
masked_workflow = img2img_client.img2img_with_masking(
    input_image_path="room.jpg",
    mask_image_path="wall_mask.png", 
    positive_prompt="modern art gallery wall, white walls, professional lighting",
    denoise_strength=0.8
)
```

## Error Handling and Best Practices

### Robust Error Handling

```python
def execute_workflow_robust(client, workflow, max_retries=3):
    """Execute workflow with retry logic and proper error handling"""
    
    for attempt in range(max_retries):
        try:
            session_id = client.execute_workflow(workflow)
            result = client.wait_for_completion(session_id, timeout=600)
            
            if result.get("has_error"):
                error_msg = result.get("error", "Unknown error")
                raise RuntimeError(f"Workflow execution failed: {error_msg}")
            
            return session_id
            
        except (requests.RequestException, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            time.sleep(5)
    
    raise RuntimeError("All retry attempts failed")
```

### Input Validation

```python
def validate_workflow(workflow):
    """Validate workflow structure before execution"""
    required_fields = ["nodes", "edges", "meta"]
    
    for field in required_fields:
        if field not in workflow:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate nodes have required fields
    for node in workflow["nodes"]:
        if "id" not in node or "type" not in node:
            raise ValueError(f"Node missing required fields: {node}")
    
    # Validate edges reference existing nodes
    node_ids = {node["id"] for node in workflow["nodes"]}
    for edge in workflow["edges"]:
        source_id = edge["source"]["node_id"]
        dest_id = edge["destination"]["node_id"]
        
        if source_id not in node_ids:
            raise ValueError(f"Edge references non-existent source node: {source_id}")
        if dest_id not in node_ids:
            raise ValueError(f"Edge references non-existent destination node: {dest_id}")
```

## Hardware Requirements & Performance Optimization

### System Requirements by Model Type

#### SDXL Requirements
- **Minimum VRAM**: 8GB (with optimizations)
- **Recommended VRAM**: 12GB+ 
- **RAM**: 16GB system RAM
- **Storage**: 15GB+ for base models and VAE

#### FLUX Requirements
- **FP8 Quantized**: 8GB+ VRAM
- **GGUF Quantized**: 6GB+ VRAM  
- **NF4 Quantized**: 6GB+ VRAM
- **Original**: 16GB+ VRAM
- **RAM**: 32GB system RAM recommended
- **Storage**: 20GB+ for FLUX models

#### ControlNet Additional Requirements
- **Per ControlNet Model**: +2-4GB VRAM
- **Multiple ControlNets**: Scale linearly
- **Preprocessing**: +1-2GB VRAM during processing

### Memory Optimization Strategies

```python
# Memory optimization settings
OPTIMIZATION_CONFIGS = {
    "low_vram": {
        "precision": "fp16",
        "attention_slicing": True,
        "cpu_offload": True,
        "sequential_cpu_offload": True,
        "vae_slicing": True,
        "attention_flash": False  # May not be stable on all cards
    },
    "balanced": {
        "precision": "fp16", 
        "attention_slicing": True,
        "cpu_offload": False,
        "sequential_cpu_offload": False,
        "vae_slicing": True,
        "attention_flash": True
    },
    "high_performance": {
        "precision": "fp32",
        "attention_slicing": False,
        "cpu_offload": False,
        "sequential_cpu_offload": False, 
        "vae_slicing": False,
        "attention_flash": True
    }
}

def apply_memory_optimizations(client, config_name: str):
    """Apply memory optimization configuration"""
    config = OPTIMIZATION_CONFIGS.get(config_name, OPTIMIZATION_CONFIGS["balanced"])
    
    # Set precision
    client.set_precision(config["precision"])
    
    # Configure attention mechanisms
    if config["attention_slicing"]:
        client.enable_attention_slicing()
    
    if config["attention_flash"]:
        client.enable_flash_attention()
    
    # Configure CPU offloading
    if config["cpu_offload"]:
        client.enable_cpu_offload()
    
    if config["sequential_cpu_offload"]:
        client.enable_sequential_cpu_offload()
    
    # Configure VAE slicing for large images
    if config["vae_slicing"]:
        client.enable_vae_slicing()
```

### Batch Processing Optimization

```python
class BatchProcessor:
    """Optimized batch processing for multiple images"""
    
    def __init__(self, client, max_concurrent: int = 2):
        self.client = client
        self.max_concurrent = max_concurrent
        self.active_sessions = []
    
    def process_batch(
        self,
        workflows: List[Dict[str, Any]], 
        callback: Optional[Callable] = None
    ) -> List[str]:
        """Process multiple workflows with concurrency control"""
        
        session_ids = []
        completed = 0
        
        for i in range(0, len(workflows), self.max_concurrent):
            batch = workflows[i:i + self.max_concurrent]
            batch_sessions = []
            
            # Start batch
            for workflow in batch:
                try:
                    session_id = self.client.execute_workflow(workflow)
                    batch_sessions.append(session_id)
                    session_ids.append(session_id)
                except Exception as e:
                    print(f"Failed to start workflow: {e}")
            
            # Wait for batch completion
            for session_id in batch_sessions:
                try:
                    result = self.client.wait_for_completion(session_id, timeout=600)
                    completed += 1
                    
                    if callback:
                        callback(session_id, result, completed, len(workflows))
                        
                except Exception as e:
                    print(f"Workflow {session_id} failed: {e}")
        
        return session_ids
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Out of Memory Errors

**Symptoms**: CUDA out of memory, allocation failures
**Solutions**:
```python
# Reduce batch size
workflow["nodes"][noise_node_id]["data"]["batch_size"] = 1

# Enable memory optimizations
client.enable_attention_slicing()
client.enable_vae_slicing() 
client.enable_cpu_offload()

# Use lower precision
workflow["nodes"][model_node_id]["data"]["precision"] = "fp16"

# Reduce image dimensions
workflow["nodes"][noise_node_id]["data"]["width"] = 512
workflow["nodes"][noise_node_id]["data"]["height"] = 512
```

#### 2. Model Loading Failures

**Symptoms**: Model not found, checksum errors
**Solutions**:
```python
# Verify model paths
available_models = client.get_available_models()
print("Available models:", available_models)

# Check model placement
# SDXL: /models/checkpoints/
# ControlNet: /models/controlnet/
# VAE: /models/vae/
# LoRA: /models/loras/

# Re-download corrupted models
client.download_model("stabilityai/stable-diffusion-xl-base-1.0")
```

#### 3. Workflow Execution Errors

**Symptoms**: Invalid node connections, missing parameters
**Solutions**:
```python
def validate_workflow(workflow: Dict[str, Any]) -> List[str]:
    """Validate workflow structure and return errors"""
    errors = []
    
    nodes = {node["id"]: node for node in workflow["nodes"]}
    
    for edge in workflow["edges"]:
        source_id = edge["source"]["node_id"]
        dest_id = edge["destination"]["node_id"]
        
        if source_id not in nodes:
            errors.append(f"Source node '{source_id}' not found")
        
        if dest_id not in nodes:
            errors.append(f"Destination node '{dest_id}' not found")
    
    return errors

# Usage
errors = validate_workflow(workflow)
if errors:
    print("Workflow errors:", errors)
else:
    session_id = client.execute_workflow(workflow)
```

#### 4. ControlNet Issues

**Symptoms**: No structural control, unexpected results
**Solutions**:
```python
# Check ControlNet model compatibility
CONTROLNET_COMPATIBILITY = {
    "SD1.5": ["control_canny", "control_depth", "control_openpose"],
    "SDXL": ["diffusers_xl_canny_mid", "diffusers_xl_depth_mid"],
    "FLUX": ["flux-controlnet-canny", "flux-controlnet-depth"]
}

# Verify control image preprocessing
def debug_controlnet_image(image_path: str, controlnet_type: str):
    """Debug ControlNet preprocessing"""
    from PIL import Image
    import cv2
    import numpy as np
    
    image = Image.open(image_path)
    image_array = np.array(image)
    
    if controlnet_type == "canny":
        edges = cv2.Canny(image_array, 100, 200)
        print(f"Canny edges detected: {np.sum(edges > 0)} pixels")
        
    elif controlnet_type == "depth":
        # Simulate depth map analysis
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        print(f"Depth range: {gray.min()} - {gray.max()}")

# Adjust ControlNet strength
workflow["nodes"][controlnet_node_id]["data"]["strength"] = 0.8  # Try 0.5-1.0
```

#### 5. Performance Issues

**Symptoms**: Slow generation, high memory usage
**Solutions**:
```python
# Performance monitoring
import time
import psutil
import GPUtil

class PerformanceMonitor:
    def __init__(self):
        self.start_time = None
        self.start_memory = None
    
    def start_monitoring(self):
        self.start_time = time.time()
        self.start_memory = psutil.virtual_memory().used
        
        gpus = GPUtil.getGPUs()
        if gpus:
            self.start_gpu_memory = gpus[0].memoryUsed
    
    def end_monitoring(self):
        end_time = time.time()
        end_memory = psutil.virtual_memory().used
        
        print(f"Generation time: {end_time - self.start_time:.2f}s")
        print(f"Memory used: {(end_memory - self.start_memory) / 1024**3:.2f}GB")
        
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_memory_used = gpus[0].memoryUsed - self.start_gpu_memory
            print(f"GPU memory used: {gpu_memory_used}MB")

# Usage
monitor = PerformanceMonitor()
monitor.start_monitoring()

session_id = client.execute_workflow(workflow)
result = client.wait_for_completion(session_id)

monitor.end_monitoring()
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

## References

- [InvokeAI Workflows Documentation](https://invoke-ai.github.io/InvokeAI/contributing/frontend/workflows/)
- [InvokeAI API Reference](https://github.com/invoke-ai/InvokeAI/blob/main/invokeai/app/api/)
- [Community Workflow Examples](https://invoke-ai.github.io/InvokeAI/nodes/communityNodes/)
- [Node Development Guide](https://invoke-ai.github.io/InvokeAI/nodes/contributingNodes/)

## Example Workflow Files

You can find working workflow JSON examples in:
- InvokeAI Community Nodes repository
- InvokeAI documentation examples
- Community shared workflows on Discord/GitHub

Note: Always validate workflow JSON structure and test with simple examples before using complex workflows in production.
