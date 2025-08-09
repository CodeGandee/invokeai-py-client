# SDXL + ControlNet + IP-Adapter Workflows

Advanced guide for combining SDXL with ControlNet and IP-Adapter for maximum control over image generation.

## Overview

SDXL combined with ControlNet and IP-Adapter provides exceptional control over image generation, allowing you to maintain structure while applying artistic styles and precise conditioning.

### Essential Components

1. **SDXL Base Model**: Provides high-quality 1024x1024+ generation
2. **ControlNet**: Maintains structural guidance (pose, edges, depth)
3. **IP-Adapter**: Applies style and visual characteristics from reference images
4. **VAE**: Handles encoding/decoding between pixel and latent space

## System Requirements

### Hardware Requirements
- **Minimum VRAM**: 8GB (with optimizations)
- **Recommended VRAM**: 12GB+ 
- **RAM**: 16GB system RAM
- **Storage**: 15GB+ for base models and VAE

### Model Files Needed
```
/models/checkpoints/sd_xl_base_1.0.safetensors
/models/checkpoints/sd_xl_refiner_1.0.safetensors
/models/vae/sdxl_vae.safetensors
/models/controlnet/diffusers_xl_canny_mid.safetensors
/models/controlnet/diffusers_xl_depth_mid.safetensors
/models/ip_adapter/ip-adapter-plus_sdxl_vit-h.safetensors
/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
```

## Complete SDXL+ControlNet+IP-Adapter Workflow JSON

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

## Python Implementation for SDXL+ControlNet+IP-Adapter

```python
import json
import random
from typing import Optional, Dict, Any, List

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

class AdvancedSDXLWorkflow:
    """Class for managing advanced SDXL workflows"""
    
    def __init__(self, client):
        self.client = client
    
    def execute_combined_workflow(
        self,
        prompt: str,
        control_image_path: str,
        style_image_path: str,
        controlnet_strength: float = 0.8,
        ip_adapter_weight: float = 0.7
    ):
        """Execute a workflow combining all features"""
        
        workflow = create_advanced_sdxl_workflow(
            positive_prompt=prompt,
            control_image_path=control_image_path,
            style_image_path=style_image_path,
            controlnet_strength=controlnet_strength,
            ip_adapter_weight=ip_adapter_weight
        )
        
        try:
            session_id = self.client.execute_workflow(workflow)
            print(f"Advanced SDXL workflow started: {session_id}")
            
            result = self.client.wait_for_completion(session_id, timeout=600)
            print("Advanced SDXL generation completed!")
            
            return session_id
            
        except Exception as e:
            print(f"Advanced SDXL workflow error: {e}")
            raise

# Usage example
advanced_client = AdvancedSDXLWorkflow(client)

# Create portrait with pose control and style transfer
session_id = advanced_client.execute_combined_workflow(
    prompt="professional business portrait, confident expression, modern office lighting",
    control_image_path="pose_reference.jpg",
    style_image_path="corporate_style.jpg",
    controlnet_strength=0.9,
    ip_adapter_weight=0.6
)
```

## ControlNet Types for SDXL

### Available ControlNet Models
```python
SDXL_CONTROLNET_MODELS = {
    "canny": "diffusers_xl_canny_mid.safetensors",
    "depth": "diffusers_xl_depth_mid.safetensors",
    "openpose": "diffusers_xl_openpose_mid.safetensors",
    "scribble": "diffusers_xl_scribble_mid.safetensors",
    "softedge": "diffusers_xl_softedge_mid.safetensors"
}
```

### Preprocessing Parameters
```python
CONTROLNET_PREPROCESSORS = {
    "canny": {
        "type": "canny_edge_preprocessor",
        "params": {
            "low_threshold": 100,
            "high_threshold": 200,
            "resolution": 1024
        }
    },
    "depth": {
        "type": "midas_depth_processor", 
        "params": {
            "a": 6.28,
            "bg_threshold": 0.1,
            "resolution": 1024
        }
    },
    "openpose": {
        "type": "openpose_preprocessor",
        "params": {
            "detect_hand": True,
            "detect_body": True,
            "detect_face": True,
            "resolution": 1024
        }
    }
}
```

## IP-Adapter Variants

### SDXL IP-Adapter Models
```python
SDXL_IP_ADAPTER_MODELS = {
    "base": "ip-adapter_sdxl.safetensors",
    "plus": "ip-adapter-plus_sdxl_vit-h.safetensors", 
    "plus_face": "ip-adapter-plus-face_sdxl_vit-h.safetensors",
    "faceid": "ip-adapter-faceid_sdxl.safetensors"
}
```

### Weight Configuration Guidelines
- **0.3-0.5**: Subtle style influence
- **0.6-0.8**: Moderate style transfer  
- **0.9-1.0**: Strong style dominance
- **1.0+**: May cause oversaturation

## Common Use Cases

### Professional Portrait Generation
```python
# Executive headshot with pose control and corporate style
workflow = create_advanced_sdxl_workflow(
    positive_prompt="professional executive portrait, confident expression, business attire, studio lighting",
    control_image_path="executive_pose.jpg",
    style_image_path="corporate_style.jpg",
    controlnet_strength=0.8,
    ip_adapter_weight=0.6
)
```

### Artistic Style Transfer
```python
# Convert photo to artistic style while maintaining composition
workflow = create_advanced_sdxl_workflow(
    positive_prompt="oil painting, renaissance style, dramatic lighting, classical composition",
    control_image_path="photo_composition.jpg", 
    style_image_path="renaissance_painting.jpg",
    controlnet_strength=0.7,
    ip_adapter_weight=0.8
)
```

### Product Photography Enhancement
```python
# Enhance product photos with specific lighting and style
workflow = create_advanced_sdxl_workflow(
    positive_prompt="professional product photography, clean background, studio lighting, high detail",
    control_image_path="product_layout.jpg",
    style_image_path="premium_lighting.jpg",
    controlnet_strength=0.6,
    ip_adapter_weight=0.4
)
```

## Performance Optimization

### Memory Management
```python
# Optimize for lower VRAM usage
def optimize_for_low_vram(workflow):
    """Adjust workflow for systems with limited VRAM"""
    
    # Reduce resolution
    for node in workflow["nodes"]:
        if node["type"] == "noise":
            node["data"]["width"] = 768
            node["data"]["height"] = 768
    
    # Use fewer sampling steps
    for node in workflow["nodes"]:
        if node["type"] == "ksampler":
            node["data"]["steps"] = 15
    
    return workflow
```

### Batch Processing
```python
def create_batch_variations(base_workflow, variations):
    """Create multiple variations of the same workflow"""
    
    batch_workflows = []
    
    for i, variation in enumerate(variations):
        workflow = base_workflow.copy()
        
        # Update prompt
        for node in workflow["nodes"]:
            if node["id"] == "positive_text":
                node["data"]["text"] = f"{node['data']['text']}, {variation}"
        
        # Randomize seed
        seed = random.randint(0, 2**32 - 1)
        for node in workflow["nodes"]:
            if "seed" in node["data"]:
                node["data"]["seed"] = seed
        
        batch_workflows.append(workflow)
    
    return batch_workflows
```

## Troubleshooting SDXL Workflows

### Common Issues

1. **Out of Memory**: Reduce resolution, enable CPU offload
2. **Model Loading Errors**: Check file paths and permissions
3. **Poor ControlNet Effect**: Adjust strength (0.5-1.0)
4. **IP-Adapter Artifacts**: Lower weight (0.3-0.7)
5. **Slow Generation**: Reduce steps, optimize VAE settings

### Debug Checklist
```python
def debug_sdxl_workflow(workflow):
    """Debug common SDXL workflow issues"""
    
    checks = []
    
    # Check for required models
    required_models = ["sdxl_model_loader", "vae_loader"]
    for model_type in required_models:
        if not any(node["type"] == model_type for node in workflow["nodes"]):
            checks.append(f"Missing {model_type}")
    
    # Check resolution compatibility
    for node in workflow["nodes"]:
        if node["type"] == "noise":
            width = node["data"].get("width", 512)
            height = node["data"].get("height", 512)
            if width < 1024 or height < 1024:
                checks.append("SDXL works best with 1024x1024+ resolution")
    
    return checks
```
