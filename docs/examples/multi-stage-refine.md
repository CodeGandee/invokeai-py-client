# Multi-Stage Refine

Advanced techniques for progressive image enhancement using multiple refinement stages. This guide explains how to organize your workflows, which inputs to expose in the GUI Form, how indices are used, and how to run multi-stage pipelines reliably.

## What you'll learn

- Compose a multi-stage pipeline (base → refine → upscale) using multiple exported workflows and one Python script.
- Discover Form-exposed inputs by index and set them type-safely.
- Submit synchronously and wait for completion (blocking mode).
- Map output nodes to produced image filenames and download results.
- Manage index drift across GUI edits.

## Prerequisites

- InvokeAI server running at http://localhost:9090 (adjust as needed).
- Exported workflow JSONs, e.g.:
  - data/workflows/sdxl_base.json
  - data/workflows/sdxl_refiner.json
  - data/workflows/esrgan_upscale.json
- The Form in each workflow contains the inputs you intend to control.

Tip: Indices are the stable API only relative to the current Form tree. If you change Form layout (add/remove/reorder), re-list inputs and update your index constants.

## Form requirements (GUI)

Place representative fields into the Form before export:
- Base (txt2img): Positive Prompt, Negative Prompt, Seed, Steps, CFG, Width, Height, Board (for final image node)
- Refiner: Image (input from base), Prompts, Refinement Steps, Strength, CFG, Board
- Upscale: Image, Scale, Model choice (optional), Board

Labels are not guaranteed unique or present. The input index (depth-first pre-order over the Form tree) is the stable handle.

## Inspect input indices (optional)

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

client = InvokeAIClient.from_url("http://localhost:9090")

# Example: inspect the base workflow's inputs
base = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/sdxl_base.json")
)
for inp in base.list_inputs():
    print(f"[{inp.input_index:02d}] {inp.label or inp.field_name} :: {type(inp.field).__name__}")
```

Record the indices you will use in your script.

## Quick Start

```python
from invokeai_py_client import InvokeAIClient
from invokeai_py_client.workflow import WorkflowDefinition

# 1) Initialize client (URL helper parses host/port/base_path)
client = InvokeAIClient.from_url("http://localhost:9090")

# 2) Load a multi-stage workflow (single JSON that encapsulates refine stages)
wf = client.workflow_repo.create_workflow(
    WorkflowDefinition.from_file("data/workflows/sdxl_with_refiner.json")
)

# 3) Normalize model identifier fields against server inventory
wf.sync_dnn_model(by_name=True, by_base=True)

# 4) Set inputs by index (indices discovered via list_inputs(); adjust to your Form)
wf.get_input_value(0).value = "Epic landscape with mountains and lakes, highly detailed"
wf.get_input_value(1).value = "blurry, low quality"
wf.get_input_value(2).value = 42    # Seed
wf.get_input_value(3).value = 30    # Base steps
wf.get_input_value(4).value = 15    # Refiner steps
wf.get_input_value(5).value = 0.8   # Switch point / handoff (if applicable)
# Optionally set a Board field if exposed:
# wf.get_input_value(BOARD_INDEX).value = "none"  # uncategorized

# 5) Submit and wait (blocking)
wf.submit_sync()
result = wf.wait_for_completion_sync(timeout=240)
print("Final status:", result.get("status"))

# 6) Map outputs (node -> image filenames)
for m in wf.map_outputs_to_images(result):
    print(f"node={m['node_id'][:8]} board={m.get('board_id')} images={m.get('image_names', [])}")
```

## How it works

1) Each exported workflow JSON is immutable. The client copies it and substitutes only values for inputs you set.
2) Inputs are discovered by a depth-first traversal of the Form tree; the index ordering is the public, stable API.
3) submit_sync() enqueues; wait_for_completion_sync() polls until a terminal status or timeout.
4) map_outputs_to_images() correlates output-capable nodes to their produced image names and board destinations.

## Common pitfalls

- Using labels/names instead of indices. Indices are the stable contract.
- Not exposing a Board field in the Form for outputs: you then cannot dynamically route images; ensure default board is valid in the JSON.
- Expecting wait_for_completion_sync() to take a submission parameter: it does not—call it after submit_sync() with an optional timeout.
- Assuming refiner/upscale stages use the same indices as base: indices are per-workflow and depend on each Form's structure.


## Complete Implementation

### Multi-Stage Refiner Pipeline

```python
from typing import Optional, List, Dict, Any, Tuple
import json

class MultiStageRefiner:
    """Multi-stage image refinement pipeline."""
    
    def __init__(self, client: InvokeAIClient):
        self.client = client
        self.base_wf = None
        self.refiner_wf = None
        self.upscale_wf = None
        self.setup_workflows()
    
    def setup_workflows(self):
        """Setup all workflow stages."""
        # Base generation
        self.base_wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file("data/workflows/sdxl_base.json")
        )
        self.base_wf.sync_dnn_model(by_name=True, by_base=True)
        
        # Refinement stage
        self.refiner_wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file("data/workflows/sdxl_refiner.json")
        )
        self.refiner_wf.sync_dnn_model(by_name=True, by_base=True)
        
        # Upscaling stage
        self.upscale_wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file("data/workflows/esrgan_upscale.json")
        )
    
    def generate_base(
        self,
        prompt: str,
        negative_prompt: str = "",
        seed: int = -1,
        steps: int = 30,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate base image."""
        print("Stage 1: Base generation...")
        
        # Set parameters
        self.base_wf.get_input_value(0).value = prompt
        self.base_wf.get_input_value(1).value = negative_prompt
        self.base_wf.get_input_value(2).value = seed
        self.base_wf.get_input_value(3).value = steps
        self.base_wf.get_input_value(4).value = cfg_scale
        self.base_wf.get_input_value(5).value = width
        self.base_wf.get_input_value(6).value = height
        self.base_wf.get_input_value(7).value = "base_stage"  # board
        
        # Generate
        submission = self.base_wf.submit_sync()
        result = self.base_wf.wait_for_completion_sync(submission)
        
        if result['status'] == 'COMPLETED':
            images = self.base_wf.map_outputs_to_images(result)
            if images:
                return images[0], result
        
        return None, result
    
    def refine_image(
        self,
        base_image: str,
        prompt: str,
        negative_prompt: str = "",
        refiner_steps: int = 15,
        refiner_strength: float = 0.3,
        cfg_scale: float = 7.0
    ) -> Tuple[str, Dict[str, Any]]:
        """Refine base image."""
        print("Stage 2: Refinement...")
        
        # Set parameters
        self.refiner_wf.get_input_value(0).value = base_image
        self.refiner_wf.get_input_value(1).value = prompt
        self.refiner_wf.get_input_value(2).value = negative_prompt
        self.refiner_wf.get_input_value(3).value = refiner_steps
        self.refiner_wf.get_input_value(4).value = refiner_strength
        self.refiner_wf.get_input_value(5).value = cfg_scale
        self.refiner_wf.get_input_value(6).value = "refined_stage"
        
        # Refine
        submission = self.refiner_wf.submit_sync()
        result = self.refiner_wf.wait_for_completion_sync(submission)
        
        if result['status'] == 'COMPLETED':
            images = self.refiner_wf.map_outputs_to_images(result)
            if images:
                return images[0], result
        
        return None, result
    
    def upscale_image(
        self,
        image: str,
        scale: int = 2,
        model: str = "RealESRGAN_x4plus"
    ) -> Tuple[str, Dict[str, Any]]:
        """Upscale image."""
        print(f"Stage 3: Upscaling {scale}x...")
        
        # Set parameters
        self.upscale_wf.get_input_value(0).value = image
        self.upscale_wf.get_input_value(1).value = scale
        self.upscale_wf.get_input_value(2).value = model
        self.upscale_wf.get_input_value(3).value = "upscaled_stage"
        
        # Upscale
        submission = self.upscale_wf.submit_sync()
        result = self.upscale_wf.wait_for_completion_sync(submission)
        
        if result['status'] == 'COMPLETED':
            images = self.upscale_wf.map_outputs_to_images(result)
            if images:
                return images[0], result
        
        return None, result
    
    def full_pipeline(
        self,
        prompt: str,
        negative_prompt: str = "",
        seed: int = -1,
        base_steps: int = 30,
        refiner_steps: int = 15,
        upscale: bool = True,
        upscale_factor: int = 2
    ) -> Dict[str, Any]:
        """Execute full multi-stage pipeline."""
        results = {
            'base': None,
            'refined': None,
            'upscaled': None,
            'metadata': {}
        }
        
        # Stage 1: Base
        base_image, base_result = self.generate_base(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            steps=base_steps
        )
        
        if not base_image:
            print("Base generation failed")
            return results
        
        results['base'] = base_image
        results['metadata']['base'] = base_result
        
        # Stage 2: Refine
        refined_image, refine_result = self.refine_image(
            base_image=base_image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            refiner_steps=refiner_steps
        )
        
        if not refined_image:
            print("Refinement failed, using base image")
            refined_image = base_image
        else:
            results['refined'] = refined_image
            results['metadata']['refined'] = refine_result
        
        # Stage 3: Upscale (optional)
        if upscale:
            upscaled_image, upscale_result = self.upscale_image(
                image=refined_image,
                scale=upscale_factor
            )
            
            if upscaled_image:
                results['upscaled'] = upscaled_image
                results['metadata']['upscaled'] = upscale_result
            else:
                print("Upscaling failed")
        
        return results

# Use multi-stage pipeline
client = InvokeAIClient()
refiner = MultiStageRefiner(client)

results = refiner.full_pipeline(
    prompt="A majestic castle on a mountain, fantasy art, highly detailed",
    negative_prompt="blurry, low quality",
    seed=42,
    base_steps=30,
    refiner_steps=15,
    upscale=True,
    upscale_factor=2
)

print(f"Base: {results['base']}")
print(f"Refined: {results['refined']}")
print(f"Upscaled: {results['upscaled']}")
```

## Advanced Refinement Techniques

### Progressive Refinement

```python
class ProgressiveRefiner(MultiStageRefiner):
    """Progressive refinement with multiple passes."""
    
    def progressive_refine(
        self,
        image: str,
        prompt: str,
        passes: int = 3,
        strength_schedule: Optional[List[float]] = None
    ) -> List[str]:
        """Apply multiple refinement passes."""
        if not strength_schedule:
            # Decreasing strength for each pass
            strength_schedule = [0.5, 0.3, 0.15][:passes]
        
        refined_images = []
        current_image = image
        
        for i, strength in enumerate(strength_schedule):
            print(f"Refinement pass {i+1}/{passes} (strength: {strength})")
            
            refined, _ = self.refine_image(
                base_image=current_image,
                prompt=prompt,
                refiner_strength=strength,
                refiner_steps=10
            )
            
            if refined:
                refined_images.append(refined)
                current_image = refined
            else:
                print(f"Pass {i+1} failed, skipping")
        
        return refined_images
    
    def adaptive_refinement(
        self,
        image: str,
        prompt: str,
        quality_threshold: float = 0.8
    ) -> str:
        """Adaptively refine until quality threshold met."""
        current_image = image
        passes = 0
        max_passes = 5
        
        while passes < max_passes:
            # Assess current quality (simplified)
            quality = self.assess_quality(current_image)
            
            if quality >= quality_threshold:
                print(f"Quality threshold met after {passes} passes")
                break
            
            # Calculate refinement strength based on quality gap
            strength = min(0.5, (quality_threshold - quality) * 0.8)
            
            print(f"Pass {passes+1}: Quality {quality:.2f}, applying strength {strength:.2f}")
            
            refined, _ = self.refine_image(
                base_image=current_image,
                prompt=prompt,
                refiner_strength=strength,
                refiner_steps=12
            )
            
            if refined:
                current_image = refined
            
            passes += 1
        
        return current_image
    
    def assess_quality(self, image: str) -> float:
        """Assess image quality (placeholder)."""
        # In a real implementation, this would use quality metrics
        # Like BRISQUE, NIQE, or a trained quality model
        import random
        return random.uniform(0.6, 0.95)

# Progressive refinement
refiner = ProgressiveRefiner(client)

# Generate base
base_image, _ = refiner.generate_base(
    prompt="Portrait of a warrior, detailed armor",
    steps=25
)

# Apply progressive refinement
refined_stages = refiner.progressive_refine(
    image=base_image,
    prompt="Portrait of a warrior, detailed armor, sharp focus",
    passes=3
)

# Or use adaptive refinement
final_image = refiner.adaptive_refinement(
    image=base_image,
    prompt="Portrait of a warrior, ultra detailed",
    quality_threshold=0.85
)
```

### Face Enhancement

```python
class FaceRefiner(MultiStageRefiner):
    """Specialized face enhancement pipeline."""
    
    def __init__(self, client: InvokeAIClient):
        super().__init__(client)
        self.face_restore_wf = None
        self.setup_face_workflows()
    
    def setup_face_workflows(self):
        """Setup face-specific workflows."""
        # Face restoration workflow
        self.face_restore_wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file("data/workflows/face_restore.json")
        )
    
    def detect_and_enhance_faces(
        self,
        image: str,
        enhancement_strength: float = 0.5
    ) -> str:
        """Detect and enhance faces in image."""
        print("Detecting and enhancing faces...")
        
        # Set parameters
        self.face_restore_wf.get_input_value(0).value = image
        self.face_restore_wf.get_input_value(1).value = enhancement_strength
        self.face_restore_wf.get_input_value(2).value = "CodeFormer"  # or GFPGAN
        self.face_restore_wf.get_input_value(3).value = "face_enhanced"
        
        # Process
        submission = self.face_restore_wf.submit_sync()
        result = self.face_restore_wf.wait_for_completion_sync(submission)
        
        if result['status'] == 'COMPLETED':
            images = self.face_restore_wf.map_outputs_to_images(result)
            if images:
                return images[0]
        
        return image  # Return original if enhancement fails
    
    def portrait_pipeline(
        self,
        prompt: str,
        negative_prompt: str = "",
        enhance_face: bool = True,
        face_strength: float = 0.5
    ) -> Dict[str, Any]:
        """Complete portrait generation and enhancement."""
        results = {}
        
        # Generate base portrait
        base_image, _ = self.generate_base(
            prompt=prompt + ", portrait, face focus",
            negative_prompt=negative_prompt + ", bad face, distorted face",
            steps=35,
            cfg_scale=7.5
        )
        
        results['base'] = base_image
        
        if not base_image:
            return results
        
        # Refine overall image
        refined, _ = self.refine_image(
            base_image=base_image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            refiner_steps=15,
            refiner_strength=0.3
        )
        
        results['refined'] = refined or base_image
        
        # Enhance face if requested
        if enhance_face:
            face_enhanced = self.detect_and_enhance_faces(
                image=results['refined'],
                enhancement_strength=face_strength
            )
            results['face_enhanced'] = face_enhanced
        
        return results

# Face enhancement
face_refiner = FaceRefiner(client)

portrait_results = face_refiner.portrait_pipeline(
    prompt="Professional headshot of a business person, studio lighting",
    negative_prompt="cartoon, anime",
    enhance_face=True,
    face_strength=0.6
)
```

### Detail Enhancement

```python
class DetailEnhancer(MultiStageRefiner):
    """Enhance specific details in images."""
    
    def enhance_region(
        self,
        image: str,
        mask: str,
        prompt: str,
        detail_level: str = "high"
    ) -> str:
        """Enhance specific region with mask."""
        detail_configs = {
            "low": {"steps": 10, "strength": 0.3, "cfg": 5.0},
            "medium": {"steps": 15, "strength": 0.5, "cfg": 7.0},
            "high": {"steps": 20, "strength": 0.7, "cfg": 8.0},
            "ultra": {"steps": 30, "strength": 0.9, "cfg": 10.0}
        }
        
        config = detail_configs.get(detail_level, detail_configs["high"])
        
        # Create masked refinement workflow
        masked_wf = self.client.workflow_repo.create_workflow(
            WorkflowDefinition.from_file("data/workflows/masked_refine.json")
        )
        
        # Set parameters
        masked_wf.get_input_value(0).value = image
        masked_wf.get_input_value(1).value = mask
        masked_wf.get_input_value(2).value = prompt
        masked_wf.get_input_value(3).value = config["steps"]
        masked_wf.get_input_value(4).value = config["strength"]
        masked_wf.get_input_value(5).value = config["cfg"]
        
        # Process
        submission = masked_wf.submit_sync()
        result = masked_wf.wait_for_completion_sync(submission)
        
        if result['status'] == 'COMPLETED':
            images = masked_wf.map_outputs_to_images(result)
            if images:
                return images[0]
        
        return image
    
    def enhance_textures(
        self,
        image: str,
        texture_type: str = "fabric"
    ) -> str:
        """Enhance specific texture types."""
        texture_prompts = {
            "fabric": "detailed fabric texture, visible weave, cloth material",
            "metal": "metallic surface, reflective, detailed metal texture",
            "skin": "detailed skin texture, pores, natural skin",
            "wood": "wood grain, detailed wood texture, natural pattern",
            "stone": "stone texture, rough surface, detailed rock"
        }
        
        prompt = texture_prompts.get(texture_type, "enhanced details")
        
        return self.refine_image(
            base_image=image,
            prompt=prompt,
            refiner_steps=15,
            refiner_strength=0.4,
            cfg_scale=8.0
        )[0]
    
    def multi_detail_enhancement(
        self,
        image: str,
        enhancements: List[Dict[str, Any]]
    ) -> str:
        """Apply multiple targeted enhancements."""
        current_image = image
        
        for enhancement in enhancements:
            region_type = enhancement.get("type", "general")
            
            if region_type == "face":
                current_image = self.detect_and_enhance_faces(
                    current_image,
                    enhancement.get("strength", 0.5)
                )
            elif region_type == "texture":
                current_image = self.enhance_textures(
                    current_image,
                    enhancement.get("texture_type", "fabric")
                )
            elif region_type == "masked":
                current_image = self.enhance_region(
                    current_image,
                    enhancement["mask"],
                    enhancement["prompt"],
                    enhancement.get("detail_level", "high")
                )
        
        return current_image

# Detail enhancement
enhancer = DetailEnhancer(client)

# Define enhancements
enhancements = [
    {"type": "face", "strength": 0.6},
    {"type": "texture", "texture_type": "fabric"},
    {
        "type": "masked",
        "mask": "background_mask.png",
        "prompt": "detailed background, sharp focus",
        "detail_level": "high"
    }
]

# Apply all enhancements
final_enhanced = enhancer.multi_detail_enhancement(
    "portrait.png",
    enhancements
)
```

## Optimization Strategies

### Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelRefiner(MultiStageRefiner):
    """Parallel multi-stage processing."""
    
    def __init__(self, client: InvokeAIClient, max_workers: int = 3):
        super().__init__(client)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def parallel_variations(
        self,
        base_image: str,
        prompts: List[str],
        common_params: Dict[str, Any] = None
    ) -> List[str]:
        """Generate variations in parallel."""
        params = common_params or {}
        
        async def refine_variant(prompt):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self.refine_image,
                base_image,
                prompt,
                params.get("negative_prompt", ""),
                params.get("steps", 15),
                params.get("strength", 0.4),
                params.get("cfg_scale", 7.0)
            )
        
        tasks = [refine_variant(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks)
        
        return [r[0] for r in results if r[0]]
    
    def batch_refine(
        self,
        images: List[str],
        prompt: str,
        parallel: bool = True
    ) -> List[str]:
        """Batch refine multiple images."""
        if parallel:
            # Process in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(
                        self.refine_image,
                        img,
                        prompt,
                        refiner_steps=15
                    )
                    for img in images
                ]
                
                results = [f.result()[0] for f in futures]
        else:
            # Process sequentially
            results = []
            for img in images:
                refined, _ = self.refine_image(img, prompt)
                results.append(refined)
        
        return results

# Parallel processing
parallel_refiner = ParallelRefiner(client)

# Generate base images
base_images = []
for seed in [42, 123, 456]:
    img, _ = parallel_refiner.generate_base(
        prompt="Fantasy landscape",
        seed=seed
    )
    if img:
        base_images.append(img)

# Refine in parallel
refined_batch = parallel_refiner.batch_refine(
    base_images,
    prompt="Fantasy landscape, ultra detailed, masterpiece",
    parallel=True
)

# Or generate variations
async def generate_variations():
    variations = await parallel_refiner.parallel_variations(
        base_images[0],
        prompts=[
            "Fantasy landscape, morning light",
            "Fantasy landscape, sunset",
            "Fantasy landscape, night time"
        ]
    )
    return variations

# Run async variations
variations = asyncio.run(generate_variations())
```

### Memory-Efficient Pipeline

```python
class EfficientRefiner(MultiStageRefiner):
    """Memory-efficient refinement pipeline."""
    
    def __init__(self, client: InvokeAIClient):
        super().__init__(client)
        self.cleanup_intermediate = True
    
    def cleanup_image(self, image_name: str):
        """Delete image to free memory."""
        if self.cleanup_intermediate:
            try:
                self.client._make_request("DELETE", f"/images/i/{image_name}")
            except:
                pass
    
    def streaming_pipeline(
        self,
        prompts: List[str],
        stages: List[str] = ["base", "refine", "upscale"]
    ):
        """Stream results without storing all in memory."""
        for prompt in prompts:
            print(f"\nProcessing: {prompt[:50]}...")
            
            # Generate base
            if "base" in stages:
                base_img, _ = self.generate_base(prompt)
                if not base_img:
                    continue
                
                yield {"stage": "base", "prompt": prompt, "image": base_img}
                current_img = base_img
            
            # Refine
            if "refine" in stages and current_img:
                refined_img, _ = self.refine_image(current_img, prompt)
                
                # Cleanup base if refined succeeded
                if refined_img and self.cleanup_intermediate:
                    self.cleanup_image(current_img)
                
                if refined_img:
                    yield {"stage": "refined", "prompt": prompt, "image": refined_img}
                    current_img = refined_img
            
            # Upscale
            if "upscale" in stages and current_img:
                upscaled_img, _ = self.upscale_image(current_img)
                
                # Cleanup refined if upscaled succeeded
                if upscaled_img and self.cleanup_intermediate:
                    self.cleanup_image(current_img)
                
                if upscaled_img:
                    yield {"stage": "upscaled", "prompt": prompt, "image": upscaled_img}

# Efficient processing
efficient = EfficientRefiner(client)

# Process stream
for result in efficient.streaming_pipeline(
    prompts=[
        "Mountain landscape",
        "Ocean sunset",
        "Forest path"
    ],
    stages=["base", "refine"]
):
    print(f"{result['stage']}: {result['image']}")
    
    # Process each result as it comes
    # Without storing all in memory
```

## Integration Example

### Complete Multi-Stage Application

```python
def main():
    """Complete multi-stage refinement application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Stage Image Refiner")
    parser.add_argument("prompt", help="Generation prompt")
    parser.add_argument("--negative", default="", help="Negative prompt")
    parser.add_argument("--seed", type=int, default=-1, help="Random seed")
    parser.add_argument("--base-steps", type=int, default=30)
    parser.add_argument("--refine-steps", type=int, default=15)
    parser.add_argument("--refine-strength", type=float, default=0.3)
    parser.add_argument("--upscale", action="store_true", help="Enable upscaling")
    parser.add_argument("--upscale-factor", type=int, default=2)
    parser.add_argument("--enhance-face", action="store_true")
    parser.add_argument("--output-dir", default="refined_outputs")
    
    args = parser.parse_args()
    
    # Initialize
    client = InvokeAIClient()
    
    # Choose pipeline based on options
    if args.enhance_face:
        refiner = FaceRefiner(client)
        results = refiner.portrait_pipeline(
            prompt=args.prompt,
            negative_prompt=args.negative,
            enhance_face=True
        )
    else:
        refiner = MultiStageRefiner(client)
        results = refiner.full_pipeline(
            prompt=args.prompt,
            negative_prompt=args.negative,
            seed=args.seed,
            base_steps=args.base_steps,
            refiner_steps=args.refine_steps,
            upscale=args.upscale,
            upscale_factor=args.upscale_factor
        )
    
    # Save results
    import os
    os.makedirs(args.output_dir, exist_ok=True)
    
    for stage, image_name in results.items():
        if image_name and stage != "metadata":
            # Download image
            board = client.board_repo.get_board_handle(f"{stage}_stage")
            image_data = board.download_image(image_name, full_resolution=True)
            
            # Save
            output_path = os.path.join(args.output_dir, f"{stage}.png")
            with open(output_path, "wb") as f:
                f.write(image_data)
            
            print(f"Saved {stage}: {output_path}")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Next Steps

- Review [SDXL Text-to-Image](sdxl-text-to-image.md) for base generation
- Explore [FLUX Image-to-Image](flux-image-to-image.md) for transformations
- See [Raw API](raw-api.md) for custom pipelines
- Check [Workflow Basics](../user-guide/workflow-basics.md) for fundamentals