# FLUX Image-to-Image

Advanced image editing and transformation using FLUX models.

## Quick Start

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# Initialize client
client = InvokeAIClient(base_url="http://localhost:9090")

# Upload source image
board = client.board_repo.get_board_handle("flux_inputs")
source_image = board.upload_image_file("source.png")

# Load FLUX img2img workflow
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/flux_img2img.json")
)

# Sync models
wf.sync_dnn_model(by_name=True, by_base=True)

# Set parameters
wf.get_input_value(0).value = source_image  # Source image
wf.get_input_value(1).value = "Transform into cyberpunk style with neon lights"
wf.get_input_value(2).value = 0.75  # Denoising strength
wf.get_input_value(3).value = 4  # Steps (FLUX is fast)
wf.get_input_value(4).value = 3.5  # CFG scale

# Generate
submission = wf.submit_sync()
result = wf.wait_for_completion_sync(submission)
images = wf.map_outputs_to_images(result)
print(f"Transformed: {images[0]}")
```

## Complete Implementation

### FLUX Image-to-Image Pipeline

```python
from typing import Optional, List, Dict, Any
from PIL import Image
import io

class FLUXImageToImage:
    """FLUX image-to-image transformation."""
    
    def __init__(self, client: InvokeAIClient, workflow_path: str):
        self.client = client
        self.workflow_path = workflow_path
        self.wf = None
        self.input_board = None
        self.output_board = "flux_outputs"
        self.setup()
    
    def setup(self):
        """Initialize workflow and boards."""
        # Create workflow
        self.wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file(self.workflow_path)
        )
        
        # Sync FLUX models
        print("Syncing FLUX models...")
        self.wf.sync_dnn_model(by_name=True, by_base=True)
        
        # Setup boards
        self.input_board = self.client.board_repo.get_board_handle("flux_inputs")
        
        # Map inputs
        inputs = self.wf.list_inputs()
        self.input_map = {inp.label: inp.input_index for inp in inputs}
    
    def transform_image(
        self,
        source_path: str,
        prompt: str,
        negative_prompt: str = "",
        denoising_strength: float = 0.75,
        steps: int = 4,
        cfg_scale: float = 3.5,
        seed: int = -1
    ) -> List[str]:
        """Transform image with FLUX."""
        # Upload source image
        print(f"Uploading: {source_path}")
        source_name = self.input_board.upload_image_file(source_path)
        
        # Set parameters
        if "Image" in self.input_map:
            self.wf.get_input_value(self.input_map["Image"]).value = source_name
        
        if "Prompt" in self.input_map:
            self.wf.get_input_value(self.input_map["Prompt"]).value = prompt
        
        if "Negative Prompt" in self.input_map:
            self.wf.get_input_value(self.input_map["Negative Prompt"]).value = negative_prompt
        
        if "Denoising Strength" in self.input_map:
            self.wf.get_input_value(self.input_map["Denoising Strength"]).value = denoising_strength
        
        if "Steps" in self.input_map:
            self.wf.get_input_value(self.input_map["Steps"]).value = steps
        
        if "CFG Scale" in self.input_map:
            self.wf.get_input_value(self.input_map["CFG Scale"]).value = cfg_scale
        
        if "Seed" in self.input_map:
            self.wf.get_input_value(self.input_map["Seed"]).value = seed
        
        if "Board" in self.input_map:
            self.wf.get_input_value(self.input_map["Board"]).value = self.output_board
        
        # Submit
        print(f"Transforming with prompt: {prompt[:50]}...")
        submission = self.wf.submit_sync()
        result = self.wf.wait_for_completion_sync(submission, timeout=60)
        
        if result['status'] == 'COMPLETED':
            images = self.wf.map_outputs_to_images(result)
            print(f"Generated {len(images)} transformed image(s)")
            return images
        else:
            print(f"Transformation failed: {result['status']}")
            return []

# Use the transformer
client = InvokeAIClient()
flux = FLUXImageToImage(client, "data/workflows/flux_img2img.json")

transformed = flux.transform_image(
    source_path="original.png",
    prompt="cyberpunk style, neon lights, futuristic",
    denoising_strength=0.7,
    steps=4
)
```

## Advanced Techniques

### Style Transfer

```python
class FLUXStyleTransfer(FLUXImageToImage):
    """FLUX-based style transfer."""
    
    STYLE_PROMPTS = {
        "anime": "anime style, manga illustration, cel shading",
        "oil_painting": "oil painting, thick brushstrokes, impressionist",
        "watercolor": "watercolor painting, soft edges, artistic",
        "sketch": "pencil sketch, line art, hand drawn",
        "3d_render": "3D render, CGI, photorealistic 3D",
        "pixel_art": "pixel art, 8-bit style, retro game graphics",
        "comic": "comic book style, bold outlines, vibrant colors"
    }
    
    def style_transfer(
        self,
        source_path: str,
        style: str,
        strength: float = 0.6,
        preserve_content: bool = True
    ) -> List[str]:
        """Apply style transfer to image."""
        if style not in self.STYLE_PROMPTS:
            raise ValueError(f"Unknown style: {style}")
        
        prompt = self.STYLE_PROMPTS[style]
        
        if preserve_content:
            # Lower strength to preserve more content
            strength = min(strength, 0.5)
            prompt = f"[preserve content] {prompt}"
        
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=strength,
            steps=6,  # More steps for style transfer
            cfg_scale=4.0
        )
    
    def multi_style_blend(
        self,
        source_path: str,
        styles: List[str],
        weights: Optional[List[float]] = None
    ) -> List[str]:
        """Blend multiple styles."""
        if not weights:
            weights = [1.0 / len(styles)] * len(styles)
        
        # Build weighted prompt
        prompt_parts = []
        for style, weight in zip(styles, weights):
            if style in self.STYLE_PROMPTS:
                weighted = f"({self.STYLE_PROMPTS[style]}:{weight:.2f})"
                prompt_parts.append(weighted)
        
        combined_prompt = ", ".join(prompt_parts)
        
        return self.transform_image(
            source_path=source_path,
            prompt=combined_prompt,
            denoising_strength=0.7,
            steps=8
        )

# Apply style transfer
transfer = FLUXStyleTransfer(client, "data/workflows/flux_img2img.json")

# Single style
anime_version = transfer.style_transfer(
    "portrait.jpg",
    style="anime",
    strength=0.6
)

# Blended styles
blended = transfer.multi_style_blend(
    "landscape.jpg",
    styles=["watercolor", "impressionist"],
    weights=[0.7, 0.3]
)
```

### Image Enhancement

```python
class FLUXEnhancer(FLUXImageToImage):
    """FLUX-based image enhancement."""
    
    def upscale(
        self,
        source_path: str,
        scale_factor: int = 2,
        enhance_details: bool = True
    ) -> List[str]:
        """Upscale and enhance image."""
        # Prepare upscaling prompt
        prompt = "high resolution, ultra detailed, sharp focus, 4K quality"
        
        if enhance_details:
            prompt += ", enhanced details, refined textures"
        
        # Lower denoising for upscaling
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=0.3,
            steps=6,
            cfg_scale=2.0
        )
    
    def restore_old_photo(
        self,
        source_path: str,
        restoration_level: str = "moderate"
    ) -> List[str]:
        """Restore old or damaged photos."""
        levels = {
            "light": (0.3, "light restoration, preserve original"),
            "moderate": (0.5, "restore photo, fix damage, enhance clarity"),
            "heavy": (0.7, "full restoration, reconstruct missing parts")
        }
        
        strength, prompt = levels.get(restoration_level, levels["moderate"])
        
        full_prompt = f"{prompt}, restored photograph, clear details, fixed colors"
        
        return self.transform_image(
            source_path=source_path,
            prompt=full_prompt,
            negative_prompt="blurry, damaged, artifacts, noise",
            denoising_strength=strength,
            steps=8,
            cfg_scale=3.5
        )
    
    def colorize_bw(self, source_path: str) -> List[str]:
        """Colorize black and white images."""
        return self.transform_image(
            source_path=source_path,
            prompt="colorized photograph, natural colors, realistic coloring",
            negative_prompt="black and white, grayscale, monochrome",
            denoising_strength=0.6,
            steps=6,
            cfg_scale=4.0
        )

# Use enhancer
enhancer = FLUXEnhancer(client, "data/workflows/flux_img2img.json")

# Upscale image
upscaled = enhancer.upscale("low_res.jpg", scale_factor=2)

# Restore old photo
restored = enhancer.restore_old_photo("old_photo.jpg", "moderate")

# Colorize B&W
colorized = enhancer.colorize_bw("bw_photo.jpg")
```

### Creative Edits

```python
class FLUXCreativeEditor(FLUXImageToImage):
    """Creative image editing with FLUX."""
    
    def change_season(
        self,
        source_path: str,
        target_season: str
    ) -> List[str]:
        """Change season in landscape images."""
        seasons = {
            "spring": "spring season, blooming flowers, green leaves, bright",
            "summer": "summer season, lush green, bright sunshine, vibrant",
            "autumn": "autumn season, fall colors, orange leaves, golden hour",
            "winter": "winter season, snow covered, frost, cold atmosphere"
        }
        
        prompt = seasons.get(target_season, seasons["spring"])
        
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=0.6,
            steps=6
        )
    
    def change_time_of_day(
        self,
        source_path: str,
        target_time: str
    ) -> List[str]:
        """Change time of day in images."""
        times = {
            "dawn": "dawn lighting, sunrise, soft morning light, golden",
            "morning": "morning light, bright daylight, clear skies",
            "noon": "midday sun, harsh shadows, bright lighting",
            "evening": "evening light, sunset, warm colors, golden hour",
            "night": "night time, dark sky, moonlight, stars, city lights"
        }
        
        prompt = times.get(target_time, times["morning"])
        
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=0.5,
            steps=5
        )
    
    def add_weather_effects(
        self,
        source_path: str,
        weather: str
    ) -> List[str]:
        """Add weather effects to images."""
        effects = {
            "rain": "heavy rain, wet surfaces, rain drops, moody",
            "snow": "snowing, snow falling, winter weather, white",
            "fog": "foggy, misty, low visibility, atmospheric",
            "storm": "stormy weather, dark clouds, lightning, dramatic"
        }
        
        prompt = effects.get(weather, effects["rain"])
        
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=0.4,
            steps=5
        )

# Creative edits
editor = FLUXCreativeEditor(client, "data/workflows/flux_img2img.json")

# Change season
winter_scene = editor.change_season("summer_landscape.jpg", "winter")

# Change time
night_version = editor.change_time_of_day("day_scene.jpg", "night")

# Add weather
rainy = editor.add_weather_effects("street.jpg", "rain")
```

## Batch Processing

### Batch Transformation

```python
class FLUXBatchProcessor(FLUXImageToImage):
    """Batch image processing with FLUX."""
    
    def batch_transform(
        self,
        image_paths: List[str],
        prompts: List[str],
        common_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """Transform multiple images."""
        if len(prompts) == 1:
            # Use same prompt for all
            prompts = prompts * len(image_paths)
        elif len(prompts) != len(image_paths):
            raise ValueError("Prompts count must match images or be 1")
        
        params = common_params or {}
        results = {}
        
        for i, (path, prompt) in enumerate(zip(image_paths, prompts)):
            print(f"\nProcessing {i+1}/{len(image_paths)}: {path}")
            
            images = self.transform_image(
                source_path=path,
                prompt=prompt,
                **params
            )
            
            results[path] = images
        
        return results
    
    def batch_style_variations(
        self,
        source_path: str,
        styles: List[str],
        strengths: Optional[List[float]] = None
    ) -> Dict[str, List[str]]:
        """Generate style variations of single image."""
        if not strengths:
            strengths = [0.6] * len(styles)
        
        results = {}
        
        for style, strength in zip(styles, strengths):
            print(f"\nApplying style: {style}")
            
            images = self.transform_image(
                source_path=source_path,
                prompt=style,
                denoising_strength=strength,
                steps=5
            )
            
            results[style] = images
        
        return results

# Batch processing
batch_processor = FLUXBatchProcessor(client, "data/workflows/flux_img2img.json")

# Transform multiple images
image_files = ["img1.jpg", "img2.jpg", "img3.jpg"]
prompts = ["cyberpunk style", "watercolor painting", "anime illustration"]

batch_results = batch_processor.batch_transform(
    image_files,
    prompts,
    common_params={"denoising_strength": 0.7, "steps": 5}
)

# Generate variations
variations = batch_processor.batch_style_variations(
    "portrait.jpg",
    styles=["oil painting", "pencil sketch", "pop art"],
    strengths=[0.6, 0.5, 0.7]
)
```

## Image Inpainting

### FLUX Inpainting

```python
class FLUXInpainting(FLUXImageToImage):
    """FLUX-based inpainting and object removal."""
    
    def prepare_mask(
        self,
        image_path: str,
        mask_path: str
    ) -> tuple[str, str]:
        """Prepare image and mask for inpainting."""
        # Upload image
        image_name = self.input_board.upload_image_file(image_path)
        
        # Upload mask
        mask_name = self.input_board.upload_image_file(mask_path)
        
        return image_name, mask_name
    
    def inpaint(
        self,
        image_path: str,
        mask_path: str,
        prompt: str,
        preserve_unmasked: bool = True
    ) -> List[str]:
        """Inpaint masked areas."""
        image_name, mask_name = self.prepare_mask(image_path, mask_path)
        
        # Set image and mask
        if "Image" in self.input_map:
            self.wf.get_input_value(self.input_map["Image"]).value = image_name
        
        if "Mask" in self.input_map:
            self.wf.get_input_value(self.input_map["Mask"]).value = mask_name
        
        # Inpainting prompt
        full_prompt = prompt
        if preserve_unmasked:
            full_prompt = f"[preserve unmasked] {prompt}"
        
        return self.transform_image(
            source_path=image_path,  # Already uploaded
            prompt=full_prompt,
            denoising_strength=1.0,  # Full denoising for masked area
            steps=8
        )
    
    def remove_object(
        self,
        image_path: str,
        mask_path: str
    ) -> List[str]:
        """Remove object using inpainting."""
        return self.inpaint(
            image_path=image_path,
            mask_path=mask_path,
            prompt="background, seamless removal, natural continuation",
            preserve_unmasked=True
        )
    
    def replace_object(
        self,
        image_path: str,
        mask_path: str,
        replacement: str
    ) -> List[str]:
        """Replace masked object with something else."""
        return self.inpaint(
            image_path=image_path,
            mask_path=mask_path,
            prompt=f"{replacement}, perfectly integrated, matching lighting",
            preserve_unmasked=True
        )

# Inpainting
inpainter = FLUXInpainting(client, "data/workflows/flux_inpaint.json")

# Remove object
cleaned = inpainter.remove_object("photo.jpg", "object_mask.png")

# Replace object
replaced = inpainter.replace_object(
    "room.jpg",
    "furniture_mask.png",
    "modern sofa"
)
```

## Performance Optimization

### Optimized FLUX Pipeline

```python
class OptimizedFLUX(FLUXImageToImage):
    """Performance-optimized FLUX processing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_cache = {}
        self.model_loaded = False
    
    def ensure_model_loaded(self):
        """Ensure FLUX model is loaded."""
        if not self.model_loaded:
            # Warm up model
            print("Warming up FLUX model...")
            self.wf.sync_dnn_model(by_name=True, by_base=True)
            self.model_loaded = True
    
    def cached_upload(self, source_path: str) -> str:
        """Upload with caching."""
        if source_path in self.image_cache:
            return self.image_cache[source_path]
        
        image_name = self.input_board.upload_image_file(source_path)
        self.image_cache[source_path] = image_name
        return image_name
    
    def fast_transform(
        self,
        source_path: str,
        prompt: str
    ) -> List[str]:
        """Optimized fast transformation."""
        self.ensure_model_loaded()
        
        # Use cached upload
        source_name = self.cached_upload(source_path)
        
        # Minimal steps for speed
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=0.5,
            steps=2,  # Ultra fast
            cfg_scale=1.0  # Low CFG for speed
        )
    
    def quality_transform(
        self,
        source_path: str,
        prompt: str
    ) -> List[str]:
        """High quality transformation."""
        self.ensure_model_loaded()
        
        return self.transform_image(
            source_path=source_path,
            prompt=prompt,
            denoising_strength=0.7,
            steps=10,  # More steps for quality
            cfg_scale=5.0  # Higher CFG for adherence
        )

# Optimized usage
opt_flux = OptimizedFLUX(client, "data/workflows/flux_img2img.json")

# Fast preview
preview = opt_flux.fast_transform("input.jpg", "artistic style")

# High quality final
final = opt_flux.quality_transform("input.jpg", "artistic style")
```

## Integration Example

### Complete FLUX Application

```python
def main():
    """Complete FLUX img2img application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FLUX Image Transformer")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("prompt", help="Transformation prompt")
    parser.add_argument("--strength", type=float, default=0.7)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--cfg", type=float, default=3.5)
    parser.add_argument("--style", help="Apply style preset")
    parser.add_argument("--output", default="flux_output.png")
    
    args = parser.parse_args()
    
    # Initialize
    client = InvokeAIClient()
    
    if args.style:
        # Use style transfer
        flux = FLUXStyleTransfer(client, "data/workflows/flux_img2img.json")
        images = flux.style_transfer(
            args.input,
            style=args.style,
            strength=args.strength
        )
    else:
        # Regular transformation
        flux = FLUXImageToImage(client, "data/workflows/flux_img2img.json")
        images = flux.transform_image(
            args.input,
            prompt=args.prompt,
            denoising_strength=args.strength,
            steps=args.steps,
            cfg_scale=args.cfg
        )
    
    if images:
        # Download and save
        board = client.board_repo.get_board_handle("flux_outputs")
        image_data = board.download_image(images[0], full_resolution=True)
        
        with open(args.output, "wb") as f:
            f.write(image_data)
        
        print(f"Saved to: {args.output}")
    else:
        print("Transformation failed")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Next Steps

- Explore [SDXL Text-to-Image](sdxl-text-to-image.md) for generation
- Try [Multi-Stage Refine](multi-stage-refine.md) for enhancement
- See [Raw API](raw-api.md) for custom implementations
- Review [Image Operations](../user-guide/images.md) for management