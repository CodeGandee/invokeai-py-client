# SDXL Text-to-Image

Complete example of generating images with Stable Diffusion XL.

## Quick Start

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# Initialize client
client = InvokeAIClient(base_url="http://localhost:9090")

# Load SDXL workflow
workflow_path = "data/workflows/sdxl_text_to_image.json"
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file(workflow_path)
)

# Sync models to server
wf.sync_dnn_model(by_name=True, by_base=True)

# Set generation parameters
wf.get_input_value(0).value = "A majestic mountain landscape at sunset, highly detailed, 8k"
wf.get_input_value(1).value = "blurry, low quality, distorted"
wf.get_input_value(2).value = 42  # seed
wf.get_input_value(3).value = 30  # steps
wf.get_input_value(4).value = 7.0  # cfg_scale
wf.get_input_value(5).value = 1024  # width
wf.get_input_value(6).value = 1024  # height

# Generate image
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(submission)

# Get output
images = wf.map_outputs_to_images(result)
print(f"Generated: {images[0]}")
```

## Complete Implementation

### Full SDXL Pipeline

```python
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

class SDXLGenerator:
    """SDXL text-to-image generator."""
    
    def __init__(self, client: InvokeAIClient, workflow_path: str):
        self.client = client
        self.workflow_path = workflow_path
        self.wf = None
        self.setup_workflow()
    
    def setup_workflow(self):
        """Initialize and configure workflow."""
        # Load workflow definition
        self.wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file(self.workflow_path)
        )
        
        # Sync models
        print("Syncing models...")
        changes = self.wf.sync_dnn_model(by_name=True, by_base=True)
        if changes:
            print(f"Synced {len(changes)} model fields")
        
        # Set default parameters
        self.set_defaults()
    
    def set_defaults(self):
        """Set default generation parameters."""
        # Find input indices by label
        inputs = self.wf.list_inputs()
        self.input_map = {inp.label: inp.input_index for inp in inputs}
        
        # Set defaults
        if "Positive Prompt" in self.input_map:
            self.wf.get_input_value(self.input_map["Positive Prompt"]).value = ""
        if "Negative Prompt" in self.input_map:
            self.wf.get_input_value(self.input_map["Negative Prompt"]).value = (
                "blurry, low quality, distorted, deformed"
            )
        if "Seed" in self.input_map:
            self.wf.get_input_value(self.input_map["Seed"]).value = -1  # Random
        if "Steps" in self.input_map:
            self.wf.get_input_value(self.input_map["Steps"]).value = 30
        if "CFG Scale" in self.input_map:
            self.wf.get_input_value(self.input_map["CFG Scale"]).value = 7.0
        if "Width" in self.input_map:
            self.wf.get_input_value(self.input_map["Width"]).value = 1024
        if "Height" in self.input_map:
            self.wf.get_input_value(self.input_map["Height"]).value = 1024
        if "Board" in self.input_map:
            self.wf.get_input_value(self.input_map["Board"]).value = "sdxl_outputs"
    
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        seed: int = -1,
        steps: int = 30,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024,
        scheduler: str = "euler",
        board: str = "sdxl_outputs"
    ) -> List[str]:
        """Generate image from text prompt."""
        # Set parameters
        if "Positive Prompt" in self.input_map:
            self.wf.get_input_value(self.input_map["Positive Prompt"]).value = prompt
        
        if negative_prompt and "Negative Prompt" in self.input_map:
            self.wf.get_input_value(self.input_map["Negative Prompt"]).value = negative_prompt
        
        if "Seed" in self.input_map:
            self.wf.get_input_value(self.input_map["Seed"]).value = seed
        
        if "Steps" in self.input_map:
            self.wf.get_input_value(self.input_map["Steps"]).value = steps
        
        if "CFG Scale" in self.input_map:
            self.wf.get_input_value(self.input_map["CFG Scale"]).value = cfg_scale
        
        if "Width" in self.input_map:
            self.wf.get_input_value(self.input_map["Width"]).value = width
        
        if "Height" in self.input_map:
            self.wf.get_input_value(self.input_map["Height"]).value = height
        
        if "Scheduler" in self.input_map:
            self.wf.get_input_value(self.input_map["Scheduler"]).value = scheduler
        
        if "Board" in self.input_map:
            self.wf.get_input_value(self.input_map["Board"]).value = board
        
        # Submit workflow
        print(f"Generating: {prompt[:50]}...")
        submission = self.wf.submit_sync()
        
        # Wait for completion
        result = self.wf.wait_for_completion_sync(submission, timeout=120)
        
        # Extract images
        if result['status'] == 'COMPLETED':
            images = self.wf.map_outputs_to_images(result)
            print(f"Generated {len(images)} image(s)")
            return images
        else:
            print(f"Generation failed: {result['status']}")
            return []
    
    def batch_generate(self, prompts: List[str], **kwargs) -> Dict[str, List[str]]:
        """Generate images for multiple prompts."""
        results = {}
        
        for i, prompt in enumerate(prompts):
            print(f"\nBatch {i+1}/{len(prompts)}")
            images = self.generate(prompt, **kwargs)
            results[prompt] = images
        
        return results

# Use the generator
client = InvokeAIClient()
generator = SDXLGenerator(client, "data/workflows/sdxl_text_to_image.json")

# Single generation
images = generator.generate(
    prompt="A futuristic city with flying cars, cyberpunk style, neon lights",
    negative_prompt="blurry, low quality",
    seed=42,
    steps=35,
    cfg_scale=7.5
)

# Batch generation
prompts = [
    "A serene Japanese garden with cherry blossoms",
    "A steampunk airship floating above clouds",
    "An underwater coral reef teeming with colorful fish"
]

batch_results = generator.batch_generate(
    prompts,
    steps=30,
    cfg_scale=7.0,
    width=1024,
    height=1024
)

for prompt, images in batch_results.items():
    print(f"{prompt[:30]}: {len(images)} images")
```

## Advanced Features

### With LoRA Support

```python
class SDXLWithLoRA(SDXLGenerator):
    """SDXL generator with LoRA support."""
    
    def apply_lora(self, lora_name: str, weight: float = 1.0):
        """Apply LoRA to the workflow."""
        # Find LoRA field
        for inp in self.wf.list_inputs():
            if "lora" in inp.label.lower():
                field = self.wf.get_input_value(inp.input_index)
                if hasattr(field, 'key'):
                    field.key = lora_name
                    field.name = lora_name
                    if hasattr(field, 'weight'):
                        field.weight = weight
                    print(f"Applied LoRA: {lora_name} (weight: {weight})")
                    return True
        
        print("No LoRA field found in workflow")
        return False
    
    def generate_with_lora(
        self,
        prompt: str,
        lora_name: str,
        lora_weight: float = 0.8,
        **kwargs
    ) -> List[str]:
        """Generate with LoRA applied."""
        self.apply_lora(lora_name, lora_weight)
        return self.generate(prompt, **kwargs)

# Use with LoRA
generator = SDXLWithLoRA(client, "data/workflows/sdxl_with_lora.json")

images = generator.generate_with_lora(
    prompt="Portrait in anime style",
    lora_name="anime-style-xl",
    lora_weight=0.7,
    negative_prompt="realistic, photographic",
    steps=30
)
```

### Style Presets

```python
class SDXLStyled(SDXLGenerator):
    """SDXL with style presets."""
    
    STYLES = {
        "photorealistic": {
            "positive_suffix": ", photorealistic, high detail, sharp focus, 8k, professional photography",
            "negative": "cartoon, anime, illustration, painting, drawing",
            "cfg_scale": 7.5
        },
        "anime": {
            "positive_suffix": ", anime style, manga, illustration, detailed",
            "negative": "photorealistic, 3d render, photograph",
            "cfg_scale": 10.0
        },
        "oil_painting": {
            "positive_suffix": ", oil painting, classical art, brush strokes, canvas texture",
            "negative": "digital art, photograph, 3d render",
            "cfg_scale": 8.0
        },
        "watercolor": {
            "positive_suffix": ", watercolor painting, soft colors, artistic",
            "negative": "photograph, digital art, 3d render",
            "cfg_scale": 9.0
        },
        "cyberpunk": {
            "positive_suffix": ", cyberpunk style, neon lights, futuristic, high tech",
            "negative": "medieval, rustic, natural",
            "cfg_scale": 7.0
        }
    }
    
    def generate_styled(
        self,
        prompt: str,
        style: str = "photorealistic",
        **kwargs
    ) -> List[str]:
        """Generate with style preset."""
        if style not in self.STYLES:
            print(f"Unknown style: {style}, using photorealistic")
            style = "photorealistic"
        
        style_config = self.STYLES[style]
        
        # Apply style
        styled_prompt = prompt + style_config["positive_suffix"]
        kwargs['negative_prompt'] = kwargs.get('negative_prompt', '') + ", " + style_config["negative"]
        kwargs['cfg_scale'] = kwargs.get('cfg_scale', style_config["cfg_scale"])
        
        print(f"Applying style: {style}")
        return self.generate(styled_prompt, **kwargs)

# Use styled generator
generator = SDXLStyled(client, "data/workflows/sdxl_text_to_image.json")

# Generate with different styles
for style in ["photorealistic", "anime", "oil_painting"]:
    images = generator.generate_styled(
        prompt="A majestic dragon",
        style=style,
        seed=42  # Same seed for comparison
    )
    print(f"Generated {style}: {images}")
```

## Prompt Engineering

### Enhanced Prompting

```python
class PromptEnhancer:
    """Enhance prompts for better SDXL results."""
    
    def __init__(self):
        self.quality_tags = [
            "masterpiece", "best quality", "highly detailed",
            "ultra-detailed", "8k", "high resolution"
        ]
        
        self.lighting_tags = [
            "perfect lighting", "dramatic lighting", "cinematic lighting",
            "natural lighting", "studio lighting"
        ]
        
        self.composition_tags = [
            "perfect composition", "rule of thirds", "golden ratio",
            "centered", "symmetrical"
        ]
    
    def enhance(
        self,
        prompt: str,
        add_quality: bool = True,
        add_lighting: bool = True,
        add_composition: bool = False,
        custom_tags: List[str] = None
    ) -> str:
        """Enhance prompt with quality tags."""
        enhanced = prompt
        
        tags = []
        
        if add_quality:
            tags.extend(self.quality_tags[:3])
        
        if add_lighting:
            tags.append(self.lighting_tags[0])
        
        if add_composition:
            tags.append(self.composition_tags[0])
        
        if custom_tags:
            tags.extend(custom_tags)
        
        if tags:
            enhanced = f"{prompt}, {', '.join(tags)}"
        
        return enhanced
    
    def build_negative(self, base_negative: str = "") -> str:
        """Build comprehensive negative prompt."""
        default_negative = [
            "low quality", "worst quality", "blurry", "distorted",
            "deformed", "disfigured", "bad anatomy", "wrong anatomy",
            "mutation", "mutated", "ugly", "duplicate", "morbid",
            "out of frame", "extra limbs", "malformed limbs",
            "poorly drawn hands", "poorly drawn face", "jpeg artifacts"
        ]
        
        if base_negative:
            return f"{base_negative}, {', '.join(default_negative[:10])}"
        
        return ", ".join(default_negative[:10])

# Use prompt enhancer
enhancer = PromptEnhancer()
generator = SDXLGenerator(client, "data/workflows/sdxl_text_to_image.json")

enhanced_prompt = enhancer.enhance(
    "A magical forest with glowing mushrooms",
    add_quality=True,
    add_lighting=True,
    custom_tags=["fantasy art", "enchanted"]
)

negative_prompt = enhancer.build_negative()

images = generator.generate(
    prompt=enhanced_prompt,
    negative_prompt=negative_prompt,
    steps=35,
    cfg_scale=7.5
)
```

## Integration Example

### Complete Application

```python
def main():
    """Complete SDXL application example."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SDXL Image Generator")
    parser.add_argument("prompt", help="Text prompt for generation")
    parser.add_argument("--negative", default="", help="Negative prompt")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed")
    parser.add_argument("--steps", type=int, default=30, help="Inference steps")
    parser.add_argument("--cfg", type=float, default=7.0, help="CFG scale")
    parser.add_argument("--width", type=int, default=1024, help="Image width")
    parser.add_argument("--height", type=int, default=1024, help="Image height")
    parser.add_argument("--style", default="photorealistic", help="Style preset")
    parser.add_argument("--output", default="output.png", help="Output filename")
    
    args = parser.parse_args()
    
    # Initialize
    client = InvokeAIClient()
    generator = SDXLStyled(client, "data/workflows/sdxl_text_to_image.json")
    
    # Generate
    print(f"Generating: {args.prompt}")
    images = generator.generate_styled(
        prompt=args.prompt,
        style=args.style,
        negative_prompt=args.negative,
        seed=args.seed,
        steps=args.steps,
        cfg_scale=args.cfg,
        width=args.width,
        height=args.height
    )
    
    if images:
        # Download result
        board = client.board_repo.get_board_handle("sdxl_outputs")
        image_data = board.download_image(images[0], full_resolution=True)
        
        # Save to file
        with open(args.output, "wb") as f:
            f.write(image_data)
        
        print(f"Saved to: {args.output}")
    else:
        print("Generation failed")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Next Steps

- Try [FLUX Image-to-Image](flux-image-to-image.md) for image editing
- Explore [Multi-Stage Refine](multi-stage-refine.md) for quality enhancement
- See [Raw API](raw-api.md) for custom implementations
- Review [Workflow Basics](../user-guide/workflow-basics.md) for fundamentals