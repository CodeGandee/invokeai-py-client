import requests

response = requests.get("http://127.0.0.1:9090/api/v1/boards/")
if response.status_code == 200:
    boards = response.json().get('items', [])
    auto_boards = [b for b in boards if 'auto-test' in b.get('board_name', '')]
    
    print(f"Found {len(auto_boards)} auto-test boards:")
    for board in auto_boards:
        print(f"- {board['board_name']}: {board.get('image_count', 0)} images (ID: {board['board_id']})")
        
        # Get image details for this board
        if board.get('image_count', 0) > 0:
            img_response = requests.get(f"http://127.0.0.1:9090/api/v1/boards/{board['board_id']}/image_names")
            if img_response.status_code == 200:
                image_names = img_response.json()
                print(f"  First 3 images: {image_names[:3]}")