"""
Test different SDXL models WITHOUT board assignment
To isolate if the issue is board-related or model-related
"""

import requests
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, Optional

class ModelTester:
    def __init__(self, base_url: str = "http://127.0.0.1:9090"):
        self.base_url = base_url
        self.session = requests.Session()
        Path("./tmp").mkdir(exist_ok=True)
    
    def get_sdxl_models(self):
        """Get all SDXL models"""
        response = self.session.get(f"{self.base_url}/api/v2/models/")
        if response.status_code == 200:
            models = response.json()['models']
            sdxl_models = []
            for model in models:
                if model['type'] == 'main' and model['base'] == 'sdxl':
                    sdxl_models.append({
                        'name': model['name'],
                        'key': model['key'],
                        'hash': model.get('hash', 'random_hash'),
                        'base': model['base'],
                        'type': model['type']
                    })
            return sdxl_models
        return []
    
    def create_simple_graph(self, model: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Create a simple SDXL graph WITHOUT board assignment"""
        seed = random.randint(1, 999999)
        
        return {
            "id": f"test_{seed}",
            "nodes": {
                "model": {
                    "id": "model",
                    "type": "sdxl_model_loader",
                    "model": {
                        "key": model['key'],
                        "hash": model['hash'],
                        "name": model['name'],
                        "base": model['base'],
                        "type": model['type']
                    }
                },
                "pos_prompt": {
                    "id": "pos_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": prompt,
                    "style": ""  # Try without style
                },
                "neg_prompt": {
                    "id": "neg_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": "blurry, low quality",
                    "style": ""
                },
                "noise": {
                    "id": "noise",
                    "type": "noise",
                    "width": 1024,
                    "height": 1024,
                    "seed": seed,
                    "use_cpu": True
                },
                "denoise": {
                    "id": "denoise",
                    "type": "denoise_latents",
                    "steps": 20,  # Reduced steps for faster testing
                    "cfg_scale": 7.5,
                    "scheduler": "euler_a",
                    "denoising_start": 0,
                    "denoising_end": 1
                },
                "l2i": {
                    "id": "l2i",
                    "type": "l2i",
                    "fp32": False
                    # NO board assignment
                }
            },
            "edges": [
                {"source": {"node_id": "model", "field": "unet"},
                 "destination": {"node_id": "denoise", "field": "unet"}},
                {"source": {"node_id": "model", "field": "vae"},
                 "destination": {"node_id": "l2i", "field": "vae"}},
                {"source": {"node_id": "model", "field": "clip"},
                 "destination": {"node_id": "pos_prompt", "field": "clip"}},
                {"source": {"node_id": "model", "field": "clip2"},
                 "destination": {"node_id": "pos_prompt", "field": "clip2"}},
                {"source": {"node_id": "model", "field": "clip"},
                 "destination": {"node_id": "neg_prompt", "field": "clip"}},
                {"source": {"node_id": "model", "field": "clip2"},
                 "destination": {"node_id": "neg_prompt", "field": "clip2"}},
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
    
    def test_model(self, model: Dict[str, Any], prompt: str) -> bool:
        """Test a single model"""
        print(f"\nTesting: {model['name']}")
        print("-" * 50)
        
        # Create graph
        graph = self.create_simple_graph(model, prompt)
        
        # Enqueue
        batch_data = {
            "batch": {
                "batch_id": f"test_{model['name']}_{int(time.time())}",
                "graph": graph,
                "runs": 1
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/queue/default/enqueue_batch",
            json=batch_data
        )
        
        if response.status_code not in [200, 201]:
            print(f"[FAIL] Could not enqueue: {response.status_code}")
            return False
        
        print("[OK] Enqueued")
        
        # Wait for completion
        start_time = time.time()
        while time.time() - start_time < 120:
            response = self.session.get(f"{self.base_url}/api/v1/queue/default/status")
            if response.status_code == 200:
                status = response.json()
                queue = status['queue']
                if queue['in_progress'] == 0 and queue['pending'] == 0:
                    break
            time.sleep(2)
        
        # Get recent image
        response = self.session.get(
            f"{self.base_url}/api/v1/images/",
            params={"limit": 1, "offset": 0}
        )
        
        if response.status_code == 200:
            images = response.json().get('items', [])
            if images:
                image = images[0]
                image_name = image['image_name']
                
                # Download
                img_response = self.session.get(
                    f"{self.base_url}/api/v1/images/i/{image_name}/full"
                )
                
                if img_response.status_code == 200:
                    output_path = f"./tmp/test_{model['name'].replace(' ', '_')}_{image_name}"
                    with open(output_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    file_size = Path(output_path).stat().st_size
                    
                    if file_size < 50000:
                        print(f"[FAIL] Generated black image ({file_size} bytes)")
                        return False
                    else:
                        print(f"[OK] Valid image generated ({file_size:,} bytes)")
                        print(f"     Saved to: {output_path}")
                        return True
        
        print("[FAIL] No image generated")
        return False
    
    def run_tests(self):
        """Test multiple models"""
        print("=" * 70)
        print("TESTING SDXL MODELS WITHOUT BOARD ASSIGNMENT")
        print("=" * 70)
        
        models = self.get_sdxl_models()
        
        if not models:
            print("No SDXL models found")
            return
        
        print(f"Found {len(models)} SDXL models")
        
        # Test models
        test_prompt = "a beautiful mountain landscape at sunset, professional photography, golden hour"
        
        # Test specific models
        test_indices = [2, 8, 1]  # cyberrealisticXL, xxmix9realistic, NightVision
        
        results = []
        for idx in test_indices:
            if idx < len(models):
                model = models[idx]
                success = self.test_model(model, test_prompt)
                results.append((model['name'], success))
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        for name, success in results:
            status = "[OK]" if success else "[FAIL]"
            print(f"{status} {name}")

def main():
    tester = ModelTester()
    tester.run_tests()

if __name__ == "__main__":
    main()