"""
Test InvokeAI Workflow API with proper structure
Based on the workflow documentation
"""

import requests
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, Optional

class InvokeWorkflowClient:
    def __init__(self, base_url: str = "http://127.0.0.1:9090"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def check_api(self) -> bool:
        """Check if API is available"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/app/version")
            if response.status_code == 200:
                version = response.json()
                print(f"[OK] API Version: {version['version']}")
                return True
        except Exception as e:
            print(f"[FAIL] API not available: {e}")
            return False
    
    def get_models(self) -> Dict[str, Any]:
        """Get available models"""
        response = self.session.get(f"{self.base_url}/api/v2/models/")
        if response.status_code == 200:
            return response.json()
        return {"models": []}
    
    def get_sdxl_model(self) -> Optional[Dict[str, Any]]:
        """Get first available SDXL model"""
        models_data = self.get_models()
        for model in models_data['models']:
            if model['type'] == 'main' and model['base'] == 'sdxl':
                print(f"[OK] Found SDXL model: {model['name']}")
                return model
        return None
    
    def create_simple_sdxl_graph(self, prompt: str, board_id: str = None) -> Dict[str, Any]:
        """Create a simple SDXL graph that actually works"""
        model = self.get_sdxl_model()
        if not model:
            raise Exception("No SDXL model available")
        
        seed = random.randint(1, 999999)
        
        # This is the working graph structure from the demo
        graph = {
            "id": f"sdxl_gen_{seed}",
            "nodes": {
                "model": {
                    "id": "model",
                    "type": "sdxl_model_loader",
                    "model": {
                        "key": model['key'],
                        "hash": model.get('hash', 'random_hash'),
                        "name": model['name'],
                        "base": model['base'],
                        "type": model['type']
                    }
                },
                "positive_prompt": {
                    "id": "positive_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": prompt,
                    "style": "photographic"
                },
                "negative_prompt": {
                    "id": "negative_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": "blurry, low quality, distorted, ugly",
                    "style": ""
                },
                "latents": {
                    "id": "latents",
                    "type": "noise",
                    "width": 1024,
                    "height": 1024,
                    "seed": seed,
                    "use_cpu": True
                },
                "denoise": {
                    "id": "denoise",
                    "type": "denoise_latents",
                    "steps": 30,
                    "cfg_scale": 7.5,
                    "scheduler": "euler_a",
                    "denoising_start": 0,
                    "denoising_end": 1
                },
                "l2i": {
                    "id": "l2i",
                    "type": "l2i",
                    "fp32": False
                }
            },
            "edges": [
                {"source": {"node_id": "model", "field": "unet"},
                 "destination": {"node_id": "denoise", "field": "unet"}},
                {"source": {"node_id": "model", "field": "vae"},
                 "destination": {"node_id": "l2i", "field": "vae"}},
                {"source": {"node_id": "model", "field": "clip"},
                 "destination": {"node_id": "positive_prompt", "field": "clip"}},
                {"source": {"node_id": "model", "field": "clip2"},
                 "destination": {"node_id": "positive_prompt", "field": "clip2"}},
                {"source": {"node_id": "model", "field": "clip"},
                 "destination": {"node_id": "negative_prompt", "field": "clip"}},
                {"source": {"node_id": "model", "field": "clip2"},
                 "destination": {"node_id": "negative_prompt", "field": "clip2"}},
                {"source": {"node_id": "positive_prompt", "field": "conditioning"},
                 "destination": {"node_id": "denoise", "field": "positive_conditioning"}},
                {"source": {"node_id": "negative_prompt", "field": "conditioning"},
                 "destination": {"node_id": "denoise", "field": "negative_conditioning"}},
                {"source": {"node_id": "latents", "field": "noise"},
                 "destination": {"node_id": "denoise", "field": "noise"}},
                {"source": {"node_id": "denoise", "field": "latents"},
                 "destination": {"node_id": "l2i", "field": "latents"}}
            ]
        }
        
        # Add board assignment if provided
        if board_id:
            graph["nodes"]["l2i"]["board"] = {"board_id": board_id}
        
        return graph
    
    def enqueue_graph(self, graph: Dict[str, Any]) -> str:
        """Enqueue graph for execution"""
        batch_data = {
            "batch": {
                "batch_id": f"batch_{int(time.time())}",
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
            print(f"[FAIL] Enqueue failed: {response.status_code}")
            if response.content:
                try:
                    error = response.json()
                    print(f"Error details: {json.dumps(error, indent=2)}")
                except:
                    print(f"Error: {response.text}")
            return None
    
    def wait_for_completion(self, timeout: int = 180) -> bool:
        """Wait for queue to be empty"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.session.get(f"{self.base_url}/api/v1/queue/default/status")
            if response.status_code == 200:
                status = response.json()
                queue = status['queue']
                
                if queue['in_progress'] == 0 and queue['pending'] == 0:
                    return True
                
                print(f"  Queue: Pending={queue['pending']}, Processing={queue['in_progress']}")
                time.sleep(3)
        
        return False
    
    def get_recent_images(self, limit: int = 5) -> list:
        """Get recent images from gallery"""
        response = self.session.get(
            f"{self.base_url}/api/v1/images/",
            params={"limit": limit, "offset": 0}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
        return []
    
    def download_image(self, image_name: str, output_path: str):
        """Download an image"""
        response = self.session.get(
            f"{self.base_url}/api/v1/images/i/{image_name}/full"
        )
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    
    def test_simple_generation(self):
        """Test simple SDXL generation"""
        print("=" * 70)
        print("TESTING SIMPLE SDXL GENERATION")
        print("=" * 70)
        
        if not self.check_api():
            return
        
        # Create simple graph
        print("\n[1] Creating SDXL graph...")
        graph = self.create_simple_sdxl_graph(
            prompt="a beautiful sunset over mountains, golden hour photography, professional landscape photo"
        )
        
        # Enqueue
        print("\n[2] Enqueueing generation...")
        batch_id = self.enqueue_graph(graph)
        
        if not batch_id:
            print("[FAIL] Could not enqueue generation")
            return
        
        print(f"[OK] Enqueued batch: {batch_id}")
        
        # Wait
        print("\n[3] Waiting for completion...")
        if self.wait_for_completion():
            print("[OK] Generation completed!")
        else:
            print("[WARN] Timeout waiting for completion")
        
        # Get recent images
        print("\n[4] Getting recent images...")
        images = self.get_recent_images(limit=1)
        
        if images:
            image = images[0]
            image_name = image['image_name']
            output_path = f"./tmp/test_workflow_{image_name}"
            
            print(f"[OK] Found image: {image_name}")
            
            # Download
            if self.download_image(image_name, output_path):
                print(f"[OK] Downloaded to: {output_path}")
                
                # Check file size
                file_size = Path(output_path).stat().st_size
                print(f"[INFO] File size: {file_size:,} bytes")
                
                if file_size < 50000:
                    print("[WARN] Image seems too small, might be black/corrupted")
                else:
                    print("[OK] Image appears to be valid size")
        else:
            print("[FAIL] No images found")
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)

def main():
    client = InvokeWorkflowClient()
    client.test_simple_generation()

if __name__ == "__main__":
    main()