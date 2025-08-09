#!/usr/bin/env python3
"""
InvokeAI API GUI Sorting Demo

This script demonstrates how to replicate the InvokeAI web GUI sorting options using API calls.
The GUI provides these sorting controls:
1. Newest First / Oldest First dropdown
2. "Show starred images first" checkbox

These map to API parameters:
- order_dir: "DESC" (newest first) or "ASC" (oldest first)  
- starred_first: true/false (starred images appear first regardless of date)

API Endpoint: GET /api/v1/images/names
Parameters:
- board_id: target board ID (or "none" for uncategorized)
- order_dir: SQLiteDirection enum ("DESC" | "ASC")
- starred_first: boolean (default: true)
"""

import requests
import json
from datetime import datetime
from pathlib import Path

INVOKEAI_URL = "http://localhost:9090"

def get_images_with_sorting(board_id, order_dir="DESC", starred_first=True, limit=10):
    """
    Get images from a board with specific sorting options.
    
    Args:
        board_id: Board ID (or "none" for uncategorized)
        order_dir: "DESC" (newest first) or "ASC" (oldest first)
        starred_first: Show starred images first (boolean)
        limit: Maximum number of images to return
    """
    url = f"{INVOKEAI_URL}/api/v1/images/names"
    
    params = {
        "board_id": board_id,
        "order_dir": order_dir,
        "starred_first": starred_first,
        "limit": limit
    }
    
    print(f"\n{'='*60}")
    print(f"Fetching images with sorting:")
    print(f"  Board ID: {board_id}")
    print(f"  Order: {order_dir} ({'Newest First' if order_dir == 'DESC' else 'Oldest First'})")
    print(f"  Starred First: {starred_first}")
    print(f"  Limit: {limit}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        image_names = response.json()
        print(f"Found {len(image_names)} images")
        
        if not image_names:
            print("No images found")
            return []
        
        # Get detailed info for these images to show sorting results
        limited_names = image_names[:limit] if len(image_names) > limit else image_names
        return get_image_details(limited_names)
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching images: {e}")
        return []

def get_image_details(image_names):
    """Get detailed ImageDTO objects for the given image names."""
    url = f"{INVOKEAI_URL}/api/v1/images/images_by_names"
    
    payload = {"image_names": image_names}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image details: {e}")
        return []

def display_sorted_results(images, title):
    """Display the sorting results in a readable format."""
    print(f"\n{title}")
    print("-" * len(title))
    
    if not images:
        print("No images to display")
        return
    
    for i, img in enumerate(images, 1):
        created_date = datetime.fromisoformat(img['created_at'].replace('Z', '+00:00'))
        starred_indicator = "⭐" if img.get('starred', False) else "  "
        
        print(f"{i:2d}. {starred_indicator} {img['image_name']} | {created_date.strftime('%Y-%m-%d %H:%M:%S')}")

def demonstrate_gui_sorting_options():
    """Demonstrate all GUI sorting combinations."""
    
    # First, get available boards
    boards_response = requests.get(f"{INVOKEAI_URL}/api/v1/boards/?all=true")
    boards_response.raise_for_status()
    boards = boards_response.json()
    
    # Find a board with content (prefer "probe" board from our previous examples)
    target_board = None
    for board in boards:
        if board['board_name'] == 'probe':
            target_board = board
            break
    
    if not target_board:
        # Fall back to first board with images
        for board in boards:
            if board['image_count'] > 0:
                target_board = board
                break
    
    if not target_board:
        print("No boards with images found. Trying uncategorized...")
        board_id = "none"
        board_name = "Uncategorized"
    else:
        board_id = target_board['board_id']
        board_name = target_board['board_name']
    
    print(f"\nDemonstrating GUI sorting options for board: '{board_name}'")
    print(f"Board ID: {board_id}")
    
    # Demonstrate all 4 combinations of GUI sorting options
    sorting_combinations = [
        ("DESC", True, "GUI: 'Newest First' + 'Show starred first' ✓"),
        ("DESC", False, "GUI: 'Newest First' + 'Show starred first' ✗"),
        ("ASC", True, "GUI: 'Oldest First' + 'Show starred first' ✓"),
        ("ASC", False, "GUI: 'Oldest First' + 'Show starred first' ✗"),
    ]
    
    for order_dir, starred_first, description in sorting_combinations:
        images = get_images_with_sorting(board_id, order_dir, starred_first, limit=8)
        display_sorted_results(images, description)
        
        # Add separator between results
        print()

def demonstrate_api_vs_gui_equivalence():
    """Show the exact API parameter mappings for GUI options."""
    print("\n" + "="*70)
    print("GUI TO API PARAMETER MAPPING")
    print("="*70)
    
    mappings = [
        {
            "gui_option": "Dropdown: 'Newest First'",
            "api_param": "order_dir='DESC'",
            "description": "Sort by creation date descending (most recent first)"
        },
        {
            "gui_option": "Dropdown: 'Oldest First'", 
            "api_param": "order_dir='ASC'",
            "description": "Sort by creation date ascending (oldest first)"
        },
        {
            "gui_option": "Checkbox: 'Show starred images first' ✓",
            "api_param": "starred_first=true",
            "description": "Starred images appear first, then by date order"
        },
        {
            "gui_option": "Checkbox: 'Show starred images first' ✗",
            "api_param": "starred_first=false", 
            "description": "All images sorted purely by date (no starred priority)"
        }
    ]
    
    for mapping in mappings:
        print(f"\nGUI: {mapping['gui_option']}")
        print(f"API: {mapping['api_param']}")
        print(f"     {mapping['description']}")
    
    print(f"\n{'='*70}")
    print("COMPLETE API CALL EXAMPLES")
    print("="*70)
    
    examples = [
        {
            "scenario": "Default GUI behavior (newest first, starred priority)",
            "url": "/api/v1/images/names?board_id=probe&order_dir=DESC&starred_first=true"
        },
        {
            "scenario": "Oldest first with starred priority",
            "url": "/api/v1/images/names?board_id=probe&order_dir=ASC&starred_first=true"
        },
        {
            "scenario": "Newest first, no starred priority",
            "url": "/api/v1/images/names?board_id=probe&order_dir=DESC&starred_first=false"
        },
        {
            "scenario": "Pure chronological oldest first",
            "url": "/api/v1/images/names?board_id=probe&order_dir=ASC&starred_first=false"
        }
    ]
    
    for example in examples:
        print(f"\n{example['scenario']}:")
        print(f"GET {INVOKEAI_URL}{example['url']}")

if __name__ == "__main__":
    print("InvokeAI API GUI Sorting Demo")
    print("Demonstrating how GUI sorting options map to API parameters")
    
    try:
        # Show the theoretical mappings first
        demonstrate_api_vs_gui_equivalence()
        
        # Then demonstrate with actual API calls
        demonstrate_gui_sorting_options()
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to InvokeAI API at {INVOKEAI_URL}: {e}")
        print("Make sure InvokeAI is running and accessible.")
    except Exception as e:
        print(f"Unexpected error: {e}")
