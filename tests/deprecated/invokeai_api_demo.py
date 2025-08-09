"""
Simplified InvokeAI API demonstration script
Shows how to upload images, generate images, and download results
"""

import requests
import json
import cv2
import numpy as np
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

def main():
    base_url = "http://127.0.0.1:9090"
    session = requests.Session()
    
    # Ensure tmp directory exists
    Path("./tmp").mkdir(exist_ok=True)
    
    print("=" * 60)
    print("InvokeAI API Demonstration")
    print("=" * 60)
    
    # 1. Check API is running
    print("\n1. Checking API...")
    response = session.get(f"{base_url}/api/v1/app/version")
    if response.status_code == 200:
        version = response.json()
        print(f"   [OK] API Version: {version['version']}")
    else:
        print("   [FAIL] API not available")
        return
    
    # 2. Generate a test image with OpenCV
    print("\n2. Generating test image with OpenCV...")
    test_img = np.zeros((512, 512, 3), dtype=np.uint8)
    
    # Create gradient background
    for i in range(512):
        test_img[i, :] = [i//2, 100 + i//4, 255 - i//2]
    
    # Add geometric shapes
    cv2.circle(test_img, (256, 256), 80, (255, 200, 0), -1)
    cv2.rectangle(test_img, (100, 100), (412, 412), (0, 255, 200), 4)
    cv2.putText(test_img, "InvokeAI Demo", (140, 256), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Save test image
    test_image_path = "./tmp/opencv_test_image.png"
    cv2.imwrite(test_image_path, test_img)
    print(f"   [OK] Saved to {test_image_path}")
    
    # 3. Upload image to InvokeAI
    print("\n3. Uploading image to InvokeAI...")
    with open(test_image_path, 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        params = {
            'image_category': 'general',
            'is_intermediate': False
        }
        response = session.post(
            f"{base_url}/api/v1/images/upload",
            files=files,
            params=params
        )
    
    if response.status_code in [200, 201]:
        uploaded_data = response.json()
        uploaded_image_name = uploaded_data['image_name']
        print(f"   [OK] Uploaded as: {uploaded_image_name}")
    else:
        print(f"   [FAIL] Upload failed: {response.status_code}")
        return
    
    # 4. Get available SDXL models
    print("\n4. Finding SDXL models...")
    response = session.get(f"{base_url}/api/v2/models/")
    models_data = response.json()
    
    sdxl_models = []
    for model in models_data['models']:
        if model['type'] == 'main' and model['base'] == 'sdxl':
            sdxl_models.append({
                'name': model['name'],
                'key': model['key']
            })
    
    if sdxl_models:
        model = sdxl_models[0]
        print(f"   [OK] Using model: {model['name']}")
    else:
        print("   [FAIL] No SDXL models found")
        return
    
    # 5. Text-to-Image generation
    print("\n5. Text-to-Image Generation...")
    print("   Prompt: 'fantasy landscape with mountains and lake'")
    
    txt2img_graph = {
        "id": "txt2img_demo",
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
                    "prompt": "beautiful fantasy landscape with mountains and crystal lake, highly detailed",
                    "style": "photographic, high quality"
                }
            },
            "neg_prompt": {
                "id": "neg_prompt",
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
                    "seed": 12345
                }
            },
            "denoise": {
                "id": "denoise",
                "type": "denoise_latents",
                "inputs": {
                    "steps": 15,
                    "cfg_scale": 7.0,
                    "scheduler": "euler",
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
    
    batch_data = {
        "batch": {
            "batch_id": f"txt2img_{int(time.time())}",
            "graph": txt2img_graph,
            "runs": 1
        }
    }
    
    response = session.post(
        f"{base_url}/api/v1/queue/default/enqueue_batch",
        json=batch_data
    )
    
    if response.status_code in [200, 201]:
        print("   [OK] Text-to-image batch enqueued")
    else:
        print(f"   [FAIL] Enqueue failed: {response.status_code}")
    
    # 6. Image-to-Image generation
    print("\n6. Image-to-Image Generation...")
    print(f"   Using uploaded image: {uploaded_image_name}")
    print("   Prompt: 'cyberpunk style with neon lights'")
    
    img2img_graph = {
        "id": "img2img_demo",
        "nodes": {
            "model": {
                "id": "model",
                "type": "sdxl_model_loader",
                "inputs": {
                    "model": {"key": model['key']}
                }
            },
            "input_img": {
                "id": "input_img",
                "type": "image",
                "inputs": {
                    "image": {"image_name": uploaded_image_name}
                }
            },
            "i2l": {
                "id": "i2l",
                "type": "i2l",
                "inputs": {
                    "fp32": False
                }
            },
            "pos_prompt": {
                "id": "pos_prompt",
                "type": "sdxl_compel_prompt",
                "inputs": {
                    "prompt": "cyberpunk style, neon lights, futuristic",
                    "style": "digital art"
                }
            },
            "neg_prompt": {
                "id": "neg_prompt",
                "type": "sdxl_compel_prompt",
                "inputs": {
                    "prompt": "ugly, blurry",
                    "style": ""
                }
            },
            "noise": {
                "id": "noise",
                "type": "noise",
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "seed": 54321
                }
            },
            "denoise": {
                "id": "denoise",
                "type": "denoise_latents",
                "inputs": {
                    "steps": 15,
                    "cfg_scale": 7.0,
                    "scheduler": "euler",
                    "denoising_start": 0.3,  # Keep 70% of original
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
            {"source": {"node_id": "input_img", "field": "image"},
             "destination": {"node_id": "i2l", "field": "image"}},
            {"source": {"node_id": "model", "field": "vae"},
             "destination": {"node_id": "i2l", "field": "vae"}},
            {"source": {"node_id": "i2l", "field": "latents"},
             "destination": {"node_id": "denoise", "field": "latents"}},
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
    
    batch_data = {
        "batch": {
            "batch_id": f"img2img_{int(time.time())}",
            "graph": img2img_graph,
            "runs": 1
        }
    }
    
    response = session.post(
        f"{base_url}/api/v1/queue/default/enqueue_batch",
        json=batch_data
    )
    
    if response.status_code in [200, 201]:
        print("   [OK] Image-to-image batch enqueued")
    else:
        print(f"   [FAIL] Enqueue failed: {response.status_code}")
    
    # 7. Wait for processing
    print("\n7. Waiting for generation to complete...")
    print("   (This may take 30-60 seconds)")
    
    for i in range(30):  # Wait up to 60 seconds
        time.sleep(2)
        response = session.get(f"{base_url}/api/v1/queue/default/status")
        if response.status_code == 200:
            status = response.json()
            queue = status['queue']
            if queue['in_progress'] == 0 and queue['pending'] == 0:
                print("   [OK] Generation complete")
                break
            else:
                print(f"   ... pending: {queue['pending']}, in progress: {queue['in_progress']}")
    
    # 8. Download generated images
    print("\n8. Downloading generated images...")
    response = session.get(f"{base_url}/api/v1/images/?limit=5&offset=0")
    
    if response.status_code == 200:
        images = response.json()['items']
        
        for i, img in enumerate(images[:3]):
            image_name = img['image_name']
            output_path = f"./tmp/result_{i+1}_{image_name}"
            
            img_response = session.get(f"{base_url}/api/v1/images/i/{image_name}/full")
            if img_response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(img_response.content)
                print(f"   [OK] Downloaded: {output_path}")
            else:
                print(f"   [FAIL] Could not download {image_name}")
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("Check ./tmp directory for generated images:")
    print("  - opencv_test_image.png (input)")
    print("  - result_*.png (generated)")
    print("=" * 60)


if __name__ == "__main__":
    main()