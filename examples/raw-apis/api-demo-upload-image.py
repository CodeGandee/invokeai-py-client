#!/usr/bin/env python3
"""
InvokeAI API Demo - Upload Image to Board

Task 5: Upload image as asset to a board
- Upload data/images/ad7ae269-135e-4432-ac9a-db349cae64d2.png to 'samples' board

API Endpoint: POST /api/v1/images/upload
Required Parameters:
- image_category: "user" (since we're uploading a user-provided image)
- is_intermediate: false (this is a final image, not intermediate)
- board_id: board_id of the "samples" board
- file: image file as multipart/form-data

Author: webapi-expert
"""

import requests
import json
import os
from pathlib import Path

# Configuration
INVOKEAI_URL = "http://localhost:9090"
IMAGE_PATH = "data/images/ad7ae269-135e-4432-ac9a-db349cae64d2.png"
TARGET_BOARD_NAME = "samples"

def get_board_by_name(board_name):
    """Get board information by name"""
    try:
        response = requests.get(f"{INVOKEAI_URL}/api/v1/boards/?all=true")
        response.raise_for_status()
        boards = response.json()
        
        for board in boards:
            if board.get('board_name') == board_name:
                return board
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching boards: {e}")
        return None

def create_board(board_name):
    """Create a new board if it doesn't exist"""
    try:
        board_data = {"board_name": board_name}
        response = requests.post(f"{INVOKEAI_URL}/api/v1/boards/", json=board_data)
        response.raise_for_status()
        board = response.json()
        print(f"✅ Created new board: '{board_name}' (ID: {board['board_id']})")
        return board
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating board: {e}")
        return None

def upload_image_to_board(image_path, board_id):
    """Upload image to specified board"""
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return None
    
    try:
        # Prepare the multipart form data
        with open(image_path, 'rb') as image_file:
            files = {
                'file': (os.path.basename(image_path), image_file, 'image/png')
            }
            
            params = {
                'image_category': 'user',  # User-provided image
                'is_intermediate': False,  # This is a final image
                'board_id': board_id       # Target board
            }
            
            print(f"📤 Uploading {os.path.basename(image_path)} to board {board_id}...")
            response = requests.post(
                f"{INVOKEAI_URL}/api/v1/images/upload",
                files=files,
                params=params
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ Upload successful!")
            return result
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error uploading image: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Response text: {e.response.text}")
        return None

def main():
    """Main execution function"""
    print("🚀 InvokeAI API Demo - Upload Image to Board")
    print("=" * 50)
    
    # Step 1: Check if target board exists
    print(f"🔍 Looking for board: '{TARGET_BOARD_NAME}'")
    board = get_board_by_name(TARGET_BOARD_NAME)
    
    if not board:
        print(f"📋 Board '{TARGET_BOARD_NAME}' not found, creating it...")
        board = create_board(TARGET_BOARD_NAME)
        if not board:
            print("❌ Failed to create board. Exiting.")
            return
    else:
        print(f"✅ Found board: '{TARGET_BOARD_NAME}' (ID: {board['board_id']})")
    
    # Step 2: Upload the image
    print(f"\n📂 Image to upload: {IMAGE_PATH}")
    if os.path.exists(IMAGE_PATH):
        file_size = os.path.getsize(IMAGE_PATH) / (1024 * 1024)  # MB
        print(f"   File size: {file_size:.2f} MB")
    
    result = upload_image_to_board(IMAGE_PATH, board['board_id'])
    
    if result:
        print(f"\n✅ Upload Results:")
        print(f"   Image Name: {result.get('image_name', 'N/A')}")
        print(f"   Image Category: {result.get('image_category', 'N/A')}")
        print(f"   Board ID: {result.get('board_id', 'N/A')}")
        print(f"   Created At: {result.get('created_at', 'N/A')}")
        print(f"   Width x Height: {result.get('width', 'N/A')} x {result.get('height', 'N/A')}")
        
        # Verify the image was assigned to the board
        print(f"\n🔍 Verifying upload in board '{TARGET_BOARD_NAME}'...")
        verification_response = requests.get(f"{INVOKEAI_URL}/api/v1/boards/{board['board_id']}/image_names")
        if verification_response.ok:
            board_images = verification_response.json()
            # Handle both list and dict response formats
            if isinstance(board_images, dict):
                image_names = board_images.get('image_names', [])
            else:
                image_names = board_images  # It's already a list
            
            if result['image_name'] in image_names:
                print(f"✅ Confirmed: Image successfully added to board!")
                print(f"   Total images in board: {len(image_names)}")
            else:
                print(f"⚠️  Warning: Image not found in board image list")
        
        print(f"\n🎯 Task 5 completed successfully!")
        print(f"   Uploaded: {os.path.basename(IMAGE_PATH)}")
        print(f"   To board: '{TARGET_BOARD_NAME}' ({board['board_id']})")
        print(f"   Image ID: {result['image_name']}")
    else:
        print("❌ Upload failed. Check the error messages above.")

if __name__ == "__main__":
    main()
