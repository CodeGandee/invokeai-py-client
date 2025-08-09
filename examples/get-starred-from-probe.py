#!/usr/bin/env python3
"""
Simple script to get starred images from the 'probe' board.
"""

import requests

def get_starred_images_from_probe():
    """Get starred images from the probe board."""
    BASE_URL = "http://127.0.0.1:9090"
    
    try:
        # Find probe board
        boards_response = requests.get(f"{BASE_URL}/api/v1/boards/?all=true")
        boards = boards_response.json()
        
        probe_board = None
        for board in boards:
            if board.get('board_name') == 'probe':
                probe_board = board
                break
        
        if not probe_board:
            print("Probe board not found")
            return []
        
        board_id = probe_board['board_id']
        print(f"Found probe board (ID: {board_id})")
        
        # Get all image names from the board
        images_response = requests.get(f"{BASE_URL}/api/v1/boards/{board_id}/image_names")
        image_names = images_response.json()
        
        print(f"Found {len(image_names)} total images in probe board")
        
        # Get full image data with starred status
        dto_response = requests.post(
            f"{BASE_URL}/api/v1/images/images_by_names",
            json={"image_names": image_names}
        )
        image_dtos = dto_response.json()
        
        # Filter for starred images
        starred_images = [img for img in image_dtos if img.get('starred', False)]
        
        print(f"Found {len(starred_images)} starred images:")
        for i, img in enumerate(starred_images, 1):
            print(f"  {i}. {img['image_name']} (created: {img.get('created_at', 'Unknown')})")
        
        return starred_images
        
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    get_starred_images_from_probe()
