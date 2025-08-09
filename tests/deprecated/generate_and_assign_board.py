"""
Generate images first, then assign them to a board
This avoids the black image issue with direct board assignment
"""

import requests
import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Creative prompts
PROMPTS = [
    {
        "prompt": "a majestic phoenix rising from crystal flames, ethereal and magical, fantasy art masterpiece, highly detailed volumetric lighting",
        "name": "phoenix_rising"
    },
    {
        "prompt": "ancient library in the clouds, floating books, golden sunbeams, magical atmosphere, studio ghibli style dreamlike whimsical",
        "name": "cloud_library"
    },
    {
        "prompt": "bioluminescent forest at night, glowing mushrooms and fireflies, mystical path, fantasy photography cinematic atmospheric",
        "name": "glowing_forest"
    },
    {
        "prompt": "steampunk airship above victorian london, brass and copper details, sunset sky, detailed mechanical design vintage",
        "name": "steampunk_airship"
    },
    {
        "prompt": "zen garden on mars, red sand patterns, earth visible in sky, futuristic tranquility, science fiction art minimalist surreal",
        "name": "mars_garden"
    }
]

class SmartBoardGenerator:
    def __init__(self, base_url: str = "http://127.0.0.1:9090", board_name: str = "auto-test-board-working"):
        self.base_url = base_url
        self.board_name = board_name
        self.board_id = None
        self.session = requests.Session()
        self.generated_images = []
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
    
    def get_or_create_board(self) -> str:
        """Get existing board or create new one"""
        response = self.session.get(f"{self.base_url}/api/v1/boards/")
        if response.status_code == 200:
            boards = response.json().get('items', [])
            for board in boards:
                if board.get('board_name') == self.board_name:
                    self.board_id = board['board_id']
                    print(f"[OK] Found existing board: {self.board_name} (id: {self.board_id})")
                    print(f"     Current image count: {board.get('image_count', 0)}")
                    return self.board_id
        
        # Create new board
        response = self.session.post(
            f"{self.base_url}/api/v1/boards/",
            params={'board_name': self.board_name, 'is_private': False}
        )
        
        if response.status_code in [200, 201]:
            board_data = response.json()
            self.board_id = board_data['board_id']
            print(f"[OK] Created new board: {self.board_name} (id: {self.board_id})")
            return self.board_id
        
        print(f"[FAIL] Could not create board: {response.status_code}")
        return None
    
    def get_best_sdxl_model(self) -> Optional[Dict[str, Any]]:
        """Get a known working SDXL model"""
        response = self.session.get(f"{self.base_url}/api/v2/models/")
        if response.status_code == 200:
            models = response.json()['models']
            
            # Try to find a specific working model
            preferred = ['cyberrealisticXL', 'xxmix9realistic', 'NightVision']
            
            for pref in preferred:
                for model in models:
                    if model['type'] == 'main' and model['base'] == 'sdxl':
                        if pref.lower() in model['name'].lower():
                            return {
                                'name': model['name'],
                                'key': model['key'],
                                'hash': model.get('hash', 'random_hash'),
                                'base': model['base'],
                                'type': model['type']
                            }
            
            # Return any SDXL model
            for model in models:
                if model['type'] == 'main' and model['base'] == 'sdxl':
                    return {
                        'name': model['name'],
                        'key': model['key'],
                        'hash': model.get('hash', 'random_hash'),
                        'base': model['base'],
                        'type': model['type']
                    }
        return None
    
    def create_generation_graph(self, prompt: str, seed: int = None) -> Dict[str, Any]:
        """Create SDXL graph WITHOUT board assignment"""
        if seed is None:
            seed = random.randint(1, 999999)
        
        model = self.get_best_sdxl_model()
        if not model:
            raise Exception("No SDXL model available")
        
        return {
            "id": f"gen_{seed}",
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
                    "style": ""
                },
                "neg_prompt": {
                    "id": "neg_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": "blurry, low quality, distorted, ugly, bad anatomy",
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
                    "steps": 25,
                    "cfg_scale": 7.5,
                    "scheduler": "euler_a",
                    "denoising_start": 0,
                    "denoising_end": 1
                },
                "l2i": {
                    "id": "l2i",
                    "type": "l2i",
                    "fp32": False
                    # NO board assignment here
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
    
    def generate_image(self, prompt_info: Dict[str, str]) -> Optional[str]:
        """Generate a single image and return its name"""
        graph = self.create_generation_graph(prompt_info['prompt'])
        
        batch_data = {
            "batch": {
                "batch_id": f"gen_{prompt_info['name']}_{int(time.time())}",
                "graph": graph,
                "runs": 1
            }
        }
        
        # Remember images before generation
        before_response = self.session.get(
            f"{self.base_url}/api/v1/images/",
            params={"limit": 10, "offset": 0}
        )
        before_images = set()
        if before_response.status_code == 200:
            for img in before_response.json().get('items', []):
                before_images.add(img['image_name'])
        
        # Enqueue generation
        response = self.session.post(
            f"{self.base_url}/api/v1/queue/default/enqueue_batch",
            json=batch_data
        )
        
        if response.status_code not in [200, 201]:
            print(f"[FAIL] Could not enqueue {prompt_info['name']}")
            return None
        
        print(f"[OK] Enqueued: {prompt_info['name']}")
        
        # Wait for completion
        start_time = time.time()
        while time.time() - start_time < 60:
            response = self.session.get(f"{self.base_url}/api/v1/queue/default/status")
            if response.status_code == 200:
                status = response.json()
                queue = status['queue']
                if queue['in_progress'] == 0 and queue['pending'] == 0:
                    break
            time.sleep(2)
        
        # Find the new image
        time.sleep(1)  # Brief pause for image to be saved
        
        after_response = self.session.get(
            f"{self.base_url}/api/v1/images/",
            params={"limit": 10, "offset": 0}
        )
        
        if after_response.status_code == 200:
            for img in after_response.json().get('items', []):
                if img['image_name'] not in before_images:
                    print(f"[OK] Generated: {img['image_name']}")
                    return img['image_name']
        
        return None
    
    def assign_image_to_board(self, image_name: str) -> bool:
        """Assign an image to the board"""
        response = self.session.post(
            f"{self.base_url}/api/v1/board_images/",
            json={
                "board_id": self.board_id,
                "image_name": image_name
            }
        )
        
        if response.status_code in [200, 201]:
            print(f"[OK] Assigned {image_name} to board")
            return True
        else:
            print(f"[FAIL] Could not assign {image_name} to board: {response.status_code}")
            return False
    
    def download_image(self, image_name: str, prefix: str = "") -> Optional[str]:
        """Download an image"""
        response = self.session.get(
            f"{self.base_url}/api/v1/images/i/{image_name}/full"
        )
        
        if response.status_code == 200:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"./tmp/{prefix}_{timestamp}_{image_name}"
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            file_size = Path(output_path).stat().st_size
            if file_size < 50000:
                print(f"[WARN] Small file ({file_size} bytes): {output_path}")
                return None
            else:
                print(f"[OK] Downloaded ({file_size:,} bytes): {output_path}")
                return output_path
        
        return None
    
    def run(self):
        """Main execution"""
        print("=" * 70)
        print("SMART BOARD GENERATION (Generate then Assign)")
        print(f"Target Board: {self.board_name}")
        print("=" * 70)
        
        if not self.check_api():
            return
        
        # Setup board
        print("\nBOARD SETUP:")
        print("-" * 70)
        if not self.get_or_create_board():
            return
        
        # Check model
        model = self.get_best_sdxl_model()
        if not model:
            print("[FAIL] No SDXL model available")
            return
        
        print(f"\n[OK] Using model: {model['name']}")
        
        # Generate images
        print("\nGENERATING IMAGES:")
        print("-" * 70)
        
        generated_images = []
        for i, prompt_info in enumerate(PROMPTS, 1):
            print(f"\n{i}. {prompt_info['name'].upper()}")
            print(f"   Prompt: {prompt_info['prompt'][:70]}...")
            
            image_name = self.generate_image(prompt_info)
            
            if image_name:
                generated_images.append((prompt_info['name'], image_name))
            else:
                print(f"   [FAIL] Could not generate image")
        
        # Assign to board
        print("\n" + "=" * 70)
        print("ASSIGNING TO BOARD:")
        print("-" * 70)
        
        assigned = []
        for name, image_name in generated_images:
            if self.assign_image_to_board(image_name):
                assigned.append((name, image_name))
        
        # Download
        print("\n" + "=" * 70)
        print("DOWNLOADING IMAGES:")
        print("-" * 70)
        
        downloaded = []
        for name, image_name in assigned:
            path = self.download_image(image_name, f"board_{self.board_name}_{name}")
            if path:
                downloaded.append(path)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Board: {self.board_name} (ID: {self.board_id})")
        print(f"Requested: {len(PROMPTS)}")
        print(f"Generated: {len(generated_images)}")
        print(f"Assigned to board: {len(assigned)}")
        print(f"Downloaded: {len(downloaded)}")
        
        if downloaded:
            print("\nSuccessful generations:")
            for path in downloaded:
                print(f"  - {Path(path).name}")
        
        print("\n" + "=" * 70)
        print("COMPLETE!")
        print("=" * 70)


def main():
    generator = SmartBoardGenerator()
    generator.run()


if __name__ == "__main__":
    main()