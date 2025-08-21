#!/usr/bin/env python3
"""
InvokeAI Starred Images Demo

This demo shows how to get starred images from a specific board.
- Find starred images from board 'probe'
- Display starred image details
- Optionally download starred images

API Endpoints demonstrated:
- GET /api/v1/boards/ - Get all boards to find board ID
- GET /api/v1/boards/{board_id}/image_names - Get all images in board
- POST /api/v1/images/images_by_names - Get ImageDTOs with starred status
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

def get_starred_images_from_board(board_id: str) -> List[Dict[str, Any]]:
    """Get all starred images from a board."""
    try:
        # First, get all image names from the board
        response = requests.get(f"{BASE_URL}/api/v1/boards/{board_id}/image_names")
        
        if response.status_code != 200:
            print(f"Failed to get image names: {response.status_code}")
            return []
            
        image_names = response.json()
        
        if not image_names:
            print("No images found in the board")
            return []
            
        print(f"Found {len(image_names)} images in board, checking for starred images...")
        
        # Get full DTOs with starred status for all images
        dto_response = requests.post(
            f"{BASE_URL}/api/v1/images/images_by_names",
            json={"image_names": image_names}
        )
        
        if dto_response.status_code != 200:
            print(f"Failed to get image DTOs: {dto_response.status_code}")
            return []
            
        image_dtos = dto_response.json()
        
        if not image_dtos:
            print("No image data retrieved")
            return []
            
        # Filter for starred images only
        starred_images = [img for img in image_dtos if img.get('starred', False)]
        
        print(f"Found {len(starred_images)} starred images out of {len(image_dtos)} total images")
        
        # Sort starred images by creation time (most recent first)
        starred_images_sorted = sorted(
            starred_images, 
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        return starred_images_sorted
            
    except Exception as e:
        print(f"Error getting starred images: {e}")
        return []

def display_starred_images(starred_images: List[Dict[str, Any]]) -> None:
    """Display information about starred images."""
    if not starred_images:
        print("No starred images to display")
        return
    
    print(f"\n⭐ Starred Images ({len(starred_images)} total):")
    print("=" * 60)
    
    for i, img in enumerate(starred_images, 1):
        print(f"\n{i}. {img['image_name']}")
        print(f"   Created: {img.get('created_at', 'Unknown')}")
        print(f"   Dimensions: {img.get('width', 'Unknown')}x{img.get('height', 'Unknown')}")
        print(f"   Category: {img.get('image_category', 'Unknown')}")
        print(f"   Has workflow: {img.get('has_workflow', False)}")
        
        # Get additional generation metadata
        try:
            metadata_response = requests.get(f"{BASE_URL}/api/v1/images/i/{img['image_name']}/metadata")
            if metadata_response.status_code == 200:
                metadata = metadata_response.json()
                print(f"   Generation mode: {metadata.get('generation_mode', 'Unknown')}")
                print(f"   Seed: {metadata.get('seed', 'Unknown')}")
                model_info = metadata.get('model', {})
                if isinstance(model_info, dict):
                    print(f"   Model: {model_info.get('model_name', 'Unknown')}")
                else:
                    print(f"   Model: {model_info}")
        except:
            print(f"   (Could not retrieve generation metadata)")

def download_starred_images(starred_images: List[Dict[str, Any]], download_dir: str = "./tmp/downloads/starred/") -> bool:
    """Download all starred images to a directory."""
    if not starred_images:
        print("No starred images to download")
        return True
    
    try:
        # Create download directory if it doesn't exist
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"\nDownloading {len(starred_images)} starred images to: {download_dir}")
        
        success_count = 0
        for i, img in enumerate(starred_images, 1):
            image_name = img['image_name']
            print(f"  Downloading {i}/{len(starred_images)}: {image_name}")
            
            # Get the full resolution image
            response = requests.get(f"{BASE_URL}/api/v1/images/i/{image_name}/full")
            
            if response.status_code == 200:
                # Save the image
                file_path = os.path.join(download_dir, image_name)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = os.path.getsize(file_path)
                print(f"    ✅ Downloaded: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
                success_count += 1
            else:
                print(f"    ❌ Failed to download: {response.status_code}")
        
        print(f"\nDownload complete: {success_count}/{len(starred_images)} images downloaded successfully")
        return success_count == len(starred_images)
        
    except Exception as e:
        print(f"Error downloading starred images: {e}")
        return False

def demo_starred_images():
    """Demonstrate getting starred images from a board."""
    print("⭐ InvokeAI Starred Images Demo")
    print("=" * 50)
    
    # Test API connection
    if not test_api_connection():
        return
    
    print(f"\nFinding starred images from 'probe' board")
    print("-" * 40)
    
    # Find the probe board
    board_name = "probe"
    board = find_board_by_name(board_name)
    
    if not board:
        return
    
    board_id = board['board_id']
    print(f"Found board '{board_name}' (ID: {board_id})")
    print(f"Board has {board.get('image_count', 0)} total images")
    
    # Get starred images
    starred_images = get_starred_images_from_board(board_id)
    
    if not starred_images:
        print("\n⭐ No starred images found in this board")
        print("\n💡 Tip: You can star images in InvokeAI web interface or use the API:")
        print(f"   POST {BASE_URL}/api/v1/images/star")
        print(f"   Body: {{\"image_names\": [\"image.png\"]}}")
        return
    
    # Display starred images
    display_starred_images(starred_images)
    
    # Ask if user wants to download starred images
    print(f"\n📥 Would you like to download all {len(starred_images)} starred images? (This is automatic in demo)")
    
    # Download starred images
    download_success = download_starred_images(starred_images)
    
    if download_success:
        print(f"\n✅ Demo completed successfully!")
        print(f"   Found and downloaded {len(starred_images)} starred images from '{board_name}' board")
    else:
        print(f"\n⚠️  Demo completed with some download failures")

if __name__ == "__main__":
    demo_starred_images()
