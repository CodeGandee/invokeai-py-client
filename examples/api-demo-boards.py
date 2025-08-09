#!/usr/bin/env python3
"""
InvokeAI Boards API Demo

This demo shows how to interact with the InvokeAI boards API.
Successfully demonstrates Task 1: Getting board names.

API Endpoints demonstrated:
- GET /api/v1/boards/ - List all boards
- GET /api/v1/boards/{board_id} - Get specific board details
- GET /api/v1/boards/{board_id}/image_names - Get images in a board
- GET /api/v1/boards/none/image_names - Get uncategorized images
"""

import requests
import json
from typing import List, Dict, Any

# InvokeAI API base URL
BASE_URL = "http://127.0.0.1:9090"

def test_api_connection() -> bool:
    """Test if the InvokeAI API is accessible."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/app/version")
        if response.status_code == 200:
            version_info = response.json()
            print(f"✅ API Connection successful - InvokeAI version: {version_info.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Connection failed: {e}")
        return False

def get_all_boards() -> List[Dict[str, Any]]:
    """
    Get all boards from InvokeAI.
    
    Returns:
        List of board dictionaries
    """
    endpoint = f"{BASE_URL}/api/v1/boards/"
    params = {'all': True}  # Get all boards in single response
    
    try:
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle both paginated and non-paginated responses
            if isinstance(data, list):
                boards = data  # Direct list response (when all=True)
            elif isinstance(data, dict) and 'items' in data:
                boards = data['items']  # Paginated response
            else:
                print("❌ Unexpected response format")
                return []
            
            print(f"✅ Retrieved {len(boards)} boards")
            return boards
            
        else:
            print(f"❌ Failed to get boards: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting boards: {e}")
        return []

def get_board_names(boards: List[Dict[str, Any]]) -> List[str]:
    """Extract board names from board data."""
    return [board.get('board_name', 'Unknown') for board in boards]

def get_complete_board_overview() -> Dict[str, Any]:
    """Get a complete overview of all boards and uncategorized images."""
    overview = {
        'boards': [],
        'uncategorized_count': 0,
        'total_images': 0
    }
    
    # Get all boards
    boards = get_all_boards()
    overview['boards'] = boards
    
    # Calculate total images in boards
    board_image_count = sum(board.get('image_count', 0) for board in boards)
    
    # Get uncategorized images
    uncategorized_images = get_uncategorized_images()
    overview['uncategorized_count'] = len(uncategorized_images)
    
    # Calculate total images
    overview['total_images'] = board_image_count + overview['uncategorized_count']
    
    return overview

def display_board_summary(boards: List[Dict[str, Any]]) -> None:
    """Display summary information about boards."""
    print("\n📋 Board Summary:")
    print("=" * 40)
    
    for i, board in enumerate(boards, 1):
        print(f"{i}. {board.get('board_name', 'Unknown')} ({board.get('image_count', 0)} images)")

def get_board_details(board_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific board."""
    endpoint = f"{BASE_URL}/api/v1/boards/{board_id}"
    
    try:
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get board {board_id}: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ Error getting board {board_id}: {e}")
        return {}

def get_board_images(board_id: str) -> List[str]:
    """Get list of image names for a specific board."""
    endpoint = f"{BASE_URL}/api/v1/boards/{board_id}/image_names"
    
    try:
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get images for board {board_id}: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting images for board {board_id}: {e}")
        return []

def get_uncategorized_images() -> List[str]:
    """Get list of uncategorized image names (images not assigned to any board)."""
    endpoint = f"{BASE_URL}/api/v1/boards/none/image_names"
    
    try:
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get uncategorized images: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting uncategorized images: {e}")
        return []

def demo_boards_api():
    """Demonstrate the boards API functionality."""
    print("🔍 InvokeAI Boards API Demo")
    print("=" * 40)
    
    # Test API connection
    if not test_api_connection():
        return
    
    print("\n📋 Task 1: Getting Board Names")
    print("-" * 30)
    
    # Get complete overview
    overview = get_complete_board_overview()
    boards = overview['boards']
    
    if not boards:
        print("No boards found or API error occurred.")
        return
    
    # Extract and display board names
    board_names = get_board_names(boards)
    
    print(f"\n📝 Board Names ({len(board_names)} total):")
    for i, name in enumerate(board_names, 1):
        print(f"  {i}. {name}")
    
    # Display board summary
    display_board_summary(boards)
    
    # Display uncategorized images info
    print(f"\n🗂️  Image Summary:")
    print(f"   Boards: {len(boards)} with {overview['total_images'] - overview['uncategorized_count']} images")
    print(f"   Uncategorized: {overview['uncategorized_count']} images")
    print(f"   Total Images: {overview['total_images']}")
    
    if overview['uncategorized_count'] > 0:
        uncategorized_images = get_uncategorized_images()
        print(f"   Sample uncategorized: {uncategorized_images[:3]}")
    
    # Demo: Get details for first board
    if boards:
        print(f"\n🔍 Demo: Getting details for '{boards[0].get('board_name')}'")
        board_id = boards[0].get('board_id')
        
        if board_id:
            board_details = get_board_details(board_id)
            
            if board_details:
                print(f"✅ Board details retrieved successfully")
                print(f"   Name: {board_details.get('board_name')}")
                print(f"   ID: {board_details.get('board_id')}")
                print(f"   Created: {board_details.get('created_at')}")
                print(f"   Image count: {board_details.get('image_count', 0)}")
                print(f"   Cover image: {board_details.get('cover_image_name', 'None')}")
            
            # Get images for this board
            images = get_board_images(board_id)
            if images:
                print(f"   Sample images: {images[:3]}")
    
    print("\n✨ Demo complete!")
    print("\n📚 Summary - How to get board names and images:")
    print("1. GET /api/v1/boards/?all=true - Get all boards")
    print("2. Extract 'board_name' from each board object")
    print("3. GET /api/v1/boards/{board_id}/image_names - Get images in a board")
    print("4. GET /api/v1/boards/none/image_names - Get uncategorized images")
    print("5. Optional: Use board_id for detailed board information")

if __name__ == "__main__":
    demo_boards_api()
