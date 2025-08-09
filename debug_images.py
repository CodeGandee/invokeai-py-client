"""
Debug image generation and retrieval
"""

import requests
import json
import time
import random
from pathlib import Path
from datetime import datetime

def debug_generation():
    base_url = "http://127.0.0.1:9090"
    session = requests.Session()
    
    print("=" * 70)
    print("DEBUG IMAGE GENERATION AND RETRIEVAL")
    print("=" * 70)
    
    # Get model
    response = session.get(f"{base_url}/api/v2/models/")
    models = response.json()['models']
    model = None
    for m in models:
        if m['type'] == 'main' and m['base'] == 'sdxl' and 'cyberrealistic' in m['name'].lower():
            model = m
            break
    
    if not model:
        print("No suitable model found")
        return
    
    print(f"Using model: {model['name']}")
    
    # Create a simple graph
    seed = random.randint(1, 999999)
    graph = {
        "id": f"debug_{seed}",
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
            "pos_prompt": {
                "id": "pos_prompt",
                "type": "sdxl_compel_prompt",
                "prompt": "a beautiful sunset over mountains, professional photography",
                "style": ""
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
                "steps": 20,
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
    
    # Enqueue
    batch_data = {
        "batch": {
            "batch_id": f"debug_batch_{int(time.time())}",
            "graph": graph,
            "runs": 1
        }
    }
    
    print("\nEnqueueing generation...")
    response = session.post(
        f"{base_url}/api/v1/queue/default/enqueue_batch",
        json=batch_data
    )
    
    if response.status_code not in [200, 201]:
        print(f"Failed to enqueue: {response.status_code}")
        return
    
    result = response.json()
    batch_info = result.get('batch', {})
    print(f"Batch ID: {batch_info.get('batch_id')}")
    
    # Wait for completion
    print("\nWaiting for completion...")
    start_time = time.time()
    while time.time() - start_time < 60:
        response = session.get(f"{base_url}/api/v1/queue/default/status")
        if response.status_code == 200:
            status = response.json()
            queue = status['queue']
            if queue['in_progress'] == 0 and queue['pending'] == 0:
                print("Generation complete!")
                break
            print(f"Queue: Pending={queue['pending']}, Processing={queue['in_progress']}")
        time.sleep(2)
    
    # Check queue items to find our batch
    print("\nChecking queue items...")
    response = session.get(f"{base_url}/api/v1/queue/default/list")
    if response.status_code == 200:
        queue_data = response.json()
        print(f"Queue items: {len(queue_data.get('items', []))}")
    
    # Get recent images with more details
    print("\nGetting recent images...")
    response = session.get(
        f"{base_url}/api/v1/images/",
        params={"limit": 5, "offset": 0}
    )
    
    if response.status_code == 200:
        images_data = response.json()
        images = images_data.get('items', [])
        
        print(f"Found {len(images)} recent images:")
        for i, img in enumerate(images):
            print(f"\n{i+1}. {img['image_name']}")
            print(f"   Created: {img.get('created_at', 'N/A')}")
            print(f"   Width: {img.get('width', 'N/A')} x Height: {img.get('height', 'N/A')}")
            print(f"   Board: {img.get('board', 'None')}")
            
            # Try to download
            img_response = session.get(f"{base_url}/api/v1/images/i/{img['image_name']}/full")
            if img_response.status_code == 200:
                output_path = f"./tmp/debug_{i+1}_{img['image_name']}"
                with open(output_path, 'wb') as f:
                    f.write(img_response.content)
                
                file_size = Path(output_path).stat().st_size
                print(f"   Downloaded: {file_size:,} bytes")
                
                if file_size < 50000:
                    print(f"   [WARNING] Image appears to be black/corrupted")
                else:
                    print(f"   [OK] Valid image")
    
    # Try different download methods
    print("\n" + "=" * 70)
    print("Testing different download methods...")
    
    if images:
        test_image = images[0]['image_name']
        
        # Method 1: /full endpoint
        response = session.get(f"{base_url}/api/v1/images/i/{test_image}/full")
        print(f"Method 1 (/full): Status={response.status_code}, Size={len(response.content)} bytes")
        
        # Method 2: /url endpoint (if exists)
        response = session.get(f"{base_url}/api/v1/images/i/{test_image}/url")
        print(f"Method 2 (/url): Status={response.status_code}")
        if response.status_code == 200:
            print(f"   URL: {response.json()}")
        
        # Method 3: metadata
        response = session.get(f"{base_url}/api/v1/images/i/{test_image}/metadata")
        print(f"Method 3 (metadata): Status={response.status_code}")
        if response.status_code == 200:
            metadata = response.json()
            print(f"   Metadata keys: {list(metadata.keys())}")


if __name__ == "__main__":
    debug_generation()