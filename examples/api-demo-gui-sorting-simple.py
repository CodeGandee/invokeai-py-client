#!/usr/bin/env python3
"""
InvokeAI API GUI Sorting Demo - Simple Version

Shows how GUI sorting options map to API parameters by comparing image name lists.
"""

import requests
import json

INVOKEAI_URL = "http://localhost:9090"

def test_sorting_parameters(board_id="probe"):
    """Test all sorting parameter combinations and show results."""
    
    print("InvokeAI GUI Sorting Parameter Demo")
    print("="*50)
    
    # Get the board ID for "probe" board
    boards_response = requests.get(f"{INVOKEAI_URL}/api/v1/boards/?all=true")
    boards_response.raise_for_status()
    boards = boards_response.json()
    
    probe_board_id = None
    for board in boards:
        if board['board_name'] == 'probe':
            probe_board_id = board['board_id']
            break
    
    if not probe_board_id:
        print("Probe board not found")
        return
    
    print(f"Testing sorting on 'probe' board: {probe_board_id}")
    print()
    
    # Test all combinations
    combinations = [
        ("DESC", True, "Newest First + Starred First (Default GUI)"),
        ("DESC", False, "Newest First + No Starred Priority"),
        ("ASC", True, "Oldest First + Starred First"),
        ("ASC", False, "Oldest First + No Starred Priority"),
    ]
    
    for order_dir, starred_first, description in combinations:
        print(f"Testing: {description}")
        print(f"API: order_dir={order_dir}, starred_first={starred_first}")
        
        url = f"{INVOKEAI_URL}/api/v1/images/names"
        params = {
            "board_id": probe_board_id,
            "order_dir": order_dir,
            "starred_first": starred_first,
            "limit": 10
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            image_names = result.get('image_names', [])
            starred_count = result.get('starred_count', 0)
            total_count = result.get('total_count', 0)
            
            print(f"Result: {len(image_names)} images returned (starred: {starred_count}, total: {total_count})")
            if image_names and len(image_names) > 0:
                print(f"First image: {image_names[0]}")
                if len(image_names) > 1:
                    print(f"Last image:  {image_names[-1]}")
            print()
            
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            print()

def show_parameter_mapping():
    """Show the exact GUI to API parameter mapping."""
    print("\nGUI SORTING OPTIONS → API PARAMETERS")
    print("="*45)
    print()
    print("GUI Dropdown: 'Newest First'")
    print("  → API: order_dir='DESC'")
    print()
    print("GUI Dropdown: 'Oldest First'") 
    print("  → API: order_dir='ASC'")
    print()
    print("GUI Checkbox: 'Show starred images first' ✓")
    print("  → API: starred_first=true")
    print()
    print("GUI Checkbox: 'Show starred images first' ✗")
    print("  → API: starred_first=false")
    print()
    print("EXAMPLE API CALLS:")
    print("-" * 20)
    print("# Default GUI behavior:")
    print("GET /api/v1/images/names?board_id=probe&order_dir=DESC&starred_first=true")
    print()
    print("# Oldest first without starred priority:")
    print("GET /api/v1/images/names?board_id=probe&order_dir=ASC&starred_first=false")
    print()

if __name__ == "__main__":
    try:
        show_parameter_mapping()
        test_sorting_parameters()
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to InvokeAI: {e}")
        print("Make sure InvokeAI is running on localhost:9090")
