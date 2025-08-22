# Image Operations

Learn how to upload, download, and manage images with the InvokeAI Python Client.

## Overview

Image operations are essential for:
- **Image-to-Image workflows**: Upload source images
- **Result retrieval**: Download generated images
- **Asset management**: Organize and manage image libraries
- **Batch processing**: Handle multiple images efficiently

## Uploading Images

### Upload to Board

```python
# Get board handle
board = client.board_repo.get_board_handle("my_board")

# Upload from file
image_name = board.upload_image_file("source.png")
print(f"Uploaded: {image_name}")

# Upload from bytes
with open("image.jpg", "rb") as f:
    image_data = f.read()
    image_name = board.upload_image_data(image_data, "custom_name.jpg")
```

### Upload from PIL Image

```python
from PIL import Image
import io

# Create or load PIL image
pil_image = Image.open("source.png")

# Convert to bytes
buffer = io.BytesIO()
pil_image.save(buffer, format="PNG")
image_bytes = buffer.getvalue()

# Upload
board = client.board_repo.get_board_handle("inputs")
image_name = board.upload_image_data(image_bytes, "pil_image.png")
```

### Upload from URL

```python
import requests

def upload_from_url(board, image_url, name=None):
    """Download and upload image from URL."""
    response = requests.get(image_url)
    response.raise_for_status()
    
    if not name:
        name = image_url.split("/")[-1]
    
    return board.upload_image_data(response.content, name)

# Use it
board = client.board_repo.get_board_handle("downloads")
image_name = upload_from_url(board, "https://example.com/image.jpg")
```

## Downloading Images

### Download Single Image

```python
# Get board and download
board = client.board_repo.get_board_handle("outputs")
image_data = board.download_image("image_name.png", full_resolution=True)

# Save to file
with open("downloaded.png", "wb") as f:
    f.write(image_data)
```

### Download to PIL

```python
from PIL import Image
import io

def download_as_pil(board, image_name):
    """Download image as PIL Image object."""
    image_data = board.download_image(image_name, full_resolution=True)
    return Image.open(io.BytesIO(image_data))

# Use it
pil_image = download_as_pil(board, "result.png")
pil_image.show()  # Display
```

### Batch Download

```python
def download_all_images(board, output_dir="downloads"):
    """Download all images from a board."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    image_names = board.list_images()
    
    for i, name in enumerate(image_names):
        print(f"Downloading {i+1}/{len(image_names)}: {name}")
        
        image_data = board.download_image(name, full_resolution=True)
        output_path = os.path.join(output_dir, name)
        
        with open(output_path, "wb") as f:
            f.write(image_data)
    
    print(f"Downloaded {len(image_names)} images to {output_dir}")

# Download entire board
board = client.board_repo.get_board_handle("my_outputs")
download_all_images(board)
```

## Image Metadata

### Get Image Info

```python
# Get image metadata
def get_image_metadata(client, image_name):
    """Get detailed image metadata."""
    # This would use the REST API directly
    response = client._make_request("GET", f"/images/i/{image_name}/metadata")
    return response.json()

# Get info
metadata = get_image_metadata(client, "image_abc123.png")
print(f"Width: {metadata.get('width')}")
print(f"Height: {metadata.get('height')}")
print(f"Created: {metadata.get('created_at')}")
```

### Image DTOs

```python
def get_image_dtos(client, image_names):
    """Get image data transfer objects."""
    response = client._make_request(
        "POST",
        "/images/images_by_names",
        json={"image_names": image_names}
    )
    return response.json()

# Get DTOs for multiple images
dtos = get_image_dtos(client, ["img1.png", "img2.png"])
for dto in dtos:
    print(f"{dto['image_name']}: {dto['width']}x{dto['height']}")
```

## Image Management

### List Board Images

```python
# Get all images in a board
board = client.board_repo.get_board_handle("my_board")
images = board.list_images()

print(f"Board contains {len(images)} images:")
for img in images[:10]:  # First 10
    print(f"  - {img}")
```

### Move Images Between Boards

```python
def move_image(client, image_name, from_board_id, to_board_id):
    """Move image from one board to another."""
    # This would use the REST API
    response = client._make_request(
        "POST",
        f"/images/i/{image_name}/board",
        json={"board_id": to_board_id}
    )
    return response.ok

# Move image
success = move_image(
    client,
    "image.png",
    from_board_id="source_board",
    to_board_id="dest_board"
)
```

### Delete Images

```python
def delete_image(client, image_name):
    """Delete an image."""
    response = client._make_request(
        "DELETE",
        f"/images/i/{image_name}"
    )
    return response.ok

# Delete single image
deleted = delete_image(client, "unwanted.png")

# Delete multiple
def delete_images(client, image_names):
    """Delete multiple images."""
    deleted_count = 0
    for name in image_names:
        if delete_image(client, name):
            deleted_count += 1
    return deleted_count
```

## Image Processing

### Resize Before Upload

```python
from PIL import Image

def resize_and_upload(board, image_path, max_size=(1024, 1024)):
    """Resize image before uploading."""
    # Open and resize
    img = Image.open(image_path)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    
    # Upload
    filename = os.path.basename(image_path)
    return board.upload_image_data(buffer.getvalue(), filename)
```

### Image Format Conversion

```python
def convert_and_upload(board, image_path, output_format="PNG"):
    """Convert image format before upload."""
    img = Image.open(image_path)
    
    # Convert RGBA to RGB if needed
    if output_format == "JPEG" and img.mode == "RGBA":
        # Create white background
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])  # Use alpha as mask
        img = bg
    
    # Save in new format
    buffer = io.BytesIO()
    img.save(buffer, format=output_format)
    
    # Upload with new extension
    name = os.path.splitext(os.path.basename(image_path))[0]
    name = f"{name}.{output_format.lower()}"
    
    return board.upload_image_data(buffer.getvalue(), name)
```

## Workflow Integration

### Image-to-Image Setup

```python
def setup_img2img(wf, source_image_path, board_name="inputs"):
    """Set up image-to-image workflow."""
    # Upload source image
    board = client.board_repo.get_board_handle(board_name)
    image_name = board.upload_image_file(source_image_path)
    
    # Find image field in workflow
    for inp in wf.list_inputs():
        if inp.field_name == "image":
            # Set the image reference
            field = wf.get_input_value(inp.input_index)
            if hasattr(field, 'value'):
                field.value = image_name
                print(f"Set image input: {image_name}")
                return True
    
    print("No image input found in workflow")
    return False

# Use it
setup_img2img(wf, "source.png")
```

### Batch Image Processing

```python
def process_image_batch(client, wf, image_paths, output_board="results"):
    """Process multiple images through workflow."""
    results = []
    
    # Get boards
    input_board = client.board_repo.get_board_handle("batch_inputs")
    output_board_id = output_board
    
    for i, path in enumerate(image_paths):
        print(f"Processing {i+1}/{len(image_paths)}: {path}")
        
        # Upload source
        image_name = input_board.upload_image_file(path)
        
        # Set in workflow
        wf.get_input_value(IMAGE_IDX).value = image_name
        wf.get_input_value(BOARD_IDX).value = output_board_id
        
        # Submit and wait
        submission = wf.submit_sync()
        result = wf.wait_for_completion_sync(submission)
        
        # Map outputs
        mappings = wf.map_outputs_to_images(result)
        results.append({
            'source': path,
            'outputs': mappings
        })
    
    return results
```

## Performance Optimization

### Parallel Upload

```python
import concurrent.futures

def parallel_upload(board, image_paths, max_workers=4):
    """Upload multiple images in parallel."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(board.upload_image_file, path): path
            for path in image_paths
        }
        
        results = {}
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
            try:
                image_name = future.result()
                results[path] = image_name
                print(f" Uploaded: {path} -> {image_name}")
            except Exception as e:
                print(f" Failed: {path} - {e}")
                results[path] = None
        
        return results
```

### Image Caching

```python
class ImageCache:
    """Cache downloaded images to avoid re-downloading."""
    
    def __init__(self, cache_dir="image_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_path(self, image_name):
        return os.path.join(self.cache_dir, image_name)
    
    def has(self, image_name):
        return os.path.exists(self.get_cache_path(image_name))
    
    def get(self, board, image_name, force_download=False):
        cache_path = self.get_cache_path(image_name)
        
        if not force_download and self.has(image_name):
            with open(cache_path, "rb") as f:
                return f.read()
        
        # Download and cache
        image_data = board.download_image(image_name, full_resolution=True)
        with open(cache_path, "wb") as f:
            f.write(image_data)
        
        return image_data

# Use cache
cache = ImageCache()
board = client.board_repo.get_board_handle("outputs")

# First access downloads
data1 = cache.get(board, "image.png")

# Second access uses cache
data2 = cache.get(board, "image.png")
```

## Error Handling

### Upload Errors

```python
def safe_upload(board, image_path, max_retries=3):
    """Upload with retry logic."""
    for attempt in range(max_retries):
        try:
            return board.upload_image_file(image_path)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                raise
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Download Errors

```python
def safe_download(board, image_name):
    """Download with error handling."""
    try:
        return board.download_image(image_name, full_resolution=True)
    except FileNotFoundError:
        print(f"Image not found: {image_name}")
        return None
    except PermissionError:
        print(f"No permission to download: {image_name}")
        return None
    except Exception as e:
        print(f"Download error: {e}")
        return None
```

## Best Practices

### 1. Clean Up Temporary Images

```python
# Track uploaded images
uploaded_images = []

try:
    # Upload and process
    for path in image_paths:
        name = board.upload_image_file(path)
        uploaded_images.append(name)
        # Process...
finally:
    # Clean up
    for name in uploaded_images:
        try:
            delete_image(client, name)
        except:
            pass
```

### 2. Use Appropriate Resolution

```python
# Download thumbnails for preview
thumbnail = board.download_image(name, full_resolution=False)

# Download full for processing
full_image = board.download_image(name, full_resolution=True)
```

### 3. Validate Before Upload

```python
def validate_image(path):
    """Validate image before upload."""
    try:
        img = Image.open(path)
        img.verify()
        
        # Check size
        if img.size[0] > 4096 or img.size[1] > 4096:
            raise ValueError("Image too large")
        
        # Check format
        if img.format not in ['PNG', 'JPEG', 'WEBP']:
            raise ValueError(f"Unsupported format: {img.format}")
        
        return True
    except Exception as e:
        print(f"Invalid image: {e}")
        return False
```

## Next Steps

- Learn about [Model Management](models.md)
- Explore [Execution Modes](execution-modes.md)
- Master [Output Mapping](output-mapping.md)
- Review [Board Management](boards.md)