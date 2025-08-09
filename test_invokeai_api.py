"""
Test script for InvokeAI API operations
Tests: image upload, text-to-image, image-to-image, and download
"""

import requests
import json
import cv2
import numpy as np
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import base64
from io import BytesIO
from PIL import Image

class InvokeAIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:9090"):
        self.base_url = base_url
        self.session = requests.Session()
        
        # Create tmp directory if it doesn't exist
        Path("./tmp").mkdir(exist_ok=True)
        
    def check_api(self) -> bool:
        """Check if API is available"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/app/version")
            if response.status_code == 200:
                version = response.json()
                print(f"[OK] API is running - Version: {version['version']}")
                return True
        except Exception as e:
            print(f"[FAIL] API check failed: {e}")
        return False
    
    def get_models(self) -> Dict[str, Any]:
        """Get available models"""
        response = self.session.get(f"{self.base_url}/api/v2/models/")
        if response.status_code == 200:
            data = response.json()
            models = {}
            for model in data['models']:
                if model['type'] == 'main':
                    models[model['name']] = {
                        'key': model['key'],
                        'base': model['base'],
                        'type': model['type']
                    }
            return models
        return {}
    
    def generate_test_image(self, filename: str = "test_input.png") -> str:
        """Generate a test image using OpenCV"""
        # Create a colorful test image
        img = np.zeros((512, 512, 3), dtype=np.uint8)
        
        # Add gradient background
        for i in range(512):
            img[i, :] = [i//2, 128, 255 - i//2]
        
        # Add some shapes
        cv2.circle(img, (256, 256), 100, (255, 255, 0), -1)
        cv2.rectangle(img, (150, 150), (362, 362), (0, 255, 255), 3)
        cv2.putText(img, "InvokeAI Test", (130, 256), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
        
        # Save the image
        filepath = f"./tmp/{filename}"
        cv2.imwrite(filepath, img)
        print(f"[OK] Generated test image: {filepath}")
        return filepath
    
    def upload_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Upload an image to InvokeAI"""
        try:
            with open(image_path, 'rb') as f:
                files = {'file': (os.path.basename(image_path), f, 'image/png')}
                params = {
                    'image_category': 'general',
                    'is_intermediate': False
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/v1/images/upload",
                    files=files,
                    params=params
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    print(f"[OK] Image uploaded successfully: {data.get('image_name', 'unknown')}")
                    return data
                else:
                    print(f"[FAIL] Upload failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[FAIL] Upload error: {e}")
        return None
    
    def get_queue_list(self) -> Dict[str, Any]:
        """Get available queues"""
        response = self.session.get(f"{self.base_url}/api/v1/queue/list")
        if response.status_code == 200:
            return response.json()
        return {}
    
    def create_text_to_image_graph(self, prompt: str, model_key: str, 
                                  width: int = 1024, height: int = 1024) -> Dict[str, Any]:
        """Create a text-to-image workflow graph for SDXL"""
        return {
            "id": "txt2img_workflow",
            "nodes": {
                "model_loader": {
                    "id": "model_loader",
                    "type": "sdxl_model_loader",
                    "inputs": {
                        "model": {
                            "key": model_key
                        }
                    }
                },
                "positive_prompt": {
                    "id": "positive_prompt",
                    "type": "sdxl_compel_prompt",
                    "inputs": {
                        "prompt": prompt,
                        "style": ""
                    }
                },
                "negative_prompt": {
                    "id": "negative_prompt",
                    "type": "sdxl_compel_prompt",
                    "inputs": {
                        "prompt": "ugly, blurry, low quality, distorted",
                        "style": ""
                    }
                },
                "noise": {
                    "id": "noise",
                    "type": "noise",
                    "inputs": {
                        "width": width,
                        "height": height,
                        "seed": 42,
                        "use_cpu": True
                    }
                },
                "denoise": {
                    "id": "denoise",
                    "type": "denoise_latents",
                    "inputs": {
                        "steps": 20,
                        "cfg_scale": 7.5,
                        "scheduler": "dpmpp_2m",
                        "denoising_start": 0,
                        "denoising_end": 1
                    }
                },
                "latents_to_image": {
                    "id": "latents_to_image",
                    "type": "l2i",
                    "inputs": {
                        "fp32": True,
                        "tiled": False
                    }
                }
            },
            "edges": [
                {
                    "source": {"node_id": "model_loader", "field": "clip"},
                    "destination": {"node_id": "positive_prompt", "field": "clip"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip2"},
                    "destination": {"node_id": "positive_prompt", "field": "clip2"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip"},
                    "destination": {"node_id": "negative_prompt", "field": "clip"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip2"},
                    "destination": {"node_id": "negative_prompt", "field": "clip2"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "unet"},
                    "destination": {"node_id": "denoise", "field": "unet"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "vae"},
                    "destination": {"node_id": "latents_to_image", "field": "vae"}
                },
                {
                    "source": {"node_id": "positive_prompt", "field": "conditioning"},
                    "destination": {"node_id": "denoise", "field": "positive_conditioning"}
                },
                {
                    "source": {"node_id": "negative_prompt", "field": "conditioning"},
                    "destination": {"node_id": "denoise", "field": "negative_conditioning"}
                },
                {
                    "source": {"node_id": "noise", "field": "noise"},
                    "destination": {"node_id": "denoise", "field": "noise"}
                },
                {
                    "source": {"node_id": "denoise", "field": "latents"},
                    "destination": {"node_id": "latents_to_image", "field": "latents"}
                }
            ]
        }
    
    def create_image_to_image_graph(self, prompt: str, model_key: str, 
                                   image_name: str, strength: float = 0.7) -> Dict[str, Any]:
        """Create an image-to-image workflow graph for SDXL"""
        return {
            "id": "img2img_workflow",
            "nodes": {
                "model_loader": {
                    "id": "model_loader",
                    "type": "sdxl_model_loader",
                    "inputs": {
                        "model": {
                            "key": model_key
                        }
                    }
                },
                "input_image": {
                    "id": "input_image",
                    "type": "image",
                    "inputs": {
                        "image": {
                            "image_name": image_name
                        }
                    }
                },
                "image_to_latents": {
                    "id": "image_to_latents",
                    "type": "i2l",
                    "inputs": {
                        "tiled": False,
                        "fp32": True
                    }
                },
                "positive_prompt": {
                    "id": "positive_prompt",
                    "type": "sdxl_compel_prompt",
                    "inputs": {
                        "prompt": prompt,
                        "style": ""
                    }
                },
                "negative_prompt": {
                    "id": "negative_prompt",
                    "type": "sdxl_compel_prompt",
                    "inputs": {
                        "prompt": "ugly, blurry, low quality",
                        "style": ""
                    }
                },
                "noise": {
                    "id": "noise",
                    "type": "noise",
                    "inputs": {
                        "width": 1024,
                        "height": 1024,
                        "seed": 42,
                        "use_cpu": True
                    }
                },
                "denoise": {
                    "id": "denoise",
                    "type": "denoise_latents",
                    "inputs": {
                        "steps": 20,
                        "cfg_scale": 7.5,
                        "scheduler": "dpmpp_2m",
                        "denoising_start": 1.0 - strength,
                        "denoising_end": 1
                    }
                },
                "latents_to_image": {
                    "id": "latents_to_image",
                    "type": "l2i",
                    "inputs": {
                        "fp32": True,
                        "tiled": False
                    }
                }
            },
            "edges": [
                {
                    "source": {"node_id": "input_image", "field": "image"},
                    "destination": {"node_id": "image_to_latents", "field": "image"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "vae"},
                    "destination": {"node_id": "image_to_latents", "field": "vae"}
                },
                {
                    "source": {"node_id": "image_to_latents", "field": "latents"},
                    "destination": {"node_id": "denoise", "field": "latents"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip"},
                    "destination": {"node_id": "positive_prompt", "field": "clip"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip2"},
                    "destination": {"node_id": "positive_prompt", "field": "clip2"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip"},
                    "destination": {"node_id": "negative_prompt", "field": "clip"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "clip2"},
                    "destination": {"node_id": "negative_prompt", "field": "clip2"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "unet"},
                    "destination": {"node_id": "denoise", "field": "unet"}
                },
                {
                    "source": {"node_id": "model_loader", "field": "vae"},
                    "destination": {"node_id": "latents_to_image", "field": "vae"}
                },
                {
                    "source": {"node_id": "positive_prompt", "field": "conditioning"},
                    "destination": {"node_id": "denoise", "field": "positive_conditioning"}
                },
                {
                    "source": {"node_id": "negative_prompt", "field": "conditioning"},
                    "destination": {"node_id": "denoise", "field": "negative_conditioning"}
                },
                {
                    "source": {"node_id": "noise", "field": "noise"},
                    "destination": {"node_id": "denoise", "field": "noise"}
                },
                {
                    "source": {"node_id": "denoise", "field": "latents"},
                    "destination": {"node_id": "latents_to_image", "field": "latents"}
                }
            ]
        }
    
    def enqueue_batch(self, graph: Dict[str, Any], queue_id: str = "default") -> Optional[str]:
        """Submit a workflow to the queue"""
        try:
            batch_data = {
                "batch": {
                    "batch_id": f"batch_{int(time.time())}",
                    "graph": graph,
                    "runs": 1
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/queue/{queue_id}/enqueue_batch",
                json=batch_data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                batch_id = result.get('batch', {}).get('batch_id')
                print(f"[OK] Batch enqueued: {batch_id}")
                return batch_id
            else:
                print(f"[FAIL] Enqueue failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[FAIL] Enqueue error: {e}")
        return None
    
    def wait_for_batch(self, batch_id: str, queue_id: str = "default", timeout: int = 120) -> bool:
        """Wait for a batch to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/v1/queue/{queue_id}/status"
                )
                if response.status_code == 200:
                    status = response.json()
                    # Check if our batch is complete
                    queue_items = status.get('queue', {}).get('pending', []) + \
                                 status.get('queue', {}).get('in_progress', [])
                    
                    batch_found = False
                    for item in queue_items:
                        if item.get('batch_id') == batch_id:
                            batch_found = True
                            break
                    
                    if not batch_found:
                        print(f"[OK] Batch {batch_id} completed")
                        return True
                    
                    print(f"  Waiting for batch {batch_id}...")
                    time.sleep(2)
            except Exception as e:
                print(f"  Status check error: {e}")
                time.sleep(2)
        
        print(f"[FAIL] Timeout waiting for batch {batch_id}")
        return False
    
    def get_recent_images(self, limit: int = 10) -> list:
        """Get recent generated images"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/images/",
                params={"limit": limit, "offset": 0}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
        except Exception as e:
            print(f"[FAIL] Error getting images: {e}")
        return []
    
    def download_image(self, image_name: str, output_path: str) -> bool:
        """Download an image from InvokeAI"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/images/i/{image_name}/full"
            )
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"[OK] Image downloaded: {output_path}")
                return True
            else:
                print(f"[FAIL] Download failed: {response.status_code}")
        except Exception as e:
            print(f"[FAIL] Download error: {e}")
        return False


def main():
    print("=" * 60)
    print("InvokeAI API Test Script")
    print("=" * 60)
    
    client = InvokeAIClient()
    
    # 1. Check API
    if not client.check_api():
        print("API is not available. Please start InvokeAI server.")
        return
    
    # 2. Get available models
    print("\n" + "=" * 60)
    print("Available SDXL Models:")
    print("-" * 60)
    models = client.get_models()
    sdxl_models = {k: v for k, v in models.items() if v['base'] == 'sdxl'}
    
    if not sdxl_models:
        print("No SDXL models found!")
        return
    
    for name, info in sdxl_models.items():
        print(f"  - {name} ({info['base']})")
    
    # Select first SDXL model
    model_name = list(sdxl_models.keys())[0]
    model_key = sdxl_models[model_name]['key']
    print(f"\nUsing model: {model_name}")
    
    # 3. Generate and upload test image
    print("\n" + "=" * 60)
    print("Task 1: Generate and Upload Test Image")
    print("-" * 60)
    test_image_path = client.generate_test_image()
    uploaded_image = client.upload_image(test_image_path)
    
    if not uploaded_image:
        print("Failed to upload image")
        return
    
    uploaded_image_name = uploaded_image.get('image_name')
    print(f"Uploaded image name: {uploaded_image_name}")
    
    # 4. Text-to-Image generation
    print("\n" + "=" * 60)
    print("Task 2: Text-to-Image Generation")
    print("-" * 60)
    prompt = "a beautiful fantasy landscape with mountains and a crystal clear lake, highly detailed, artstation"
    print(f"Prompt: {prompt}")
    
    txt2img_graph = client.create_text_to_image_graph(prompt, model_key)
    txt2img_batch_id = client.enqueue_batch(txt2img_graph)
    
    if txt2img_batch_id:
        if client.wait_for_batch(txt2img_batch_id):
            # Get and download the generated image
            time.sleep(2)  # Wait a bit for image to be available
            recent_images = client.get_recent_images(limit=5)
            if recent_images:
                latest_image = recent_images[0]
                image_name = latest_image['image_name']
                output_path = f"./tmp/txt2img_result_{image_name}"
                client.download_image(image_name, output_path)
                txt2img_result = image_name
            else:
                print("No images found after generation")
                txt2img_result = None
    else:
        txt2img_result = None
    
    # 5. Image-to-Image generation
    print("\n" + "=" * 60)
    print("Task 3: Image-to-Image Generation")
    print("-" * 60)
    
    if uploaded_image_name:
        img2img_prompt = "transform this into a cyberpunk futuristic scene with neon lights"
        print(f"Prompt: {img2img_prompt}")
        print(f"Using uploaded image: {uploaded_image_name}")
        
        img2img_graph = client.create_image_to_image_graph(
            img2img_prompt, model_key, uploaded_image_name, strength=0.7
        )
        img2img_batch_id = client.enqueue_batch(img2img_graph)
        
        if img2img_batch_id:
            if client.wait_for_batch(img2img_batch_id):
                # Get and download the generated image
                time.sleep(2)
                recent_images = client.get_recent_images(limit=5)
                if recent_images:
                    # Find the newest image that's not the txt2img result
                    for img in recent_images:
                        if img['image_name'] != txt2img_result:
                            image_name = img['image_name']
                            output_path = f"./tmp/img2img_result_{image_name}"
                            client.download_image(image_name, output_path)
                            break
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("Check ./tmp directory for downloaded images")
    print("=" * 60)


if __name__ == "__main__":
    main()