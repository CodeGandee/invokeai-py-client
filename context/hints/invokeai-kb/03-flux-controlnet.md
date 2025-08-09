# FLUX + ControlNet Integration

Advanced guide for using FLUX.1 models with ControlNet for next-generation image generation with superior text understanding and image quality.

## Overview

FLUX.1 represents the next generation of diffusion models with superior text understanding and image quality. InvokeAI v6.3.0+ includes native FLUX Kontext support for multiple reference images.

### Key Advantages
- **Superior Text Understanding**: Better prompt adherence and complex scene composition
- **Higher Image Quality**: Enhanced detail and realism compared to SDXL
- **Efficient Architecture**: Optimized for modern hardware with quantization support
- **Native Multi-Reference**: Built-in support for multiple conditioning images

## System Requirements

### Hardware Requirements by Quantization
- **FP8 Quantized**: 8GB+ VRAM
- **GGUF Quantized**: 6GB+ VRAM  
- **NF4 Quantized**: 6GB+ VRAM
- **Original**: 16GB+ VRAM
- **RAM**: 32GB system RAM recommended
- **Storage**: 20GB+ for FLUX models

### Model Files Setup

```bash
# FLUX model structure
/models/unet/flux1-dev.safetensors
/models/vae/FLUX1/ae.safetensors
/models/clip/FLUX1/clip_l.safetensors
/models/xlabs/controlnets/flux-controlnet-canny.safetensors
/models/xlabs/controlnets/flux-controlnet-depth.safetensors
/models/xlabs/controlnets/flux-controlnet-hed.safetensors
/models/xlabs/controlnets/flux-controlnet-pose.safetensors
```

## FLUX ControlNet Models and Setup

```python
# FLUX ControlNet models available
FLUX_CONTROLNET_MODELS = {
    "canny": "XLabs-AI/flux-controlnet-canny",
    "depth": "XLabs-AI/flux-controlnet-depth", 
    "hed": "XLabs-AI/flux-controlnet-hed",
    "pose": "XLabs-AI/flux-controlnet-pose"
}

# Memory requirements by quantization:
QUANTIZATION_OPTIONS = {
    "fp8_e4m3fn": {"vram": "8GB+", "quality": "high", "speed": "fast"},
    "gguf": {"vram": "6GB+", "quality": "high", "speed": "medium"},
    "nf4": {"vram": "6GB+", "quality": "medium", "speed": "fast"},
    "original": {"vram": "16GB+", "quality": "highest", "speed": "slow"}
}
```

## Complete FLUX + ControlNet Workflow JSON

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

## Python FLUX ControlNet Implementation

```python
import json
import random
from typing import Optional, Dict, Any, List

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
        seed: Optional[int] = None,
        precision: str = "fp8_e4m3fn"
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
            "canny": {
                "type": "canny_edge_preprocessor", 
                "params": {"low_threshold": 100, "high_threshold": 200}
            },
            "depth": {
                "type": "midas_depth_processor", 
                "params": {"a": 6.28, "bg_threshold": 0.1}
            },
            "hed": {
                "type": "hed_preprocessor", 
                "params": {"safe": True}
            },
            "pose": {
                "type": "openpose_preprocessor", 
                "params": {"detect_hand": True, "detect_body": True, "detect_face": True}
            }
        }
        
        if controlnet_type not in controlnet_models:
            raise ValueError(f"Unsupported ControlNet type: {controlnet_type}")
            
        preprocessor_config = preprocessors[controlnet_type]
        
        workflow = {
            "meta": {
                "version": "3.0.0",
                "name": f"FLUX {controlnet_type.upper()} ControlNet",
                "description": f"FLUX.1 with {controlnet_type} ControlNet - {prompt[:50]}"
            },
            "nodes": [
                # FLUX model components
                {
                    "id": "flux_model",
                    "type": "flux_model_loader",
                    "data": {
                        "model": "black-forest-labs/FLUX.1-dev",
                        "precision": precision
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
    
    def create_multi_controlnet_workflow(
        self,
        prompt: str,
        control_configs: List[Dict[str, Any]],
        guidance: float = 3.5,
        steps: int = 20,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create FLUX workflow with multiple ControlNets"""
        
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        
        workflow = {
            "meta": {
                "version": "3.0.0",
                "name": "FLUX Multi-ControlNet Workflow",
                "description": f"FLUX.1 with multiple ControlNets"
            },
            "nodes": [
                # Base FLUX components
                {
                    "id": "flux_model",
                    "type": "flux_model_loader",
                    "data": {
                        "model": "black-forest-labs/FLUX.1-dev",
                        "precision": "fp8_e4m3fn"
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
                {
                    "id": "text_encode",
                    "type": "flux_text_encode",
                    "data": {
                        "text": prompt,
                        "guidance": guidance
                    }
                },
                {
                    "id": "empty_latent",
                    "type": "flux_empty_latent",
                    "data": {
                        "width": width,
                        "height": height,
                        "batch_size": 1
                    }
                },
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
                {
                    "id": "decode",
                    "type": "vae_decode",
                    "data": {}
                },
                {
                    "id": "save",
                    "type": "save_image",
                    "data": {"filename_prefix": "flux_multi_controlnet_"}
                }
            ],
            "edges": [
                {"source": {"node_id": "flux_model", "field": "model"}, "destination": {"node_id": "sampler", "field": "model"}},
                {"source": {"node_id": "flux_clip", "field": "clip"}, "destination": {"node_id": "text_encode", "field": "clip"}},
                {"source": {"node_id": "empty_latent", "field": "latent"}, "destination": {"node_id": "sampler", "field": "latent_image"}},
                {"source": {"node_id": "sampler", "field": "latent"}, "destination": {"node_id": "decode", "field": "samples"}},
                {"source": {"node_id": "flux_vae", "field": "vae"}, "destination": {"node_id": "decode", "field": "vae"}},
                {"source": {"node_id": "decode", "field": "image"}, "destination": {"node_id": "save", "field": "images"}}
            ]
        }
        
        # Add multiple ControlNet configurations
        conditioning_nodes = ["text_encode"]
        
        for i, config in enumerate(control_configs):
            controlnet_nodes = self._add_controlnet_nodes(
                workflow, config, i, width, height
            )
            conditioning_nodes.append(controlnet_nodes["apply_id"])
        
        # Chain conditioning nodes
        for i in range(len(conditioning_nodes) - 1):
            workflow["edges"].append({
                "source": {"node_id": conditioning_nodes[i], "field": "conditioning"},
                "destination": {"node_id": conditioning_nodes[i + 1], "field": "conditioning"}
            })
        
        # Connect final conditioning to sampler
        workflow["edges"].append({
            "source": {"node_id": conditioning_nodes[-1], "field": "conditioning"},
            "destination": {"node_id": "sampler", "field": "conditioning"}
        })
        
        return workflow
    
    def _add_controlnet_nodes(
        self, workflow: Dict[str, Any], config: Dict[str, Any], index: int, width: int, height: int
    ) -> Dict[str, str]:
        """Add ControlNet nodes to workflow"""
        
        controlnet_type = config["type"]
        image_path = config["image_path"]
        strength = config.get("strength", 0.8)
        
        # Node IDs
        loader_id = f"controlnet_loader_{index}"
        image_id = f"control_image_{index}"
        preprocessor_id = f"preprocessor_{index}"
        apply_id = f"apply_controlnet_{index}"
        
        # Model mapping
        controlnet_models = {
            "canny": "flux-controlnet-canny.safetensors",
            "depth": "flux-controlnet-depth.safetensors",
            "hed": "flux-controlnet-hed.safetensors",
            "pose": "flux-controlnet-pose.safetensors"
        }
        
        # Preprocessor mapping
        preprocessors = {
            "canny": {"type": "canny_edge_preprocessor", "params": {"low_threshold": 100, "high_threshold": 200}},
            "depth": {"type": "midas_depth_processor", "params": {"a": 6.28, "bg_threshold": 0.1}},
            "hed": {"type": "hed_preprocessor", "params": {"safe": True}},
            "pose": {"type": "openpose_preprocessor", "params": {"detect_hand": True, "detect_body": True}}
        }
        
        # Add nodes
        workflow["nodes"].extend([
            {
                "id": loader_id,
                "type": "flux_controlnet_loader",
                "data": {"control_net_name": controlnet_models[controlnet_type]}
            },
            {
                "id": image_id,
                "type": "load_image",
                "data": {"image": image_path}
            },
            {
                "id": preprocessor_id,
                "type": preprocessors[controlnet_type]["type"],
                "data": {
                    "resolution": max(width, height),
                    **preprocessors[controlnet_type]["params"]
                }
            },
            {
                "id": apply_id,
                "type": "flux_controlnet",
                "data": {
                    "strength": strength,
                    "control_guidance_start": 0.0,
                    "control_guidance_end": 1.0
                }
            }
        ])
        
        # Add edges
        workflow["edges"].extend([
            {"source": {"node_id": image_id, "field": "image"}, "destination": {"node_id": preprocessor_id, "field": "image"}},
            {"source": {"node_id": preprocessor_id, "field": "image"}, "destination": {"node_id": apply_id, "field": "image"}},
            {"source": {"node_id": loader_id, "field": "control_net"}, "destination": {"node_id": apply_id, "field": "control_net"}}
        ])
        
        return {"apply_id": apply_id}

# Usage examples
flux_client = FluxControlNetWorkflow(client)

# Single ControlNet workflow
pose_workflow = flux_client.create_flux_controlnet_workflow(
    prompt="a professional headshot of a business executive, confident expression, modern office background",
    control_image_path="pose_reference.jpg",
    controlnet_type="pose",
    strength=0.9,
    guidance=4.0,
    steps=25
)

# Multi-ControlNet workflow
multi_control_workflow = flux_client.create_multi_controlnet_workflow(
    prompt="a detailed architectural interior, modern design, natural lighting",
    control_configs=[
        {
            "type": "canny",
            "image_path": "structure_reference.jpg",
            "strength": 0.8
        },
        {
            "type": "depth",
            "image_path": "depth_reference.jpg", 
            "strength": 0.6
        }
    ],
    guidance=3.5,
    steps=25
)

# Execute workflows
session_id = flux_client.execute_flux_workflow(pose_workflow)
multi_session_id = flux_client.execute_flux_workflow(multi_control_workflow)
```

## ControlNet Types for FLUX

### Available Models and Use Cases

```python
FLUX_CONTROLNET_TYPES = {
    "canny": {
        "model": "flux-controlnet-canny.safetensors",
        "use_case": "Edge detection and line art control",
        "best_for": "Architectural drawings, line art, sharp edges",
        "strength_range": "0.7-1.0"
    },
    "depth": {
        "model": "flux-controlnet-depth.safetensors", 
        "use_case": "Depth-based spatial control",
        "best_for": "3D composition, spatial relationships, foreground/background",
        "strength_range": "0.5-0.8"
    },
    "hed": {
        "model": "flux-controlnet-hed.safetensors",
        "use_case": "Holistically-nested edge detection",
        "best_for": "Soft edge preservation, artistic style transfer",
        "strength_range": "0.6-0.9"
    },
    "pose": {
        "model": "flux-controlnet-pose.safetensors",
        "use_case": "Human pose and body structure control",
        "best_for": "Portrait photography, character poses, dance/sports",
        "strength_range": "0.8-1.0"
    }
}
```

### Preprocessing Parameter Optimization

```python
# Optimized preprocessing settings for FLUX
FLUX_PREPROCESSOR_SETTINGS = {
    "canny": {
        "low_threshold": 50,    # Lower for more detail
        "high_threshold": 150,  # Adjusted for FLUX sensitivity
        "resolution": 1024
    },
    "depth": {
        "a": 6.28,
        "bg_threshold": 0.05,   # Lower threshold for better depth
        "resolution": 1024
    },
    "hed": {
        "safe": True,
        "resolution": 1024
    },
    "pose": {
        "detect_hand": True,
        "detect_body": True,
        "detect_face": True,
        "resolution": 1024
    }
}
```

## FLUX-Specific Optimizations

### Guidance Scale Tuning
```python
# FLUX guidance recommendations
FLUX_GUIDANCE_SETTINGS = {
    "photorealistic": 3.5,
    "artistic": 4.0,
    "abstract": 2.5,
    "technical": 4.5,
    "portrait": 3.8
}
```

### Sampling Configuration
```python
# Optimized FLUX sampling parameters
FLUX_SAMPLING_PRESETS = {
    "quality": {
        "steps": 30,
        "max_shift": 1.15,
        "base_shift": 0.5,
        "sampler_name": "euler",
        "scheduler": "simple"
    },
    "balanced": {
        "steps": 20,
        "max_shift": 1.15,
        "base_shift": 0.5,
        "sampler_name": "euler",
        "scheduler": "simple"
    },
    "speed": {
        "steps": 15,
        "max_shift": 1.0,
        "base_shift": 0.5,
        "sampler_name": "euler",
        "scheduler": "simple"
    }
}
```

## Common Use Cases

### Professional Photography
```python
# Corporate headshot with pose control
workflow = flux_client.create_flux_controlnet_workflow(
    prompt="professional corporate headshot, business attire, confident expression, studio lighting, sharp focus",
    control_image_path="corporate_pose.jpg",
    controlnet_type="pose",
    strength=0.9,
    guidance=3.8,
    steps=25,
    precision="fp8_e4m3fn"
)
```

### Architectural Visualization
```python
# Building design with structural control
workflow = flux_client.create_flux_controlnet_workflow(
    prompt="modern minimalist architecture, clean lines, glass and concrete, natural lighting, contemporary design",
    control_image_path="building_structure.jpg",
    controlnet_type="canny",
    strength=0.8,
    guidance=4.0,
    steps=30,
    precision="fp8_e4m3fn"
)
```

### Creative Art Generation
```python
# Artistic interpretation with soft edge control
workflow = flux_client.create_flux_controlnet_workflow(
    prompt="abstract expressionist painting, vibrant colors, dynamic composition, artistic brushstrokes",
    control_image_path="composition_guide.jpg",
    controlnet_type="hed",
    strength=0.7,
    guidance=3.0,
    steps=25,
    precision="fp8_e4m3fn"
)
```

## Performance Optimization

### Memory Management
```python
def optimize_flux_memory(workflow: Dict[str, Any], vram_gb: int) -> Dict[str, Any]:
    """Optimize FLUX workflow for available VRAM"""
    
    if vram_gb <= 8:
        # Use FP8 quantization
        for node in workflow["nodes"]:
            if node["type"] == "flux_model_loader":
                node["data"]["precision"] = "fp8_e4m3fn"
        
        # Reduce batch size
        for node in workflow["nodes"]:
            if node["type"] == "flux_empty_latent":
                node["data"]["batch_size"] = 1
    
    elif vram_gb <= 12:
        # Balanced settings
        for node in workflow["nodes"]:
            if node["type"] == "flux_model_loader":
                node["data"]["precision"] = "fp8_e4m3fn"
    
    else:
        # High quality settings
        for node in workflow["nodes"]:
            if node["type"] == "flux_model_loader":
                node["data"]["precision"] = "original"
    
    return workflow
```

### Batch Processing for FLUX
```python
def create_flux_batch_processor(client, max_concurrent: int = 1):
    """Create optimized batch processor for FLUX workflows"""
    
    class FluxBatchProcessor:
        def __init__(self):
            self.client = client
            self.max_concurrent = max_concurrent  # FLUX uses more VRAM
        
        def process_batch(self, workflows: List[Dict[str, Any]]) -> List[str]:
            session_ids = []
            
            # Process sequentially for memory management
            for i, workflow in enumerate(workflows):
                try:
                    print(f"Processing FLUX workflow {i+1}/{len(workflows)}")
                    session_id = self.client.execute_workflow(workflow)
                    
                    # Wait for completion before starting next
                    result = self.client.wait_for_completion(session_id, timeout=900)
                    session_ids.append(session_id)
                    
                    print(f"FLUX workflow {i+1} completed: {session_id}")
                    
                except Exception as e:
                    print(f"FLUX workflow {i+1} failed: {e}")
            
            return session_ids
    
    return FluxBatchProcessor()
```

## Troubleshooting FLUX Workflows

### Common Issues and Solutions

1. **Out of Memory with FLUX**
```python
# Solution: Use quantization and reduce resolution
workflow["nodes"][0]["data"]["precision"] = "fp8_e4m3fn"
workflow["nodes"][-2]["data"]["width"] = 768
workflow["nodes"][-2]["data"]["height"] = 768
```

2. **Poor ControlNet Effect**
```python
# Solution: Increase strength and adjust guidance
workflow["nodes"][-3]["data"]["strength"] = 0.9
workflow["nodes"][-4]["data"]["guidance"] = 4.0
```

3. **Slow Generation Speed**
```python
# Solution: Reduce steps and use speed preset
workflow["nodes"][-4]["data"]["steps"] = 15
workflow["nodes"][-4]["data"]["max_shift"] = 1.0
```

### Debug Workflow Validator
```python
def validate_flux_workflow(workflow: Dict[str, Any]) -> List[str]:
    """Validate FLUX-specific workflow requirements"""
    
    errors = []
    
    # Check for FLUX-specific nodes
    required_flux_nodes = ["flux_model_loader", "flux_text_encode", "flux_sampler"]
    for node_type in required_flux_nodes:
        if not any(node["type"] == node_type for node in workflow["nodes"]):
            errors.append(f"Missing required FLUX node: {node_type}")
    
    # Check guidance values
    for node in workflow["nodes"]:
        if node["type"] == "flux_text_encode":
            guidance = node["data"].get("guidance", 3.5)
            if not 1.0 <= guidance <= 10.0:
                errors.append(f"FLUX guidance should be 1.0-10.0, got {guidance}")
    
    # Check precision settings
    for node in workflow["nodes"]:
        if node["type"] == "flux_model_loader":
            precision = node["data"].get("precision", "fp8_e4m3fn")
            valid_precisions = ["fp8_e4m3fn", "gguf", "nf4", "original"]
            if precision not in valid_precisions:
                errors.append(f"Invalid FLUX precision: {precision}")
    
    return errors
```
