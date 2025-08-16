"""
Generate images to a specific board in InvokeAI
Ensures images are saved to and downloaded from the correct board
"""

import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Creative prompts for generation
PROMPTS = [
    {
        "prompt": "a majestic phoenix rising from crystal flames, ethereal and magical, fantasy art masterpiece",
        "style": "fantasy digital art, highly detailed, volumetric lighting",
        "name": "phoenix_rising",
    },
    {
        "prompt": "ancient library in the clouds, floating books, golden sunbeams, magical atmosphere",
        "style": "studio ghibli style, dreamlike, whimsical",
        "name": "cloud_library",
    },
    {
        "prompt": "bioluminescent forest at night, glowing mushrooms and fireflies, mystical path",
        "style": "fantasy photography, cinematic, atmospheric",
        "name": "glowing_forest",
    },
    {
        "prompt": "steampunk airship above victorian london, brass and copper details, sunset sky",
        "style": "steampunk art, detailed mechanical design, vintage",
        "name": "steampunk_airship",
    },
    {
        "prompt": "zen garden on mars, red sand patterns, earth visible in sky, futuristic tranquility",
        "style": "science fiction art, minimalist, surreal",
        "name": "mars_garden",
    },
]


class BoardImageGenerator:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9090",
        board_name: str = "auto-test-board",
    ):
        self.base_url = base_url
        self.board_name = board_name
        self.board_id = None
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

    def get_or_create_board(self) -> str:
        """Get existing board or create new one"""
        # List existing boards
        response = self.session.get(f"{self.base_url}/api/v1/boards/")
        if response.status_code == 200:
            boards = response.json().get("items", [])
            for board in boards:
                if board.get("board_name") == self.board_name:
                    self.board_id = board["board_id"]
                    print(
                        f"[OK] Found existing board: {self.board_name} (id: {self.board_id})"
                    )
                    print(f"     Current image count: {board.get('image_count', 0)}")
                    return self.board_id

        # Create new board if not found
        response = self.session.post(
            f"{self.base_url}/api/v1/boards/",
            params={"board_name": self.board_name, "is_private": False},
        )

        if response.status_code in [200, 201]:
            board_data = response.json()
            self.board_id = board_data["board_id"]
            print(f"[OK] Created new board: {self.board_name} (id: {self.board_id})")
            return self.board_id
        else:
            print(f"[FAIL] Could not create board: {response.status_code}")
            return None

    def get_sdxl_model(self) -> Optional[Dict[str, Any]]:
        """Get first available SDXL model"""
        response = self.session.get(f"{self.base_url}/api/v2/models/")
        if response.status_code == 200:
            models = response.json()["models"]
            for model in models:
                if model["type"] == "main" and model["base"] == "sdxl":
                    return {
                        "name": model["name"],
                        "key": model["key"],
                        "hash": model.get("hash", "random_hash"),
                        "base": model["base"],
                        "type": model["type"],
                    }
        return None

    def create_sdxl_graph_with_board(
        self, prompt: str, style: str, seed: int = None
    ) -> Dict[str, Any]:
        """Create SDXL text-to-image graph with board assignment"""
        if seed is None:
            seed = random.randint(1, 999999)

        model = self.get_sdxl_model()
        if not model:
            raise Exception("No SDXL model available")

        return {
            "id": f"board_gen_{seed}",
            "nodes": {
                "model": {
                    "id": "model",
                    "type": "sdxl_model_loader",
                    "model": {
                        "key": model["key"],
                        "hash": model["hash"],
                        "name": model["name"],
                        "base": model["base"],
                        "type": model["type"],
                    },
                },
                "pos_prompt": {
                    "id": "pos_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": prompt,
                    "style": style,
                },
                "neg_prompt": {
                    "id": "neg_prompt",
                    "type": "sdxl_compel_prompt",
                    "prompt": "ugly, blurry, low quality, distorted, disfigured, bad anatomy",
                    "style": "low quality",
                },
                "noise": {
                    "id": "noise",
                    "type": "noise",
                    "width": 1024,
                    "height": 1024,
                    "seed": seed,
                    "use_cpu": True,
                },
                "denoise": {
                    "id": "denoise",
                    "type": "denoise_latents",
                    "steps": 20,
                    "cfg_scale": 7.5,
                    "scheduler": "euler_a",
                    "denoising_start": 0,
                    "denoising_end": 1,
                },
                "l2i": {
                    "id": "l2i",
                    "type": "l2i",
                    "fp32": False,
                    "board": {"board_id": self.board_id},
                },
            },
            "edges": [
                {
                    "source": {"node_id": "model", "field": "clip"},
                    "destination": {"node_id": "pos_prompt", "field": "clip"},
                },
                {
                    "source": {"node_id": "model", "field": "clip2"},
                    "destination": {"node_id": "pos_prompt", "field": "clip2"},
                },
                {
                    "source": {"node_id": "model", "field": "clip"},
                    "destination": {"node_id": "neg_prompt", "field": "clip"},
                },
                {
                    "source": {"node_id": "model", "field": "clip2"},
                    "destination": {"node_id": "neg_prompt", "field": "clip2"},
                },
                {
                    "source": {"node_id": "model", "field": "unet"},
                    "destination": {"node_id": "denoise", "field": "unet"},
                },
                {
                    "source": {"node_id": "model", "field": "vae"},
                    "destination": {"node_id": "l2i", "field": "vae"},
                },
                {
                    "source": {"node_id": "pos_prompt", "field": "conditioning"},
                    "destination": {
                        "node_id": "denoise",
                        "field": "positive_conditioning",
                    },
                },
                {
                    "source": {"node_id": "neg_prompt", "field": "conditioning"},
                    "destination": {
                        "node_id": "denoise",
                        "field": "negative_conditioning",
                    },
                },
                {
                    "source": {"node_id": "noise", "field": "noise"},
                    "destination": {"node_id": "denoise", "field": "noise"},
                },
                {
                    "source": {"node_id": "denoise", "field": "latents"},
                    "destination": {"node_id": "l2i", "field": "latents"},
                },
            ],
        }

    def enqueue_generation(self, prompt_info: Dict[str, str]) -> str:
        """Enqueue a single image generation to the board"""
        graph = self.create_sdxl_graph_with_board(
            prompt_info["prompt"], prompt_info["style"]
        )

        batch_data = {
            "batch": {
                "batch_id": f"board_{prompt_info['name']}_{int(time.time())}",
                "graph": graph,
                "runs": 1,
            }
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/queue/default/enqueue_batch", json=batch_data
        )

        if response.status_code in [200, 201]:
            result = response.json()
            batch_id = result.get("batch", {}).get("batch_id")
            return batch_id
        else:
            print(
                f"[FAIL] Enqueue failed for {prompt_info['name']}: {response.status_code}"
            )
            if response.content:
                try:
                    error = response.json()
                    print(f"       Error: {error}")
                except:
                    print(f"       Error: {response.text}")
            return None

    def wait_for_completion(self, timeout: int = 180) -> bool:
        """Wait for all generations to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = self.session.get(f"{self.base_url}/api/v1/queue/default/status")
            if response.status_code == 200:
                status = response.json()
                queue = status["queue"]

                if queue["in_progress"] == 0 and queue["pending"] == 0:
                    return True

                print(
                    f"  Queue: Pending={queue['pending']}, Processing={queue['in_progress']}"
                )
                time.sleep(3)

        return False

    def get_board_images(self) -> List[str]:
        """Get all image names from the board"""
        response = self.session.get(
            f"{self.base_url}/api/v1/boards/{self.board_id}/image_names"
        )

        if response.status_code == 200:
            image_names = response.json()
            print(f"[OK] Found {len(image_names)} images in board {self.board_name}")
            return image_names
        else:
            print(f"[FAIL] Could not get board images: {response.status_code}")
            return []

    def download_board_images(self, limit: int = None) -> List[str]:
        """Download images from the specific board"""
        downloaded = []

        # Get image names from board
        image_names = self.get_board_images()

        if not image_names:
            print("[WARN] No images found in board")
            return downloaded

        # Sort by most recent (assuming they're in order)
        if limit:
            image_names = image_names[-limit:]  # Get last N images

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, image_name in enumerate(image_names):
            output_path = (
                f"./tmp/board_{self.board_name}_{timestamp}_{i + 1}_{image_name}"
            )

            img_response = self.session.get(
                f"{self.base_url}/api/v1/images/i/{image_name}/full"
            )

            if img_response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                downloaded.append(output_path)
                print(f"[OK] Downloaded: {output_path}")
            else:
                print(f"[FAIL] Could not download {image_name}")

        return downloaded

    def generate_batch(self):
        """Main batch generation process"""
        print("=" * 70)
        print("BOARD-SPECIFIC IMAGE GENERATION")
        print(f"Target Board: {self.board_name}")
        print("=" * 70)

        # Check API
        if not self.check_api():
            return

        # Get or create board
        print("\nBOARD SETUP:")
        print("-" * 70)
        if not self.get_or_create_board():
            print("[FAIL] Could not setup board")
            return

        # Check model
        model = self.get_sdxl_model()
        if not model:
            print("[FAIL] No SDXL model available")
            return

        print(f"\n[OK] Using model: {model['name']}")

        # Enqueue all generations
        print("\nENQUEUING GENERATIONS:")
        print("-" * 70)
        batch_ids = []

        for i, prompt_info in enumerate(PROMPTS, 1):
            print(f"\n{i}. {prompt_info['name'].upper()}")
            print(f"   Prompt: {prompt_info['prompt'][:70]}...")

            batch_id = self.enqueue_generation(prompt_info)
            if batch_id:
                batch_ids.append(batch_id)
                print(f"   [OK] Enqueued: {batch_id}")
            else:
                print("   [FAIL] Failed to enqueue")

        if not batch_ids:
            print("\n[FAIL] No batches were enqueued")
            return

        # Wait for completion
        print("\n" + "=" * 70)
        print("PROCESSING...")
        print("-" * 70)
        print("Waiting for generations to complete...")

        if self.wait_for_completion():
            print("[OK] All generations completed!")
        else:
            print("[WARN] Timeout - some may not be complete")

        # Wait a bit for images to be saved
        time.sleep(2)

        # Download from board
        print("\n" + "=" * 70)
        print(f"DOWNLOADING FROM BOARD: {self.board_name}")
        print("-" * 70)

        downloaded = self.download_board_images(limit=len(batch_ids))

        # Summary
        print("\n" + "=" * 70)
        print("GENERATION SUMMARY")
        print("=" * 70)
        print(f"Board: {self.board_name} (ID: {self.board_id})")
        print(f"Prompts used: {len(PROMPTS)}")
        print(f"Successfully enqueued: {len(batch_ids)}")
        print(f"Images downloaded from board: {len(downloaded)}")

        print("\nPrompts generated:")
        for i, prompt_info in enumerate(PROMPTS, 1):
            print(f"  {i}. {prompt_info['name']}")

        if downloaded:
            print("\nDownloaded files:")
            for file in downloaded:
                print(f"  - {Path(file).name}")

        print("\n" + "=" * 70)
        print(f"Complete! Images saved to ./tmp from board '{self.board_name}'")
        print("=" * 70)


def main():
    generator = BoardImageGenerator(board_name="auto-test-board")
    generator.generate_batch()


if __name__ == "__main__":
    main()
