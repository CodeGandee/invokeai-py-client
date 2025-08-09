"""
Batch image generation with InvokeAI API
Generates 5 images with creative random prompts
"""

import requests
import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Creative prompt templates
PROMPTS = [
    {
        "prompt": "a majestic dragon perched on a crystal mountain peak, sunset sky with aurora borealis, fantasy art style, highly detailed, epic composition",
        "style": "fantasy digital painting, artstation trending",
        "name": "dragon_mountain"
    },
    {
        "prompt": "futuristic Tokyo street at night, neon signs reflecting in rain puddles, cyberpunk aesthetic, flying cars, holographic advertisements",
        "style": "blade runner style, cinematic lighting, ultra realistic",
        "name": "cyberpunk_tokyo"
    },
    {
        "prompt": "steampunk mechanical butterfly in a Victorian greenhouse, brass gears and copper wings, surrounded by exotic plants",
        "style": "steampunk art, intricate details, vintage photography style",
        "name": "steampunk_butterfly"
    },
    {
        "prompt": "underwater ancient temple ruins with bioluminescent sea creatures, sunlight rays penetrating deep blue water, mysterious atmosphere",
        "style": "underwater photography, mystical, james cameron style",
        "name": "underwater_temple"
    },
    {
        "prompt": "astronaut discovering alien garden on distant planet, exotic flora with crystalline structures, three moons in purple sky",
        "style": "science fiction art, otherworldly, vivid colors, digital art",
        "name": "alien_garden"
    }
]

class BatchImageGenerator:
    def __init__(self, base_url: str = "http://127.0.0.1:9090"):
        self.base_url = base_url
        self.session = requests.Session()
        self.generated_images = []
        
        # Ensure tmp directory exists
        Path("./tmp").mkdir(exist_ok=True)
        
    def check_api(self) -> bool:
        """Check if API is running"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/app/version")
            if response.status_code == 200:
                version = response.json()
                print(f"[OK] API Version: {version['version']}")
                return True
        except Exception as e:
            print(f"[FAIL] API not available: {e}")
            return False
    
    def get_sdxl_model(self) -> Dict[str, Any]:
        """Get first available SDXL model"""
        response = self.session.get(f"{self.base_url}/api/v2/models/")
        if response.status_code == 200:
            models = response.json()['models']
            for model in models:
                if model['type'] == 'main' and model['base'] == 'sdxl':
                    return {
                        'name': model['name'],
                        'key': model['key']
                    }
        return None
    
    def create_sdxl_graph(self, prompt: str, style: str, seed: int = None) -> Dict[str, Any]:
        """Create SDXL text-to-image graph"""
        if seed is None:
            seed = random.randint(1, 999999)
            
        model = self.get_sdxl_model()
        if not model:
            raise Exception("No SDXL model available")
        
        return {
            "id": f"batch_gen_{seed}",
            "nodes": {
                "model": {
                    "id": "model",
                    "type": "sdxl_model_loader",
                    "inputs": {
                        "model": {"key": model['key']}
                    }
                },
                "pos_prompt": {
                    "id": "pos_prompt",
                    "type": "sdxl_compel_prompt",
                    "inputs": {
                        "prompt": prompt,
                        "style": style
                    }
                },
                "neg_prompt": {
                    "id": "neg_prompt",
                    "type": "sdxl_compel_prompt",
                    "inputs": {
                        "prompt": "ugly, blurry, low quality, distorted, disfigured, bad anatomy, watermark, signature",
                        "style": "low quality, amateur"
                    }
                },
                "noise": {
                    "id": "noise",
                    "type": "noise",
                    "inputs": {
                        "width": 1024,
                        "height": 1024,
                        "seed": seed
                    }
                },
                "denoise": {
                    "id": "denoise",
                    "type": "denoise_latents",
                    "inputs": {
                        "steps": 20,
                        "cfg_scale": 7.5,
                        "scheduler": "euler_a",
                        "denoising_start": 0,
                        "denoising_end": 1
                    }
                },
                "l2i": {
                    "id": "l2i",
                    "type": "l2i",
                    "inputs": {
                        "fp32": False
                    }
                }
            },
            "edges": [
                {"source": {"node_id": "model", "field": "clip"},
                 "destination": {"node_id": "pos_prompt", "field": "clip"}},
                {"source": {"node_id": "model", "field": "clip2"},
                 "destination": {"node_id": "pos_prompt", "field": "clip2"}},
                {"source": {"node_id": "model", "field": "clip"},
                 "destination": {"node_id": "neg_prompt", "field": "clip"}},
                {"source": {"node_id": "model", "field": "clip2"},
                 "destination": {"node_id": "neg_prompt", "field": "clip2"}},
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
    
    def enqueue_generation(self, prompt_info: Dict[str, str]) -> str:
        """Enqueue a single image generation"""
        graph = self.create_sdxl_graph(
            prompt_info['prompt'],
            prompt_info['style']
        )
        
        batch_data = {
            "batch": {
                "batch_id": f"batch_{prompt_info['name']}_{int(time.time())}",
                "graph": graph,
                "runs": 1
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/queue/default/enqueue_batch",
            json=batch_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            batch_id = result.get('batch', {}).get('batch_id')
            return batch_id
        else:
            print(f"[FAIL] Enqueue failed for {prompt_info['name']}: {response.status_code}")
            return None
    
    def wait_for_completion(self, timeout: int = 180) -> bool:
        """Wait for all generations to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.session.get(f"{self.base_url}/api/v1/queue/default/status")
            if response.status_code == 200:
                status = response.json()
                queue = status['queue']
                
                if queue['in_progress'] == 0 and queue['pending'] == 0:
                    return True
                
                print(f"  Queue status - Pending: {queue['pending']}, In Progress: {queue['in_progress']}")
                time.sleep(3)
        
        return False
    
    def download_recent_images(self, count: int = 5) -> List[str]:
        """Download the most recent generated images"""
        downloaded = []
        
        response = self.session.get(
            f"{self.base_url}/api/v1/images/",
            params={"limit": count, "offset": 0}
        )
        
        if response.status_code == 200:
            images = response.json()['items']
            
            for i, img in enumerate(images[:count]):
                image_name = img['image_name']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"./tmp/batch_{timestamp}_{i+1}_{image_name}"
                
                img_response = self.session.get(
                    f"{self.base_url}/api/v1/images/i/{image_name}/full"
                )
                
                if img_response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(img_response.content)
                    downloaded.append(output_path)
                    print(f"[OK] Downloaded: {output_path}")
                else:
                    print(f"[FAIL] Could not download {image_name}")
        
        return downloaded
    
    def generate_batch(self):
        """Main batch generation process"""
        print("=" * 70)
        print("BATCH IMAGE GENERATION WITH RANDOM PROMPTS")
        print("=" * 70)
        
        # Check API
        if not self.check_api():
            return
        
        # Check model availability
        model = self.get_sdxl_model()
        if not model:
            print("[FAIL] No SDXL model available")
            return
        
        print(f"[OK] Using model: {model['name']}\n")
        
        # Enqueue all generations
        print("ENQUEUEING GENERATIONS:")
        print("-" * 70)
        batch_ids = []
        
        for i, prompt_info in enumerate(PROMPTS, 1):
            print(f"\n{i}. {prompt_info['name'].upper()}")
            print(f"   Prompt: {prompt_info['prompt'][:80]}...")
            print(f"   Style: {prompt_info['style']}")
            
            batch_id = self.enqueue_generation(prompt_info)
            if batch_id:
                batch_ids.append(batch_id)
                print(f"   [OK] Enqueued batch: {batch_id}")
            else:
                print(f"   [FAIL] Failed to enqueue")
        
        if not batch_ids:
            print("\n[FAIL] No batches were enqueued successfully")
            return
        
        # Wait for all to complete
        print("\n" + "=" * 70)
        print("PROCESSING...")
        print("-" * 70)
        print("Waiting for all generations to complete (this may take 2-3 minutes)...")
        
        if self.wait_for_completion():
            print("[OK] All generations completed!")
        else:
            print("[WARNING] Timeout reached, some generations may not be complete")
        
        # Download results
        print("\n" + "=" * 70)
        print("DOWNLOADING RESULTS...")
        print("-" * 70)
        
        downloaded = self.download_recent_images(len(batch_ids))
        
        # Summary
        print("\n" + "=" * 70)
        print("GENERATION SUMMARY")
        print("=" * 70)
        print(f"Prompts used: {len(PROMPTS)}")
        print(f"Successfully enqueued: {len(batch_ids)}")
        print(f"Images downloaded: {len(downloaded)}")
        print("\nGenerated prompts:")
        for i, prompt_info in enumerate(PROMPTS, 1):
            print(f"  {i}. {prompt_info['name']}: {prompt_info['prompt'][:60]}...")
        
        print("\nDownloaded files:")
        for file in downloaded:
            print(f"  - {file}")
        
        print("\n" + "=" * 70)
        print("Batch generation complete! Check ./tmp directory for results.")
        print("=" * 70)


def main():
    generator = BatchImageGenerator()
    generator.generate_batch()


if __name__ == "__main__":
    main()