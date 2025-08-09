#!/usr/bin/env python3
"""
InvokeAI Latest Image Download Demo

This demo demonstrates Task 2: Get the latest image from a given board
- Find the latest image from board 'probe' using optimized API sorting
- Download and save it to ./tmp/downloads/

API Endpoints demonstrated:
- GET /api/v1/boards/ - Get all boards to find board ID
- GET /api/v1/images/names - Get sorted image names (newest first with limit=1)
- POST /api/v1/images/images_by_names - Get image DTO for the latest image
- GET /api/v1/images/i/{image_name}/metadata - Get image metadata
- GET /api/v1/images/i/{image_name}/full - Download full resolution image

Optimization: Uses order_dir=DESC with limit=1 instead of fetching all images.
"""

import requests
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# InvokeAI API base URL
BASE_URL = "http://127.0.0.1:9090"

def test_api_connection() -> bool:
    """Test if the InvokeAI API is accessible."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/app/version")
        if response.status_code == 200:
            version_info = response.json()
            print(f"API Connection successful - InvokeAI version: {version_info.get('version', 'unknown')}")
            return True
        else:
            print(f"API returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"API Connection failed: {e}")
        return False

def find_board_by_name(board_name: str) -> Optional[Dict[str, Any]]:
    """Find a board by its name."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/boards/?all=true")
        
        if response.status_code == 200:
            boards = response.json()
            
            for board in boards:
                if board.get('board_name') == board_name:
                    return board
            
            print(f"Board '{board_name}' not found")
            return None
            
        else:
            print(f"Failed to get boards: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error finding board: {e}")
        return None

def get_latest_image_from_board(board_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest (most recent) image from a board using system sorting.
    
    Optimization: Uses the /api/v1/images/names endpoint with order_dir=DESC and limit=1
    instead of fetching all images and sorting manually. This is much more efficient
    for boards with many images.
    
    Previous approach: GET all images → POST for all DTOs → Sort by timestamp
    Optimized approach: GET 1 image (sorted by system) → POST for 1 DTO
    """
    try:
        # Use the /api/v1/images/names endpoint with DESC sorting to get newest first
        response = requests.get(f"{BASE_URL}/api/v1/images/names", params={
            "board_id": board_id,
            "order_dir": "DESC",  # Newest first
            "starred_first": False,  # Pure chronological order
            "limit": 1  # Only get the latest image
        })
        
        if response.status_code != 200:
            print(f"Failed to get image names: {response.status_code}")
            return None
            
        result = response.json()
        image_names = result.get('image_names', [])
        total_count = result.get('total_count', 0)
        
        if not image_names:
            print("No images found in the board")
            return None
            
        print(f"Board has {total_count} total images, getting latest...")
        
        # Get the image DTO for the latest image
        latest_image_name = image_names[0]
        dto_response = requests.post(
            f"{BASE_URL}/api/v1/images/images_by_names",
            json={"image_names": [latest_image_name]}
        )
        
        if dto_response.status_code != 200:
            print(f"Failed to get image DTO: {dto_response.status_code}")
            return None
            
        image_dtos = dto_response.json()
        
        if not image_dtos:
            print("No image data retrieved")
            return None
            
        latest_image = image_dtos[0]
        
        print(f"Latest image found: {latest_image_name}")
        print(f"Created at: {latest_image.get('created_at', 'Unknown')}")
        print(f"Updated at: {latest_image.get('updated_at', 'Unknown')}")
        print(f"Image category: {latest_image.get('image_category', 'Unknown')}")
        print(f"Dimensions: {latest_image.get('width', 'Unknown')}x{latest_image.get('height', 'Unknown')}")
        
        return latest_image
            
    except Exception as e:
        print(f"Error getting latest image: {e}")
        return None

def get_image_metadata(image_name: str) -> Optional[Dict[str, Any]]:
    """Get metadata for an image."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/images/i/{image_name}/metadata")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get metadata for {image_name}: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting image metadata: {e}")
        return None

def download_image(image_name: str, download_dir: str) -> bool:
    """Download an image to the specified directory."""
    try:
        # Create download directory if it doesn't exist
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        # Get the full resolution image
        response = requests.get(f"{BASE_URL}/api/v1/images/i/{image_name}/full")
        
        if response.status_code == 200:
            # Determine file path
            file_path = os.path.join(download_dir, image_name)
            
            # Save the image
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Image downloaded successfully: {file_path}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            print(f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            return True
        else:
            print(f"Failed to download image: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

def demo_latest_image_download():
    """Demonstrate getting and downloading the latest image from a board."""
    print("InvokeAI Latest Image Download Demo")
    print("=" * 50)
    
    # Test API connection
    if not test_api_connection():
        return
    
    print(f"\nTask 2: Get latest image from 'probe' board")
    print("-" * 40)
    
    # Find the probe board
    board_name = "probe"
    board = find_board_by_name(board_name)
    
    if not board:
        return
    
    board_id = board['board_id']
    print(f"Found board '{board_name}' (ID: {board_id})")
    print(f"Board has {board.get('image_count', 0)} images")
    
    # Get the latest image
    latest_image = get_latest_image_from_board(board_id)
    
    if not latest_image:
        return
    
    latest_image_name = latest_image['image_name']
    
    # Get image metadata for additional info (generation details)
    metadata = get_image_metadata(latest_image_name)
    if metadata:
        print(f"Generation mode: {metadata.get('generation_mode', 'Unknown')}")
        print(f"Model: {metadata.get('model', {}).get('model_name', 'Unknown') if isinstance(metadata.get('model'), dict) else metadata.get('model', 'Unknown')}")
        print(f"Seed: {metadata.get('seed', 'Unknown')}")
    else:
        print("Note: Could not retrieve generation metadata")
    
    # Download the image
    download_dir = "./tmp/downloads/"
    print(f"\nDownloading to: {download_dir}")
    
    success = download_image(latest_image_name, download_dir)
    
    if success:
        print(f"\nTask 2 completed successfully!")
        print(f"Latest image from '{board_name}' board downloaded to {download_dir}{latest_image_name}")
    else:
        print(f"\nTask 2 failed - could not download the image")

if __name__ == "__main__":
    demo_latest_image_download()
